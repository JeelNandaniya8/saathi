import os
from datetime import datetime,timezone
from urllib.parse import urlparse,parse_qs
import pytest
from cryptography.fernet import Fernet
from test_database_flows import db_app,one
import classroom_integration as cc
pytestmark=pytest.mark.skipif(not os.environ.get('TEST_DATABASE_URL'),reason='Requires isolated PostgreSQL')

@pytest.fixture
def configured(monkeypatch):
    for k,v in {'CLASSROOM_ENABLED':'true','CLASSROOM_CLIENT_ID':'fixture-client','CLASSROOM_CLIENT_SECRET':'fixture-secret',
                'CLASSROOM_REDIRECT_URI':'https://example.test/api/classroom/callback','CLASSROOM_TOKEN_KEY':Fernet.generate_key().decode()}.items():monkeypatch.setenv(k,v)
    monkeypatch.setattr(cc,'provider_json',lambda *a,**kw:{'refresh_token':'private-refresh','access_token':'private-access','scope':' '.join(cc.SCOPES)})


def connect(c):
    r=c.post('/api/classroom/connect',json={'confirmed':True});assert r.status_code==200,r.json
    query=parse_qs(urlparse(r.json['url']).query)
    assert query['code_challenge_method']==['S256'] and query['access_type']==['offline']
    state=query['state'][0];r=c.get('/api/classroom/callback',query_string={'code':'test-code','state':state})
    assert r.status_code==302,r.json
    return state


def test_oauth_state_session_single_use_and_private_export(db_app,configured):
    _,c,db=db_app
    assert c.post('/api/classroom/connect',json={}).status_code==400
    assert c.get('/api/classroom/callback?state=invalid').status_code==400
    state=connect(c)
    assert c.get('/api/classroom/callback',query_string={'code':'test-code','state':state}).status_code==400
    stored=one(db,'SELECT refresh_cipher FROM classroom_connections')['refresh_cipher']
    assert 'private-refresh' not in stored and cc.cipher().decrypt(stored.encode())==b'private-refresh'
    export=c.get('/api/export-data').get_data(as_text=True)
    assert 'private-refresh' not in export and 'refresh_cipher' not in export
    with c.session_transaction() as s:s['user_id']=2
    assert c.get('/api/classroom/status').json['connected'] is False
    assert c.get('/api/classroom/assignments').json['assignments']==[]
    assert c.post('/api/classroom/disconnect',json={'confirmed':True,'remove_imports':True}).json['ok']
    assert one(db,'SELECT COUNT(*) n FROM classroom_connections')['n']==1


def test_selected_courses_sync_duplicate_update_missing_and_planner(db_app,configured,monkeypatch):
    _,c,db=db_app;connect(c)
    items=[{'id':'work','title':'Essay','description':'Write it','alternateLink':'https://classroom.google.com/c/course1'}]
    def pages(token,path,key,params):
        if path=='courses':
            assert params['studentId']=='me';return [{'id':'course1','name':'English'},{'id':'course2','name':'Other'}]
        assert path=='courses/course1/courseWork';return list(items)
    monkeypatch.setattr(cc,'list_pages',pages)
    courses=c.get('/api/classroom/courses?refresh=1').json
    assert c.post('/api/classroom/select',json={'confirmed':True,'courses':['course1'],'version':courses['version']}).status_code==200
    assert c.post('/api/classroom/select',json={'confirmed':True,'courses':['course2'],'version':courses['version']}).status_code==409
    assert c.post('/api/classroom/sync',json={'confirmed':True}).json['imported']==1
    a=c.get('/api/classroom/assignments').json['assignments'][0];assert a['due_at'] is None
    url='/api/classroom/assignments/'+str(a['id'])+'/planner'
    assert c.post(url,json={}).status_code==400
    assert c.post(url,json={'confirmed':True}).status_code==201
    assert c.post(url,json={'confirmed':True}).json['replayed']
    with c.session_transaction() as s:s['user_id']=2
    assert c.post(url,json={'confirmed':True}).status_code in (400,404)
    with c.session_transaction() as s:s['user_id']=1
    def allow_sync():
        with db() as conn:
            with conn.cursor() as cur:cur.execute('UPDATE classroom_connections SET last_sync=NULL')
    items[0]['title']='Edited';allow_sync()
    assert c.post('/api/classroom/sync',json={'confirmed':True}).json['imported']==1
    assert one(db,'SELECT COUNT(*) n FROM classroom_assignments')['n']==1
    assert one(db,'SELECT title FROM tasks')['title']=='Essay','Never overwrite local task edits on sync'
    items.clear();allow_sync();c.post('/api/classroom/sync',json={'confirmed':True})
    assert c.get('/api/classroom/assignments').json['assignments'][0]['available'] is False
    monkeypatch.setattr(cc.requests,'post',lambda *a,**kw:type('Reply',(),{'status_code':200})())
    assert c.post('/api/classroom/disconnect',json={'confirmed':True,'remove_imports':True}).json['revoked']
    assert one(db,'SELECT COUNT(*) n FROM classroom_assignments')['n']==0
    assert one(db,'SELECT COUNT(*) n FROM tasks')['n']==1


def test_sync_error_retains_snapshot_and_scope_denial_never_saves_token(db_app,configured,monkeypatch):
    _,c,db=db_app
    monkeypatch.setattr(cc,'provider_json',lambda *a,**kw:{'refresh_token':'secret','scope':cc.SCOPES[0]})
    r=c.post('/api/classroom/connect',json={'confirmed':True});state=parse_qs(urlparse(r.json['url']).query)['state'][0]
    assert c.get('/api/classroom/callback',query_string={'state':state,'code':'code'}).status_code==503
    assert one(db,'SELECT COUNT(*) n FROM classroom_connections')['n']==0


def test_revoked_session_cannot_finish_oauth(db_app,configured):
    _,c,db=db_app
    r=c.post('/api/classroom/connect',json={'confirmed':True});state=parse_qs(urlparse(r.json['url']).query)['state'][0]
    with c.session_transaction() as s:s['session_version']=2
    assert c.get('/api/classroom/callback',query_string={'state':state,'code':'code'}).status_code in (400,401)
    assert one(db,'SELECT COUNT(*) n FROM classroom_connections')['n']==0


def test_failed_full_sync_keeps_previous_imports(db_app,configured,monkeypatch):
    _,c,db=db_app;connect(c)
    with db() as conn:
        with conn.cursor() as cur:
            cur.execute('UPDATE classroom_connections SET selected_courses=%s::jsonb WHERE user_id=1',('["one","two"]',))
            cur.execute("INSERT INTO classroom_assignments(user_id,course_id,external_id,title) VALUES(1,'one','old','Retained')")
    def pages(token,path,key,params):
        if path.endswith('two/courseWork'):raise cc.ProviderError('quota')
        return [{'id':'new','title':'New'}]
    monkeypatch.setattr(cc,'list_pages',pages)
    assert c.post('/api/classroom/sync',json={'confirmed':True}).status_code==503
    assert one(db,'SELECT COUNT(*) n FROM classroom_assignments')['n']==1
    assert one(db,'SELECT available FROM classroom_assignments')['available']
    assert one(db,'SELECT last_error FROM classroom_connections')['last_error']=='quota'


def selected_setup(c,monkeypatch):
    connect(c)
    def pages(token,path,key,params):
        return [{'id':'course1','name':'English'}] if path=='courses' else [{'id':'work','title':'Essay','description':'Original instruction'}]
    monkeypatch.setattr(cc,'list_pages',pages)
    courses=c.get('/api/classroom/courses?refresh=1').json
    assert c.post('/api/classroom/select',json={'confirmed':True,'courses':['course1'],'version':courses['version']}).status_code==200
    return c.get('/api/classroom/status').json['connection']['version']


def test_scheduler_opt_in_auth_backoff_and_disconnect(db_app,configured,monkeypatch):
    b,c,db=db_app;version=selected_setup(c,monkeypatch);monkeypatch.setattr(b,'CRON_SECRET','test-cron')
    headers={'X-Cron-Secret':'test-cron'}
    assert c.post('/api/cron/classroom').status_code==401
    assert c.post('/api/cron/classroom',headers=headers).json['processed']==0
    assert c.post('/api/classroom/schedule',json={'confirmed':True,'enabled':True,'version':version-1}).status_code==409
    assert c.post('/api/classroom/schedule',json={'confirmed':True,'enabled':True,'version':version}).status_code==200
    assert c.post('/api/cron/classroom',headers=headers).json['imported']==1
    row=one(db,'SELECT * FROM classroom_connections');assert row['auto_sync_enabled'] and row['next_sync_at']>row['last_sync'] and row['sync_failures']==0
    assert c.post('/api/cron/classroom',headers=headers).json['processed']==0
    with db() as conn:
        with conn.cursor() as cur:cur.execute("UPDATE classroom_connections SET next_sync_at=NOW()-INTERVAL '1 minute'")
    def failed(*a,**kw):raise cc.ProviderError('quota')
    monkeypatch.setattr(cc,'list_pages',failed)
    r=c.post('/api/cron/classroom',headers=headers);assert r.json['error_code']=='quota'
    assert one(db,'SELECT sync_failures FROM classroom_connections')['sync_failures']==1
    assert one(db,'SELECT COUNT(*) n FROM classroom_assignments WHERE available')['n']==1
    assert c.post('/api/classroom/disconnect',json={'confirmed':True,'remove_imports':False}).status_code==200
    assert c.post('/api/cron/classroom',headers=headers).json['processed']==0


def test_course_changes_cancel_auto_and_require_fresh_opt_in(db_app,configured,monkeypatch):
    _,c,db=db_app;v=selected_setup(c,monkeypatch)
    assert c.post('/api/classroom/schedule',json={'confirmed':True,'enabled':True,'version':v}).status_code==200
    v=c.get('/api/classroom/status').json['connection']['version']
    assert c.post('/api/classroom/select',json={'confirmed':True,'courses':[],'version':v}).status_code==200
    row=one(db,'SELECT auto_sync_enabled,next_sync_at FROM classroom_connections');assert not row['auto_sync_enabled'] and row['next_sync_at'] is None


def test_selected_assignment_ai_consent_ownership_no_memory_and_revocation_race(db_app,configured,monkeypatch):
    b,c,db=db_app;selected_setup(c,monkeypatch);c.post('/api/classroom/sync',json={'confirmed':True})
    aid=one(db,'SELECT id FROM classroom_assignments')['id'];url=f'/api/classroom/assignments/{aid}/explain';calls=[]
    def answer(messages,**kw):calls.append((messages,kw));return ('Small steps',{})
    monkeypatch.setattr(b,'generate_gemini_reply',answer)
    assert c.post(url,json={'confirmed':True}).status_code==400 and calls==[]
    with c.session_transaction() as s:s['user_id']=2
    assert c.post(url,json={'confirmed':True,'ai_confirmed':True}).status_code==404 and calls==[]
    with c.session_transaction() as s:s['user_id']=1
    r=c.post(url,json={'confirmed':True,'ai_confirmed':True,'language':'gu'});assert r.status_code==200,r.json
    assert r.json['explanation']=='Small steps' and not r.json['saved'] and not r.json['verified']
    assert calls[0][1]['memory_context']=='' and calls[0][1]['mode']=='explain' and calls[0][1]['language']=='gu'
    assert 'Original instruction' in calls[0][0][0]['content'] and 'untrusted' in calls[0][0][0]['content']
    assert one(db,'SELECT COUNT(*) n FROM tasks')['n']==0 and one(db,'SELECT COUNT(*) n FROM messages')['n']==0
    def changed(messages,**kw):
        with db() as conn:
            with conn.cursor() as cur:cur.execute('DELETE FROM classroom_connections')
        return ('Must not return',{})
    monkeypatch.setattr(b,'generate_gemini_reply',changed)
    assert c.post(url,json={'confirmed':True,'ai_confirmed':True}).status_code==409
