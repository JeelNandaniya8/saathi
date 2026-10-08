import json
import os
from datetime import datetime,timedelta,timezone
import pytest
from test_database_flows import db_app,one
pytestmark=pytest.mark.skipif(not os.environ.get('TEST_DATABASE_URL'),reason='Requires isolated PostgreSQL test service')


def message(connect,kind='task',title='Read chapter',text='Revise concepts',at=None):
    body='<SAATHI_ACTION>'+json.dumps(dict(kind=kind,title=title,text=text,at=at))+'</SAATHI_ACTION>'
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO messages(user_id,role,content,created_at) VALUES(1,'assistant',%s,NOW()) RETURNING id",(body,));return cur.fetchone()['id']


def test_confirm_edit_idempotency_ownership_and_export(db_app):
    _,c,connect=db_app
    mid=message(connect);path='/api/chat-actions/'+str(mid)
    draft=c.get(path).json['action'];draft['title']='Edited before saving'
    assert c.post(path,json={'action':draft}).status_code==400
    assert one(connect,'SELECT COUNT(*) AS n FROM tasks')['n']==0
    body=dict(action=draft,confirmed=True)
    first=c.post(path,json=body);assert first.status_code==201
    assert c.post(path,json=body).json['receipt']==first.json['receipt']
    assert one(connect,'SELECT COUNT(*) AS n FROM tasks')['n']==1
    assert one(connect,'SELECT title FROM tasks')['title']=='Edited before saving'
    assert c.get('/api/export-data').json['chat_action_receipts'][0]['message_id']==mid
    with c.session_transaction() as s:s['user_id']=2
    assert c.get(path).status_code==404
    assert c.post(path,json=body).status_code==404


def test_context_revocation_and_account_isolation(db_app):
    b,c,connect=db_app
    c.post('/api/tasks',json={'title':'Owner-only task'})
    c.patch('/api/chat-context',json=dict(tasks=True,reminders=False,classroom=False))
    text,labels=b.load_active_memory_bundle(1,include_workspace=True)
    assert 'Owner-only task' in text and 'Shared tasks' in labels
    c.patch('/api/chat-context',json=dict(tasks=False,reminders=False,classroom=False))
    assert 'Owner-only task' not in b.load_active_memory_bundle(1,include_workspace=True)[0]
    assert 'Owner-only task' not in b.load_active_memory_bundle(2,include_workspace=True)[0]
    with c.session_transaction() as s:s['user_id']=2
    assert c.get('/api/chat-context').json['permissions']==dict.fromkeys(__import__('chat_actions').SOURCES,False)


def test_note_reminder_and_separate_memory_consent(db_app):
    _,c,connect=db_app
    for kind in ('note','reminder','memory'):
        at=(datetime.now(timezone.utc)+timedelta(days=1)).isoformat() if kind=='reminder' else None
        mid=message(connect,kind=kind,at=at);path='/api/chat-actions/'+str(mid);draft=c.get(path).json['action']
        payload=dict(action=draft,confirmed=True)
        if kind=='memory':
            assert c.post(path,json=payload).status_code==400
            payload['memory_consent']=True
        assert c.post(path,json=payload).status_code==201
        assert c.post(path,json=payload).status_code==200
    assert one(connect,'SELECT COUNT(*) AS n FROM quick_notes')['n']==1
    assert one(connect,'SELECT COUNT(*) AS n FROM reminders')['n']==1
    assert one(connect,'SELECT COUNT(*) AS n FROM memories')['n']==1


def test_general_scheduler_auth_and_medical_exclusion(db_app,monkeypatch):
    _,c,_=db_app
    import push_notifications as push
    seen=[]
    monkeypatch.setenv('BACKGROUND_ALERTS_ENABLED','true');monkeypatch.setenv('CLASSROOM_CRON_SECRET','test-scheduler')
    monkeypatch.setattr(push,'deliver_due',lambda b,general_only=False: seen.append(general_only) or dict(configured=True,sent=0,failed=0,skipped=0))
    assert c.post('/api/cron/background-alerts').status_code==401
    assert c.post('/api/cron/background-alerts',headers={'X-Cron-Secret':'test-scheduler'}).status_code==200
    assert seen==[True]
    assert c.get('/api/push/config').json['scheduler']['last_run']


def test_habit_journal_checkin_are_confirmed_and_ratings_not_inferred(db_app):
    _,c,connect=db_app
    cases=[dict(kind='habit',title='Walk for ten minutes',text='',recurrence='daily'),dict(kind='journal',title='Today',text='My own reflection',entry_date='2026-10-08'),dict(kind='checkin',title='Check-in',text='Feeling calm',mood=3,energy=4)]
    for draft in cases:
        content='<SAATHI_ACTION>'+json.dumps(draft)+'</SAATHI_ACTION>'
        with connect() as conn:
            with conn.cursor() as cur:
                cur.execute("INSERT INTO messages(user_id,role,content,created_at) VALUES(1,'assistant',%s,NOW()) RETURNING id",(content,));mid=cur.fetchone()['id']
        path='/api/chat-actions/'+str(mid);preview=c.get(path)
        assert preview.status_code==200,preview.json
        assert c.post(path,json=dict(action=preview.json['action'],confirmed=True)).status_code==201
    assert one(connect,'SELECT name FROM habits')['name']=='Walk for ten minutes'
    assert one(connect,'SELECT content FROM journal_entries')['content']=='My own reflection'
    assert one(connect,'SELECT mood,energy FROM check_ins')==dict(mood=3,energy=4)


def test_general_dispatch_excludes_medication_even_when_clinical_gate_enabled(db_app,monkeypatch):
    b,c,connect=db_app
    import push_notifications as push
    from test_workspace_database import subscribed,reminder
    subscribed(db_app,monkeypatch)
    rid=reminder(connect)
    with connect() as conn:
        with conn.cursor() as cur:cur.execute("UPDATE reminders SET kind='medication' WHERE id=%s",(rid,))
    monkeypatch.setenv('CARE_ROUTINES_ENABLED','true')
    seen=[];monkeypatch.setattr(push,'send_push',lambda *args:seen.append(args) or 201)
    assert push.deliver_due(vars(b),general_only=True)['sent']==0
    assert not seen
    legacy=reminder(connect)
    with connect() as conn:
        with conn.cursor() as cur:cur.execute("UPDATE reminders SET title='Evening medicine' WHERE id=%s",(legacy,))
    assert push.deliver_due(vars(b),general_only=True)['sent']==0
    reminder(connect)
    assert push.deliver_due(vars(b),general_only=True)['sent']==1
    assert len(seen)==1


def test_local_preview_saves_exchange_and_action_without_ai_service(db_app,monkeypatch):
    b,c,connect=db_app
    monkeypatch.setattr(b,'provider_post',lambda *a,**kw:pytest.fail('Explicit commands must not contact AI'))
    monkeypatch.setattr(b,'GEMINI_API_KEY','')
    c.patch('/api/chat-context',json=dict(tasks=True,reminders=False,classroom=False))
    cid=c.post('/api/conversations',json={}).json['conversation']['id']
    reply=c.post(f'/api/conversations/{cid}/messages',json={'content':'Add a task: Revise fractions. No deadline. Show the save preview.'})
    assert reply.status_code==200,reply.json
    message=reply.json['assistant_message']
    assert 'without AI' in message['content'] and message['memory_labels']==[]
    assert one(connect,'SELECT COUNT(*) AS n FROM ai_usage_events')['n']==0
    path='/api/chat-actions/'+str(message['id']);draft=c.get(path).json['action']
    assert c.post(path,json=dict(action=draft,confirmed=True)).status_code==201
    assert one(connect,'SELECT title FROM tasks')['title']=='Revise fractions'


def test_extended_context_defaults_ownership_revocation_and_old_clients(db_app):
    b,c,connect=db_app
    keys=__import__('chat_actions').SOURCES
    assert c.get('/api/chat-context').json['permissions']==dict.fromkeys(keys,False)
    mid=message(connect,kind='note',title='Private owner note',text='Owner-only details')
    draft=c.get('/api/chat-actions/'+str(mid)).json['action']
    assert c.post('/api/chat-actions/'+str(mid),json=dict(action=draft,confirmed=True)).status_code==201
    assert 'Owner-only details' not in b.load_active_memory_bundle(1,include_workspace=True)[0]
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO habits(user_id,name,frequency,created_at,updated_at) VALUES(1,'Owner-only habit','daily',NOW(),NOW())")
            cur.execute("INSERT INTO revision_items(user_id,message_id,item_index,topic,front,back) VALUES(1,%s,0,'Owner-only revision','Question','Answer')",(mid,))
            cur.execute("INSERT INTO exam_plans(user_id,client_id,title,exam_date,timezone,daily_minutes,topics) VALUES(1,%s,'Owner-only exam','2026-12-01','UTC',30,%s)",(__import__('uuid').uuid4().hex,json.dumps(['Topic '+str(i) for i in range(60)])))
    prefs=dict.fromkeys(keys,True)
    assert c.patch('/api/chat-context',json=prefs).status_code==200
    shared=b.load_active_memory_bundle(1,include_workspace=True)[0]
    for title in ('Owner-only details','Owner-only habit','Owner-only revision','Owner-only exam'):assert title in shared
    assert 'Topic 11' in shared and 'Topic 12' not in shared
    other=b.load_active_memory_bundle(2,include_workspace=True)[0]
    for title in ('Owner-only details','Owner-only habit','Owner-only revision','Owner-only exam'):assert title not in other
    assert 'Owner-only details' not in b.load_active_memory_bundle(2,include_workspace=True)[0]
    c.patch('/api/chat-context',json=dict(tasks=False,reminders=False,classroom=False))
    assert c.get('/api/chat-context').json['permissions']['notes'] is True
    prefs=dict.fromkeys(keys,False);c.patch('/api/chat-context',json=prefs)
    assert 'Owner-only details' not in b.load_active_memory_bundle(1,include_workspace=True)[0]
    assert c.patch('/api/chat-context',json={**prefs,'notes':'true'}).status_code==400
    assert c.patch('/api/chat-context',json={**prefs,'journal':True}).status_code==400
