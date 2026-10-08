from datetime import date, datetime, timedelta, timezone
import exam_replanning as er

NOW = datetime(2026,10,8,8,tzinfo=timezone.utc)

def plan(**kw):
    return dict(id=1, exam_date=date(2026,10,12),timezone='UTC',daily_minutes=30,**kw)

def task(i, **kw):
    row=dict(id=i,title='Study',details='',completed=False,due_at=NOW-timedelta(days=2),
             created_at=NOW-timedelta(days=10),updated_at=NOW-timedelta(days=10),last_replanned_at=None)
    return {**row,**kw}

def test_preserve_completed_manual_and_future_blocks_and_rest_day():
    rows=[task(1),task(2,completed=True),task(3,updated_at=NOW),
          task(4,due_at=datetime(2026,10,8,18,tzinfo=timezone.utc))]
    p=er.preview(plan(),rows,NOW)
    assert [i['id'] for i in p['items']]==[1]
    assert p['items'][0]['due_at'].startswith('2026-10-09')
    assert p['preserved']==[3] and p['unscheduled']==0
    assert p['rest_date']=='2026-10-11'

def test_budget_and_shortfall_are_explicit():
    p=er.preview(plan(),[task(i) for i in range(8)],NOW)
    assert len(p['items'])==3 and p['unscheduled']==5
    assert len({i['due_at'] for i in p['items']})==3

def test_snapshot_changes_with_progress_or_manual_edits():
    original=er.preview(plan(),[task(1)],NOW)['preview_token']
    for row in [task(1,completed=True),task(1,title='Changed'),task(1,updated_at=NOW)]:
        assert er.preview(plan(),[row],NOW)['preview_token']!=original

def test_evening_and_expired_exam_never_create_past_or_exam_day_tasks():
    evening=NOW.replace(hour=19)
    p=er.preview(plan(),[task(1)],evening)
    assert p['items'][0]['due_at'].startswith('2026-10-09')
    p=er.preview(plan(),[task(1)],NOW+timedelta(days=8))
    assert p['items']==[] and p['unscheduled']==1

def test_previous_replan_can_move_again_but_later_manual_edits_cannot():
    assert len(er.preview(plan(),[task(1,updated_at=NOW,last_replanned_at=NOW)],NOW)['items'])==1
    assert not er.preview(plan(),[task(1,updated_at=NOW,last_replanned_at=NOW-timedelta(seconds=1))],NOW)['items']


def test_other_plans_reserve_capacity_in_target_timezone():
    other = [task(99, due_at=NOW.replace(hour=18), plan_daily_minutes=20)]
    p = er.preview(plan(), [task(1)], NOW, other_tasks=other)
    assert p['items'][0]['due_at'].startswith('2026-10-09')
    assert other[0]['due_at'] == NOW.replace(hour=18)
    changed = [{**other[0], 'due_at': NOW.replace(hour=18)+timedelta(days=1)}]
    assert er.preview(plan(), [task(1)], NOW, other_tasks=changed)['preview_token'] != p['preview_token']


def test_other_plans_can_exhaust_capacity_without_duplicate_or_overbudget_work():
    others = [task(99+i, due_at=NOW.replace(hour=18)+timedelta(days=i), plan_daily_minutes=30) for i in range(3)]
    p = er.preview(plan(), [task(1)], NOW, other_tasks=others)
    assert p['items'] == [] and p['unscheduled'] == 1
    others[0]['completed'] = True
    assert er.preview(plan(), [task(1)], NOW, other_tasks=others)['unscheduled'] == 1
