import os
from datetime import datetime,timedelta,timezone,time
from uuid import uuid4
import pytest
from test_database_flows import db_app,one
pytestmark=pytest.mark.skipif(not os.environ.get('TEST_DATABASE_URL'),reason='Requires isolated PostgreSQL')

def setup(c,db):
    body=dict(title='Exam',topics=['A','B'],daily_minutes=30,timezone='UTC',confirmed=True,
              exam_date=(datetime.now(timezone.utc)+timedelta(days=20)).date().isoformat(),client_id=str(uuid4()))
    body['preview_token']=c.post('/api/exam-plans/preview',json=body).json['plan']['preview_token']
    pid=c.post('/api/exam-plans',json=body).json['id']
    with db() as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE tasks SET due_at=NOW()-INTERVAL '2 days' WHERE user_id=1")
    return '/api/exam-plans/'+str(pid)+'/replan/'

def test_owned_confirmed_atomic_and_retry_safe(db_app):
    _,c,db=db_app;url=setup(c,db)
    assert c.post(url+'preview',json={}).status_code==400
    with c.session_transaction() as s:s['user_id']=2
    assert c.post(url+'preview',json={'confirmed':True}).status_code==404
    with c.session_transaction() as s:s['user_id']=1
    p=c.post(url+'preview',json={'confirmed':True}).json['plan']
    assert len(p['items'])==6
    payload={'confirmed':True,'preview_token':p['preview_token']}
    assert c.post(url+'apply',json=payload).json['moved']==6
    assert c.post(url+'apply',json=payload).json['replayed']
    assert one(db,'SELECT COUNT(*) n FROM tasks')['n']==6
    assert one(db,'SELECT COUNT(*) n FROM tasks WHERE due_at>NOW()')['n']==6

def test_progress_between_preview_and_apply_is_never_overwritten(db_app):
    _,c,db=db_app;url=setup(c,db)
    p=c.post(url+'preview',json={'confirmed':True}).json['plan']
    tid=p['items'][0]['id']
    with db() as conn:
        with conn.cursor() as cur:cur.execute('UPDATE tasks SET completed=TRUE,updated_at=NOW() WHERE id=%s',(tid,))
    assert c.post(url+'apply',json={'confirmed':True,'preview_token':p['preview_token']}).status_code==409
    assert one(db,'SELECT COUNT(*) n FROM tasks WHERE due_at>NOW()')['n']==0
    again=c.post(url+'preview',json={'confirmed':True}).json['plan']
    assert len(again['items'])==5


def test_other_exam_plans_reserve_time_and_invalidate_stale_preview(db_app):
    _, c, db = db_app
    first = setup(c, db)
    second = setup(c, db)
    second_id = int(second.split('/')[3])
    now = datetime.now(timezone.utc)
    start = now.date()+timedelta(days=int(now.hour >= 18))
    reserved = set()
    with db() as conn:
        with conn.cursor() as cur:
            cur.execute('SELECT task_id FROM exam_plan_tasks WHERE plan_id=%s ORDER BY task_id', (second_id,))
            ids = [r['task_id'] for r in cur.fetchall()]
            for index, tid in enumerate(ids):
                due = datetime.combine(start+timedelta(days=index), time(18), timezone.utc)
                reserved.add(due.date().isoformat())
                cur.execute('UPDATE tasks SET due_at=%s WHERE id=%s', (due, tid))
    response = c.post(first+'preview', json={'confirmed': True})
    assert response.status_code == 200
    p = response.json['plan']
    assert len(p['items']) == 6
    assert not {item['due_at'][:10] for item in p['items']} & reserved
    with db() as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE tasks SET due_at=due_at+INTERVAL '7 days',updated_at=NOW() WHERE id=%s", (ids[0],))
    assert c.post(first+'apply', json={'confirmed': True, 'preview_token': p['preview_token']}).status_code == 409


def test_date_change_is_previewed_confirmed_atomic_and_preserves_manual_work(db_app):
    _, c, db = db_app
    url = setup(c, db)
    pid = int(url.split('/')[3])
    new_date = (datetime.now(timezone.utc)+timedelta(days=10)).date().isoformat()
    with db() as conn:
        with conn.cursor() as cur:
            cur.execute('SELECT task_id FROM exam_plan_tasks WHERE plan_id=%s ORDER BY task_id', (pid,))
            ids = [row['task_id'] for row in cur.fetchall()]
            cur.execute("UPDATE tasks SET due_at=NOW()+INTERVAL '15 days' WHERE id=%s", (ids[0],))
            cur.execute("UPDATE tasks SET due_at=NOW()+INTERVAL '18 days',updated_at=NOW() WHERE id=%s", (ids[1],))
            cur.execute('UPDATE tasks SET completed=TRUE WHERE id=%s', (ids[2],))
    assert c.post(url+'preview', json={'confirmed': True, 'exam_date': None}).status_code == 400
    p = c.post(url+'preview', json={'confirmed': True, 'exam_date': new_date}).json['plan']
    assert p['date_changed'] and p['outside_window'] == 1
    assert ids[0] in [item['id'] for item in p['items']]
    assert ids[1] in p['preserved'] and ids[2] not in [item['id'] for item in p['items']]
    assert str(one(db, 'SELECT exam_date FROM exam_plans WHERE id=%s', (pid,))['exam_date']) != new_date
    payload = {'confirmed': True, 'exam_date': new_date, 'preview_token': p['preview_token']}
    assert c.post(url+'apply', json=payload).json['moved'] == 4
    assert c.post(url+'apply', json=payload).json['replayed']
    assert str(one(db, 'SELECT exam_date FROM exam_plans WHERE id=%s', (pid,))['exam_date']) == new_date
    assert one(db, 'SELECT COUNT(*) n FROM tasks')['n'] == 6


def test_intervening_exam_date_change_rejects_old_preview(db_app):
    _, c, db = db_app
    url = setup(c, db)
    pid = int(url.split('/')[3])
    target = (datetime.now(timezone.utc)+timedelta(days=10)).date().isoformat()
    p = c.post(url+'preview', json={'confirmed': True, 'exam_date': target}).json['plan']
    with db() as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE exam_plans SET exam_date=exam_date+1 WHERE id=%s", (pid,))
    assert c.post(url+'apply', json={'confirmed': True, 'exam_date': target, 'preview_token': p['preview_token']}).status_code == 409
