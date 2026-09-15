"""Google sign-in with signature, audience, expiry and browser nonce validation."""
import base64
import json
import re
import secrets
import threading
import time
from datetime import datetime, timezone

import psycopg2
import requests
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from flask import jsonify, request, session
from workspace_extras import avatar_url
from werkzeug.security import generate_password_hash

_keys = {}
_keys_until = 0
_keys_refreshed_at = 0
_keys_lock = threading.Lock()


def decode_segment(value):
    if not re.fullmatch(r'[A-Za-z0-9_-]+', value):
        raise ValueError('Invalid sign-in token.')
    return base64.urlsafe_b64decode(value + '=' * (-len(value) % 4))


def signing_keys(refresh=False):
    global _keys, _keys_until, _keys_refreshed_at
    with _keys_lock:
        now = time.monotonic()
        if _keys and now < _keys_until and (not refresh or now - _keys_refreshed_at < 60):
            return _keys
        try:
            response = requests.get('https://www.googleapis.com/oauth2/v3/certs', timeout=(5, 8))
            response.raise_for_status()
            keys = response.json()['keys']
            result = {key['kid']: key for key in keys if key.get('kty') == 'RSA' and key.get('alg') == 'RS256'}
            if not result:
                raise ValueError('Missing signing keys')
            max_age = re.search(r'max-age=(\d+)', response.headers.get('Cache-Control', ''))
            _keys = result
            _keys_refreshed_at = time.monotonic()
            _keys_until = time.monotonic() + min(int(max_age[1]) if max_age else 300, 3600)
            return _keys
        except (requests.RequestException, ValueError, KeyError, TypeError):
            raise RuntimeError('Google sign-in could not connect. Try again or use email sign-in.') from None


def verify_credential(credential, client_id, nonce):
    if not client_id or not isinstance(credential, str) or len(credential) > 16000 or not nonce:
        raise ValueError('Start Google sign-in again from the account page.')
    try:
        header_part, claims_part, signature_part = credential.split('.')
        header = json.loads(decode_segment(header_part))
        if not isinstance(header, dict) or header.get('alg') != 'RS256':
            raise ValueError('Invalid signing algorithm')
        kid = header.get('kid')
        if not isinstance(kid, str) or len(kid) > 200:
            raise ValueError('Invalid signing key')
        key = signing_keys().get(kid)
        if not key:
            key = signing_keys(refresh=True).get(kid)
        if not key:
            raise ValueError('Unknown signing key')
        public_key = rsa.RSAPublicNumbers(
            int.from_bytes(decode_segment(key['e']), 'big'),
            int.from_bytes(decode_segment(key['n']), 'big'),
        ).public_key()
        public_key.verify(decode_segment(signature_part), (header_part + '.' + claims_part).encode('ascii'), padding.PKCS1v15(), hashes.SHA256())
        claims = json.loads(decode_segment(claims_part))
        now = time.time()
        if not isinstance(claims, dict) or claims.get('aud') != client_id or claims.get('iss') not in {'accounts.google.com', 'https://accounts.google.com'}:
            raise ValueError('Invalid token audience or issuer')
        if type(claims.get('exp')) is not int or claims['exp'] <= now:
            raise ValueError('Expired token')
        if type(claims.get('iat')) is not int or claims['iat'] > now + 30 or claims['iat'] >= claims['exp']:
            raise ValueError('Invalid issued time')
        if not isinstance(claims.get('nonce'), str) or not secrets.compare_digest(claims['nonce'], nonce):
            raise ValueError('Sign-in browser mismatch')
        if claims.get('email_verified') is not True or not isinstance(claims.get('sub'), str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,255}', claims['sub']):
            raise ValueError('Unverified identity')
        email = str(claims.get('email') or '').strip().lower()
        if len(email) > 200 or not re.fullmatch(r'[^@\s]+@[^@\s]+\.[^@\s]+', email):
            raise ValueError('Invalid email')
        claims['email'] = email
        return claims
    except (ValueError, TypeError, KeyError, InvalidSignature, UnicodeError):
        raise ValueError('Google sign-in could not be verified. Please start again.') from None


def register(app, backend):
    @app.get('/api/auth/config')
    def auth_config():
        if not session.get('google_nonce') or time.time() - session.get('google_nonce_at', 0) > 600:
            session['google_nonce'] = secrets.token_urlsafe(32)
            session['google_nonce_at'] = time.time()
        return jsonify(google_client_id=backend['GOOGLE_CLIENT_ID'] or None, nonce=session['google_nonce'])

    @app.post('/api/google-auth')
    def google_auth():
        client_id = backend['GOOGLE_CLIENT_ID']
        if not client_id:
            return jsonify(error='Google sign-in is not connected yet. Use email to continue.'), 503
        data = request.get_json(silent=True) or {}
        if not isinstance(data, dict) or not data.get('credential'):
            return jsonify(error='A verified Google credential is required. Use email sign-in otherwise.'), 400
        remember = data.get('remember', False)
        if not isinstance(remember, bool):
            return jsonify(error='Choose a valid sign-in preference.'), 400
        limit = backend['limited']('google_auth', request.remote_addr or 'unknown', 12, 5)
        if limit:
            return limit
        if time.time() - session.get('google_nonce_at', 0) > 600:
            return jsonify(error='This sign-in expired. Refresh and try again.'), 401
        try:
            claims = verify_credential(data['credential'], client_id, session.get('google_nonce'))
        except ValueError as error:
            return jsonify(error=str(error)), 401
        except RuntimeError as error:
            return jsonify(error=str(error)), 503
        email, subject = claims['email'], claims['sub']
        # For third-party mailboxes Google is not authoritative. Require the
        # existing email verification flow before linking a new identity.
        authoritative = email.endswith('@gmail.com') or bool(claims.get('hd'))
        conn = backend['get_db']()
        cur = conn.cursor()
        try:
            cur.execute('SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))', ('google:' + email,))
            cur.execute('SELECT * FROM users WHERE google_subject = %s FOR UPDATE', (subject,))
            user = cur.fetchone()
            if not user:
                if not authoritative:
                    return jsonify(error='Use email verification to sign in with this email provider.'), 409
                cur.execute('SELECT * FROM users WHERE email = %s FOR UPDATE', (email,))
                user = cur.fetchone()
                if user and user.get('google_subject') not in (None, subject):
                    return jsonify(error='This account uses another Google identity. Use email sign-in.'), 409
                now = datetime.now(timezone.utc)
                if user:
                    cur.execute('UPDATE users SET google_subject=%s, email_verified_at=COALESCE(email_verified_at,%s) WHERE id=%s RETURNING *', (subject, now, user['id']))
                else:
                    name = re.sub(r'[\x00-\x1f<>]', '', str(claims.get('name') or 'Student')).strip()[:50] or 'Student'
                    stem = re.sub(r'[^a-z0-9_]', '', name.lower().replace(' ', '_'))[:10] or 'student'
                    username = stem + '_' + secrets.token_hex(4)
                    ref = str(data.get('ref') or '').strip().upper()[:40]
                    cur.execute('SELECT id FROM users WHERE referral_code=%s', (ref,))
                    inviter = cur.fetchone() if ref else None
                    cur.execute('''INSERT INTO users (name,username,email,password_hash,plan,plan_status,session_version,google_subject,email_verified_at,referral_code,referred_by_id,created_at)
                        VALUES (%s,%s,%s,%s,'free','active',1,%s,%s,%s,%s,%s) RETURNING *''',
                        (name, username, email, generate_password_hash(secrets.token_urlsafe(32)), subject, now, secrets.token_hex(6).upper(), inviter['id'] if inviter else None, now))
                user = cur.fetchone()
            if 'picture' in claims:
                cur.execute('UPDATE users SET avatar_url=%s WHERE id=%s RETURNING *', (avatar_url(claims['picture']), user['id']))
                user = cur.fetchone()
            conn.commit()
            backend['start_user_session'](user, remember)
            return jsonify(ok=True, user=backend['user_to_dict'](user), csrf_token=session['csrf_token'])
        except psycopg2.errors.UniqueViolation:
            conn.rollback()
            return jsonify(error='Your account changed during sign-in. Please try again.'), 409
        finally:
            cur.close()
            conn.close()
