"""October 17: disposable PostgreSQL only; never exercise provider/production quotas."""
import io
import json
import os
import statistics
from time import perf_counter
from uuid import uuid4
import pytest
import struct
import zlib
from test_database_flows import db_app,one,questions
from test_audit_reliability_database import send

pytestmark=pytest.mark.skipif(not os.environ.get('TEST_DATABASE_URL'),reason='Requires isolated PostgreSQL')


def fixture_reply(b,monkeypatch,reply='Fixture reply.',before=None):
    def answer(*args,**kwargs):
        if before:before()
        return reply,{}
    def stream(*args,**kwargs):
        text,usage=answer();yield text;return usage
    monkeypatch.setattr(b,'generate_gemini_reply',answer)
    monkeypatch.setattr(b,'stream_gemini_reply',stream)


def upload(c,path,key,color='red',mode='normal',file_only=True):
    pixel=b'\xff\x00\x00' if color=='red' else b'\x00\x00\xff'
    def chunk(kind,data):return struct.pack('!I',len(data))+kind+data+struct.pack('!I',zlib.crc32(kind+data))
    png=b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('!IIBBBBB',8,8,8,2,0,0,0))+chunk(b'IDAT',zlib.compress((b'\x00'+pixel*8)*8))+chunk(b'IEND',b'')
    image=io.BytesIO(png)
    return c.post(path,data=dict(content='Read the fixture code.',mode=mode,request_id=key,file_only=str(file_only).lower(),attachments=(image,'same.png')),content_type='multipart/form-data')


@pytest.mark.parametrize('stream',[False,True])
def test_exact_retry_rejects_changed_file_mode_or_privacy_and_supports_legacy(db_app,monkeypatch,stream):
    b,c,connect=db_app;fixture_reply(b,monkeypatch)
    cid=c.post('/api/conversations',json={}).json['conversation']['id'];key=str(uuid4())
    path=f'/api/conversations/{cid}/messages'+('/stream' if stream else '')
    first=upload(c,path,key);assert first.status_code==200,first.data
    replay=upload(c,path,key);assert replay.status_code==200,replay.data
    for changed in [dict(color='blue'),dict(mode='explain'),dict(file_only=False)]:
        result=upload(c,path,key,**changed);assert result.status_code==409,result.data
    with connect() as conn:
        with conn.cursor() as cur:cur.execute('UPDATE messages SET request_fingerprint=NULL WHERE client_request_id=%s',(key,))
    assert upload(c,path,key).status_code==200
    assert upload(c,path,key,color='blue').status_code==409
    assert one(connect,'SELECT COUNT(*) AS n FROM messages')['n']==2
    assert one(connect,'SELECT COUNT(*) AS n FROM chat_attachments')['n']==1
    assert one(connect,'SELECT file_only FROM messages WHERE role=\'user\'')['file_only']


@pytest.mark.parametrize('stream',[False,True])
def test_cancel_winning_race_prevents_save_and_late_cancel_returns_receipt(db_app,monkeypatch,stream):
    b,c,connect=db_app;cid=c.post('/api/conversations',json={}).json['conversation']['id'];key=str(uuid4())
    def cancel():
        worker=b.app.test_client();worker.environ_base['HTTP_X_CSRF_TOKEN']='stop'
        with worker.session_transaction() as session:session.update(user_id=1,session_version=1,csrf_token='stop')
        assert worker.post(f'/api/conversations/{cid}/cancel',json=dict(request_id=key)).json['cancelled']
    fixture_reply(b,monkeypatch,before=cancel)
    path=f'/api/conversations/{cid}/messages'+('/stream' if stream else '')
    body=dict(content='Fixture ordinary question',mode='normal',request_id=key)
    response=c.post(path,json=body)
    if stream:assert json.loads(response.data.splitlines()[-1])['code']=='AI_STOPPED'
    else:assert response.status_code==409 and response.json['code']=='AI_STOPPED'
    assert one(connect,'SELECT COUNT(*) AS n FROM messages')['n']==0
    assert c.post(path,json=body).status_code==409
    fixture_reply(b,monkeypatch)
    result=send(c,cid,body['content'],stream,str(uuid4()))
    saved_key=one(connect,"SELECT client_request_id FROM messages WHERE role='user'")['client_request_id']
    late=c.post(f'/api/conversations/{cid}/cancel',json=dict(request_id=saved_key)).json
    assert not late['cancelled'] and late['completed']['assistant_message']['id']==result['assistant_message']['id']
    assert '_request_fingerprint' not in late['completed']
    with c.session_transaction() as session:session['user_id']=2
    assert c.post(f'/api/conversations/{cid}/cancel',json=dict(request_id=saved_key)).status_code==404
    assert one(connect,'SELECT COUNT(*) AS n FROM messages')['n']==2


def test_exact_job_lookup_recovers_saved_result_even_with_exhausted_quota(db_app,monkeypatch):
    b,c,connect=db_app;calls=[]
    monkeypatch.setattr(b,'generate_study_json',lambda *a:(calls.append(True) or questions()))
    body=dict(job_id=str(uuid4()),topic='Fixture maths',question_count=5,time_limit_minutes=5,language='hi')
    response=c.post('/api/mock-tests/generate',json=body);assert response.status_code==200,response.json
    tid=response.json['test']['id']
    with connect() as conn:
        with conn.cursor() as cur:
            for _ in range(6):cur.execute("INSERT INTO study_jobs(id,user_id,kind,request,status) VALUES(%s,1,'mock','{}','failed')",(str(uuid4()),))
    job=c.get('/api/study-jobs?kind=mock&job_id='+body['job_id']).json['jobs']
    assert len(job)==1 and job[0]['status']=='ready' and job[0]['result_id']==tid
    assert c.get('/api/study-allowance?kind=mock').json['allowance']['remaining']==0
    assert c.post('/api/mock-tests/generate',json=body).status_code==202
    assert len(calls)==1 and one(connect,'SELECT COUNT(*) AS n FROM mock_tests')['n']==1
    with c.session_transaction() as session:session['user_id']=2
    assert c.get('/api/study-jobs?kind=mock&job_id='+body['job_id']).json['jobs']==[]


def test_job_receipt_and_document_commit_atomically_on_response_failure(db_app,monkeypatch):
    import study_tools
    b,c,connect=db_app;monkeypatch.setattr(b,'generate_study_json',lambda *a:questions())
    original=study_tools.public_test
    def interrupted(_row):raise RuntimeError('Fixture response interrupted after resource commit')
    monkeypatch.setattr(study_tools,'public_test',interrupted)
    body=dict(job_id=str(uuid4()),topic='Fixture atomic save',question_count=5,time_limit_minutes=5)
    response=c.post('/api/mock-tests/generate',json=body)
    assert response.status_code==503
    row=one(connect,'SELECT status,result_id FROM study_jobs WHERE id=%s',(body['job_id'],))
    assert row['status']=='ready' and row['result_id']
    assert one(connect,'SELECT COUNT(*) AS n FROM mock_tests')['n']==1
    monkeypatch.setattr(study_tools,'public_test',original)
    assert c.get('/api/mock-tests/'+str(row['result_id'])).status_code==200
    assert c.post('/api/mock-tests/generate',json=body).status_code==202
    assert one(connect,'SELECT COUNT(*) AS n FROM mock_tests')['n']==1


@pytest.mark.parametrize('stream',[False,True])
def test_wrong_transcription_polarity_is_not_persisted(db_app,monkeypatch,stream):
    b,c,connect=db_app
    fixture_reply(b,monkeypatch,'[FLASHCARDS]\nFront: Which DNA strand is the transcription template?\nBack: The template strand has 5′→3′ polarity.\n[/FLASHCARDS]')
    cid=c.post('/api/conversations',json={}).json['conversation']['id']
    response=c.post(f'/api/conversations/{cid}/messages'+('/stream' if stream else ''),json=dict(content='Create transcription flashcards',mode='flashcards',request_id=str(uuid4())))
    if stream:assert json.loads(response.data.splitlines()[-1])['code']=='AI_ACCURACY'
    else:assert response.status_code==502
    assert one(connect,'SELECT COUNT(*) AS n FROM messages')['n']==0
    assert one(connect,'SELECT COUNT(*) AS n FROM revision_items')['n']==0


def test_100_save_replay_reload_journeys_have_exact_receipts_without_duplicates(db_app,monkeypatch,capsys):
    b,c,connect=db_app
    monkeypatch.setattr(b,'provider_send',lambda *a,**k:pytest.fail('Literal note journeys must not call the provider'))
    cid=c.post('/api/conversations',json={}).json['conversation']['id']
    timings=[]
    for index in range(100):
        lang=['en','gu','hi'][index%3]
        title={'en':'Fixture note','gu':'અભ્યાસ નોંધ','hi':'अभ्यास नोट'}[lang]+' '+str(index)
        text='Save this as a private note titled '+title+': fixture text '+str(index)
        key=str(uuid4());started=perf_counter();result=send(c,cid,text,True,key);timings.append((perf_counter()-started)*1000);again=send(c,cid,text,True,key)
        mid=result['assistant_message']['id'];receipt=result['assistant_message']['action_receipt']
        assert receipt['kind']=='note' and again['assistant_message']['id']==mid
        assert one(connect,'SELECT title,content FROM quick_notes WHERE id=%s AND user_id=1',(receipt['resource_id'],))==dict(title=title,content='fixture text '+str(index))
        loaded=c.get(f'/api/conversations/{cid}/messages?limit=100').json['messages'][-1]
        assert loaded['id']==mid and loaded['action_receipt']['resource_id']==receipt['resource_id']
    assert one(connect,'SELECT COUNT(*) AS n FROM quick_notes')['n']==100
    assert one(connect,'SELECT COUNT(*) AS n FROM chat_action_receipts')['n']==100
    assert one(connect,'SELECT COUNT(*) AS n FROM messages')['n']==200
    with capsys.disabled():print('STAGING_NOTE_RECEIPTS '+json.dumps(dict(n=100,completed=100,duplicates=0,false_saves=0,p50_receipt_ms=round(statistics.median(timings),1),p95_receipt_ms=round(sorted(timings)[94],1),scope='local Flask and PostgreSQL; no provider/network; not first-word latency')))


@pytest.mark.parametrize('stream',[False,True])
def test_regeneration_stop_is_durable_and_unknown_retry_is_idempotent(db_app,monkeypatch,stream):
    b,c,connect=db_app;fixture_reply(b,monkeypatch,'Original answer.')
    cid=c.post('/api/conversations',json={}).json['conversation']['id']
    original=send(c,cid,'Fixture ordinary question',True)['assistant_message'];key=str(uuid4())
    def cancel():
        worker=b.app.test_client();worker.environ_base['HTTP_X_CSRF_TOKEN']='stop'
        with worker.session_transaction() as session:session.update(user_id=1,session_version=1,csrf_token='stop')
        assert worker.post(f'/api/conversations/{cid}/cancel',json=dict(request_id=key)).json['cancelled']
    fixture_reply(b,monkeypatch,'Alternative answer.',before=cancel)
    path=f'/api/conversations/{cid}/regenerate';headers={'Accept':'application/x-ndjson'} if stream else {}
    response=c.post(path,json=dict(request_id=key),headers=headers)
    if stream:assert json.loads(response.data.splitlines()[-1])['code']=='AI_STOPPED'
    else:assert response.status_code==409 and response.json['code']=='AI_STOPPED'
    assert one(connect,"SELECT content FROM messages WHERE role='assistant'")['content']=='Original answer.'
    fixture_reply(b,monkeypatch,'Saved alternative.');key=str(uuid4())
    saved=c.post(path,json=dict(request_id=key)).json['assistant_message']
    replay=c.post(path,json=dict(request_id=key)).json
    assert replay['replayed'] and replay['assistant_message']['id']==saved['id']
    late=c.post(f'/api/conversations/{cid}/cancel',json=dict(request_id=key)).json
    assert not late['cancelled'] and late['completed_regeneration']['assistant_message']['id']==saved['id']
    assert one(connect,'SELECT COUNT(*) AS n FROM messages')['n']==2


def test_habit_journal_and_checkin_exact_link_reads_exclude_other_accounts(db_app):
    _,c,_=db_app
    resources=[('/api/habits',dict(name='Exact habit',frequency='daily'),'habit','habits'),('/api/journal',dict(title='Exact journal',content='private text',entry_date='2026-10-17'),'entry','entries'),('/api/check-ins',dict(mood=3,energy=3,note='private reflection'),'check_in','check_ins')]
    for path,body,key,collection in resources:
        response=c.post(path,json=body);assert response.status_code in {200,201},response.json
        item=response.json[key];identity=item['id']
        exact=c.get(path+'?id='+str(identity)).json[collection]
        assert len(exact)==1 and exact[0]['id']==identity
        assert c.get(path+'?id=invalid').status_code==400
        with c.session_transaction() as session:session['user_id']=2
        assert c.get(path+'?id='+str(identity)).json[collection]==[]
        with c.session_transaction() as session:session['user_id']=1
