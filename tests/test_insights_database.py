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
