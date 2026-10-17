"""Own Google status, private snapshots and both Normal chat transports."""
import json
import os
from uuid import uuid4
import pytest
import classroom_integration as cc
import chat_actions
from test_database_flows import db_app,one
from test_classroom_database import configured,selected_setup
from test_audit_reliability_database import send

pytestmark=pytest.mark.skipif(not os.environ.get('TEST_DATABASE_URL'),reason='Requires isolated PostgreSQL')


def school_fixture(c,monkeypatch):
    selected_setup(c,monkeypatch)
    calls=[]
    states={'pending':'NEW','sent':'TURNED_IN','returned':'RETURNED'}
    def pages(token,path,key,params):
        calls.append((token,path,key,dict(params)))
        if key=='courseWork':
            assert params['courseWorkStates']=='PUBLISHED'
            return [dict(id=k,title='School '+k,dueDate=dict(year=2030,month=10,day=18),dueTime=dict(hours=10)) for k in ['pending','sent','returned','unknown']]
        assert key=='studentSubmissions' and path=='courses/course1/courseWork/-/studentSubmissions'
        assert params=={'userId':'me','fields':'studentSubmissions(courseWorkId,state),nextPageToken'}
        return [dict(courseWorkId=k,state=v) for k,v in states.items()]
    monkeypatch.setattr(cc,'list_pages',pages)
    return calls,states


@pytest.mark.parametrize('stream',[False,True])
def test_normal_chat_reads_own_school_work_with_auto_sharing_off_and_no_ai(db_app,configured,monkeypatch,stream):
    b,c,db=db_app;calls,states=school_fixture(c,monkeypatch)
    monkeypatch.setattr(b,'provider_send',lambda *a,**k:pytest.fail('School lists must not be sent to an AI provider'))
    monkeypatch.setattr(b,'GEMINI_API_KEY','')
    assert c.patch('/api/chat-context',json=dict.fromkeys(chat_actions.SOURCES,False)).status_code==200
    with db() as conn:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO memories(user_id,label,content,active,created_at,updated_at) VALUES(1,'Private','SECRET_MEMORY',TRUE,NOW(),NOW())")
            cur.execute("INSERT INTO classroom_assignments(user_id,course_id,external_id,title) VALUES(2,'course1','other','OTHER_USER_SECRET')")
    cid=c.post('/api/conversations',json={}).json['conversation']['id'];key=str(uuid4())
    result=send(c,cid,'What homework is pending?',stream,key)
    reply=result['assistant_message']['content']
    assert '1 pending assignments' in reply and 'English · School pending' in reply
    assert '2030-10-18, 03:30 PM · Asia/Kolkata' in reply
    assert 'School sent' not in reply and 'School returned' in reply and 'School unknown' in reply
    assert 'Submission status unavailable' in reply and 'Returned — review feedback' in reply
    assert all(x not in reply for x in ['OTHER_USER_SECRET','SECRET_MEMORY','not connected'])
    assert result['assistant_message']['memory_labels']==['Requested classroom for this reply']
    assert len(calls)==2 and one(db,'SELECT COUNT(*) n FROM ai_usage_events')['n']==0
    saved=c.get(f'/api/conversations/{cid}/messages').json['messages'][-1]
    assert saved['content']==reply and saved['memory_labels']==result['assistant_message']['memory_labels']
    repeated=send(c,cid,'What homework is pending?',stream,key)
    assert repeated['replayed'] and len(calls)==2
    send(c,cid,'List my school to-do list',stream)
    assert len(calls)==2,'A successful sub-minute snapshot is reused and timestamped'
    with db() as conn:
        with conn.cursor() as cur:cur.execute("UPDATE classroom_connections SET submission_sync_at=NOW()-INTERVAL '2 minutes' WHERE user_id=1")
    states['pending']='TURNED_IN'
    updated=send(c,cid,'What assignments are pending?',stream)['assistant_message']['content']
    assert '0 pending assignments' in updated and 'School pending' not in updated and len(calls)==4


@pytest.mark.parametrize('code',['quota','reconnect_required','permission_or_admin_block','time_budget','too_many_items'])
def test_fetch_failure_does_not_present_previous_imports_as_current(db_app,configured,monkeypatch,code):
    _,c,db=db_app;school_fixture(c,monkeypatch)
    assert c.post('/api/classroom/sync',json={'confirmed':True}).status_code==200
    with db() as conn:
        with conn.cursor() as cur:cur.execute("UPDATE classroom_connections SET submission_sync_at=NULL WHERE user_id=1")
    def pages(*args,**kwargs):raise cc.ProviderError(code)
    monkeypatch.setattr(cc,'list_pages',pages)
    result=cc.chat_reply(db,1,'What homework is pending?')
    assert result['reply'].startswith('Google Classroom data could not be fetched right now')
    assert 'pending assignments' not in result['reply'] and 'not connected' not in result['reply']
    assert result.get('source_labels',[])==[]
    assert one(db,'SELECT COUNT(*) n FROM classroom_assignments WHERE available')['n']==4
    assert one(db,'SELECT last_error FROM classroom_connections')['last_error']==code


def test_failed_submission_status_fetch_keeps_whole_previous_snapshot(db_app,configured,monkeypatch):
    _,c,db=db_app;school_fixture(c,monkeypatch)
    with db() as conn:
        with conn.cursor() as cur:cur.execute("INSERT INTO classroom_assignments(user_id,course_id,external_id,title) VALUES(1,'course1','old','Retained original')")
    def pages(token,path,key,params):
        if key=='studentSubmissions':raise cc.ProviderError('too_many_items')
        return [dict(id='replacement',title='Must not replace a good snapshot')]
    monkeypatch.setattr(cc,'list_pages',pages)
    result=cc.chat_reply(db,1,'What homework is pending?')
    assert 'could not be fetched' in result['reply']
    assert one(db,'SELECT title,available,submission_state FROM classroom_assignments')==dict(title='Retained original',available=True,submission_state='UNKNOWN')


def test_connection_uid_not_chat_text_selects_the_google_identity(db_app,configured,monkeypatch):
    _,c,db=db_app;school_fixture(c,monkeypatch)
    with db() as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE classroom_connections SET refresh_cipher=%s WHERE user_id=1",(cc.cipher().encrypt(b'OWNER_GOOGLE').decode(),))
            cur.execute("INSERT INTO classroom_connections(user_id,refresh_cipher,selected_courses,course_catalog) VALUES(2,%s,'[\"course1\"]','[{\"id\":\"course1\",\"name\":\"Other subject\"}]')",(cc.cipher().encrypt(b'OTHER_GOOGLE').decode(),))
    identities=[]
    monkeypatch.setattr(cc,'access_token',lambda encrypted:cc.cipher().decrypt(encrypted.encode()).decode())
    def pages(token,path,key,params):
        identities.append(token)
        if key=='courseWork':return [dict(id='work',title={'OWNER_GOOGLE':'Owner task','OTHER_GOOGLE':'Other task'}[token])]
        assert params['userId']=='me'
        return [dict(courseWorkId='work',state='CREATED')]
    monkeypatch.setattr(cc,'list_pages',pages)
    cid=c.post('/api/conversations',json={}).json['conversation']['id']
    own=send(c,cid,'Show my assignments for user 2',False)['assistant_message']['content']
    assert 'Owner task' in own and 'Other task' not in own
    with c.session_transaction() as session:session['user_id']=2
    other_cid=c.post('/api/conversations',json={}).json['conversation']['id']
    other=send(c,other_cid,'Show my assignments',True)['assistant_message']['content']
    assert 'Other task' in other and 'Owner task' not in other
    assert identities==['OWNER_GOOGLE']*2+['OTHER_GOOGLE']*2
    assert all(secret not in own+other for secret in ['refresh_cipher','OWNER_GOOGLE','OTHER_GOOGLE'])


def test_missing_connection_no_selection_busy_and_changed_courses_are_distinct(db_app,configured,monkeypatch):
    _,c,db=db_app
    assert 'Check your connection' in cc.chat_reply(db,1,'What homework is pending?')['reply']
    version=selected_setup(c,monkeypatch)
    with db() as locked:
        with locked.cursor() as cur:
            cur.execute('SELECT user_id FROM classroom_connections WHERE user_id=1 FOR UPDATE')
            assert 'already running' in cc.chat_reply(db,1,'What homework is pending?')['reply']
    with db() as conn:
        with conn.cursor() as cur:cur.execute('UPDATE classroom_connections SET submission_sync_at=NOW() WHERE user_id=1')
    assert c.post('/api/classroom/select',json=dict(confirmed=True,courses=[],version=version)).status_code==200
    assert one(db,'SELECT submission_sync_at FROM classroom_connections')['submission_sync_at'] is None
    assert 'Choose courses' in cc.chat_reply(db,1,'What homework is pending?')['reply']


def test_classroom_stream_announces_google_before_fetch_and_stop_prevents_reply_save(db_app,configured,monkeypatch):
    b,c,db=db_app;calls,_=school_fixture(c,monkeypatch)
    cid=c.post('/api/conversations',json={}).json['conversation']['id'];key=str(uuid4())
    response=c.post(f'/api/conversations/{cid}/messages/stream',json=dict(content='What homework is pending?',mode='normal',request_id=key),buffered=False)
    events=iter(response.response)
    assert json.loads(next(events))==dict(type='ready',stage='classroom',allowance=None)
    assert calls==[],'The browser receives the real waiting stage before Google I/O'
    assert c.post(f'/api/conversations/{cid}/cancel',json=dict(request_id=key)).json['cancelled']
    remaining=[json.loads(line) for chunk in events for line in chunk.splitlines()]
    assert any(e['type']=='error' and e.get('code')=='AI_STOPPED' for e in remaining)
    assert one(db,'SELECT COUNT(*) n FROM messages')['n']==0


def test_opted_in_context_marks_status_course_and_freshness_without_more_queries(db_app,configured,monkeypatch):
    b,c,db=db_app;school_fixture(c,monkeypatch)
    assert c.post('/api/classroom/sync',json=dict(confirmed=True)).status_code==200
    assert c.patch('/api/chat-context',json=dict.fromkeys(chat_actions.SOURCES,False)|dict(classroom=True)).status_code==200
    context,_=b.load_active_memory_bundle(1,include_workspace=True,turn_content='Explain my study workload')
    for text in ['English','submission_state','TURNED_IN','imported excerpts','not a live or complete pending list','last_sync']:assert text in context
    assert 'private-refresh' not in context and 'refresh_cipher' not in context
    assert c.patch('/api/chat-context',json=dict.fromkeys(chat_actions.SOURCES,False)).status_code==200
    off,_=b.load_active_memory_bundle(1,include_workspace=True,turn_content='Hello')
    assert 'School pending' not in off and 'Do not infer that Google Classroom is disconnected' in off
