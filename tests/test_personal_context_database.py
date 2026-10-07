import os
from datetime import datetime,timedelta,timezone
from uuid import uuid4
import pytest
from test_database_flows import db_app,one
pytestmark=pytest.mark.skipif(not os.environ.get('TEST_DATABASE_URL'),reason='Requires isolated PostgreSQL test service')


def test_context_isolation_consent_export_revoke_and_conflict(db_app):
    b,c,connect=db_app
    path='/api/personal-context/care/allergies'
    body={'value':'Peanuts','version':0,'confirmed':True,'use_in_ai':False}
    assert c.put(path,json={**body,'confirmed':False}).status_code==400
    assert c.put(path,json=body).status_code==200
    field=c.get('/api/personal-context').json['fields'][0]
    assert field['source']=='user_reported' and not field['use_in_ai']
    assert b.load_active_memory_bundle(1,None,'healer')==('',[])
    assert c.put(path,json={**body,'version':field['version'],'use_in_ai':True}).status_code==200
    assert 'Peanuts' in b.load_active_memory_bundle(1,None,'healer')[0]
    assert b.load_active_memory_bundle(1,None,'normal')==('',[])
    assert c.put(path,json=body).status_code==409
    with c.session_transaction() as session:session['user_id']=2
    assert c.get('/api/personal-context').json['fields']==[]
    assert c.delete(path,json={'version':field['version']}).status_code==409
    with c.session_transaction() as session:session['user_id']=1
    assert c.get('/api/export-data').json['personal_context_fields'][0]['value']=='Peanuts'
    assert c.post('/api/personal-context/revoke',json={}).status_code==200
    assert b.load_active_memory_bundle(1,None,'healer')==('',[])
    field=c.get('/api/personal-context').json['fields'][0]
    assert c.delete(path,json={'version':field['version']}).status_code==200
    assert c.put(path,json=body).status_code==200
    assert c.put(path,json={**body,'version':field['version']}).status_code==409, 'Delete/recreate must not revive stale versions'


def test_exam_preview_required_idempotent_owned_and_tasks_retained(db_app):
    _,c,connect=db_app
    body={'title':'Test','topics':['Algebra','Python'],'daily_minutes':30,'timezone':'UTC',
          'exam_date':(datetime.now(timezone.utc)+timedelta(days=20)).date().isoformat(),
          'confirmed':True,'client_id':str(uuid4())}
    preview=c.post('/api/exam-plans/preview',json=body)
    assert preview.status_code==200
    assert c.post('/api/exam-plans',json=body).status_code==409
    body['preview_token']=preview.json['plan']['preview_token']
    result=c.post('/api/exam-plans',json=body);assert result.status_code==201
    assert c.post('/api/exam-plans',json=body).json['replayed']
    assert one(connect,'SELECT COUNT(*) AS n FROM tasks WHERE user_id=1')['n']==6
    plan_id=result.json['id']
    with c.session_transaction() as session:session['user_id']=2
    assert c.get('/api/exam-plans').json['plans']==[]
    assert c.delete('/api/exam-plans/'+str(plan_id)).status_code==404
    with c.session_transaction() as session:session['user_id']=1
    assert c.get('/api/export-data').json['exam_plans'][0]['title']=='Test'
    assert c.delete('/api/exam-plans/'+str(plan_id)).json['tasks_retained']
    assert one(connect,'SELECT COUNT(*) AS n FROM tasks WHERE user_id=1')['n']==6
    with connect() as conn:
        with conn.cursor() as cur:cur.execute('DELETE FROM users WHERE id=1')
    assert one(connect,'SELECT COUNT(*) AS n FROM exam_plan_tasks')['n']==0


def test_clear_memories_requires_confirmation_and_is_account_scoped(db_app):
    b,c,connect=db_app
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO memories(user_id,label,content,active,created_at,updated_at) VALUES(1,'A','one',TRUE,NOW(),NOW()),(2,'B','two',TRUE,NOW(),NOW())")
    assert c.delete('/api/memories',json={}).status_code==400
    assert c.delete('/api/memories',json={'confirmed':True}).status_code==200
    assert b.load_active_memory_bundle(1)==('',[])
    assert one(connect,'SELECT COUNT(*) AS n FROM memories WHERE user_id=2')['n']==1
