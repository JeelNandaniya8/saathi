"""Disposable PostgreSQL + synthetic Google responses; never uses real files."""
import json
import os
from urllib.parse import urlparse,parse_qs
import pytest
from cryptography.fernet import Fernet
from psycopg2.extras import Json
from test_database_flows import db_app,one
import classroom_integration as cc
import classroom_files as files
from test_classroom_files import Response

pytestmark=pytest.mark.skipif(not os.environ.get('TEST_DATABASE_URL'),reason='Requires isolated PostgreSQL')

@pytest.fixture
def prepared(db_app,monkeypatch):
    b,c,db=db_app
    for key,value in {'CLASSROOM_ENABLED':'true','CLASSROOM_FILE_PICKER_ENABLED':'true','CLASSROOM_CLIENT_ID':'fixture',
        'CLASSROOM_CLIENT_SECRET':'fixture-secret','CLASSROOM_REDIRECT_URI':'https://example.test/api/classroom/callback',
        'CLASSROOM_TOKEN_KEY':Fernet.generate_key().decode()}.items():monkeypatch.setenv(key,value)
    with db() as conn:
        with conn.cursor() as cur:
            cur.execute("""INSERT INTO classroom_connections(user_id,refresh_cipher,selected_courses,course_catalog)
                VALUES(1,%s,'["course"]','[{"id":"course","name":"Synthetic course"}]')""",(cc.cipher().encrypt(b'original-classroom-refresh').decode(),))
            cur.execute("""INSERT INTO classroom_assignments(user_id,course_id,external_id,title,instructions,file_materials)
                VALUES(1,'course','work','Synthetic worksheet','Read the attached worksheet',%s) RETURNING id""",
                (Json([{'id':'fixture_pdf','title':'Practice.pdf','url':'https://drive.google.com/open?id=fixture_pdf'}]),))
            aid=cur.fetchone()['id']
    def provider(method,url,**kwargs):
        if url==cc.TOKEN:return {'scope':files.DRIVE_SCOPE,'access_token':'short-lived-fixture','expires_in':3600}
        assert url==files.DRIVE+'fixture_pdf'
        return {'id':'fixture_pdf','mimeType':'application/pdf','size':'17','capabilities':{'canDownload':True}}
    monkeypatch.setattr(cc,'provider_json',provider)
    monkeypatch.setattr(files.requests,'get',lambda *a,**kw:Response())
    monkeypatch.setattr(b,'generate_gemini_reply',lambda *a,**kw:pytest.fail('File preparation must not call AI'))
    return b,c,db,aid

def begin(prepared):
    _,c,_,aid=prepared
    result=c.post(f'/api/classroom/assignments/{aid}/files/fixture_pdf/authorize',json={'confirmed':True,'file_confirmed':True})
    assert result.status_code==200,result.json
    return parse_qs(urlparse(result.json['url']).query)

def finish(prepared,query=None,**extra):
    _,c,_,_=prepared;query=query or begin(prepared)
    return c.get('/api/classroom/callback',query_string={'state':query['state'][0],'code':'fixture-code','picked_file_ids':'fixture_pdf',**extra})

def grant(prepared):
    result=finish(prepared);assert result.status_code==302 and result.location.startswith('/chat?classroom_file='),result.location
    return parse_qs(urlparse(result.location).query)['classroom_file'][0]

def test_per_file_pkce_consent_scope_and_encrypted_short_lived_grant(prepared):
    _,c,db,_=prepared
    before=one(db,'SELECT refresh_cipher,version,selected_courses FROM classroom_connections')
    query=begin(prepared)
    assert query['scope']==[files.DRIVE_SCOPE] and query['access_type']==['online']
    assert query['trigger_onepick']==['true'] and query['file_ids']==['fixture_pdf'] and query['allow_multiple']==['false']
    assert query['code_challenge_method']==['S256'] and query['prompt']==['consent']
    result=finish(prepared,query);assert result.location.startswith('/chat?classroom_file=')
    stored=one(db,'SELECT * FROM classroom_file_grants')
    assert stored['access_cipher']!='short-lived-fixture' and cc.cipher().decrypt(stored['access_cipher'].encode())==b'short-lived-fixture'
    assert (stored['expires_at']-stored['created_at']).total_seconds()<=601
    assert one(db,'SELECT refresh_cipher,version,selected_courses FROM classroom_connections')==before
    assert c.get('/api/classroom/callback',query_string={'state':query['state'][0],'code':'fixture-code'}).location.endswith('classroom_result=expired#study')
    assert 'short-lived-fixture' not in c.get('/api/export-data').get_data(as_text=True)

@pytest.mark.parametrize('payload',[{}, {'confirmed':True},{'file_confirmed':True}])
def test_selection_requires_explicit_file_consent(prepared,payload):
    _,c,db,aid=prepared
    assert c.post(f'/api/classroom/assignments/{aid}/files/fixture_pdf/authorize',json=payload).status_code==400
    assert one(db,'SELECT count(*) n FROM classroom_oauth_requests')['n']==0

def test_disabled_feature_never_starts_google_flow(prepared,monkeypatch):
    _,c,db,aid=prepared;monkeypatch.delenv('CLASSROOM_FILE_PICKER_ENABLED')
    assert c.get('/api/classroom/status').json['file_picker_ready'] is False
    assert c.post(f'/api/classroom/assignments/{aid}/files/fixture_pdf/authorize',json={'confirmed':True,'file_confirmed':True}).status_code==400

@pytest.mark.parametrize('callback',[
    {'error':'access_denied'},{'picked_file_ids':'other_file'},
    {'picked_file_ids':'fixture_pdf,other_file'},{'picked_file_ids':''}])
def test_cancel_or_wrong_file_preserves_classroom_and_creates_no_grant(prepared,callback):
    _,_,db,_=prepared;before=one(db,'SELECT * FROM classroom_connections')
    result=finish(prepared,**callback)
    assert result.location.startswith('/dashboard?classroom_result=file_')
    assert one(db,'SELECT count(*) n FROM classroom_file_grants')['n']==0
    assert one(db,'SELECT * FROM classroom_connections')==before

def test_extra_scope_is_rejected_not_silently_accepted(prepared,monkeypatch):
    _,_,db,_=prepared
    monkeypatch.setattr(cc,'provider_json',lambda *a,**kw:{'scope':files.DRIVE_SCOPE+' https://www.googleapis.com/auth/drive.readonly','access_token':'fixture','expires_in':3600})
    assert 'file_failed' in finish(prepared).location
    assert one(db,'SELECT count(*) n FROM classroom_file_grants')['n']==0

@pytest.mark.parametrize('change',[
    "UPDATE classroom_connections SET version=version+1",
    "UPDATE classroom_assignments SET available=FALSE",
    "UPDATE classroom_assignments SET file_materials='[]'",
    "UPDATE classroom_connections SET selected_courses='[]'"])
def test_changed_source_or_course_invalidates_before_download(prepared,monkeypatch,change):
    _,c,db,_=prepared;gid=grant(prepared)
    with db() as conn:
        with conn.cursor() as cur:cur.execute(change)
    monkeypatch.setattr(cc,'provider_json',lambda *a,**kw:pytest.fail('Changed permission must not read Google'))
    assert c.get(f'/api/classroom/files/{gid}/download').status_code in (400,409)

def test_source_change_during_consent_cannot_mint_a_grant(prepared):
    _,_,db,_=prepared;query=begin(prepared)
    with db() as conn:
        with conn.cursor() as cur:cur.execute('UPDATE classroom_connections SET version=version+1')
    assert 'file_failed' in finish(prepared,query).location
    assert one(db,'SELECT count(*) n FROM classroom_file_grants')['n']==0

def test_download_is_private_repeatable_exact_and_does_not_send_or_spend_uploads(prepared):
    _,c,db,_=prepared;gid=grant(prepared);url=f'/api/classroom/files/{gid}/download'
    first=c.get(url);second=c.get(url)
    assert first.status_code==second.status_code==200
    assert first.data==second.data==b'%PDF-1.4\nSynthetic'
    assert first.headers['X-Saathi-File-Name']=='Practice.pdf'
    assert first.headers['X-Saathi-File-Modified']==second.headers['X-Saathi-File-Modified']
    assert 'no-store' in first.headers['Cache-Control']
    assert one(db,'SELECT count(*) n FROM chat_attachments')['n']==0
    assert one(db,'SELECT count(*) n FROM messages')['n']==0
    assert one(db,'SELECT count(*) n FROM classroom_file_grants')['n']==1

def test_a_changed_download_cannot_replace_bytes_of_the_same_grant(prepared,monkeypatch):
    _,c,_,_=prepared;gid=grant(prepared);url=f'/api/classroom/files/{gid}/download'
    assert c.get(url).status_code==200
    monkeypatch.setattr(files.requests,'get',lambda *a,**kw:Response(body=b'%PDF-1.4\nChanged'))
    result=c.get(url);assert result.status_code==409 and result.json['error_code']=='file_changed'

@pytest.mark.parametrize('invalidator',['other_user','expired','session','disconnect'])
def test_owner_expiry_session_and_disconnect_are_checked_before_google(prepared,monkeypatch,invalidator):
    _,c,db,_=prepared;gid=grant(prepared)
    if invalidator=='other_user':
        with c.session_transaction() as s:s['user_id']=2
    elif invalidator=='session':
        with db() as conn:
            with conn.cursor() as cur:cur.execute('UPDATE classroom_file_grants SET session_version=2')
    else:
        with db() as conn:
            with conn.cursor() as cur:cur.execute('DELETE FROM classroom_connections' if invalidator=='disconnect' else "UPDATE classroom_file_grants SET expires_at=NOW()-INTERVAL '1 second'")
    monkeypatch.setattr(cc,'provider_json',lambda *a,**kw:pytest.fail('Unavailable grants must not read Google'))
    assert c.get(f'/api/classroom/files/{gid}/download').status_code==410

@pytest.mark.parametrize('metadata',[
    {'id':'fixture_pdf','mimeType':'application/pdf','capabilities':[]},
    {'id':'fixture_pdf','mimeType':None,'capabilities':{}},
    {'id':'fixture_pdf','mimeType':[],'capabilities':{}}
])
def test_malformed_provider_metadata_is_a_recoverable_file_error(prepared,monkeypatch,metadata):
    _,c,db,_=prepared;gid=grant(prepared)
    monkeypatch.setattr(cc,'provider_json',lambda *a,**kw:metadata)
    result=c.get(f'/api/classroom/files/{gid}/download')
    assert result.status_code==400 and result.json['error_code'] in ('file_provider','file_type')
    assert one(db,'SELECT count(*) n FROM messages')['n']==0
    assert one(db,'SELECT count(*) n FROM chat_attachments')['n']==0

def test_permission_change_during_download_never_delivers_the_bytes(prepared,monkeypatch):
    _,c,db,_=prepared;gid=grant(prepared)
    def changed(*args,**kwargs):
        with db() as conn:
            with conn.cursor() as cur:cur.execute("UPDATE classroom_connections SET selected_courses='[]'")
        return Response()
    monkeypatch.setattr(files.requests,'get',changed)
    result=c.get(f'/api/classroom/files/{gid}/download')
    assert result.status_code==400 and result.json['error_code']=='file_unavailable'
    assert b'%PDF-' not in result.data
    assert one(db,'SELECT download_hash FROM classroom_file_grants')['download_hash'] is None

def test_user_session_change_during_google_callback_cannot_mint_access(prepared,monkeypatch):
    _,_,db,_=prepared
    def changed(*args,**kwargs):
        with db() as conn:
            with conn.cursor() as cur:cur.execute('UPDATE users SET session_version=2 WHERE id=1')
        return {'scope':files.DRIVE_SCOPE,'access_token':'fixture','expires_in':3600}
    monkeypatch.setattr(cc,'provider_json',changed)
    assert 'file_failed' in finish(prepared).location
    assert one(db,'SELECT count(*) n FROM classroom_file_grants')['n']==0
