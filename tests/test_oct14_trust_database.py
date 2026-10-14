"""Local action stages, current policy, exact receipts and due-only snooze."""
import json
import os
from datetime import datetime,timedelta,timezone
from uuid import uuid4
import pytest
import chat_actions as actions
from test_database_flows import db_app,one
from test_audit_reliability_database import send

pytestmark=pytest.mark.skipif(not os.environ.get('TEST_DATABASE_URL'),reason='Requires isolated PostgreSQL')


@pytest.mark.parametrize('stream',[False,True])
@pytest.mark.parametrize('text,kind,table,title',[
    ('Save a note. Title: Local note; Content: My private checklist','note','quick_notes','Local note'),
    ('Remember that I prefer studying Physics with worked examples','memory','memories','Study preference'),
    ('Add a task. Title: Local task; Details: Revise; Due: 2026-11-03T09:00:00+05:30','task','tasks','Local task')])
def test_local_commands_have_verified_receipts_and_retries_never_duplicate(db_app,monkeypatch,stream,text,kind,table,title):
    b,c,connect=db_app
    def no_ai(*a,**k):pytest.fail('A literal account command must not call AI')
    monkeypatch.setattr(b,'generate_gemini_reply',no_ai);monkeypatch.setattr(b,'stream_gemini_reply',no_ai)
    cid=c.post('/api/conversations',json={}).json['conversation']['id'];key=str(uuid4())
    if stream:
        r=c.post(f'/api/conversations/{cid}/messages/stream',json=dict(content=text,mode='normal',request_id=key))
        events=[json.loads(line) for line in r.data.splitlines()]
        assert events[0]['stage']=='saving' and not any(e.get('stage')=='generating' for e in events)
        result=next(e['data'] for e in events if e['type']=='complete')['assistant_message']
    else:result=send(c,cid,text,False,key)['assistant_message']
    assert result['action_receipt']['kind']==kind and result['action_resource']['title']==title
    send(c,cid,text,stream,key)
    assert one(connect,'SELECT COUNT(*) AS n FROM '+table)['n']==1
    assert c.get(f'/api/conversations/{cid}/messages').json['messages'][-1]['action_resource']['title']==title


def test_sharing_controls_and_badges_match_current_reads(db_app,monkeypatch):
    b,c,connect=db_app;captured=[]
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO tasks(user_id,title,details,priority,created_at,updated_at) VALUES(1,'TASK_PRIVATE_MARKER','','medium',NOW(),NOW())")
            for label,text,active in [('Shared tasks','ACTIVE_MEMORY_MARKER',True),('Paused fact','PAUSED_MEMORY_MARKER',False)]:
                cur.execute('INSERT INTO memories(user_id,label,content,active,created_at,updated_at) VALUES(1,%s,%s,%s,NOW(),NOW())',(label,text,active))
    def generate(messages,context,*a,**k):
        captured.append(context+'\n'+repr(messages));return 'A worked example follows from the definition.',{}
    monkeypatch.setattr(b,'generate_gemini_reply',generate)
    policy=dict.fromkeys(actions.SOURCES,False)
    assert c.patch('/api/chat-context',json=policy).json['permissions']==policy
    cid=c.post('/api/conversations',json={}).json['conversation']['id']
    result=send(c,cid,'Show a worked example of independence with its assumptions',False)['assistant_message']
    assert 'TASK_PRIVATE_MARKER' not in captured[-1] and 'PAUSED_MEMORY_MARKER' not in captured[-1]
    assert 'Shared tasks' not in result['memory_labels']
    assert c.get('/api/chat-context').json['permissions']==policy
    policy['tasks']=True
    assert c.patch('/api/chat-context',json=policy).json['permissions']==policy
    # A non-compact request exercises automatic consented context reads.
    text='Explain independence and conditional probability in detail, compare their assumptions and give a worked example. '*3
    send(c,cid,text,False)
    assert 'TASK_PRIVATE_MARKER' in captured[-1] and 'PAUSED_MEMORY_MARKER' not in captured[-1]
    policy['tasks']=False;c.patch('/api/chat-context',json=policy)
    fresh=c.post('/api/conversations',json={}).json['conversation']['id']
    send(c,fresh,text,False)
    assert 'TASK_PRIVATE_MARKER' not in captured[-1] and 'PAUSED_MEMORY_MARKER' not in captured[-1]
    assert c.get('/api/chat-context').json['permissions']==policy


@pytest.mark.parametrize('stream',[False,True])
def test_future_snooze_and_dateless_reschedule_never_change_a_record(db_app,monkeypatch,stream):
    b,c,connect=db_app;future=datetime.now(timezone.utc)+timedelta(days=2)
    monkeypatch.setattr(b,'provider_send',lambda *a,**k:pytest.fail('Reminder controls are local'))
    r=c.post('/api/reminders',json=dict(title='Exact future reminder',next_run_at=future.isoformat(),recurrence='once',email_enabled=False))
    rid=r.json['reminder']['id'];cid=c.post('/api/conversations',json={}).json['conversation']['id']
    for text in ['Snooze my Exact future reminder 30 minutes','Reschedule my Exact future reminder to 8 PM']:
        answer=send(c,cid,text,stream)['assistant_message']
        assert not answer.get('action_receipt') and '<SAATHI_ACTION>' not in answer['content']
        assert 'delete' not in answer['content'].lower()
        assert one(connect,'SELECT next_run_at FROM reminders WHERE id=%s',(rid,))['next_run_at']==future
    assert c.patch(f'/api/reminders/{rid}',json=dict(action='snooze',minutes=30)).status_code==409
    assert c.get(f'/api/reminders/{rid}').json['reminder']['next_run_at']==future.isoformat()
    with c.session_transaction() as session:session['user_id']=2
    assert c.get(f'/api/reminders/{rid}').status_code==404


def test_due_snooze_is_local_verified_and_keeps_repeat_anchor(db_app,monkeypatch):
    b,c,connect=db_app;due=datetime.now(timezone.utc)-timedelta(minutes=2)
    monkeypatch.setattr(b,'provider_send',lambda *a,**k:pytest.fail('Snooze must not call AI'))
    rid=c.post('/api/reminders',json=dict(title='Due revision',next_run_at=due.isoformat(),recurrence='daily')).json['reminder']['id']
    cid=c.post('/api/conversations',json={}).json['conversation']['id']
    result=send(c,cid,'Snooze my Due revision reminder 30 minutes',key='due-snooze-replay')['assistant_message']
    assert result['action_receipt']['resource_id']==rid
    saved=c.get(f'/api/reminders/{rid}').json['reminder']
    assert saved['next_run_at']==result['action_resource']['at']
    send(c,cid,'Snooze my Due revision reminder 30 minutes',key='due-snooze-replay')
    assert c.get(f'/api/reminders/{rid}').json['reminder']['next_run_at']==saved['next_run_at']
    assert one(connect,'SELECT snoozed_from FROM reminders WHERE id=%s',(rid,))['snoozed_from']==due


def test_removed_note_never_returns_a_new_saved_receipt(db_app):
    _,c,connect=db_app;cid=c.post('/api/conversations',json={}).json['conversation']['id']
    reply=send(c,cid,'Save a note. Title: Removed note; Content: Temporary')['assistant_message']
    rid=reply['action_receipt']['resource_id']
    assert c.delete(f'/api/quick-notes/{rid}',json=dict(version=1)).status_code==200
    stored=c.get(f'/api/conversations/{cid}/messages').json['messages'][-1]
    assert stored['action_resource']['available'] is False
    assert c.get('/api/chat-actions/'+str(reply['id'])).json['saved'] is False
    assert c.post('/api/chat-actions/'+str(reply['id']),json=dict(confirmed=True)).status_code==410
    assert one(connect,'SELECT COUNT(*) AS n FROM quick_notes')['n']==0
