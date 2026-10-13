import json
import os
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timedelta,timezone
from uuid import uuid4
import pytest
from test_database_flows import db_app,one,questions

pytestmark=pytest.mark.skipif(not os.environ.get('TEST_DATABASE_URL'),reason='Requires isolated PostgreSQL')


def send(client,cid,text,stream=True,key=None):
    path=f'/api/conversations/{cid}/messages'+('/stream' if stream else '')
    response=client.post(path,json=dict(content=text,mode='normal',request_id=key or str(uuid4())))
    if stream:
        events=[json.loads(line) for line in response.data.splitlines()]
        assert any(e['type']=='complete' for e in events),events
        return next(e['data'] for e in events if e['type']=='complete')
    assert response.status_code==200,response.json
    return response.json


@pytest.mark.parametrize('stream',[False,True])
def test_literal_note_and_clean_memory_do_not_call_a_model(db_app,monkeypatch,stream):
    b,c,connect=db_app
    def blocked(*args,**kwargs):raise AssertionError('Literal account commands must never call AI')
    monkeypatch.setattr(b,'provider_send',blocked);monkeypatch.setattr(b,'GEMINI_API_KEY','')
    cid=c.post('/api/conversations',json={}).json['conversation']['id']
    result=send(c,cid,'Save this as a private note titled Audit probability: Private formula',stream)
    assert result['assistant_message']['action_receipt']['kind']=='note'
    assert one(connect,'SELECT title,content FROM quick_notes')==dict(title='Audit probability',content='Private formula')
    send(c,cid,'Remember that my birthday is 1st January. Save this personal fact to memory.',stream)
    assert one(connect,'SELECT label,content FROM memories')==dict(label='Birthday',content='Birthday: 1 January')
    send(c,cid,'My birthday is 2nd January',stream)
    assert one(connect,'SELECT COUNT(*) AS n FROM memories')['n']==1


def test_reminder_requires_absolute_preview_and_confirmation_then_replays_safely(db_app,monkeypatch):
    b,c,connect=db_app
    monkeypatch.setattr(b,'provider_send',lambda *a,**k:(_ for _ in ()).throw(AssertionError('No AI')))
    cid=c.post('/api/conversations',json={}).json['conversation']['id']
    preview=send(c,cid,'Remind me tomorrow at 7 PM to revise probability')
    assert 'Asia/Kolkata' in preview['assistant_message']['content']
    assert one(connect,'SELECT COUNT(*) AS n FROM reminders')['n']==0
    result=send(c,cid,'Confirm reminder',key='audit-reminder-confirm')
    assert result['assistant_message']['action_resource']['scheduled'].endswith('Asia/Kolkata')
    send(c,cid,'Confirm reminder',key='audit-reminder-confirm')
    assert one(connect,'SELECT COUNT(*) AS n FROM reminders')['n']==1
    send(c,cid,'Change my revise probability reminder to tomorrow at 8 PM')
    send(c,cid,'Confirm reminder')
    assert one(connect,'SELECT EXTRACT(HOUR FROM next_run_at AT TIME ZONE %s) AS hour FROM reminders',('Asia/Kolkata',))['hour']==20


def test_expired_preview_cannot_create_an_alert(db_app):
    _,c,connect=db_app;cid=c.post('/api/conversations',json={}).json['conversation']['id']
    send(c,cid,'Remind me tomorrow at 7 PM to revise')
    with connect() as conn:
        with conn.cursor() as cur:cur.execute("UPDATE chat_action_previews SET expires_at=NOW()-INTERVAL '1 minute'")
    reply=send(c,cid,'Confirm reminder')
    assert 'expired' in reply['assistant_message']['content']
    assert one(connect,'SELECT COUNT(*) AS n FROM reminders')['n']==0


def test_today_defaults_to_india_and_counts_exam_days_in_the_account_date(db_app):
    _,c,connect=db_app
    assert c.get('/api/me').json['user']['timezone']=='Asia/Kolkata'
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO exam_plans(user_id,client_id,title,exam_date,timezone,daily_minutes,topics) VALUES(1,%s,'India exam',(NOW() AT TIME ZONE 'Asia/Kolkata')::date+2,'Asia/Kolkata',30,'[]')",(str(uuid4()),))
    assert c.get('/api/workspace/today').json['next_exam']['days_left']==2


def test_study_job_is_visible_during_creation_and_replay_never_regenerates(db_app,monkeypatch):
    b,c,connect=db_app;started=threading.Event();release=threading.Event();calls=[]
    def generate(*args):
        calls.append(True);started.set();assert release.wait(10);return questions()
    monkeypatch.setattr(b,'generate_study_json',generate)
    body=dict(job_id=str(uuid4()),topic='Probability',question_count=5,time_limit_minutes=5)
    def worker():
        client=b.app.test_client();client.environ_base['HTTP_X_CSRF_TOKEN']='worker'
        with client.session_transaction() as s:s.update(user_id=1,session_version=1,csrf_token='worker')
        return client.post('/api/mock-tests/generate',json=body)
    with ThreadPoolExecutor(max_workers=1) as pool:
        task=pool.submit(worker)
        try:
            assert started.wait(10)
            assert c.get('/api/study-jobs?kind=mock').json['jobs'][0]['status']=='creating'
            assert c.post('/api/mock-tests/generate',json=body).status_code==202
        finally:release.set()
        assert task.result(timeout=10).status_code==200
    job=c.get('/api/study-jobs?kind=mock').json['jobs'][0]
    assert job['status']=='ready' and job['result_id']
    assert c.post('/api/mock-tests/generate',json=body).status_code==202 and len(calls)==1
    with c.session_transaction() as s:s['user_id']=2
    assert c.get('/api/study-jobs?kind=mock').json['jobs']==[]
    assert c.post('/api/mock-tests/generate',json=body).status_code==404


def test_failed_job_keeps_inputs_and_can_retry_with_a_new_id(db_app,monkeypatch):
    b,c,_=db_app
    def busy(*args):raise RuntimeError('AI is busy. Retry when ready.')
    monkeypatch.setattr(b,'generate_study_json',busy)
    body=dict(job_id=str(uuid4()),topic='Probability',question_count=5,time_limit_minutes=5)
    assert c.post('/api/mock-tests/generate',json=body).status_code==503
    job=c.get('/api/study-jobs?kind=mock').json['jobs'][0]
    assert job['status']=='failed' and job['request']['topic']=='Probability'
    monkeypatch.setattr(b,'generate_study_json',lambda *a:questions())
    assert c.post('/api/mock-tests/generate',json=dict(body,job_id=str(uuid4()))).status_code==200
