"""Regression coverage for identity, model documents and payment boundaries."""
import base64
import copy
import hashlib
import hmac
import importlib
import json
import os
import time
from datetime import datetime, timedelta, timezone

import pytest
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa

import auth_google
import billing
import care
import study_tools


def b64(value):
    return base64.urlsafe_b64encode(value).decode().rstrip('=')


@pytest.fixture
def token_factory(monkeypatch):
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public = key.public_key().public_numbers()
    jwk = {'kid':'local-test','e':b64(public.e.to_bytes(3,'big')),'n':b64(public.n.to_bytes(256,'big'))}
    monkeypatch.setattr(auth_google,'signing_keys',lambda refresh=False:{'local-test':jwk})
    def make(**changes):
        claims={'aud':'test-client','iss':'https://accounts.google.com','exp':int(time.time())+300,
                'iat':int(time.time()),'nonce':'test-nonce','email':'student@example.com',
                'email_verified':True,'sub':'123456789'}
        claims.update(changes)
        payload=b64(json.dumps({'alg':'RS256','kid':'local-test'}).encode())+'.'+b64(json.dumps(claims).encode())
        return payload+'.'+b64(key.sign(payload.encode(),padding.PKCS1v15(),hashes.SHA256()))
    return make


def test_google_identity_requires_a_valid_signature(token_factory):
    credential=token_factory()
    assert auth_google.verify_credential(credential,'test-client','test-nonce')['sub']=='123456789'
    parts=credential.split('.')
    claims=json.loads(auth_google.decode_segment(parts[1]));claims['email']='another@example.com'
    parts[1]=b64(json.dumps(claims).encode())
    with pytest.raises(ValueError):auth_google.verify_credential('.'.join(parts),'test-client','test-nonce')


@pytest.mark.parametrize('claims',[{'aud':'other-client'},{'iss':'https://example.com'},
    {'exp':0},{'exp':float('nan')},{'exp':float('inf')},{'iat':int(time.time())+3600},
    {'nonce':'other-browser'},{'email_verified':False},{'sub':''},{'email':'invalid'}])
def test_google_rejects_wrong_or_expired_claims(token_factory,claims):
    with pytest.raises(ValueError):auth_google.verify_credential(token_factory(**claims),'test-client','test-nonce')


def test_email_only_google_login_is_rejected(monkeypatch):
    os.environ.pop('DATABASE_URL',None)
    backend=importlib.import_module('app');monkeypatch.setattr(backend,'GOOGLE_CLIENT_ID','test-client')
    response=backend.app.test_client().post('/api/google-auth',json={'email':'student@example.com','name':'Student'})
    assert response.status_code==400


def questions(count=5):
    return [{'question':f'Question {n}: બે અને બે કેટલા?', 'options':{'A':'ચાર','B':'પાંચ','C':'છ','D':'સાત'},
             'correct_option':'A','explanation':'બે અને બે ચાર થાય.'} for n in range(count)]


@pytest.mark.parametrize('answer',[None,'','AB',[],{},True])
def test_model_answer_keys_are_one_valid_letter(answer):
    raw=questions();raw[0]['correct_option']=answer
    with pytest.raises(ValueError):study_tools.validate_questions(raw,5)


def test_exam_shape_masks_answers_and_grades_only_submitted_choices():
    validated=study_tools.validate_questions(questions(),5)
    row={'id':1,'topic':'ગણિત','difficulty':'easy','questions_json':validated,'time_limit_minutes':5,'created_at':datetime.now(timezone.utc)}
    public=study_tools.public_test(row)
    assert public['questions'][0]['options']['A']=='ચાર'
    assert 'correct_option' not in json.dumps(public) and 'explanation' not in json.dumps(public)
    result=study_tools.grade(validated,{'1':'A','2':'B'},20)
    assert result['attempt']['score']==1 and result['attempt']['total_questions']==5
    assert result['review'][0]['correct_answer']=='A'
    with pytest.raises(ValueError):study_tools.grade(validated,{'500':'A'},0)


def test_malformed_or_duplicate_model_options_are_rejected():
    raw=questions();raw[0]['options']['B']='ચાર'
    with pytest.raises(ValueError):study_tools.validate_questions(raw)
    raw[0]['options']=[{'key':[], 'text':'unsafe'}]*4
    with pytest.raises(ValueError):study_tools.validate_questions(raw)


def test_mindmap_has_specific_nodes_and_safe_colours():
    node={'label':'પ્રકાશસંશ્લેષણ','desc':'Plants use light energy.','color':'url(javascript:bad)','children':[]}
    raw={'summary':'How plants use light.','root':{**node,'children':[node]}}
    result=study_tools.validate_mindmap(raw,'Photosynthesis')
    assert result['root']['color']=='#4263eb' and result['root']['children'][0]['id']=='node-2'
    raw['root']['children']=[]
    with pytest.raises(ValueError):study_tools.validate_mindmap(raw,'Photosynthesis')


def test_paid_access_expires_and_requires_an_actual_end_date():
    now=datetime.now(timezone.utc)
    user={'plan':'plus','plan_status':'active','subscription_end_at':now+timedelta(seconds=1)}
    assert billing.effective_plan(user,now)=='plus'
    assert billing.effective_plan(user,now+timedelta(seconds=1))=='free'
    user['subscription_end_at']=None
    assert billing.effective_plan(user,now)=='free'


def test_billing_is_disabled_by_default_and_test_keys_cannot_enable_live(monkeypatch):
    monkeypatch.delenv('SAATHI_BILLING_MODE',raising=False)
    monkeypatch.setenv('RAZORPAY_KEY_ID','rzp_test_fixture')
    monkeypatch.setenv('RAZORPAY_KEY_SECRET','test-fixture-secret')
    monkeypatch.setenv('RAZORPAY_WEBHOOK_SECRET','test-fixture-webhook')
    assert billing.configuration()['enabled'] is False
    monkeypatch.setenv('SAATHI_BILLING_MODE','live');monkeypatch.setenv('MERCHANT_VERIFIED','true')
    assert billing.configuration()['enabled'] is False
    monkeypatch.setenv('SAATHI_BILLING_MODE','test')
    assert billing.configuration()['enabled'] and billing.configuration()['test']


def test_signature_and_captured_payment_match_saved_order():
    order={'order_id':'order_fixture','amount':19900,'currency':'INR'}
    payment={'id':'pay_fixture','order_id':'order_fixture','status':'captured','captured':True,'amount':19900,'currency':'INR'}
    billing.validate_payment(payment,order,'pay_fixture')
    for changes in ({'status':'authorized'},{'captured':False},{'amount':1},{'order_id':'order_other'},{'currency':'USD'},{'amount_refunded':19900}):
        with pytest.raises(ValueError):billing.validate_payment({**payment,**changes},order)
    secret='local-test-secret';message='order_fixture|pay_fixture'
    signature=hmac.new(secret.encode(),message.encode(),hashlib.sha256).hexdigest()
    assert billing.verify_signature(secret,message,signature)
    assert not billing.verify_signature(secret,'order_other|pay_fixture',signature)


def test_wellbeing_guide_is_explicitly_general_and_unicode():
    report=care.wellbeing_report('gu')
    assert report['generated_by_ai'] is False and report['medical_concepts']==[]
    assert 'સાથી' in report['doctor_disclaimer'] and 'àª' not in json.dumps(report,ensure_ascii=False)


def test_broken_stream_cannot_be_saved_as_a_complete_reply(monkeypatch):
    os.environ.pop('DATABASE_URL',None)
    b=importlib.import_module('app');closed=[]
    class Response:
        def raise_for_status(self):pass
        def iter_lines(self,**kwargs):
            yield 'data: {"candidates":[{"content":{"parts":[{"text":"ગુજરાતીમાં"}]}}]}'
        def close(self):closed.append(True)
    monkeypatch.setattr(b,'GEMINI_API_KEY','local-test-key')
    monkeypatch.setattr(b,'provider_post',lambda *args,**kwargs:Response())
    stream=b.stream_gemini_reply([{'role':'user','content':'Hello'}])
    assert next(stream)=='ગુજરાતીમાં'
    with pytest.raises(RuntimeError,match='before it was complete'):next(stream)
    assert closed==[True]
