"""Validate trust boundaries without external requests or real notification keys."""
import base64
import json
import pytest
import requests
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
import push_notifications as push
from workspace_extras import avatar_url,note_fields


def encode(value):return base64.urlsafe_b64encode(value).decode().rstrip('=')


def push_fixture(monkeypatch):
    private=ec.generate_private_key(ec.SECP256R1())
    public=private.public_key().public_bytes(serialization.Encoding.X962,serialization.PublicFormat.UncompressedPoint)
    monkeypatch.setenv('VAPID_PUBLIC_KEY',encode(public))
    monkeypatch.setenv('VAPID_PRIVATE_KEY',encode(private.private_bytes(serialization.Encoding.DER,serialization.PrivateFormat.PKCS8,serialization.NoEncryption())))
    monkeypatch.setenv('VAPID_SUBJECT','mailto:push@example.com')
    receiver=ec.generate_private_key(ec.SECP256R1()).public_key().public_bytes(serialization.Encoding.X962,serialization.PublicFormat.UncompressedPoint)
    return {'endpoint':'https://fcm.googleapis.com/fcm/send/local-test-only','keys':{'p256dh':encode(receiver),'auth':encode(b'local-test-bytes')}}


@pytest.mark.parametrize('url',['http://lh3.googleusercontent.com/a','https://googleusercontent.com.evil.test/a','https://lh3.googleusercontent.com@evil.test/a','https://localhost/a','data:image/svg+xml,x','https://lh3.googleusercontent.com:8443/a','https://lh3.googleusercontent.com/a\nb',None])
def test_avatar_rejects_untrusted_urls(url):assert avatar_url(url) is None


def test_notes_and_avatar_keep_unicode_as_data():
    assert avatar_url('https://lh3.googleusercontent.com/a/photo=s96-c')=='https://lh3.googleusercontent.com/a/photo=s96-c'
    assert note_fields({'content':'  ગુજરાતી અભ્યાસ\n<script>alert(1)</script>  '})==('ગુજરાતી અભ્યાસ','ગુજરાતી અભ્યાસ\n<script>alert(1)</script>')
    for invalid in [None,[],{}, {'content':' '},{'content':'x'*10001},{'content':'ok','title':'x'*81},{'content':42}]:
        with pytest.raises(ValueError):note_fields(invalid)


@pytest.mark.parametrize('endpoint',['https://127.0.0.1/a','https://169.254.169.254/latest/meta-data','https://fcm.googleapis.com.evil.test/a','https://fcm.googleapis.com@evil.test/a','https://fcm.googleapis.com:8443/a','http://fcm.googleapis.com/a','https://updates.push.services.mozilla.com/','https://fcm.googleapis.com/a#part','https://fcm.googleapis.com/a\rb'])
def test_push_rejects_non_browser_destinations(endpoint):assert not push.endpoint_allowed(endpoint)


def test_push_keys_and_configuration_validation(monkeypatch):
    subscription=push_fixture(monkeypatch)
    assert push.configuration()['enabled']
    assert push.validate_subscription({**subscription,'ignored':'value'})==subscription
    for host in ['updates.push.services.mozilla.com','web.push.apple.com','wns2-db5p.notify.windows.com']:
        assert push.endpoint_allowed('https://'+host+'/subscription')
    for keys in [{}, {'p256dh':'bad','auth':'bad'},{'p256dh':encode(b'\x04'+b'\x00'*64),'auth':encode(b'x'*16)}]:
        with pytest.raises(ValueError):push.validate_subscription({**subscription,'keys':keys})
    monkeypatch.setenv('VAPID_PUBLIC_KEY',subscription['keys']['p256dh']);assert not push.configuration()['enabled']
    monkeypatch.setenv('VAPID_PRIVATE_KEY','not-a-key');assert not push.configuration()['enabled']


def test_webpush_encrypts_payload_and_disallows_redirects(monkeypatch):
    pytest.importorskip('pywebpush')
    subscription=push_fixture(monkeypatch);sent=[]
    # Intercept below the production allowlist: encryption and VAPID signing still run.
    def capture(self,method,url,**kwargs):
        sent.append((method,url,kwargs));response=requests.Response();response.status_code=201;return response
    monkeypatch.setattr(requests.Session,'request',capture)
    payload={'body':'ગુજરાતી reminder','url':'/dashboard#reminders'}
    assert push.send_push(subscription,payload,push.configuration())==201
    _,url,request=sent[0]
    assert url==subscription['endpoint'] and request['allow_redirects'] is False
    assert isinstance(request['data'],bytes) and b'body' not in request['data']
    assert json.dumps(payload).encode() not in request['data']
    assert {k.lower():v for k,v in request['headers'].items()}['content-encoding']=='aes128gcm'
    assert request['timeout']==5
    with pytest.raises(ValueError):push.PushSession().request('POST','https://localhost/private')
    assert len(sent)==1
