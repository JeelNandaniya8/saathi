"""Timings ownership, retention and completion history in real PostgreSQL."""
import os
import uuid
import pytest
from test_database_flows import db_app, one

pytestmark = pytest.mark.skipif(not os.environ.get('TEST_DATABASE_URL'), reason='Requires isolated PostgreSQL test service')


def test_timings_are_owned_idempotent_bounded_exportable_and_deletable(db_app):
    _, client, db = db_app
    conversation = client.post('/api/conversations', json={}).json['conversation']['id']
    payload = {'request_id': str(uuid.uuid4()), 'conversation_id': conversation,
               'first_text_ms': 120, 'total_ms': 700, 'outcome': 'complete'}
    for _ in range(2):
        assert client.post('/api/response-timings', json=payload).status_code == 200
    assert client.get('/api/response-timings').json['summary']['attempts'] == 1
    assert client.get('/api/export-data').json['response_timings'][0]['total_ms'] == 700
    with client.session_transaction() as session:
        session['user_id'] = 2
    assert client.post('/api/response-timings', json=payload).status_code == 404
    assert client.get('/api/response-timings').json['summary']['attempts'] == 0
    assert client.delete('/api/response-timings').status_code == 200
    with client.session_transaction() as session:
        session['user_id'] = 1
    assert client.get('/api/response-timings').json['summary']['attempts'] == 1
    with db() as conn:
        with conn.cursor() as cur:
            for _ in range(101):
                cur.execute("INSERT INTO response_timings(user_id,request_id,conversation_id,total_ms,outcome) VALUES(1,%s,%s,20,'error')", (str(uuid.uuid4()), conversation))
    assert client.post('/api/response-timings', json=payload).status_code == 200
    assert one(db, 'SELECT count(*) AS n FROM response_timings')['n'] == 100
    with db() as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE response_timings SET created_at=NOW()-INTERVAL '31 days'")
    assert client.get('/api/response-timings').json['summary']['attempts'] == 0
    assert one(db, 'SELECT count(*) AS n FROM response_timings')['n'] == 0
    assert client.post('/api/response-timings', json={**payload, 'error_code': []}).status_code == 400
    with client.session_transaction() as session:
        session.clear()
    for path in ('/api/response-timings', '/api/weekly-review'):
        assert client.get(path).status_code == 401


def test_first_word_percentile_discloses_its_actual_denominator(db_app):
    _,client,_db=db_app
    cid=client.post('/api/conversations',json={}).json['conversation']['id']
    for outcome,first,total in [('complete',1000,2000),('complete',None,3000),('error',500,2500),('cancelled',None,800),('complete',6000,7000)]:
        result=client.post('/api/response-timings',json=dict(request_id=str(uuid.uuid4()),conversation_id=cid,first_text_ms=first,total_ms=total,outcome=outcome))
        assert result.status_code==200
    summary=client.get('/api/response-timings').json['summary']
    assert (summary['attempts'],summary['completed'],summary['errors'],summary['cancelled'])==(5,3,1,1)
    assert summary['first_text_samples']==2
    assert summary['first_text_ms']==3500
    assert summary['p95_first_text_ms']==5750
    with client.session_transaction() as session:session['user_id']=2
    empty=client.get('/api/response-timings').json['summary']
    assert empty['first_text_samples']==0 and empty['p95_first_text_ms'] is None


def test_recent_timings_identify_owned_attempts_without_conversation_text(db_app):
    _, client, _db = db_app
    conversations = [client.post('/api/conversations', json={}).json['conversation']['id'] for _ in range(2)]
    attempts = []
    for index in range(10):
        payload = dict(request_id=str(uuid.uuid4()), conversation_id=conversations[index % 2],
                       first_text_ms=100 if index % 2 else None, total_ms=200,
                       outcome='complete' if index % 2 else 'error',
                       error_code='' if index % 2 else 'AI_BUSY')
        assert client.post('/api/response-timings', json=payload).status_code == 200
        attempts.append(payload)
    result = client.get('/api/response-timings').json
    assert result['summary']['attempts'] == 10
    assert len(result['recent']) == 8
    for actual, expected in zip(result['recent'], reversed(attempts[-8:])):
        assert set(actual) == {'request_id', 'conversation_id', 'first_text_ms', 'total_ms', 'outcome', 'error_code', 'created_at'}
        for field, value in expected.items():
            assert actual[field] == value
    with client.session_transaction() as session:
        session['user_id'] = 2
    assert client.get('/api/response-timings').json['recent'] == []


def test_weekly_completion_is_not_redated_by_edits_and_reopen_is_excluded(db_app, monkeypatch):
    backend, client, db = db_app
    monkeypatch.setattr(backend, 'generate_study_json', lambda *args: pytest.fail('Review must not call Gemini'))
    client.patch('/api/workspace/preferences', json={'timezone': 'Asia/Kolkata'})
    task = client.post('/api/tasks', json={'title': 'Review algebra'}).json['task']['id']
    path = f'/api/tasks/{task}'
    client.patch(path, json={'completed': True})
    completed = one(db, 'SELECT completed_at FROM tasks WHERE id=%s', (task,))['completed_at']
    assert completed is not None
    client.patch(path, json={'title': 'Review geometry'})
    assert one(db, 'SELECT completed_at FROM tasks WHERE id=%s', (task,))['completed_at'] == completed
    review = client.get('/api/weekly-review')
    assert review.status_code == 200, review.json
    assert review.json['timezone'] == 'Asia/Kolkata'
    assert review.json['summary']['completed_tasks'] == 1
    assert review.json['summary']['practice_accuracy'] is None
    with client.session_transaction() as session:
        session['user_id'] = 2
    assert client.get('/api/weekly-review').json['summary']['completed_tasks'] == 0
    with client.session_transaction() as session:
        session['user_id'] = 1
    client.patch(path, json={'completed': False})
    assert one(db, 'SELECT completed_at FROM tasks WHERE id=%s', (task,))['completed_at'] is None
    assert client.get('/api/weekly-review').json['summary']['completed_tasks'] == 0
