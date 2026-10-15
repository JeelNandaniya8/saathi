"""October 15 regressions: scoped reads, study conversion and verified saves."""
import json
import os
from datetime import datetime,timedelta,timezone
from uuid import uuid4
from zoneinfo import ZoneInfo
import pytest
from test_database_flows import db_app,one
from test_audit_reliability_database import send
from test_chat_control_database import seed

pytestmark=pytest.mark.skipif(not os.environ.get('TEST_DATABASE_URL'),reason='Requires isolated PostgreSQL')


@pytest.mark.parametrize('stream',[False,True])
def test_explicit_day_excludes_yesterday_undated_completed_and_other_accounts(db_app,monkeypatch,stream):
    b,c,connect=db_app
    monkeypatch.setattr(b,'provider_send',lambda *a,**k:pytest.fail('A date-scoped Planner read must not use AI'))
    day=datetime(2026,10,15,17,tzinfo=ZoneInfo('Asia/Kolkata'))
    with connect() as conn:
        with conn.cursor() as cur:
            for uid,title,at,done in [(1,'Day 2: Practice & Problem Solving',day,False),(1,'Audit Oct14 Day 1',day+timedelta(hours=1),False),(1,'Yesterday task',day-timedelta(days=1),False),(1,'Undated task',None,False),(1,'Tomorrow task',day+timedelta(days=1),False),(1,'Completed task',day,True),(2,'Other account task',day,False)]:
                cur.execute("INSERT INTO tasks(user_id,title,details,due_at,completed,priority,created_at,updated_at) VALUES(%s,%s,'',%s,%s,'medium',NOW(),NOW())",(uid,title,at,done))
    cid=c.post('/api/conversations',json={}).json['conversation']['id']
    for query in ['What unfinished tasks remain on 2026-10-15? Exclude tasks from 2026-10-14.','Show remaining work on 15 October 2026.']:
        message=send(c,cid,query,stream)['assistant_message']
        text=message['content']
        assert text.startswith('2 unfinished Planner tasks')
        assert 'Day 2: Practice & Problem Solving' in text and 'Audit Oct14 Day 1' in text
        assert '05:00 PM' in text and '06:00 PM' in text and 'Asia/Kolkata' in text
        assert all(name not in text for name in ['Yesterday task','Undated task','Tomorrow task','Completed task','Other account task'])
        assert not message.get('action_error') and not message.get('action_receipt')


@pytest.mark.parametrize('stream',[False,True])
def test_flashcard_conversion_after_reminder_clarification_has_no_workspace_side_effect(db_app,monkeypatch,stream):
    b,c,connect=db_app
    cid=c.post('/api/conversations',json={}).json['conversation']['id']
    with connect() as conn:
        with conn.cursor() as cur:
            for role,content in [('user','Explain DNA replication'),('assistant','DNA replication copies DNA before division.'),('user','Remind me about this'),('assistant','What date and time should I use?')]:
                cur.execute('INSERT INTO messages(user_id,conversation_id,role,content,created_at) VALUES(1,%s,%s,%s,NOW())',(cid,role,content))
    reply='[FLASHCARDS]\nFront: What copies DNA?\n---\nBack: DNA replication.\n---\nFront: When?\nBack: Before division.\n[/FLASHCARDS]'
    captured=[]
    def generate(messages,context,language,mode,**kwargs):
        captured.append((context,mode));return reply,{}
    def chunks(*args,**kwargs):
        text,usage=generate(*args,**kwargs);yield text;return usage
    monkeypatch.setattr(b,'generate_gemini_reply',generate)
    monkeypatch.setattr(b,'stream_gemini_reply',chunks)
    key=str(uuid4())
    result=send(c,cid,'Turn this into 2 flashcards about DNA for revision',stream,key)['assistant_message']
    assert result['ai_mode']=='flashcards' and result['study_progress']['kind']=='flashcards'
    assert result['content']==reply and not result.get('action_error') and not result.get('action_receipt')
    assert 'Requested reminders for this reply' not in result['memory_labels']
    assert captured[0][1]=='flashcards' and 'reminders: not shared with chat' in captured[0][0]
    assert send(c,cid,'Turn this into 2 flashcards about DNA for revision',stream,key)['assistant_message']['id']==result['id']
    assert len(captured)==1 and one(connect,'SELECT COUNT(*) AS n FROM study_progress')['n']==1
    assert one(connect,'SELECT COUNT(*) AS n FROM reminders')['n']==0
    assert one(connect,'SELECT COUNT(*) AS n FROM tasks')['n']==0
    progress=c.patch(f"/api/messages/{result['id']}/study-progress",json={'progress':{'current_index':0,'known_indices':[],'review_indices':[0]}})
    assert progress.status_code==200,progress.json
    assert one(connect,'SELECT front FROM revision_items')['front']=='What copies DNA?'


@pytest.mark.parametrize('prefix',['Not saved. Review this preview before saving.','Failed: Automatic save was not authorised.\nRetry when ready.'])
def test_plan_manual_save_reconciles_persisted_status_and_is_idempotent(db_app,prefix):
    _,c,connect=db_app
    draft=dict(kind='plan',title='DNA recall',text='Two days',items=[dict(title='Day 1',text='Active recall',at='2026-10-17T18:00:00+05:30',duration_minutes=15),dict(title='Day 2',text='Practice',at='2026-10-18T18:00:00+05:30',duration_minutes=15)])
    mid,cid=seed(connect,'Preview a study plan for two days, 15 minutes each day',draft)
    with connect() as conn:
        with conn.cursor() as cur:cur.execute('UPDATE messages SET content=%s WHERE id=%s',(prefix+'\n<SAATHI_ACTION>'+json.dumps(draft)+'</SAATHI_ACTION>',mid))
    path=f'/api/chat-actions/{mid}'
    prepared=c.get(path).json
    assert not prepared['saved'] and len(prepared['action']['items'])==2
    response=c.post(path,json=dict(confirmed=True,action=prepared['action']))
    assert response.status_code==201,response.json
    assert response.json['saved'] and response.json['resource']['count']==2
    assert response.json['content'].startswith('Study plan saved to Planner.')
    assert c.post(path,json=dict(confirmed=True,action=prepared['action'])).status_code==200
    stored=c.get(f'/api/conversations/{cid}/messages').json['messages'][-1]
    assert stored['action_receipt']['kind']=='plan' and not stored.get('action_error')
    assert stored['content'].startswith('Study plan saved to Planner.')
    assert one(connect,'SELECT COUNT(*) AS n FROM tasks')['n']==2
    assert one(connect,"SELECT COUNT(*) AS n FROM tasks WHERE details LIKE '%Duration: 15 minutes'")['n']==2
    assert one(connect,'SELECT content FROM messages WHERE id=%s',(mid,))['content']==response.json['content']


def test_plan_enrichment_preserves_requested_common_duration_before_confirmation(db_app,monkeypatch):
    b,c,connect=db_app
    draft=dict(kind='plan',title='Two day plan',text='',items=[dict(title='Day 1',at='2026-10-17T18:00:00+05:30'),dict(title='Day 2',at='2026-10-18T18:00:00+05:30')])
    monkeypatch.setattr(b,'generate_gemini_reply',lambda *a,**k:('<SAATHI_ACTION>'+json.dumps(draft)+'</SAATHI_ACTION>',{}))
    cid=c.post('/api/conversations',json={}).json['conversation']['id']
    message=send(c,cid,'Make a study plan preview for DNA on 17 and 18 October at 18:00, 15 minutes each day.',False)['assistant_message']
    action=c.get(f"/api/chat-actions/{message['id']}").json['action']
    assert all(item['duration_minutes']==15 and item['text']=='Duration: 15 minutes' for item in action['items'])
    assert one(connect,'SELECT COUNT(*) AS n FROM tasks')['n']==0


def test_next_reminder_is_future_and_past_receipt_is_readable(db_app):
    _,c,connect=db_app
    past=datetime.now(timezone.utc)-timedelta(days=1)
    with connect() as conn:
        with conn.cursor() as cur:
            for title,at in [('Overdue reminder',past),('Next future reminder',past+timedelta(days=2))]:
                cur.execute("INSERT INTO reminders(user_id,title,note,next_run_at,recurrence,created_at) VALUES(1,%s,'',%s,'once',NOW())",(title,at))
    assert c.get('/api/overview').json['next_reminder']['title']=='Next future reminder'
    rid=one(connect,"SELECT id FROM reminders WHERE title='Overdue reminder'")['id']
    mid,cid=seed(connect,'Remind me about revision',dict(kind='reminder',title='Overdue reminder',at=past.isoformat()))
    with connect() as conn:
        with conn.cursor() as cur:cur.execute("INSERT INTO chat_action_receipts(message_id,user_id,kind,resource_id) VALUES(%s,1,'reminder',%s)",(mid,rid))
    receipt=c.get(f'/api/chat-actions/{mid}')
    assert receipt.status_code==200 and receipt.json['saved']
    assert receipt.json['content'].startswith('Reminder saved.')
    loaded=c.get(f'/api/conversations/{cid}/messages').json['messages'][-1]
    assert not loaded.get('action_error') and loaded['action_receipt']['resource_id']==rid
