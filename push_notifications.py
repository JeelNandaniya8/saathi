"""Opt-in, owned Web Push subscriptions and deduplicated scheduled delivery."""
import base64
import hashlib
import json
import os
import re
from contextlib import contextmanager
from datetime import datetime,timedelta,timezone
from functools import wraps
from urllib.parse import urlsplit

import requests
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from flask import jsonify,request,session


def decode_key(value):
    if not isinstance(value,str) or len(value)>512 or not re.fullmatch(r'[A-Za-z0-9_-]+={0,2}',value):
        raise ValueError('Invalid push key.')
    return base64.urlsafe_b64decode(value+'='*(-len(value)%4))


def endpoint_allowed(endpoint):
    if not isinstance(endpoint,str) or not 1<=len(endpoint)<=4096 or any(c.isspace() or c=='\\' for c in endpoint):return False
    try:
        url=urlsplit(endpoint);host=(url.hostname or '').lower()
        if url.scheme!='https' or url.username or url.password or url.port not in (None,443) or url.fragment:return False
        return bool(url.path and url.path!='/') and (host in {'fcm.googleapis.com','updates.push.services.mozilla.com','web.push.apple.com'} or
            bool(re.fullmatch(r'[a-z0-9-]+\.push\.apple\.com',host)) or bool(re.fullmatch(r'[a-z0-9-]+\.notify\.windows\.com',host)))
    except ValueError:return False


def validate_subscription(data):
    if not isinstance(data,dict) or not endpoint_allowed(data.get('endpoint')):raise ValueError('This browser push service is not supported.')
    keys=data.get('keys')
    if not isinstance(keys,dict):raise ValueError('Invalid browser subscription.')
    try:
        point=decode_key(keys.get('p256dh'));auth=decode_key(keys.get('auth'))
        if len(point)!=65 or len(auth)!=16:raise ValueError('Invalid key size')
        ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(),point)
    except (ValueError,TypeError):raise ValueError('Invalid browser subscription keys.') from None
    return {'endpoint':data['endpoint'],'keys':{'p256dh':keys['p256dh'],'auth':keys['auth']}}


def configuration():
    public=os.environ.get('VAPID_PUBLIC_KEY','').strip();private=os.environ.get('VAPID_PRIVATE_KEY','').strip()
    subject=os.environ.get('VAPID_SUBJECT','').strip()
    enabled=False
    if public and private and len(private)<2048 and re.fullmatch(r'mailto:[^\s@]+@[^\s@]+\.[^\s@]+',subject):
        try:
            key=serialization.load_der_private_key(decode_key(private),password=None)
            if isinstance(key,ec.EllipticCurvePrivateKey) and isinstance(key.curve,ec.SECP256R1):
                expected=key.public_key().public_bytes(serialization.Encoding.X962,serialization.PublicFormat.UncompressedPoint)
                enabled=expected==decode_key(public)
        except (ValueError,TypeError):pass
    return {'enabled':enabled,'public_key':public if enabled else None,'private_key':private,'subject':subject}


class PushSession(requests.Session):
    def request(self,method,url,**kwargs):
        if not endpoint_allowed(url):raise ValueError('Unsupported push destination.')
        kwargs['allow_redirects']=False
        return super().request(method,url,**kwargs)


def send_push(subscription,payload,config):
    # Imported on delivery, so missing configuration never blocks ordinary app use.
    from pywebpush import webpush,WebPushException
    try:
        with PushSession() as session:
            response=webpush(subscription_info=subscription,data=json.dumps(payload,ensure_ascii=False),
                vapid_private_key=config['private_key'],vapid_claims={'sub':config['subject']},
                ttl=900,timeout=5,requests_session=session,headers={'Urgency':'normal'})
        return response.status_code
    except WebPushException as error:
        return getattr(error,'status_code',None) or (error.response.status_code if error.response is not None else 503)
    except requests.RequestException:return 503


@contextmanager
def database(b):
    conn=b['get_db']();cur=conn.cursor()
    try:yield conn,cur
    except Exception:
        conn.rollback();raise
    finally:cur.close();conn.close()


def deliver_due(b):
    config=configuration()
    if not config['enabled']:return {'configured':False,'sent':0,'failed':0,'skipped':0}
    now=datetime.now(timezone.utc)
    with database(b) as (_,cur):
        cur.execute('''SELECT s.id AS subscription_id,s.subscription_json,r.id AS reminder_id,r.next_run_at
            FROM push_subscriptions s JOIN users u ON u.id=s.user_id AND u.session_version=s.session_version
            JOIN reminders r ON r.user_id=s.user_id
            LEFT JOIN push_deliveries d ON d.subscription_id=s.id AND d.reminder_id=r.id AND d.scheduled_for=r.next_run_at
            WHERE r.active=TRUE AND r.next_run_at<=%s AND r.next_run_at>=%s
            AND (d.id IS NULL OR (d.status='failed' AND d.attempt_count<5 AND d.updated_at<%s)
                 OR (d.status='processing' AND d.attempt_count<5 AND d.updated_at<%s))
            ORDER BY r.next_run_at,s.id LIMIT 10''',(now,now-timedelta(days=1),now-timedelta(minutes=2),now-timedelta(minutes=5)))
        due=cur.fetchall()
    result={'configured':True,'sent':0,'failed':0,'skipped':0}
    for item in due:
        with database(b) as (conn,cur):
            cur.execute('''INSERT INTO push_deliveries(subscription_id,reminder_id,scheduled_for)
                SELECT s.id,r.id,r.next_run_at FROM push_subscriptions s
                JOIN users u ON u.id=s.user_id AND u.session_version=s.session_version
                JOIN reminders r ON r.user_id=s.user_id
                WHERE s.id=%s AND r.id=%s AND r.active=TRUE AND r.next_run_at=%s
                ON CONFLICT(subscription_id,reminder_id,scheduled_for) DO UPDATE SET status='processing',attempt_count=push_deliveries.attempt_count+1,updated_at=NOW()
                WHERE push_deliveries.attempt_count<5 AND
                ((push_deliveries.status='failed' AND push_deliveries.updated_at<%s)
                 OR (push_deliveries.status='processing' AND push_deliveries.updated_at<%s)) RETURNING id''',
                (item['subscription_id'],item['reminder_id'],item['next_run_at'],now-timedelta(minutes=2),now-timedelta(minutes=5)))
            claim=cur.fetchone();conn.commit()
        if not claim:result['skipped']+=1;continue
        tag='saathi-reminder-'+str(item['reminder_id'])+'-'+str(int(item['next_run_at'].timestamp()))
        payload={'title':'Saathi reminder','body':'A reminder you scheduled is due. Open Saathi to review it.','url':'/dashboard#reminders','tag':tag}
        try:status=send_push(validate_subscription(item['subscription_json']),payload,config)
        except (ValueError,ImportError):status=503
        sent=200<=status<300
        with database(b) as (conn,cur):
            if status in (404,410):
                cur.execute('DELETE FROM push_subscriptions WHERE id=%s',(item['subscription_id'],))
                result['skipped']+=1
            else:
                cur.execute("UPDATE push_deliveries SET status=%s,updated_at=NOW(),sent_at=CASE WHEN %s THEN NOW() ELSE sent_at END WHERE id=%s",('sent' if sent else 'failed',sent,claim['id']))
                result['sent' if sent else 'failed']+=1
            conn.commit()
    return result


def remove_device(b,uid,subscription_id):
    if type(subscription_id) is not int:return
    with database(b) as (conn,cur):
        cur.execute('DELETE FROM push_subscriptions WHERE id=%s AND user_id=%s',(subscription_id,uid));conn.commit()


def register(app,b):
    def private(fn):
        @wraps(fn)
        def wrapped(*args,**kwargs):
            uid=b['require_user_id']()
            if not uid:return jsonify(error='Please log in first.'),401
            try:return fn(uid,*args,**kwargs)
            except ValueError as error:return jsonify(error=str(error)),400
        return wrapped

    @app.get('/api/push/config')
    @private
    def push_config(uid):
        config=configuration()
        with database(b) as (_,cur):
            cur.execute('SELECT id,endpoint_hash FROM push_subscriptions WHERE user_id=%s AND session_version=(SELECT session_version FROM users WHERE id=%s)',(uid,uid));rows=cur.fetchall()
        return jsonify(enabled=config['enabled'],public_key=config['public_key'],subscriptions=rows)

    @app.post('/api/push/subscriptions')
    @private
    def subscribe(uid):
        if not configuration()['enabled']:return jsonify(error='Background notifications are not configured yet. In-app reminders remain available.'),503
        subscription=validate_subscription(request.get_json(silent=True));hashed=hashlib.sha256(subscription['endpoint'].encode()).hexdigest()
        with database(b) as (conn,cur):
            cur.execute('SELECT session_version FROM users WHERE id=%s FOR UPDATE',(uid,));user=cur.fetchone()
            cur.execute('DELETE FROM push_subscriptions WHERE user_id=%s AND session_version<>%s',(uid,user['session_version']))
            cur.execute('SELECT id,user_id FROM push_subscriptions WHERE endpoint_hash=%s',(hashed,));existing=cur.fetchone()
            if existing and existing['user_id']!=uid:return jsonify(error='This browser subscription belongs to another account. Disable it in this browser and enable notifications again.'),409
            cur.execute('SELECT COUNT(*) AS count FROM push_subscriptions WHERE user_id=%s',(uid,))
            if not existing and cur.fetchone()['count']>=10:return jsonify(error='Your account has reached its 10-device notification limit.'),409
            cur.execute('''INSERT INTO push_subscriptions(user_id,endpoint_hash,subscription_json,session_version)
                VALUES(%s,%s,%s,%s) ON CONFLICT(endpoint_hash) DO UPDATE SET
                subscription_json=EXCLUDED.subscription_json,session_version=EXCLUDED.session_version,updated_at=NOW()
                WHERE push_subscriptions.user_id=EXCLUDED.user_id RETURNING id''',(uid,hashed,json.dumps(subscription),user['session_version']))
            saved=cur.fetchone();conn.commit()
        if not saved:return jsonify(error='Subscription could not be linked to this account.'),409
        session['push_subscription_id']=saved['id']
        return jsonify(ok=True,id=saved['id'])

    @app.delete('/api/push/subscriptions/<int:subscription_id>')
    @private
    def unsubscribe(uid,subscription_id):
        remove_device(b,uid,subscription_id);return jsonify(ok=True)
