"""Network-call reductions must retain current consent, ownership and replay."""
import os
import threading
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4
import pytest
import chat_actions as actions
from test_database_flows import db_app,one
from test_audit_reliability_database import send

pytestmark=pytest.mark.skipif(not os.environ.get('TEST_DATABASE_URL'),reason='Requires isolated PostgreSQL')


def test_context_snapshot_is_one_read_with_current_policy_and_scoped_data(db_app):
    b,c,connect=db_app
    with connect() as conn:
        with conn.cursor() as cur:
            for uid,marker in [(1,'OWN'),(2,'OTHER')]:
                cur.execute("INSERT INTO tasks(user_id,title,details,priority,created_at,updated_at) VALUES(%s,%s,'','medium',NOW(),NOW())",(uid,marker+'_TASK'))
                cur.execute("INSERT INTO quick_notes(user_id,client_id,title,content) VALUES(%s,%s,'Private',%s)",(uid,str(uuid4()),marker+'_NOTE'))
                for active in [True,False]:
                    cur.execute('INSERT INTO memories(user_id,label,content,active,created_at,updated_at) VALUES(%s,%s,%s,%s,NOW(),NOW())',(uid,marker+'_MEMORY',marker+('_ACTIVE' if active else '_PAUSED'),active))
            cur.execute("INSERT INTO workspace_preferences(user_id,timezone) VALUES(1,'America/Los_Angeles') ON CONFLICT(user_id) DO UPDATE SET timezone=EXCLUDED.timezone")
    class Cursor:
        def __init__(self,cur):self.cur=cur;self.calls=0
        def execute(self,*args):self.calls+=1;return self.cur.execute(*args)
        def __getattr__(self,name):return getattr(self.cur,name)
    def read(text):
        with connect() as conn:
            with conn.cursor() as cur:
                wrapped=Cursor(cur)
                result=b.load_active_memory_bundle(1,wrapped,'flashcards',True,text)
                assert wrapped.calls==1
                return result
    off=dict.fromkeys(actions.SOURCES,False)
    assert c.patch('/api/chat-context',json=off).status_code==200
    for category,field,value in [('study','goal','OWN_STUDY_PROFILE'),('care','allergies','OWN_CARE_PROFILE')]:
        assert c.put('/api/personal-context/'+category+'/'+field,json=dict(value=value,version=0,confirmed=True,use_in_ai=True)).status_code==200
    context,labels=read('Explain conditional probability with examples')
    assert 'OWN_ACTIVE' in context and 'America/Los_Angeles' in context
    assert 'OWN_STUDY_PROFILE' in context and 'Profile: goal' in labels and 'OWN_CARE_PROFILE' not in context
    assert all(value not in context for value in ['OWN_TASK','OWN_NOTE','OWN_PAUSED','OTHER_'])
    assert 'Shared tasks' not in labels
    shared=dict(off,tasks=True,notes=True)
    assert c.patch('/api/chat-context',json=shared).status_code==200
    context,labels=read('Explain conditional probability with examples')
    assert 'OWN_TASK' in context and 'Shared tasks' in labels and 'OWN_NOTE' not in context
    context,labels=read('Make flashcards from my notes')
    assert 'OWN_NOTE' in context and 'Requested notes for this reply' in labels
    assert c.patch('/api/chat-context',json=off).status_code==200
    context,labels=read('Explain conditional probability with examples')
    assert 'OWN_TASK' not in context and 'OWN_NOTE' not in context
    assert c.post('/api/personal-context/revoke',json={}).status_code==200
    assert 'OWN_STUDY_PROFILE' not in read('Explain conditional probability with examples')[0]
    with connect() as conn:
        with conn.cursor() as cur:cur.execute("UPDATE personal_context_fields SET use_in_ai=TRUE,reviewed_at=NOW()-INTERVAL '91 days' WHERE user_id=1")
    assert 'OWN_STUDY_PROFILE' not in read('Explain conditional probability with examples')[0]
    with connect() as conn:
        with conn.cursor() as cur:
            snapshot=actions.context_snapshot(cur,1,'Hello')
            assert all(value is None for value in snapshot['sources'].values())


@pytest.mark.parametrize('stream',[False,True])
def test_retry_key_older_than_loaded_history_still_replays_without_writing(db_app,stream):
    _,c,connect=db_app
    cid=c.post('/api/conversations',json={}).json['conversation']['id'];key=str(uuid4())
    text='Save a note. Title: Old request; Content: Keep exactly once'
    first=send(c,cid,text,stream,key)
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO messages(user_id,conversation_id,role,content,created_at) SELECT 1,%s,CASE WHEN n%%2=0 THEN 'assistant' ELSE 'user' END,'Later exchange',NOW() FROM generate_series(1,40)n",(cid,))
    repeated=send(c,cid,text,stream,key)
    assert repeated['replayed'] and repeated['assistant_message']['id']==first['assistant_message']['id']
    assert one(connect,'SELECT COUNT(*) AS n FROM quick_notes')['n']==1
    assert one(connect,'SELECT COUNT(*) AS n FROM messages WHERE conversation_id=%s',(cid,))['n']==42


@pytest.mark.parametrize('stream',[False,True])
def test_chat_optimization_still_checks_revoked_session_before_any_write(db_app,stream):
    _,c,connect=db_app;cid=c.post('/api/conversations',json={}).json['conversation']['id']
    with connect() as conn:
        with conn.cursor() as cur:cur.execute('UPDATE users SET session_version=session_version+1 WHERE id=1')
    response=c.post(f'/api/conversations/{cid}/messages'+('/stream' if stream else ''),json={'content':'Save a note. Title: Blocked; Content: No write','request_id':str(uuid4())})
    assert response.status_code==401
    assert one(connect,'SELECT COUNT(*) AS n FROM quick_notes')['n']==0
    assert one(connect,'SELECT COUNT(*) AS n FROM messages')['n']==0


def test_batched_note_lock_keeps_the_cap_under_concurrent_creates(db_app):
    _,_,connect=db_app
    with connect() as conn:
        with conn.cursor() as cur:cur.execute("INSERT INTO quick_notes(user_id,client_id,title,content) SELECT 1,md5(n::text)::uuid,'Note '||n,'Saved' FROM generate_series(1,99)n")
    barrier=threading.Barrier(2)
    def create(index):
        try:
            with connect() as conn:
                with conn.cursor() as cur:
                    barrier.wait(timeout=5)
                    return actions.apply_draft(cur,1,actions.validate_action(dict(kind='note',title='Race '+str(index),text='Exactly one slot')))
        except ValueError:return None
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(create,[1,2]))
    assert sum(result is not None for result in results)==1
    assert one(connect,'SELECT COUNT(*) AS n FROM quick_notes')['n']==100
