"""Real PostgreSQL integration checks; CI supplies a disposable local database."""
import hashlib
import hmac
import importlib
import json
import os
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse

import psycopg2
import psycopg2.extras
from psycopg2 import sql
import pytest
from werkzeug.security import generate_password_hash
import billing
from test_reliability import questions

pytestmark=pytest.mark.skipif(not os.environ.get('TEST_DATABASE_URL'),reason='Requires isolated PostgreSQL test service')


@pytest.fixture
def db_app(monkeypatch):
    dsn=os.environ['TEST_DATABASE_URL'];url=urlparse(dsn)
    assert url.hostname in {'localhost','127.0.0.1'} and url.path.endswith('_test'), 'Integration checks require a local test database'
    schema='saathi_test_'+uuid.uuid4().hex
    admin=psycopg2.connect(dsn);admin.autocommit=True
    with admin.cursor() as cur:cur.execute(sql.SQL('CREATE SCHEMA {}').format(sql.Identifier(schema)))
    def connect():return psycopg2.connect(dsn,options='-c search_path='+schema,cursor_factory=psycopg2.extras.RealDictCursor)
    os.environ.pop('DATABASE_URL',None)
    b=importlib.import_module('app');b.app.config.update(TESTING=True,SESSION_COOKIE_SECURE=False)
    monkeypatch.setattr(b,'get_db',connect);monkeypatch.setattr(b,'limited',lambda *args:None)
    try:
        b.run_migrations()
        with connect() as conn:
            with conn.cursor() as cur:
                for name in ('owner','other'):
                    cur.execute("INSERT INTO users(name,username,email,password_hash,created_at,email_verified_at) VALUES(%s,%s,%s,%s,NOW(),NOW())",(name,name,name+'@example.com',generate_password_hash('Localtest123')))
        client=b.app.test_client()
        with client.session_transaction() as session:
            session['user_id']=1;session['session_version']=1;session['csrf_token']='local-csrf'
        client.environ_base['HTTP_X_CSRF_TOKEN']='local-csrf'
        yield b,client,connect
    finally:
        with admin.cursor() as cur:cur.execute(sql.SQL('DROP SCHEMA {} CASCADE').format(sql.Identifier(schema)))
        admin.close()


def one(connect,query,params=()):
    conn=connect()
    try:
        with conn.cursor() as cur:cur.execute(query,params);return cur.fetchone()
    finally:conn.close()


def test_all_migrations_repeat_without_retiring_sessions_twice(db_app):
    b,client,connect=db_app
    b.run_migrations()
    assert one(connect,'SELECT session_version FROM users WHERE id=1')['session_version']==1
    assert one(connect,'SELECT count(*) AS n FROM schema_migrations')['n']==len(list(Path('migrations').glob('*.sql')))
    assert client.get('/api/me').status_code==200


def test_pending_username_does_not_block_new_signup(db_app,monkeypatch):
    b,client,connect=db_app
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO pending_verifications(email,name,username,password_hash,otp_hash,expires_at) VALUES('old@example.com','Old','available_name','hash','hash',NOW()-INTERVAL '1 hour')")
    response=client.get('/api/check-username?username=available_name')
    assert response.status_code==200 and response.json['available'] is True
    monkeypatch.setattr(b,'BREVO_API_KEY','local-fixture');monkeypatch.setattr(b,'BREVO_SENDER_EMAIL','sender@example.com');monkeypatch.setattr(b,'send_otp_email',lambda *args:None)
    response=client.post('/api/signup',json={'name':'New Student','username':'available_name','email':'new@example.com','password':'Localtest123'})
    assert response.status_code==200 and response.json['pending'] is True


def test_mock_test_ownership_answers_expiry_and_retry(db_app,monkeypatch):
    b,client,connect=db_app
    monkeypatch.setattr(b,'generate_study_json',lambda *args:questions())
    generated=client.post('/api/mock-tests/generate',json={'topic':'ગણિત','question_count':5,'time_limit_minutes':5})
    assert generated.status_code==200,generated.json
    test=generated.json['test'];tid=test['id']
    assert 'correct_option' not in json.dumps(test)
    first=client.post(f'/api/mock-tests/{tid}/submit',json={'answers':{'1':'A'},'score':5,'time_taken_seconds':-999})
    assert first.status_code==200 and first.json['attempt']['score']==1
    repeated=client.post(f'/api/mock-tests/{tid}/submit',json={'answers':{'1':'B'}})
    assert repeated.json==first.json
    assert one(connect,'SELECT count(*) AS n FROM mock_test_attempts')['n']==1
    with client.session_transaction() as session:session['user_id']=2
    assert client.get(f'/api/mock-tests/{tid}').status_code==404
    assert client.post(f'/api/mock-tests/{tid}/submit',json={}).status_code==404
    with client.session_transaction() as session:session['user_id']=1
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO mock_tests(user_id,topic,question_count,time_limit_minutes,questions_json,created_at) VALUES(1,'Expired',5,5,%s,NOW()-INTERVAL '1 hour') RETURNING id",(json.dumps(questions()),));expired=cur.fetchone()
    assert client.post(f"/api/mock-tests/{expired['id']}/submit",json={'answers':{}}).status_code==410


def test_invalid_generated_content_is_not_saved_or_charged_to_quota(db_app,monkeypatch):
    b,client,connect=db_app
    monkeypatch.setattr(b,'generate_study_json',lambda *args:{'root':{'label':'Empty'}})
    result=client.post('/api/mindmaps/generate',json={'topic':'Photosynthesis'})
    assert result.status_code==400
    assert one(connect,'SELECT count(*) AS n FROM mindmaps')['n']==0
    for path,data in [('/api/mock-tests/generate',{'topic':'Math','language':[]}),('/api/healer/consult',{'symptoms':'Tired','language':[]})]:
        assert client.post(path,json=data).status_code==400


def test_due_reminder_completion_is_owned_and_idempotent(db_app):
    b,client,connect=db_app
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO reminders(user_id,title,next_run_at,recurrence,created_at) VALUES(1,'Stretch break',NOW()-INTERVAL '1 hour','daily',NOW()) RETURNING *");reminder=cur.fetchone()
    nudge=client.get('/api/care/nudge').json['nudge']
    assert nudge['phase']=='scheduled' and 'Stretch break' in nudge['message']
    path=f"/api/reminders/{reminder['id']}/ack";payload={'scheduled_at':nudge['scheduled_at']}
    assert client.post(path,json={}).status_code==400
    first=client.post(path,json=payload);assert first.status_code==200,first.json
    second=client.post(path,json=payload)
    assert second.json['already_completed'] is True
    assert first.json['reminder']['next_run_at']==second.json['reminder']['next_run_at']
    with client.session_transaction() as session:session['user_id']=2
    assert client.post(path,json=payload).status_code==404


def configure_payments(monkeypatch,mode='live'):
    monkeypatch.setenv('SAATHI_BILLING_MODE',mode);monkeypatch.setenv('MERCHANT_VERIFIED','true')
    monkeypatch.setenv('RAZORPAY_KEY_ID','rzp_'+mode+'_localfixture')
    monkeypatch.setenv('RAZORPAY_KEY_SECRET','local-test-secret');monkeypatch.setenv('RAZORPAY_WEBHOOK_SECRET','local-test-webhook')


def test_payment_ownership_capture_idempotency_and_refund(db_app,monkeypatch):
    b,client,connect=db_app;configure_payments(monkeypatch)
    payment={'id':'pay_fixture','order_id':'order_fixture','amount':19900,'currency':'INR','status':'captured','captured':True,'amount_refunded':0}
    monkeypatch.setattr(billing,'provider',lambda method,path,**kwargs:{'id':'order_fixture','amount':19900,'currency':'INR'} if method=='POST' else payment)
    assert client.post('/api/payment/create-order',json={'price_key':[]}).status_code==400
    created=client.post('/api/payment/create-order',json={'price_key':'plus_monthly'});assert created.status_code==200,created.json
    payload={'razorpay_order_id':'order_fixture','razorpay_payment_id':'pay_fixture','razorpay_signature':hmac.new(b'local-test-secret',b'order_fixture|pay_fixture',hashlib.sha256).hexdigest(),'plan':'family'}
    with client.session_transaction() as session:session['user_id']=2
    assert client.post('/api/payment/verify',json=payload).status_code==404
    with client.session_transaction() as session:session['user_id']=1
    payment['status']='authorized'
    assert client.post('/api/payment/verify',json=payload).status_code==400
    assert one(connect,'SELECT plan FROM users WHERE id=1')['plan']=='free'
    payment['status']='captured'
    first=client.post('/api/payment/verify',json=payload);assert first.status_code==200,first.json
    assert first.json['user']['plan']=='plus'
    repeated=client.post('/api/payment/verify',json=payload)
    assert first.json['user']['subscription_end_at']==repeated.json['user']['subscription_end_at']
    def webhook(event,payment):
        raw=json.dumps({'event':event,'payload':{'payment':{'entity':payment}}}).encode()
        sig=hmac.new(b'local-test-webhook',raw,hashlib.sha256).hexdigest()
        return client.post('/api/payment/webhook',data=raw,content_type='application/json',headers={'X-Razorpay-Signature':sig})
    refund={**payment,'amount_refunded':19900,'status':'refunded'}
    assert webhook('payment.refunded',refund).status_code==200
    assert one(connect,'SELECT plan FROM users WHERE id=1')['plan']=='free'
    assert webhook('payment.refunded',refund).status_code==200
    assert webhook('payment.captured',payment).status_code==200
    assert one(connect,"SELECT status FROM payment_orders WHERE order_id='order_fixture'")['status']=='refunded'
    assert client.post('/api/payment/verify',json=payload).status_code==400


def test_test_payment_never_activates_real_access(db_app,monkeypatch):
    b,client,connect=db_app;configure_payments(monkeypatch,'test')
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO payment_orders(order_id,user_id,price_key,plan,amount,duration_days,is_test) VALUES('order_test',1,'plus_monthly','plus',19900,30,TRUE) RETURNING *");order=cur.fetchone()
            user=billing.settle(cur,order,{'id':'pay_test','order_id':'order_test','amount':19900,'currency':'INR','captured':True,'status':'captured'})
            assert billing.effective_plan(user)=='free'
    assert one(connect,'SELECT count(*) AS n FROM access_grants')['n']==0


def test_refund_preserves_only_independently_earned_days(db_app):
    _,_,connect=db_app
    with connect() as conn:
        with conn.cursor() as cur:
            billing.grant_access(cur,1,'payment:one','plus',30)
            both=billing.grant_access(cur,1,'payment:two','plus',30)
            assert (both['subscription_end_at']-datetime.now(timezone.utc)).days>=59
            after=billing.revoke_access(cur,1,'payment:one')
            assert 29<=(after['subscription_end_at']-datetime.now(timezone.utc)).total_seconds()/86400<=31


def test_referral_reward_and_export_include_only_owned_data(db_app):
    b,client,connect=db_app
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE users SET referred_by_id=1,created_at=NOW()-INTERVAL '2 days' WHERE id=2")
            cur.execute("INSERT INTO tasks(user_id,title,completed,created_at,updated_at) VALUES(2,'Private friend task',TRUE,NOW(),NOW())")
    response=client.post('/api/referrals/claim',json={});assert response.status_code==200,response.json
    end=response.json['user']['subscription_end_at']
    repeated=client.post('/api/referrals/claim',json={})
    assert repeated.json['user']['subscription_end_at']==end
    assert one(connect,'SELECT count(*) AS n FROM referral_rewards')['n']==1
    exported=client.get('/api/export-data');assert exported.status_code==200
    assert 'mock_tests' in exported.json and 'payment_orders' in exported.json
    assert 'password_hash' not in exported.json['account']
    assert 'Private friend task' not in exported.get_data(as_text=True)
