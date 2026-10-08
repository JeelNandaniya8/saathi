"""Preview-only until confirmed; reschedule existing overdue study blocks without AI."""
import hashlib
import json
import math
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo
from flask import jsonify, request


def preview(plan, tasks, now=None, other_tasks=None, new_exam_date=None):
    other_tasks = other_tasks or []
    now = now or datetime.now(timezone.utc)
    zone = ZoneInfo(plan['timezone'])
    local = now.astimezone(zone)
    start = local.date() + timedelta(days=int(local.hour >= 18))
    original_date = plan['exam_date']
    changed_date = new_exam_date is not None and new_exam_date != original_date
    if changed_date:
        if not 2 <= (new_exam_date-local.date()).days <= 365:
            raise ValueError('Choose a confirmed exam date 2–365 days from today.')
        plan = {**plan, 'exam_date': new_exam_date}
    rest = plan['exam_date'] - timedelta(days=1)
    block = min(25, plan['daily_minutes'])
    capacity = max(1, (plan['daily_minutes']+5)//(block+5))
    candidates, preserved, occupied = [], [], {}
    for task in tasks:
        if not task['due_at']:
            continue
        due = task['due_at'].astimezone(zone).date()
        if task['completed']:
            if due >= start:
                occupied[due] = occupied.get(due, 0)+1
            continue
        untouched = task['updated_at'] in (task['created_at'], task.get('last_replanned_at'))
        if untouched and (changed_date or task['due_at'] < now):
            candidates.append(task)
        else:
            if task['due_at'] < now or (changed_date and not untouched):
                preserved.append(task['id'])
            if due >= start:
                occupied[due] = occupied.get(due, 0)+1
    # Reserve estimated study time from the user's other exam plans as well.
    # General Planner tasks have no duration, so they still require manual review.
    reserved = {}
    for task in other_tasks:
        if task['due_at']:
            day = task['due_at'].astimezone(zone).date()
            if day >= start:
                minutes = min(25, task['plan_daily_minutes']) + 5
                reserved[day] = reserved.get(day, 0) + minutes
    for day, minutes in reserved.items():
        occupied[day] = occupied.get(day, 0) + math.ceil(minutes / (block + 5))
    candidates.sort(key=lambda t: (t['due_at'], t['id']))
    slots = []
    for offset in range(max(0, min(365, (rest-start).days))):
        day = start+timedelta(days=offset)
        slots.extend([day]*max(0, capacity-occupied.get(day, 0)))
    items = [{'id': t['id'], 'title': t['title'], 'from': t['due_at'].isoformat(),
              'due_at': datetime.combine(day, time(18), zone).isoformat()}
             for t, day in zip(candidates, slots)]
    result = {'items': items, 'preserved': preserved,
              'unscheduled': len(candidates)-len(items), 'rest_date': rest.isoformat(),
              'exam_date': plan['exam_date'].isoformat(), 'date_changed': changed_date,
              'outside_window': sum(not t['completed'] and t['id'] in preserved
                  and t['due_at'].astimezone(zone).date() >= rest for t in tasks if t['due_at'])}
    # Include every linked task, including completed/manual/future work: any change
    # between preview and apply must be reviewed again.
    snapshot = {'plan': {k: plan[k] for k in ('id','exam_date','timezone','daily_minutes')},
                'original_exam_date': original_date, 'tasks': tasks, 'other_tasks': other_tasks, 'result': result, 'start': start}
    result['preview_token'] = hashlib.sha256(json.dumps(snapshot, sort_keys=True, default=str).encode()).hexdigest()
    return result


def register(app, db, private):
    @app.post('/api/exam-plans/<int:plan_id>/replan/<action>')
    @private
    def replan(uid, plan_id, action):
        if action not in ('preview', 'apply'):
            return jsonify(error='Action not found.'), 404
        data = request.get_json(silent=True)
        if not isinstance(data, dict) or data.get('confirmed') is not True:
            raise ValueError('Review your progress in Planner and confirm before replanning.')
        with db() as (conn, cur):
            cur.execute('SELECT * FROM exam_plans WHERE id=%s AND user_id=%s FOR UPDATE', (plan_id, uid))
            plan = cur.fetchone()
            if not plan:
                return jsonify(error='Plan not found.'), 404
            token = data.get('preview_token')
            if action == 'apply' and isinstance(token, str) and token == plan['last_replan_token']:
                return jsonify(ok=True, replayed=True)
            # Lock study tasks in one stable order for simultaneous cross-plan replans.
            cur.execute('''SELECT t.id,t.title,t.details,t.due_at,t.completed,t.created_at,t.updated_at,
                e.last_replanned_at,e.plan_id,p.daily_minutes AS plan_daily_minutes
                FROM exam_plan_tasks e JOIN tasks t ON t.id=e.task_id
                JOIN exam_plans p ON p.id=e.plan_id
                WHERE t.user_id=%s AND p.user_id=%s ORDER BY t.id FOR UPDATE OF t,e''', (uid, uid))
            rows = cur.fetchall()
            new_date = None
            if 'exam_date' in data:
                try:
                    value = data['exam_date']
                    if not isinstance(value, str) or len(value) != 10:
                        raise ValueError()
                    new_date = date.fromisoformat(value)
                except ValueError:
                    raise ValueError('Choose a valid confirmed exam date.')
            result = preview(plan, [t for t in rows if t['plan_id'] == plan_id],
                             other_tasks=[t for t in rows if t['plan_id'] != plan_id],
                             new_exam_date=new_date)
            if action == 'preview':
                return jsonify(plan=result)
            if token != result['preview_token']:
                return jsonify(error='Progress or dates changed. Preview again before saving.'), 409
            for item in result['items']:
                cur.execute('UPDATE tasks SET due_at=%s,updated_at=NOW() WHERE id=%s AND user_id=%s RETURNING updated_at', (item['due_at'],item['id'],uid))
                stamp = cur.fetchone()['updated_at']
                cur.execute('UPDATE exam_plan_tasks SET last_replanned_at=%s WHERE plan_id=%s AND task_id=%s', (stamp,plan_id,item['id']))
            cur.execute('UPDATE exam_plans SET last_replan_token=%s,exam_date=%s WHERE id=%s', (token,result['exam_date'],plan_id))
            conn.commit()
        return jsonify(ok=True, moved=len(result['items']))
