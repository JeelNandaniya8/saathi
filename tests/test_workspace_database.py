"""End-to-end account ownership and scheduled push checks in disposable PostgreSQL."""
import json
import os
import uuid
from concurrent.futures import ThreadPoolExecutor
from threading import Event
import pytest
import auth_google
import push_notifications as push
from test_database_flows import db_app,one
from test_workspace_extras import push_fixture

pytestmark=pytest.mark.skipif(not os.environ.get('TEST_DATABASE_URL'),reason='Requires isolated PostgreSQL test service')


def test_notes_crud_retry_conflict_and_export(db_app):
    _,client,connect=db_app
    data={'client_id':str(uuid.uuid4()),'title':'અભ્યાસ','content':'ગુજરાતી notes <script>literal</script>'}
    response=client.post('/api/quick-notes',json=data);assert response.status_code==201,response.json
    note=response.json['note'];path='/api/quick-notes/'+str(note['id'])
    retry=client.post('/api/quick-notes',json={**data,'content':'newer draft'})
    assert retry.json['replayed'] is True and retry.json['note']==note
    assert len(client.get('/api/quick-notes').json['notes'])==1
    assert client.patch(path,json={**data,'version':True}).status_code==400
    changed=client.patch(path,json={**data,'version':1,'content':'Updated note'})
    assert changed.status_code==200 and changed.json['note']['version']==2
    assert client.patch(path,json={**data,'version':1}).status_code==409
    assert client.delete(path,json={'version':1}).status_code==409
    exported=client.get('/api/export-data');assert exported.status_code==200
    assert exported.json['quick_notes'][0]['content']=='Updated note'
    with client.session_transaction() as session:session['user_id']=2
    assert client.get('/api/quick-notes').json['notes']==[]
    assert client.patch(path,json={**data,'version':2}).status_code==404
    assert client.delete(path,json={'version':2}).status_code==404
    assert client.get('/api/export-data').json['quick_notes']==[]
    with client.session_transaction() as session:session['user_id']=1
    assert client.delete(path,json={'version':2}).status_code==200
    assert one(connect,'SELECT count(*) AS n FROM quick_notes')['n']==0


def test_notes_login_csrf_and_account_limit(db_app):
    _,client,connect=db_app
    data={'client_id':str(uuid.uuid4()),'content':'Note'}
    assert client.post('/api/quick-notes',json=data,headers={'X-CSRF-Token':''}).status_code==403
    with connect() as conn:
        with conn.cursor() as cur:
            for _ in range(100):cur.execute("INSERT INTO quick_notes(user_id,client_id,title,content) VALUES(1,%s,'note','note')",(str(uuid.uuid4()),))
    assert client.post('/api/quick-notes',json=data).status_code==400
    with client.session_transaction() as session:session.clear()
    assert client.get('/api/quick-notes').status_code==401


def test_google_photo_only_comes_from_verified_identity(db_app,monkeypatch):
    b,client,connect=db_app;monkeypatch.setattr(b,'GOOGLE_CLIENT_ID','local-fixture')
    claims={'email':'owner@example.com','hd':'example.com','sub':'verified-owner','picture':'https://lh3.googleusercontent.com/a/avatar'}
    monkeypatch.setattr(auth_google,'verify_credential',lambda *args:dict(claims))
    client.get('/api/auth/config')
    result=client.post('/api/google-auth',json={'credential':'mock-verified','picture':'https://evil.test/stolen'})
    assert result.status_code==200,result.json
    assert result.json['user']['avatar_url']==claims['picture']
    assert one(connect,'SELECT avatar_url FROM users WHERE id=1')['avatar_url']==claims['picture']
    client.get('/api/auth/config');claims.pop('picture')
    result=client.post('/api/google-auth',json={'credential':'mock-verified'})
    assert result.json['user']['avatar_url']=='https://lh3.googleusercontent.com/a/avatar'
    client.get('/api/auth/config');claims['picture']='https://googleusercontent.com.evil.test/a'
    assert client.post('/api/google-auth',json={'credential':'mock-verified'}).json['user']['avatar_url'] is None


def reminder(connect,offset="1 minute",active=True,owner=1):
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO reminders(user_id,title,note,next_run_at,active,created_at) VALUES(%s,'Private title','Private note',NOW()-%s::interval,%s,NOW()) RETURNING id",(owner,offset,active));return cur.fetchone()['id']


def subscribed(db_app,monkeypatch):
    b,client,connect=db_app;subscription=push_fixture(monkeypatch)
    result=client.post('/api/push/subscriptions',json=subscription);assert result.status_code==200,result.json
    return subscription,result.json['id']


def test_subscription_ownership_csrf_config_and_logout(db_app,monkeypatch):
    b,client,connect=db_app;subscription,sid=subscribed(db_app,monkeypatch)
    assert client.post('/api/push/subscriptions',json=subscription).json['id']==sid
    config=client.get('/api/push/config').json
    assert config['enabled'] is True and config['subscriptions'][0]['id']==sid
    assert 'private_key' not in config and 'endpoint' not in config['subscriptions'][0]
    assert client.post('/api/push/subscriptions',json=subscription,headers={'X-CSRF-Token':''}).status_code==403
    with client.session_transaction() as session:session['user_id']=2
    assert client.post('/api/push/subscriptions',json=subscription).status_code==409
    assert client.delete('/api/push/subscriptions/'+str(sid)).status_code==200
    assert one(connect,'SELECT count(*) AS n FROM push_subscriptions')['n']==1
    with client.session_transaction() as session:session['user_id']=1
    assert client.post('/api/logout',json={}).status_code==200
    assert one(connect,'SELECT count(*) AS n FROM push_subscriptions')['n']==0
    assert client.get('/api/push/config').status_code==401


def test_due_push_is_generic_owned_deduplicated_and_cron_protected(db_app,monkeypatch):
    b,client,connect=db_app;subscribed(db_app,monkeypatch);rid=reminder(connect)
    reminder(connect,owner=2);reminder(connect,active=False);reminder(connect,offset='-1 hour');reminder(connect,offset='2 days')
    calls=[];monkeypatch.setattr(push,'send_push',lambda sub,payload,config:calls.append(payload) or 201)
    monkeypatch.setattr(b,'CRON_SECRET','test-cron-only');monkeypatch.setattr(b,'BREVO_API_KEY','')
    assert client.post('/api/cron/reminders').status_code==401
    result=client.post('/api/cron/reminders',headers={'X-Cron-Secret':'test-cron-only'})
    assert result.status_code==200 and result.json['push']['sent']==1,result.json
    assert 'Private' not in json.dumps(calls) and calls[0]['url']=='/dashboard#reminders'
    repeated=client.post('/api/cron/reminders',headers={'X-Cron-Secret':'test-cron-only'})
    assert repeated.json['push']['sent']==0 and len(calls)==1
    assert one(connect,'SELECT active FROM reminders WHERE id=%s',(rid,))['active'] is True
    assert 'fcm.googleapis.com' not in client.get('/api/export-data').get_data(as_text=True)


def test_push_failures_retry_then_stop_and_expired_devices_are_removed(db_app,monkeypatch):
    b,_,connect=db_app;subscribed(db_app,monkeypatch);reminder(connect)
    calls=[];monkeypatch.setattr(push,'send_push',lambda *args:calls.append(1) or 429)
    for _ in range(5):
        push.deliver_due(vars(b))
        with connect() as conn:
            with conn.cursor() as cur:cur.execute("UPDATE push_deliveries SET updated_at=NOW()-INTERVAL '6 minutes'")
    assert push.deliver_due(vars(b))['failed']==0 and len(calls)==5
    with connect() as conn:
        with conn.cursor() as cur:cur.execute('DELETE FROM push_deliveries')
    monkeypatch.setattr(push,'send_push',lambda *args:410)
    assert push.deliver_due(vars(b))['skipped']==1
    assert one(connect,'SELECT count(*) AS n FROM push_subscriptions')['n']==0


def test_concurrent_cron_and_session_revocation(db_app,monkeypatch):
    b,client,connect=db_app;subscribed(db_app,monkeypatch);reminder(connect)
    entered=Event();release=Event();calls=[]
    def sender(*args):calls.append(1);entered.set();assert release.wait(5);return 201
    monkeypatch.setattr(push,'send_push',sender)
    with ThreadPoolExecutor(max_workers=1) as pool:
        first=pool.submit(push.deliver_due,vars(b))
        assert entered.wait(5)
        try:assert push.deliver_due(vars(b))['sent']==0
        finally:release.set()
        assert first.result()['sent']==1
    assert len(calls)==1
    reminder(connect)
    assert client.post('/api/logout-all',json={}).status_code==200
    assert push.deliver_due(vars(b))['sent']==0 and len(calls)==1
