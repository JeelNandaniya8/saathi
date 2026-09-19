"""Owned search, local-day overview, timer transitions and private PDF viewing."""
import os
import uuid
from datetime import datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor
import pytest
from test_database_flows import db_app, one

pytestmark = pytest.mark.skipif(not os.environ.get('TEST_DATABASE_URL'), reason='Requires isolated PostgreSQL test service')


def switch(client, uid):
    with client.session_transaction() as session:
        session['user_id'] = uid


def insert(db, query, params=()):
    with db() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            return cur.fetchone() if cur.description else None


def message(db, uid=1, title='Saved conversation', content='ગુજરાતી keyword'):
    conversation = insert(db, 'INSERT INTO conversations(user_id,title,created_at,updated_at) VALUES(%s,%s,NOW(),NOW()) RETURNING id', (uid,title))['id']
    mid = insert(db, "INSERT INTO messages(user_id,conversation_id,role,content,created_at) VALUES(%s,%s,'user',%s,NOW()) RETURNING id", (uid,conversation,content))['id']
    return conversation, mid


def test_global_search_owned_content_unicode_and_literal_wildcards(db_app):
    _, client, db = db_app
    cid, _ = message(db)
    message(db, 2, 'Other secret', 'ગુજરાતી keyword')
    note = client.post('/api/quick-notes', json={'client_id':str(uuid.uuid4()),'title':'Note','content':'ગુજરાતી keyword 50%_off'}).json['note']
    task = client.post('/api/tasks', json={'title':'Task','details':'ગુજરાતી keyword'}).json['task']
    found = client.get('/api/workspace/search', query_string={'q':'ગુજરાતી'})
    assert found.status_code == 200, found.json
    assert {(x['kind'],x['id']) for x in found.json['items']} == {('conversation',cid),('note',note['id']),('task',task['id'])}
    assert client.get('/api/workspace/search', query_string={'q':'50%_'}).json['items'][0]['kind'] == 'note'
    assert client.get('/api/workspace/search?q=%25%25').json['items'] == []
    assert client.get('/api/workspace/search?q=a').status_code == 400
    switch(client,2)
    assert len(client.get('/api/workspace/search', query_string={'q':'ગુજરાતી'}).json['items']) == 1
    assert client.get('/api/workspace/search?q=50%25_').json['items'] == []


def test_today_uses_three_due_tasks_owned_revision_and_latest_saved_chat(db_app):
    _, client, db = db_app
    client.patch('/api/workspace/preferences', json={'timezone':'Asia/Kolkata'})
    due = datetime.now(timezone.utc)-timedelta(hours=1)
    expected = []
    for priority in ('low','high','medium'):
        item = client.post('/api/tasks', json={'title':priority,'due_at':due.isoformat(),'priority':priority}).json['task']
        expected.append(item['id'])
    client.post('/api/tasks', json={'title':'Future','due_at':(due+timedelta(days=3)).isoformat(),'priority':'high'})
    cid, mid = message(db)
    for idx,paused in enumerate((False,True)):
        insert(db, 'INSERT INTO revision_items(user_id,message_id,item_index,topic,front,back,paused) VALUES(1,%s,%s,\'Topic\',\'Question\',\'Answer\',%s)', (mid,idx,paused))
    message(db,2,'Other newer chat')
    data = client.get('/api/workspace/today');assert data.status_code == 200, data.json
    assert [t['id'] for t in data.json['tasks']] == [expected[1],expected[2],expected[0]]
    assert data.json['revision_due'] == 1 and data.json['recent_chat']['id'] == cid
    client.patch('/api/tasks/'+str(expected[1]),json={'completed':True})
    assert len(client.get('/api/workspace/today').json['tasks']) == 2
    switch(client,2)
    assert client.get('/api/workspace/today').json['tasks'] == []
    assert client.get('/api/workspace/today').json['revision_due'] == 0


def test_focus_retries_versions_expiry_exports_and_task_ownership(db_app):
    _, client, db = db_app
    task = client.post('/api/tasks',json={'title':'Focus target'}).json['task']
    payload = {'minutes':25,'client_id':str(uuid.uuid4()),'task_id':task['id']}
    switch(client,2)
    assert client.post('/api/focus',json=payload).status_code == 404
    switch(client,1)
    result = client.post('/api/focus',json=payload);assert result.status_code == 200,result.json
    current = result.json['session'];sid=current['id'];path='/api/focus/'+str(sid)
    assert current['remaining_seconds'] == 1500
    assert client.post('/api/focus',json=payload).json['session']['id'] == sid
    assert one(db,'SELECT count(*) AS n FROM focus_sessions')['n'] == 1
    assert client.post('/api/focus',json={**payload,'client_id':str(uuid.uuid4())}).status_code == 409
    insert(db,"UPDATE focus_sessions SET last_started_at=NOW()-INTERVAL '20 seconds' WHERE id=%s",(sid,))
    paused = client.patch(path,json={'action':'pause','version':1});assert paused.status_code == 200,paused.json
    assert 1478 <= paused.json['session']['remaining_seconds'] <= 1480
    assert client.patch(path,json={'action':'resume','version':1}).status_code == 409
    resumed = client.patch(path,json={'action':'resume','version':2});assert resumed.status_code == 200
    switch(client,2)
    assert client.patch(path,json={'action':'end','version':3}).status_code == 404
    assert client.get('/api/focus').json['session'] is None
    assert client.get('/api/export-data').json['focus_sessions'] == []
    switch(client,1)
    insert(db,"UPDATE focus_sessions SET last_started_at=NOW()-INTERVAL '30 minutes' WHERE id=%s",(sid,))
    completed = client.get('/api/focus').json['session']
    assert completed['status'] == 'completed' and completed['remaining_seconds'] == 0
    assert client.post('/api/focus',json=payload).json['session']['status'] == 'completed'
    assert client.get('/api/export-data').json['focus_sessions'][0]['status'] == 'completed'
    assert client.post('/api/focus',json={'minutes':50,'client_id':str(uuid.uuid4())}).status_code == 200
    for body in ({'minutes':True,'client_id':str(uuid.uuid4())},{'minutes':25,'client_id':'bad'},[],{'minutes':25,'client_id':str(uuid.uuid4()),'task_id':True}):
        assert client.post('/api/focus',json=body).status_code == 400
    assert client.post('/api/focus',json=payload,headers={'X-CSRF-Token':''}).status_code == 403


def test_simultaneous_focus_starts_create_one_active_session(db_app):
    backend, _, db = db_app
    def start(_):
        client=backend.app.test_client()
        with client.session_transaction() as session:
            session.update(user_id=1,session_version=1,csrf_token='local-csrf')
        return client.post('/api/focus',json={'minutes':25,'client_id':str(uuid.uuid4())},headers={'X-CSRF-Token':'local-csrf'}).status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(start,range(2))) == [200,409]
    assert one(db,"SELECT count(*) AS n FROM focus_sessions WHERE status='running'")['n'] == 1


def test_pdf_page_view_is_owned_inline_and_sandboxed(db_app):
    _, client, db = db_app
    cid,mid=message(db)
    aid=insert(db,"INSERT INTO chat_attachments(user_id,conversation_id,message_id,original_name,mime_type,size_bytes,content,created_at) VALUES(1,%s,%s,'lesson.pdf','application/pdf',8,%s,NOW()) RETURNING id",(cid,mid,b'%PDF-1.4'))['id']
    path='/api/attachments/'+str(aid)
    assert client.get(path).headers['Content-Disposition'].startswith('attachment')
    viewed=client.get(path+'/view')
    assert viewed.status_code == 200 and viewed.headers['Content-Disposition'].startswith('inline')
    assert 'sandbox' in viewed.headers['Content-Security-Policy']
    assert 'no-store' in viewed.headers['Cache-Control']
    switch(client,2)
    assert client.get(path+'/view').status_code == 404
    with client.session_transaction() as session:session.clear()
    for endpoint in (path+'/view','/api/workspace/today','/api/workspace/search?q=hi','/api/focus'):
        assert client.get(endpoint).status_code == 401
