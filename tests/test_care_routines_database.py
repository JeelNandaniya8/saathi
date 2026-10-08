import os
from datetime import datetime,timedelta,timezone
from uuid import uuid4
import pytest
from test_database_flows import db_app,one
import care_routines as care
pytestmark=pytest.mark.skipif(not os.environ.get('TEST_DATABASE_URL'),reason='Requires isolated PostgreSQL test service')


def create(c,**changes):
    payload={'title':'Prescribed schedule','instructions':'User-entered clinician text','timezone':'Asia/Kolkata',
             'starts_at':(datetime.now(timezone.utc)-timedelta(minutes=10)).isoformat(),
             'recurrence':'daily','confirmed':True,'client_id':str(uuid4()),**changes}
    result=c.post('/api/care/routines',json=payload)
    assert result.status_code==201,result.json
    return result.json['id'],payload


def test_gate_and_account_isolation_and_duplicate_create(db_app,monkeypatch):
    b,c,db=db_app
    monkeypatch.delenv('CARE_ROUTINES_ENABLED',raising=False)
    assert c.get('/api/care/routines/status').json['enabled'] is False
    assert c.get('/api/care/routines').status_code==503
    monkeypatch.setenv('CARE_ROUTINES_ENABLED','true')
    rid,payload=create(c)
    assert c.post('/api/care/routines',json=payload).json['replayed']
    occurrence=c.get('/api/care/routines').json['occurrences'][0]
    assert c.get('/api/reminders').json['reminders']==[]
    assert c.patch('/api/reminders/'+str(rid),json={'action':'snooze'}).status_code==409
    with c.session_transaction() as session:session['user_id']=2
    assert c.get('/api/care/routines').json['routines']==[]
    assert c.patch('/api/care/occurrences/'+str(occurrence['id']),json={'version':1,'confirmed':True,'action':'taken'}).status_code==404
    assert c.delete('/api/care/routines/'+str(rid),json={'confirmed':True}).status_code==404


def test_snooze_preserves_schedule_taken_is_idempotent_and_exported(db_app,monkeypatch):
    b,c,db=db_app;monkeypatch.setenv('CARE_ROUTINES_ENABLED','true')
    rid,_=create(c);data=c.get('/api/care/routines').json;occ=data['occurrences'][0];original=data['routines'][0]['current_scheduled_for']
    url='/api/care/occurrences/'+str(occ['id'])
    assert c.patch(url,json={'action':'snooze','version':occ['version'],'confirmed':True}).status_code==200
    routine=c.get('/api/care/routines').json['routines'][0]
    assert routine['current_scheduled_for']==original and routine['next_run_at']!=original
    assert c.patch(url,json={'action':'taken','version':occ['version'],'confirmed':True}).status_code==409
    occ=c.get('/api/care/routines').json['occurrences'][0]
    assert c.patch(url,json={'action':'taken','version':occ['version'],'confirmed':True}).status_code==200
    updated=c.get('/api/care/routines').json
    assert updated['routines'][0]['current_scheduled_for']!=original
    assert any(o['status']=='taken' for o in updated['occurrences'])
    assert c.patch(url,json={'action':'taken','version':occ['version'],'confirmed':True}).status_code==409
    assert any(o['status']=='taken' for o in c.get('/api/export-data').json['care_occurrences'])
    assert c.delete('/api/care/routines/'+str(rid),json={'confirmed':True}).status_code==200
    assert one(db,'SELECT COUNT(*) AS n FROM care_occurrences')['n']==0


def test_scheduler_advances_unconfirmed_independently_and_resume_skips_paused_gap(db_app,monkeypatch):
    b,c,db=db_app;monkeypatch.setenv('CARE_ROUTINES_ENABLED','true')
    rid,_=create(c);old=datetime.now(timezone.utc)-timedelta(days=5)
    with db() as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE reminders SET next_run_at=%s,current_scheduled_for=%s,care_schedule=jsonb_set(care_schedule,'{anchor}',to_jsonb(%s::text)) WHERE id=%s",(old,old,old.isoformat(),rid))
            cur.execute('DELETE FROM care_occurrences WHERE reminder_id=%s',(rid,))
    care.sync_due(vars(b));first=c.get('/api/care/routines').json
    assert len(first['occurrences'])==6
    assert sum(o['status']=='not_confirmed' for o in first['occurrences'])==5
    care.sync_due(vars(b));assert len(c.get('/api/care/routines').json['occurrences'])==6
    assert c.patch('/api/care/routines/'+str(rid),json={'active':False}).status_code==200
    assert c.patch('/api/care/routines/'+str(rid),json={'active':True}).status_code==200
    assert datetime.fromisoformat(c.get('/api/care/routines').json['routines'][0]['next_run_at'])>datetime.now(timezone.utc)


def test_future_record_cannot_be_snoozed_to_send_early(db_app,monkeypatch):
    _,c,_=db_app;monkeypatch.setenv('CARE_ROUTINES_ENABLED','true')
    create(c,starts_at=(datetime.now(timezone.utc)+timedelta(days=1)).isoformat())
    row=c.get('/api/care/routines').json['occurrences'][0]
    assert c.patch('/api/care/occurrences/'+str(row['id']),json={'action':'snooze','version':row['version'],'confirmed':True}).status_code==400
