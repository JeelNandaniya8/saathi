import os
from uuid import uuid4
import pytest
from test_database_flows import db_app,one
from test_care_routines_database import create
from test_care_support import food
pytestmark=pytest.mark.skipif(not os.environ.get('TEST_DATABASE_URL'),reason='Requires isolated PostgreSQL')


def test_food_separate_storage_consent_idempotency_ownership_export(db_app):
    _,c,db=db_app;data=food();p=c.post('/api/care/food-plans/preview',json=data)
    assert p.status_code==200 and one(db,'SELECT COUNT(*) n FROM food_plans')['n']==0
    data.update(preview_token=p.json['plan']['preview_token'],client_id=str(uuid4()))
    assert c.post('/api/care/food-plans',json=data).status_code==400
    data['save_confirmed']=True
    changed={**data,'days':3};assert c.post('/api/care/food-plans',json=changed).status_code==409
    r=c.post('/api/care/food-plans',json=data);assert r.status_code==201,r.json
    pid=r.json['id'];assert c.post('/api/care/food-plans',json=data).json['replayed']
    assert len(c.get('/api/export-data').json['food_plans'])==1
    with c.session_transaction() as s:s['user_id']=2
    assert c.get('/api/care/food-plans').json['plans']==[]
    assert c.delete('/api/care/food-plans/'+str(pid),json={'confirmed':True}).status_code==404
    with c.session_transaction() as s:s['user_id']=1
    assert c.delete('/api/care/food-plans/'+str(pid),json={'confirmed':True}).status_code==200


def test_caregiver_bilateral_field_consent_stale_revoke_and_removed_contact(db_app,monkeypatch):
    _,c,db=db_app;monkeypatch.setenv('CARE_ROUTINES_ENABLED','true');rid,_=create(c)
    data={'confirmed':True,'recipient_id':2,'routine_ids':[rid],'fields':['status'],'days':7}
    assert c.post('/api/care/shares',json=data).status_code==400
    with db() as conn:
        with conn.cursor() as cur:cur.execute("INSERT INTO trusted_contacts(owner_user_id,invited_email,contact_user_id,status,created_at,updated_at) VALUES(1,'other@example.com',2,'accepted',NOW(),NOW())")
    r=c.post('/api/care/shares',json=data);assert r.status_code==201,r.json
    sid=r.json['id'];respond=f'/api/care/shares/{sid}/respond';records=f'/api/care/shares/{sid}/records'
    assert c.post(respond,json={'confirmed':True,'action':'accept','version':1}).status_code==400
    with c.session_transaction() as s:s['user_id']=2
    assert c.get(records).status_code==404
    assert 'instructions' not in str(c.get('/api/care/shares').json) # metadata only
    assert c.post(respond,json={'confirmed':True,'action':'accept','version':1}).status_code==200
    rows=c.get(records).json['records'];assert len(rows)==1 and 'title' not in rows[0] and 'instructions' not in rows[0]
    assert c.post(respond,json={'confirmed':True,'action':'revoke','version':1}).status_code==409
    with c.session_transaction() as s:s['user_id']=1
    assert c.post('/api/care/shares',json={**data,'fields':['status','instructions']}).status_code==201
    with c.session_transaction() as s:s['user_id']=2
    assert c.get(records).status_code==404,'Changing fields requires fresh receiver consent'
    assert c.post(respond,json={'confirmed':True,'action':'accept','version':3}).status_code==200
    assert c.get(records).json['records'][0]['instructions']=='User-entered clinician text'
    with db() as conn:
        with conn.cursor() as cur:cur.execute('DELETE FROM trusted_contacts')
    assert c.get(records).status_code==404
    monkeypatch.setenv('CARE_ROUTINES_ENABLED','false')
    assert c.post(respond,json={'confirmed':True,'action':'revoke','version':4}).status_code==200
    assert c.get('/api/export-data').json['care_shares'][0]['status']=='revoked'


def test_caregiver_expired_and_foreign_schedule_denied(db_app,monkeypatch):
    _,c,db=db_app;monkeypatch.setenv('CARE_ROUTINES_ENABLED','true');rid,_=create(c)
    with c.session_transaction() as s:s['user_id']=2
    other,_=create(c)
    with db() as conn:
        with conn.cursor() as cur:cur.execute("INSERT INTO trusted_contacts(owner_user_id,invited_email,contact_user_id,status,created_at,updated_at) VALUES(1,'other@example.com',2,'accepted',NOW(),NOW())")
    with c.session_transaction() as s:s['user_id']=1
    data={'confirmed':True,'recipient_id':2,'routine_ids':[other],'fields':['status'],'days':7}
    assert c.post('/api/care/shares',json=data).status_code==404
    data['routine_ids']=[rid];sid=c.post('/api/care/shares',json=data).json['id']
    with db() as conn:
        with conn.cursor() as cur:cur.execute("UPDATE care_shares SET expires_at=NOW()-INTERVAL '1 minute'")
    with c.session_transaction() as s:s['user_id']=2
    assert c.post(f'/api/care/shares/{sid}/respond',json={'confirmed':True,'action':'accept','version':1}).status_code==400
    assert c.get(f'/api/care/shares/{sid}/records').status_code==404


def test_new_care_data_cascades_on_account_deletion(db_app,monkeypatch):
    _,c,db=db_app;monkeypatch.setenv('CARE_ROUTINES_ENABLED','true');rid,_=create(c)
    data=food();preview=c.post('/api/care/food-plans/preview',json=data).json['plan']
    assert c.post('/api/care/food-plans',json={**data,'save_confirmed':True,'preview_token':preview['preview_token'],'client_id':str(uuid4())}).status_code==201
    with db() as conn:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO care_shares(owner_id,recipient_id,routine_ids,fields,expires_at) VALUES(1,2,%s,'[\"status\"]',NOW()+INTERVAL '1 day')",('[%s]'%rid,))
            cur.execute('DELETE FROM users WHERE id=1')
    for table in ('food_plans','care_shares','care_occurrences'):
        assert one(db,'SELECT COUNT(*) n FROM '+table)['n']==0
