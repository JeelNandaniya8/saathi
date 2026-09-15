"""Owned payment orders, captured-payment verification and expiring access."""
import hashlib
import hmac
import json
import os
import re
import secrets
from contextlib import contextmanager
from datetime import datetime, timezone
from functools import wraps

import requests
from flask import jsonify, request

PRICES = {
    'plus_monthly': {'amount': 19900, 'currency': 'INR', 'label': 'Saathi Plus · 30 days', 'plan': 'plus', 'days': 30},
    'plus_yearly': {'amount': 149900, 'currency': 'INR', 'label': 'Saathi Plus · 365 days', 'plan': 'plus', 'days': 365},
}


def configuration():
    mode = os.environ.get('SAATHI_BILLING_MODE', 'disabled').lower()
    key = os.environ.get('RAZORPAY_KEY_ID', '')
    secret = os.environ.get('RAZORPAY_KEY_SECRET', '')
    enabled = mode in {'test', 'live'} and key.startswith('rzp_' + mode + '_') and bool(secret) and bool(os.environ.get('RAZORPAY_WEBHOOK_SECRET'))
    if mode == 'live':
        enabled = enabled and os.environ.get('MERCHANT_VERIFIED') == 'true'
    return {'enabled': bool(enabled), 'test': mode != 'live', 'key': key, 'secret': secret}


def effective_plan(user, now=None):
    if not user or user.get('plan_status') != 'active' or user.get('plan') not in {'plus', 'family'}:
        return 'free'
    end = user.get('subscription_end_at')
    if not isinstance(end, datetime):
        return 'free'
    if not end.tzinfo:
        end = end.replace(tzinfo=timezone.utc)
    return user['plan'] if end > (now or datetime.now(timezone.utc)) else 'free'


def verify_signature(secret, message, signature):
    if not secret or not isinstance(signature, str) or not re.fullmatch(r'[a-fA-F0-9]{64}', signature):
        return False
    raw = message if isinstance(message, bytes) else message.encode('utf-8')
    return hmac.compare_digest(hmac.new(secret.encode('utf-8'), raw, hashlib.sha256).hexdigest(), signature.lower())


def provider(method, path, **kwargs):
    config = configuration()
    if not config['enabled']:
        raise ValueError('Checkout is not available yet.')
    try:
        response = requests.request(method, 'https://api.razorpay.com/v1/' + path, auth=(config['key'], config['secret']), timeout=(5, 15), **kwargs)
        response.raise_for_status()
        return response.json()
    except (requests.RequestException, ValueError):
        raise RuntimeError('Payment confirmation could not connect. Please retry; do not pay again.') from None


def validate_payment(payment, order, payment_id=None):
    if not isinstance(payment, dict) or payment.get('status') != 'captured' or payment.get('captured') is not True:
        raise ValueError('Payment is awaiting confirmation. Your plan updates after capture.')
    if payment.get('order_id') != order['order_id'] or payment.get('amount') != order['amount'] or payment.get('currency') != order['currency']:
        raise ValueError('Payment details do not match the saved order.')
    if payment.get('amount_refunded', 0) != 0:
        raise ValueError('This payment has been refunded and cannot activate a plan.')
    if not re.fullmatch(r'pay_[A-Za-z0-9]+', str(payment.get('id') or '')) or (payment_id and payment.get('id') != payment_id):
        raise ValueError('Payment reference does not match.')


def refresh_access(cur, user_id):
    cur.execute("""SELECT plan, MAX(ends_at) AS ends_at FROM access_grants
        WHERE user_id=%s AND revoked_at IS NULL AND ends_at>NOW() GROUP BY plan
        ORDER BY CASE WHEN plan='family' THEN 0 ELSE 1 END LIMIT 1""", (user_id,))
    grant = cur.fetchone()
    cur.execute("UPDATE users SET plan=%s,plan_status='active',subscription_end_at=%s WHERE id=%s RETURNING *",
                (grant['plan'] if grant else 'free', grant['ends_at'] if grant else None, user_id))
    return cur.fetchone()


def grant_access(cur, user_id, source_id, plan, days):
    # Serialize grants from checkout, webhooks and referrals for the same user.
    cur.execute('SELECT id FROM users WHERE id=%s FOR UPDATE', (user_id,))
    cur.fetchone()
    cur.execute("""WITH anchor AS (SELECT GREATEST(NOW(),COALESCE(MAX(ends_at),NOW())) AS start
        FROM access_grants WHERE user_id=%s AND plan=%s AND revoked_at IS NULL)
        INSERT INTO access_grants (source_id,user_id,plan,starts_at,ends_at)
        SELECT %s,%s,%s,start,start + %s * INTERVAL '1 day' FROM anchor
        ON CONFLICT (source_id) DO NOTHING""", (user_id,plan,source_id,user_id,plan,days))
    return refresh_access(cur, user_id)


def revoke_access(cur, user_id, source_id):
    cur.execute('SELECT id FROM users WHERE id=%s FOR UPDATE', (user_id,))
    cur.fetchone()
    cur.execute('SELECT * FROM access_grants WHERE source_id=%s AND user_id=%s FOR UPDATE', (source_id,user_id))
    grant = cur.fetchone()
    if grant and not grant['revoked_at']:
        remaining = max(0, (grant['ends_at'] - max(grant['starts_at'],datetime.now(timezone.utc))).total_seconds())
        # Close the unused portion of a refunded pass without deleting days
        # purchased in a later order or earned through another grant.
        cur.execute("""UPDATE access_grants SET starts_at=starts_at-%s*INTERVAL '1 second',
            ends_at=ends_at-%s*INTERVAL '1 second' WHERE user_id=%s AND plan=%s
            AND source_id<>%s AND revoked_at IS NULL AND starts_at>=%s""",
            (remaining,remaining,user_id,grant['plan'],source_id,grant['ends_at']))
        cur.execute('UPDATE access_grants SET revoked_at=NOW() WHERE source_id=%s', (source_id,))
    return refresh_access(cur,user_id)


def settle(cur, order, payment):
    validate_payment(payment, order)
    if order['status'] == 'refunded':
        raise ValueError('This order was refunded and cannot be activated again.')
    if order.get('payment_id') and order['payment_id'] != payment['id']:
        raise ValueError('This order already has a different payment.')
    cur.execute('SELECT order_id FROM payment_orders WHERE payment_id=%s AND order_id<>%s', (payment['id'], order['order_id']))
    if cur.fetchone():
        raise ValueError('This payment was already used for another order.')
    cur.execute('UPDATE payment_orders SET payment_id=%s,status=%s,paid_at=COALESCE(paid_at,NOW()) WHERE order_id=%s',
                (payment['id'], 'test_paid' if order['is_test'] else 'paid', order['order_id']))
    if not order['is_test']:
        return grant_access(cur, order['user_id'], 'payment:' + payment['id'], order['plan'], order['duration_days'])
    cur.execute('SELECT * FROM users WHERE id=%s', (order['user_id'],))
    return cur.fetchone()


def register(app, backend):
    @contextmanager
    def db():
        conn = backend['get_db']()
        cur = conn.cursor()
        try:
            yield conn, cur
        except Exception:
            conn.rollback()
            raise
        finally:
            cur.close()
            conn.close()

    def private(fn):
        @wraps(fn)
        def wrapped(*args, **kwargs):
            uid = backend['require_user_id']()
            if not uid:
                return jsonify(error='Please log in first.'), 401
            try:
                return fn(uid, *args, **kwargs)
            except ValueError as error:
                return jsonify(error=str(error)), 400
            except RuntimeError as error:
                return jsonify(error=str(error)), 502
        return wrapped

    @app.get('/api/payment/status')
    @private
    def payment_status(uid):
        config = configuration()
        with db() as (_, cur):
            cur.execute('SELECT * FROM users WHERE id=%s', (uid,))
            user = cur.fetchone()
        return jsonify(plan=effective_plan(user), user=backend['user_to_dict'](user), payment_enabled=config['enabled'], test_mode=config['test'], plan_prices=PRICES)

    @app.post('/api/payment/create-order')
    @private
    def create_payment_order(uid):
        config = configuration()
        if not config['enabled']:
            return jsonify(error='Paid plans are coming soon. Your free tools remain available.'), 503
        data = request.get_json(silent=True) or {}
        code = data.get('price_key') if isinstance(data, dict) else None
        if not isinstance(code, str) or code not in PRICES:
            raise ValueError('Choose a valid plan.')
        limit = backend['limited']('create_order', str(uid), 5, 5)
        if limit:
            return limit
        price = PRICES[code]
        order = provider('POST', 'orders', json={'amount':price['amount'],'currency':price['currency'],'receipt':secrets.token_hex(16),'notes':{'saathi_user_id':str(uid),'price_key':code}})
        if not isinstance(order, dict) or not re.fullmatch(r'order_[A-Za-z0-9]+', str(order.get('id') or '')) or order.get('amount') != price['amount'] or order.get('currency') != price['currency']:
            raise RuntimeError('The payment order could not be verified. Please retry.')
        with db() as (conn, cur):
            cur.execute('INSERT INTO payment_orders (order_id,user_id,price_key,plan,amount,currency,duration_days,is_test) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)',
                        (order['id'],uid,code,price['plan'],price['amount'],price['currency'],price['days'],config['test']))
            conn.commit()
        return jsonify(order_id=order['id'],key_id=config['key'],amount=price['amount'],currency=price['currency'],label=price['label'],test_mode=config['test'])

    @app.post('/api/payment/verify')
    @private
    def verify_payment(uid):
        config = configuration()
        if not config['enabled']:
            return jsonify(error='Checkout is not available yet.'), 503
        data = request.get_json(silent=True) or {}
        if not isinstance(data, dict):
            raise ValueError('Use a valid payment confirmation.')
        oid = str(data.get('razorpay_order_id') or '')
        pid = str(data.get('razorpay_payment_id') or '')
        if not re.fullmatch(r'order_[A-Za-z0-9]+',oid) or not re.fullmatch(r'pay_[A-Za-z0-9]+',pid):
            raise ValueError('Invalid payment reference.')
        with db() as (_, cur):
            cur.execute('SELECT * FROM payment_orders WHERE order_id=%s AND user_id=%s', (oid,uid))
            order = cur.fetchone()
        if not order or order['is_test'] != config['test']:
            return jsonify(error='Payment order not found for this account.'), 404
        if not verify_signature(config['secret'], order['order_id'] + '|' + pid, data.get('razorpay_signature')):
            raise ValueError('Payment signature could not be verified.')
        payment = provider('GET', 'payments/' + pid)
        validate_payment(payment, order, pid)
        with db() as (conn, cur):
            cur.execute('SELECT * FROM payment_orders WHERE order_id=%s AND user_id=%s FOR UPDATE', (oid,uid))
            user = settle(cur, cur.fetchone(), payment)
            conn.commit()
        return jsonify(ok=True,test_mode=config['test'],user=backend['user_to_dict'](user),message='Test payment confirmed. Your real plan is unchanged.' if config['test'] else 'Payment confirmed. Saathi Plus is ready.')

    @app.post('/api/payment/webhook')
    def payment_webhook():
        if request.content_length and request.content_length > 1048576:
            return jsonify(error='Payload too large.'), 413
        raw = request.get_data()
        if not configuration()['enabled'] or not verify_signature(os.environ.get('RAZORPAY_WEBHOOK_SECRET',''), raw, request.headers.get('X-Razorpay-Signature')):
            return jsonify(error='Invalid webhook signature.'), 400
        try:
            data = json.loads(raw)
            event = data['event']
            event_id = request.headers.get('X-Razorpay-Event-Id') or hashlib.sha256(raw).hexdigest()
            if not isinstance(event,str) or len(event_id)>200:
                raise ValueError('Invalid event')
            payment = data.get('payload',{}).get('payment',{}).get('entity',{})
            with db() as (conn, cur):
                cur.execute('INSERT INTO payment_events (id,event_type) VALUES (%s,%s) ON CONFLICT DO NOTHING RETURNING id',(event_id,event))
                if not cur.fetchone():
                    return jsonify(ok=True)
                cur.execute('SELECT * FROM payment_orders WHERE order_id=%s FOR UPDATE',(payment.get('order_id'),))
                order = cur.fetchone()
                if order and order['is_test'] == configuration()['test']:
                    if event == 'payment.captured' and order['status'] != 'refunded':
                        settle(cur, order, payment)
                    elif event == 'payment.refunded' and payment.get('id') == order.get('payment_id') and payment.get('amount_refunded',0) >= order['amount']:
                        revoke_access(cur,order['user_id'],'payment:'+str(payment.get('id')))
                        cur.execute("UPDATE payment_orders SET status='refunded' WHERE order_id=%s",(order['order_id'],))
                        refresh_access(cur,order['user_id'])
                conn.commit()
            return jsonify(ok=True)
        except (ValueError,TypeError,KeyError,AttributeError):
            return jsonify(error='Invalid payment event.'),400

    @app.get('/api/referrals')
    @private
    def get_referrals(uid):
        with db() as (conn, cur):
            cur.execute('SELECT referral_code FROM users WHERE id=%s FOR UPDATE',(uid,))
            row = cur.fetchone()
            code = row.get('referral_code') or secrets.token_hex(6).upper()
            if not row.get('referral_code'):
                cur.execute('UPDATE users SET referral_code=%s WHERE id=%s',(code,uid))
            cur.execute('SELECT COUNT(*) AS count FROM users WHERE referred_by_id=%s AND email_verified_at IS NOT NULL',(uid,))
            count = cur.fetchone()['count']
            cur.execute('SELECT COUNT(*) AS count FROM referral_rewards WHERE referrer_user_id=%s',(uid,))
            earned = cur.fetchone()['count'] * 7
            conn.commit()
        base = backend['APP_BASE_URL'] or request.host_url.rstrip('/')
        return jsonify(referral_code=code,referral_url=base+'/account?ref='+code,total_referrals=count,bonus_days_earned=earned,referrals=[],reward_limit_days=28)

    @app.post('/api/referrals/claim')
    @private
    def claim_referrals(uid):
        with db() as (conn, cur):
            cur.execute('SELECT id FROM users WHERE id=%s FOR UPDATE',(uid,))
            cur.fetchone()
            cur.execute('SELECT COUNT(*) AS count FROM referral_rewards WHERE referrer_user_id=%s',(uid,))
            remaining = max(0,4-cur.fetchone()['count'])
            cur.execute('''SELECT u.id FROM users u WHERE u.referred_by_id=%s AND u.id<>%s
                AND u.email_verified_at IS NOT NULL AND u.created_at<NOW()-INTERVAL '1 day'
                AND NOT EXISTS (SELECT 1 FROM referral_rewards r WHERE r.referred_user_id=u.id)
                AND (EXISTS (SELECT 1 FROM mock_test_attempts a WHERE a.user_id=u.id)
                     OR EXISTS (SELECT 1 FROM tasks t WHERE t.user_id=u.id AND t.completed=TRUE))
                ORDER BY u.id LIMIT %s''',(uid,uid,remaining))
            qualified = cur.fetchall()
            for referred in qualified:
                cur.execute('INSERT INTO referral_rewards (referred_user_id,referrer_user_id) VALUES (%s,%s) ON CONFLICT DO NOTHING RETURNING referred_user_id',(referred['id'],uid))
                if cur.fetchone():
                    grant_access(cur,uid,'referral:'+str(referred['id']),'plus',7)
            user = refresh_access(cur,uid)
            conn.commit()
        return jsonify(ok=True,user=backend['user_to_dict'](user),message='Eligible invite rewards have been applied.' if qualified else 'No new eligible rewards yet. Friends qualify after one day and their first completed task or mock test.')
