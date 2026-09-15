"""Owned workflows and notification scheduling against disposable PostgreSQL."""
import json
import os
import uuid
from datetime import datetime,timedelta,timezone
import pytest
import daily_workspace as daily
import push_notifications as push
from test_database_flows import db_app,one
from test_reliability import questions
from test_workspace_database import subscribed,reminder

pytestmark=pytest.mark.skipif(not os.environ.get('TEST_DATABASE_URL'),reason='Requires isolated PostgreSQL test service')


def switch(client,uid):
    with client.session_transaction() as s:s['user_id']=uid


def test_preferences_are_owned_validated_exported_and_csrf_protected(db_app):
    _,c,db=db_app
    assert c.get('/api/workspace/preferences').json['preferences']['onboarding_done'] is False
    body={'language':'gu','timezone':'Asia/Kolkata','goal':'study','onboarding_done':True,'quiet_enabled':True,'notification_mode':'digest','digest_time':'18:00'}
    r=c.patch('/api/workspace/preferences',json=body);assert r.status_code==200,r.json
    assert r.json['preferences']['language']=='gu'
    assert c.get('/api/me').json['user']['language']=='gu'
    assert c.patch('/api/workspace/preferences',json={'timezone':'nonsense'}).status_code==400
    assert c.patch('/api/workspace/preferences',json=body,headers={'X-CSRF-Token':''}).status_code==403
    exported=c.get('/api/export-data');assert exported.status_code==200
    assert exported.json['workspace_preferences'][0]['quiet_start']=='22:00:00'
    switch(c,2);assert c.get('/api/workspace/preferences').json['preferences']['onboarding_done'] is False
    assert c.get('/api/export-data').json['workspace_preferences']==[]
    with c.session_transaction() as s:s.clear()
    for path in ('/api/workspace/preferences','/api/subject-spaces','/api/revision','/api/care/plan-preview'):
        assert c.get(path).status_code==401


def test_subject_links_ownership_retry_search_and_delete_preserve_original(db_app):
    _,c,db=db_app
    n=c.post('/api/quick-notes',json={'client_id':str(uuid.uuid4()),'title':'ગુજરાતી note','content':'Private'}).json['note']
    r=c.post('/api/subject-spaces',json={'name':'અભ્યાસ','color':'sage'});assert r.status_code==201,r.json
    sid=r.json['space']['id'];path=f'/api/subject-spaces/{sid}/items';link={'kind':'note','resource_id':n['id']}
    assert c.post(path,json=link).status_code==200
    assert c.post(path,json=link).status_code==200
    items=c.get(path).json['items'];assert len(items)==1 and items[0]['title']=='ગુજરાતી note'
    assert c.get('/api/subject-resources?kind=note&q=ગુજરાતી').json['resources'][0]['id']==n['id']
    assert c.get('/api/subject-resources?kind=users').status_code==400
    assert c.post(path,json={'kind':'note','resource_id':True}).status_code==400
    switch(c,2)
    assert c.get(path).status_code==404
    assert c.delete(f'/api/subject-spaces/{sid}').status_code==404
    assert c.get('/api/subject-resources?kind=note').json['resources']==[]
    other=c.post('/api/subject-spaces',json={'name':'Other'}).json['space']['id']
    assert c.post(f'/api/subject-spaces/{other}/items',json=link).status_code==404
    switch(c,1)
    assert c.get('/api/export-data').json['subject_items'][0]['note_id']==n['id']
    assert c.delete(f'/api/subject-spaces/{sid}').status_code==200
    assert c.get('/api/quick-notes').json['notes'][0]['id']==n['id']
    assert one(db,'SELECT count(*) AS n FROM subject_items')['n']==0


def test_original_resource_deletion_cascades_only_its_link(db_app):
    _,c,db=db_app
    sid=c.post('/api/subject-spaces',json={'name':'Chapter'}).json['space']['id']
    note=c.post('/api/quick-notes',json={'client_id':str(uuid.uuid4()),'content':'Saved'}).json['note']
    c.post(f'/api/subject-spaces/{sid}/items',json={'kind':'note','resource_id':note['id']})
    assert c.delete('/api/quick-notes/'+str(note['id']),json={'version':1}).status_code==200
    assert c.get(f'/api/subject-spaces/{sid}/items').json['items']==[]
    assert len(c.get('/api/subject-spaces').json['spaces'])==1


def test_mock_errors_review_import_and_retries_never_advance_twice(db_app,monkeypatch):
    b,c,db=db_app;monkeypatch.setattr(b,'generate_study_json',lambda *args:questions())
    test=c.post('/api/mock-tests/generate',json={'topic':'Math','question_count':5,'time_limit_minutes':5}).json['test']
    r=c.post(f"/api/mock-tests/{test['id']}/submit",json={'answers':{'1':'A'}});assert r.status_code==200,r.json
    q=c.get('/api/revision').json;assert q['due']==4
    assert c.post('/api/revision/import',json={}).status_code==200
    assert c.get('/api/revision').json['due']==4
    card=q['items'][0];path=f"/api/revision/{card['id']}";payload={'version':card['version'],'rating':'good'}
    switch(c,2);assert c.patch(path,json=payload).status_code==404;assert c.get('/api/revision').json['items']==[]
    switch(c,1)
    first=c.patch(path,json=payload);assert first.status_code==200,first.json
    assert c.patch(path,json=payload).status_code==409
    c.post('/api/revision/import',json={})
    assert c.get('/api/revision').json['due']==3
    assert one(db,'SELECT repetitions FROM revision_items WHERE id=%s',(card['id'],))['repetitions']==1


def test_flashcards_feed_queue_and_feedback_does_not_change_other_messages(db_app):
    _,c,db=db_app
    with db() as conn:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO conversations(user_id,title,created_at,updated_at) VALUES(1,'Cards',NOW(),NOW()) RETURNING id");cid=cur.fetchone()['id']
            text='[FLASHCARDS]\nFront: પ્રશ્ન\nBack: જવાબ\n---\nFront: Second\nBack: Answer\n[/FLASHCARDS]'
            cur.execute("INSERT INTO messages(user_id,conversation_id,role,content,created_at) VALUES(1,%s,'assistant',%s,NOW()) RETURNING id",(cid,text));mid=cur.fetchone()['id']
            cur.execute("INSERT INTO study_progress(user_id,conversation_id,message_id,kind,progress,created_at,updated_at) VALUES(1,%s,%s,'flashcards','{}',NOW(),NOW())",(cid,mid))
    response=c.patch(f'/api/messages/{mid}/study-progress',json={'progress':{'review_indices':[0]}});assert response.status_code==200,response.json
    assert c.get('/api/revision').json['items'][0]['front']=='પ્રશ્ન'
    c.patch(f'/api/messages/{mid}/study-progress',json={'progress':{'review_indices':[0,1]}})
    assert c.get('/api/revision').json['due']==2
    for rating in ('helpful','wrong','unclear',None):
        assert c.patch(f'/api/messages/{mid}/feedback',json={'rating':rating}).status_code==200
    assert c.patch(f'/api/messages/{mid}/feedback',json=['wrong']).status_code==400
    switch(c,2);assert c.patch(f'/api/messages/{mid}/feedback',json={'rating':'wrong'}).status_code==404


def test_care_preview_is_read_only_and_confirm_is_atomic_owned_and_stale_safe(db_app):
    _,c,db=db_app
    c.patch('/api/workspace/preferences',json={'timezone':'Asia/Kolkata','onboarding_done':True})
    with db() as conn:
        with conn.cursor() as cur:
            for uid,priority,title in [(1,'low','Read a page'),(1,'medium','Summarise'),(1,'high','Important'),(2,'low','Other')]:
                cur.execute("INSERT INTO tasks(user_id,title,priority,due_at,created_at,updated_at) VALUES(%s,%s,%s,NOW()-INTERVAL '1 hour',NOW(),NOW())",(uid,title,priority))
    before=one(db,'SELECT due_at FROM tasks WHERE id=1')['due_at']
    preview=c.get('/api/care/plan-preview');assert preview.status_code==200,preview.json
    rows=preview.json['tasks'];assert {x['title'] for x in rows}=={'Read a page','Summarise'}
    assert one(db,'SELECT due_at FROM tasks WHERE id=1')['due_at']==before
    payload={'items':[{k:x[k] for k in ('id','due_at','proposed_at')} for x in rows]}
    bad=json.loads(json.dumps(payload));bad['items'][0]['proposed_at']=before.isoformat()
    assert c.post('/api/care/lighten-plan',json=bad).status_code==409
    assert one(db,'SELECT due_at FROM tasks WHERE id=1')['due_at']==before
    switch(c,2);assert c.post('/api/care/lighten-plan',json=payload).status_code==409
    switch(c,1);result=c.post('/api/care/lighten-plan',json=payload);assert result.status_code==200,result.json
    assert result.json['moved']==2
    assert c.post('/api/care/lighten-plan',json=payload).status_code==409
    assert one(db,"SELECT due_at<NOW() AS same FROM tasks WHERE title='Important'")['same'] is True


def test_quiet_hours_filter_before_claim_and_digest_is_once_per_local_day(db_app,monkeypatch):
    b,c,db=db_app;subscribed(db_app,monkeypatch);reminder(db);calls=[]
    monkeypatch.setattr(push,'send_push',lambda sub,payload,config:calls.append(payload) or 201)
    # A one-hour window around now works across midnight without relying on wall-clock hour.
    now=datetime.now(timezone.utc)
    start=(now-timedelta(minutes=30)).strftime('%H:%M');end=(now+timedelta(minutes=30)).strftime('%H:%M')
    assert c.patch('/api/workspace/preferences',json={'quiet_enabled':True,'quiet_start':start,'quiet_end':end}).status_code==200
    assert push.deliver_due(vars(b))['sent']==0 and not calls
    assert one(db,'SELECT count(*) AS n FROM push_deliveries')['n']==0
    assert c.patch('/api/workspace/preferences',json={'quiet_enabled':False,'notification_mode':'digest','digest_time':'00:00'}).status_code==200
    r=push.deliver_due(vars(b));assert r['sent']==1,r
    assert calls[0]['kind']=='digest' and 'Private' not in json.dumps(calls)
    assert push.deliver_due(vars(b))['sent']==0
    assert one(db,'SELECT count(*) AS n FROM push_deliveries')['n']==0
    assert one(db,'SELECT count(*) AS n FROM push_digest_deliveries')['n']==1
    with db() as conn:
        with conn.cursor() as cur:cur.execute("UPDATE push_digest_deliveries SET local_date=local_date-1")
    assert push.deliver_due(vars(b))['sent']==1


def test_digest_retry_is_bounded_and_revoked_device_cannot_receive(db_app,monkeypatch):
    b,c,db=db_app;subscribed(db_app,monkeypatch);reminder(db);calls=[]
    c.patch('/api/workspace/preferences',json={'notification_mode':'digest','digest_time':'00:00'})
    monkeypatch.setattr(push,'send_push',lambda *args:calls.append(1) or 503)
    for _ in range(5):
        push.deliver_due(vars(b))
        with db() as conn:
            with conn.cursor() as cur:cur.execute("UPDATE push_digest_deliveries SET updated_at=NOW()-INTERVAL '6 minutes'")
    assert push.deliver_due(vars(b))['failed']==0 and len(calls)==5
    assert c.post('/api/logout-all',json={}).status_code==200
    assert one(db,'SELECT count(*) AS n FROM push_digest_deliveries')['n']==0
