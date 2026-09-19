"""Small owned queries and a server-clock focus timer; no AI requests."""
from contextlib import contextmanager
from datetime import datetime, time, timedelta, timezone
from functools import wraps
from uuid import UUID
from zoneinfo import ZoneInfo

from flask import jsonify, request


def focus_elapsed(row, now):
    elapsed = row['elapsed_seconds']
    if row['status'] == 'running' and row['last_started_at']:
        elapsed += max(0, int((now - row['last_started_at']).total_seconds()))
    return min(row['duration_seconds'], elapsed)


def search_pattern(value):
    query = value.strip()
    if not 2 <= len(query) <= 100:
        raise ValueError('Search using 2 to 100 characters.')
    return '%' + query.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_') + '%'


def register(app, b):
    @contextmanager
    def db():
        conn = b['get_db']()
        try:
            with conn.cursor() as cur:
                yield conn, cur
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def private(fn):
        @wraps(fn)
        def wrapped(*args, **kwargs):
            uid = b['require_user_id']()
            if not uid:
                return jsonify(error='Please log in first.'), 401
            try:
                return fn(uid, *args, **kwargs)
            except (ValueError, TypeError):
                return jsonify(error='Check the search or focus session settings.'), 400
        return wrapped

    @app.get('/api/workspace/search')
    @private
    def search(uid):
        pattern = search_pattern(request.args.get('q', ''))
        with db() as (_, cur):
            cur.execute('''SELECT * FROM (
                (SELECT 'conversation' AS kind,c.id,c.title,
                    COALESCE((SELECT LEFT(m.content,160) FROM messages m WHERE m.conversation_id=c.id
                        AND m.user_id=%s AND m.content ILIKE %s ORDER BY m.id DESC LIMIT 1),'') AS excerpt,c.updated_at
                    FROM conversations c WHERE c.user_id=%s AND (c.title ILIKE %s OR EXISTS(
                        SELECT 1 FROM messages m WHERE m.conversation_id=c.id AND m.user_id=%s AND m.content ILIKE %s))
                    ORDER BY c.updated_at DESC LIMIT 6)
                UNION ALL
                (SELECT 'note',id,title,LEFT(content,160),updated_at FROM quick_notes
                    WHERE user_id=%s AND (title ILIKE %s OR content ILIKE %s) ORDER BY updated_at DESC LIMIT 6)
                UNION ALL
                (SELECT 'task',id,title,LEFT(details,160),updated_at FROM tasks
                    WHERE user_id=%s AND (title ILIKE %s OR details ILIKE %s) ORDER BY updated_at DESC LIMIT 6)
                ) found ORDER BY updated_at DESC LIMIT 18''',
                (uid, pattern, uid, pattern, uid, pattern, uid, pattern, pattern, uid, pattern, pattern))
            items = [{**dict(row), 'updated_at': row['updated_at'].isoformat()} for row in cur.fetchall()]
        return jsonify(items=items)

    @app.get('/api/workspace/today')
    @private
    def today(uid):
        now = datetime.now(timezone.utc)
        with db() as (_, cur):
            cur.execute('SELECT timezone FROM workspace_preferences WHERE user_id=%s', (uid,))
            pref = cur.fetchone()
            zone = ZoneInfo(pref['timezone'] if pref else 'UTC')
            tomorrow = datetime.combine(now.astimezone(zone).date() + timedelta(days=1), time.min, zone)
            cur.execute('''SELECT * FROM tasks WHERE user_id=%s AND completed=FALSE AND (due_at IS NULL OR due_at<%s)
                ORDER BY CASE WHEN due_at<%s THEN 0 ELSE 1 END,
                    CASE priority WHEN 'high' THEN 0 WHEN 'medium' THEN 1 ELSE 2 END,
                    due_at NULLS LAST,id LIMIT 3''', (uid, tomorrow, now))
            tasks = [b['task_to_dict'](row) for row in cur.fetchall()]
            cur.execute('SELECT COUNT(*) AS n FROM revision_items WHERE user_id=%s AND paused=FALSE AND next_review_at<=%s', (uid, now))
            due = cur.fetchone()['n']
            cur.execute('''SELECT id,title FROM conversations c WHERE user_id=%s AND is_archived=FALSE
                AND EXISTS(SELECT 1 FROM messages m WHERE m.conversation_id=c.id AND m.user_id=%s)
                ORDER BY updated_at DESC LIMIT 1''', (uid, uid))
            recent = cur.fetchone()
        return jsonify(tasks=tasks, revision_due=due, recent_chat=dict(recent) if recent else None)

    def settle(cur, row, now):
        if row and row['status'] == 'running' and focus_elapsed(row, now) >= row['duration_seconds']:
            cur.execute("""UPDATE focus_sessions SET status='completed',elapsed_seconds=duration_seconds,
                last_started_at=NULL,version=version+1 WHERE id=%s RETURNING *""", (row['id'],))
            return cur.fetchone()
        return row

    def serialized(row, now):
        if not row:
            return None
        return {'id': row['id'], 'task_id': row['task_id'], 'status': row['status'], 'version': row['version'],
                'duration_seconds': row['duration_seconds'], 'remaining_seconds': row['duration_seconds'] - focus_elapsed(row, now)}

    @app.route('/api/focus', methods=['GET', 'POST'])
    @private
    def focus(uid):
        now = datetime.now(timezone.utc)
        data = request.get_json(silent=True) or {}
        if not isinstance(data, dict):
            raise ValueError()
        with db() as (conn, cur):
            # Serialize starts and transitions per account, including across tabs.
            cur.execute('SELECT pg_advisory_xact_lock(82,%s)', (uid,))
            cur.execute('SELECT * FROM focus_sessions WHERE user_id=%s ORDER BY id DESC LIMIT 1 FOR UPDATE', (uid,))
            row = settle(cur, cur.fetchone(), now)
            if request.method == 'POST':
                client_id = str(UUID(str(data.get('client_id', ''))))
                minutes, task = data.get('minutes'), data.get('task_id')
                if type(minutes) is not int or minutes not in (25, 50) or (task is not None and type(task) is not int):
                    raise ValueError()
                cur.execute('SELECT * FROM focus_sessions WHERE user_id=%s AND client_id=%s', (uid, client_id))
                existing = cur.fetchone()
                if existing:
                    conn.commit()
                    return jsonify(session=serialized(existing, now))
                if row and row['status'] in ('running', 'paused'):
                    conn.commit()
                    return jsonify(error='Finish the current focus session first.', session=serialized(row, now)), 409
                if task is not None:
                    cur.execute('SELECT id FROM tasks WHERE id=%s AND user_id=%s AND completed=FALSE', (task, uid))
                    if not cur.fetchone():
                        return jsonify(error='Choose an open task from your planner.'), 404
                cur.execute('''INSERT INTO focus_sessions(user_id,task_id,client_id,duration_seconds,status,last_started_at)
                    VALUES(%s,%s,%s,%s,'running',%s) RETURNING *''', (uid, task, client_id, minutes * 60, now))
                row = cur.fetchone()
                cur.execute('''DELETE FROM focus_sessions WHERE user_id=%s AND status NOT IN ('running','paused')
                    AND id NOT IN (SELECT id FROM focus_sessions WHERE user_id=%s ORDER BY id DESC LIMIT 100)''', (uid, uid))
            conn.commit()
        return jsonify(session=serialized(row, now))

    @app.patch('/api/focus/<int:session_id>')
    @private
    def change_focus(uid, session_id):
        data = request.get_json(silent=True)
        if not isinstance(data, dict) or data.get('action') not in ('pause', 'resume', 'end') or type(data.get('version')) is not int:
            raise ValueError()
        now = datetime.now(timezone.utc)
        with db() as (conn, cur):
            cur.execute('SELECT pg_advisory_xact_lock(82,%s)', (uid,))
            cur.execute('SELECT * FROM focus_sessions WHERE id=%s AND user_id=%s FOR UPDATE', (session_id, uid))
            row = cur.fetchone()
            if not row:
                return jsonify(error='Focus session not found.'), 404
            if row['version'] != data['version']:
                return jsonify(error='This session changed in another tab. Refresh it before continuing.'), 409
            elapsed = focus_elapsed(row, now)
            action = data['action']
            if row['status'] in ('completed', 'cancelled'):
                return jsonify(session=serialized(row, now))
            if (action == 'pause' and row['status'] != 'running') or (action == 'resume' and row['status'] != 'paused'):
                return jsonify(error='Refresh the focus session before continuing.'), 409
            status = 'completed' if elapsed == row['duration_seconds'] else {'pause': 'paused', 'resume': 'running', 'end': 'cancelled'}[action]
            cur.execute('''UPDATE focus_sessions SET status=%s,elapsed_seconds=%s,last_started_at=%s,version=version+1
                WHERE id=%s RETURNING *''', (status, elapsed, now if status == 'running' else None, session_id))
            row = cur.fetchone()
            conn.commit()
        return jsonify(session=serialized(row, now))
