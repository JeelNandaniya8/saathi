"""Saved-state truth, failed writes and quota boundaries against real PostgreSQL."""
import json
import os
from datetime import datetime,timedelta,timezone
from uuid import uuid4
from zoneinfo import ZoneInfo
import pytest
import chat_actions as actions
from test_database_flows import db_app,one,questions
from test_audit_reliability_database import send
from test_chat_control_database import seed,execute

pytestmark=pytest.mark.skipif(not os.environ.get('TEST_DATABASE_URL'),reason='Requires isolated PostgreSQL')


def map_data():
    return dict(summary='Probability concepts',root=dict(label='Probability',desc='Chance',color='#b38b42',children=[dict(label='Events',desc='Sets of outcomes',color='#b38b42',children=[])]))


@pytest.mark.parametrize('stream',[False,True])
def test_today_reads_only_owned_open_tasks_with_exact_local_deadlines(db_app,monkeypatch,stream):
    b,c,connect=db_app
    monkeypatch.setattr(b,'provider_send',lambda *a,**k:pytest.fail('Planner reads must not call AI'))
    monkeypatch.setattr(b,'GEMINI_API_KEY','')
    day=datetime.now(ZoneInfo('Asia/Kolkata')).replace(hour=17,minute=0,second=0,microsecond=0)
    with connect() as conn:
        with conn.cursor() as cur:
            for uid,title,due,done in [(1,'Probability revision',day,False),(1,'Chemistry recap',day-timedelta(hours=2),False),(1,'Read formulas',None,False),(1,'Future task',day+timedelta(days=1),False),(1,'Completed task',day,True),(2,'Other account task',day,False)]:
                cur.execute("INSERT INTO tasks(user_id,title,details,due_at,completed,priority,created_at,updated_at) VALUES(%s,%s,'',%s,%s,'medium',NOW(),NOW())",(uid,title,due,done))
    cid=c.post('/api/conversations',json={}).json['conversation']['id']
    text=send(c,cid,'What remains today?',stream)['assistant_message']['content']
    assert text.startswith('3 unfinished Planner tasks')
    for title in ['Probability revision','Chemistry recap','Read formulas']:assert text.count(title)==1
    assert '05:00 PM' in text and '03:00 PM' in text and 'Asia/Kolkata' in text
    assert all(title not in text for title in ['Future task','Completed task','Other account task'])
    with connect() as conn:
        with conn.cursor() as cur:cur.execute('UPDATE tasks SET completed=TRUE WHERE user_id=1')
    assert 'No saved Planner tasks' in send(c,cid,'What remains today?',stream)['assistant_message']['content']


@pytest.mark.parametrize('valid',[False,True])
def test_mindmap_claim_is_replaced_by_verified_save_or_persistent_failure(db_app,monkeypatch,valid):
    b,c,connect=db_app
    draft=dict(kind='mindmap',title='Probability',text='Study map',map=map_data() if valid else {'root':{'label':'Incomplete'}})
    def generate(*a,**k):
        yield 'Mindmap created and saved.\n<SAATHI_ACTION>'+json.dumps(draft)+'</SAATHI_ACTION>'
        return {}
    monkeypatch.setattr(b,'stream_gemini_reply',generate)
    cid=c.post('/api/conversations',json={}).json['conversation']['id']
    response=c.post(f'/api/conversations/{cid}/messages/stream',json=dict(content='Make a mindmap of probability',mode='normal',request_id=str(uuid4())))
    events=[json.loads(line) for line in response.data.splitlines()]
    assert not any(e['type']=='delta' and 'created and saved' in e.get('text','') for e in events)
    result=next(e['data']['assistant_message'] for e in events if e['type']=='complete')
    assert one(connect,'SELECT COUNT(*) AS n FROM mindmaps')['n']==int(valid)
    stored=c.get(f'/api/conversations/{cid}/messages').json['messages'][-1]
    if valid:
        rid=result['action_receipt']['resource_id']
        assert c.get('/api/mindmaps/'+str(rid)).json['mindmap']['data']['root']['label']=='Probability'
        history=c.get('/api/mindmaps/history')
        assert history.status_code==200,history.json
        assert history.json['mindmaps'][0]['id']==rid
        assert stored['content'].startswith('Mindmap created and saved.')
    else:
        assert result['content'].startswith('Failed:') and 'created and saved' not in result['content']
        assert stored['action_error'] and 'Retry' in stored['content']


def test_failed_save_readback_rolls_back_record_and_success_claim(db_app,monkeypatch):
    _,c,connect=db_app
    monkeypatch.setattr(actions,'receipt_resource',lambda *a:None)
    cid=c.post('/api/conversations',json={}).json['conversation']['id']
    result=send(c,cid,'Save a note. Title: Readback test; Content: Private data')['assistant_message']
    assert result['content'].startswith('Failed:') and not result.get('action_receipt')
    assert one(connect,'SELECT COUNT(*) AS n FROM quick_notes')['n']==0
    assert one(connect,'SELECT COUNT(*) AS n FROM chat_action_receipts')['n']==0


def test_snooze_does_not_advance_future_or_reactivate_paused_reminders(db_app):
    _,c,connect=db_app;future=datetime.now(timezone.utc)+timedelta(days=1)
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO reminders(user_id,title,note,next_run_at,recurrence,created_at) VALUES(1,'Future revision','',%s,'once',NOW()) RETURNING id",(future,));rid=cur.fetchone()['id']
    assert c.patch('/api/reminders/'+str(rid),json=dict(action='snooze',minutes=30)).status_code==409
    draft=dict(kind='reminder',operation='snooze',title='Future revision',text='',target_title='Future revision',target_id=rid,expected_at=future.isoformat(),at=(datetime.now(timezone.utc)+timedelta(minutes=30)).isoformat())
    mid,_=seed(connect,'Snooze my Future revision reminder 30 minutes',draft)
    assert execute(c,mid).status_code==400
    assert one(connect,'SELECT next_run_at FROM reminders WHERE id=%s',(rid,))['next_run_at']==future
    with connect() as conn:
        with conn.cursor() as cur:cur.execute("UPDATE reminders SET next_run_at=NOW()-INTERVAL '1 minute',active=FALSE WHERE id=%s",(rid,))
    assert c.patch('/api/reminders/'+str(rid),json=dict(action='snooze',minutes=30)).status_code==409
    with connect() as conn:
        with conn.cursor() as cur:cur.execute('UPDATE reminders SET active=TRUE WHERE id=%s',(rid,))
    assert c.patch('/api/reminders/'+str(rid),json=dict(action='snooze',minutes=30)).status_code==200


def test_note_readback_is_exact_and_account_owned(db_app):
    _,c,connect=db_app
    cid=c.post('/api/conversations',json={}).json['conversation']['id']
    result=send(c,cid,'Save a note. Title: Exact note; Content: Private content')['assistant_message']
    rid=result['action_receipt']['resource_id']
    assert c.get('/api/quick-notes/'+str(rid)).json['note']['content']=='Private content'
    with c.session_transaction() as session:session['user_id']=2
    assert c.get('/api/quick-notes/'+str(rid)).status_code==404


@pytest.mark.parametrize('recurrence',['daily','weekly'])
@pytest.mark.parametrize('ack',[False,True])
def test_snooze_preserves_the_original_repeating_clock(db_app,recurrence,ack):
    _,c,connect=db_app;original=datetime.now(timezone.utc)-timedelta(minutes=5)
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO reminders(user_id,title,note,next_run_at,recurrence,created_at) VALUES(1,'Recurring revision','',%s,%s,NOW()) RETURNING id",(original,recurrence));rid=cur.fetchone()['id']
    path='/api/reminders/'+str(rid)
    assert c.patch(path,json=dict(action='snooze',minutes=30)).status_code==200
    assert one(connect,'SELECT snoozed_from FROM reminders WHERE id=%s',(rid,))['snoozed_from']==original
    # Simulate arrival of the snoozed occurrence without moving its repeat anchor.
    due=datetime.now(timezone.utc)-timedelta(seconds=1)
    with connect() as conn:
        with conn.cursor() as cur:cur.execute('UPDATE reminders SET next_run_at=%s WHERE id=%s',(due,rid))
    result=c.post(path+'/ack',json=dict(scheduled_at=due.isoformat())) if ack else c.patch(path,json=dict(action='complete'))
    assert result.status_code==200,result.json
    saved=one(connect,'SELECT next_run_at,snoozed_from FROM reminders WHERE id=%s',(rid,))
    assert saved['next_run_at']==original+timedelta(days=1 if recurrence=='daily' else 7)
    assert saved['snoozed_from'] is None


@pytest.mark.parametrize('kind',['mock','map'])
def test_quota_block_starts_no_generation_and_no_job(db_app,monkeypatch,kind):
    b,c,connect=db_app
    monkeypatch.setattr(b,'generate_study_json',lambda *a:pytest.fail('Quota must be checked before generation'))
    with connect() as conn:
        with conn.cursor() as cur:
            if kind=='mock':cur.execute("INSERT INTO mock_tests(user_id,topic,difficulty,question_count,time_limit_minutes,questions_json,created_at) VALUES(1,'Used allowance','easy',5,5,%s,NOW())",(json.dumps(questions()),))
            else:
                for _ in range(2):cur.execute("INSERT INTO mindmaps(user_id,topic,data_json,created_at) VALUES(1,'Used allowance',%s,NOW())",(json.dumps(map_data()),))
    endpoint='/api/mock-tests/generate' if kind=='mock' else '/api/mindmaps/generate'
    result=c.post(endpoint,json=dict(job_id=str(uuid4()),topic='Probability',question_count=5,time_limit_minutes=5))
    assert result.status_code==429,result.json
    assert result.json['allowance']['remaining']==0 and 'Asia/Kolkata' in result.json['allowance']['reset_local']
    assert one(connect,'SELECT COUNT(*) AS n FROM study_jobs')['n']==0
    assert c.get('/api/study-allowance?kind='+kind).json['allowance']['remaining']==0
