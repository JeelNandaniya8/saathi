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


def test_multi_time_schedules_are_atomic_duplicate_safe_and_owned(db_app,monkeypatch):
    _,c,db=db_app;monkeypatch.setenv('CARE_ROUTINES_ENABLED','true')
    now=datetime.now(timezone.utc)
    first,payload=create(c,starts_at=[(now+timedelta(hours=1)).isoformat(),(now+timedelta(hours=9)).isoformat()])
    assert one(db,"SELECT COUNT(*) n FROM reminders WHERE kind='medication'")['n']==2
    assert one(db,'SELECT COUNT(*) n FROM care_occurrences')['n']==2
    retry=c.post('/api/care/routines',json=payload)
    assert retry.json['replayed'] and len(retry.json['ids'])==2
    assert one(db,'SELECT COUNT(*) n FROM reminders')['n']==2
    broken={**payload,'client_id':str(uuid4()),'starts_at':[payload['starts_at'][0],'bad']}
    assert c.post('/api/care/routines',json=broken).status_code==400
    assert one(db,'SELECT COUNT(*) n FROM reminders')['n']==2


def test_prescription_transcription_requires_external_consent_and_never_schedules(db_app,monkeypatch):
    import io
    b,c,db=db_app;monkeypatch.setenv('CARE_ROUTINES_ENABLED','true')
    calls=[]
    monkeypatch.setattr(b,'prepare_chat_attachments',lambda files,entitlement:[{'name':'rx.png','mime_type':'image/png','content':b'fixture'}])
    def generate(messages,**options):
        calls.append((messages,options));return 'Original text [unclear]',{'prompt_tokens':2,'output_tokens':3,'total_tokens':5}
    monkeypatch.setattr(b,'generate_gemini_reply',generate)
    assert c.post('/api/care/prescription-draft',data={'file':(io.BytesIO(b'fixture'),'rx.png')}).status_code==400
    assert not calls
    response=c.post('/api/care/prescription-draft',data={'ai_confirmed':'true','file':(io.BytesIO(b'fixture'),'rx.png')})
    assert response.status_code==200 and response.json['verified'] is False and response.json['saved'] is False
    assert calls[0][1]['memory_context']=='' and calls[0][1]['file_only'] is True
    assert 'Never guess' in calls[0][0][0]['content']
    assert one(db,'SELECT COUNT(*) n FROM reminders')['n']==0
    assert one(db,'SELECT COUNT(*) n FROM chat_attachments')['n']==0
    assert one(db,'SELECT COUNT(*) n FROM ai_usage_events')['n']==1


def test_confirmed_instruction_edit_preserves_history_timing_and_invalidates_sharing(db_app,monkeypatch):
    b,c,db=db_app;monkeypatch.setenv('CARE_ROUTINES_ENABLED','true');rid,_=create(c)
    old=one(db,'SELECT * FROM reminders WHERE id=%s',(rid,))
    with db() as conn:
        with conn.cursor() as cur:
            future=old['current_scheduled_for']+timedelta(days=1)
            care.ensure_occurrence(cur,old,future)
            cur.execute("INSERT INTO care_shares(owner_id,recipient_id,routine_ids,fields,status,expires_at) VALUES(1,2,%s,'[\"status\",\"instructions\"]','accepted',NOW()+INTERVAL '7 days')",('[%s]'%rid,))
    url=f'/api/care/routines/{rid}';data={'action':'edit_instructions','title':'Reviewed name','instructions':'Exact new clinician text','confirmed':True,'version':1}
    assert c.patch(url,json={**data,'confirmed':False}).status_code==400
    assert c.patch(url,json={**data,'starts_at':'new'}).status_code==400
    assert c.patch(url,json=data).status_code==200
    updated=one(db,'SELECT * FROM reminders WHERE id=%s',(rid,))
    assert updated['note']==data['instructions'] and updated['next_run_at']==old['next_run_at'] and updated['care_schedule']['anchor']==old['care_schedule']['anchor']
    assert one(db,'SELECT instructions_snapshot FROM care_occurrences WHERE scheduled_for=%s',(old['current_scheduled_for'],))['instructions_snapshot']=='User-entered clinician text'
    assert one(db,'SELECT instructions_snapshot FROM care_occurrences WHERE scheduled_for=%s',(future,))['instructions_snapshot']==data['instructions']
    assert one(db,'SELECT status FROM care_shares')['status']=='pending'
    assert c.patch(url,json=data).status_code==409
    assert c.get('/api/export-data').json['care_occurrences'][0]['instructions_snapshot']=='User-entered clinician text'
    with c.session_transaction() as s:s['user_id']=2
    assert c.patch(url,json={**data,'version':2}).status_code==404
