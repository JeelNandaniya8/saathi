"""Lost-response retries and exact record reads against disposable PostgreSQL."""
import os
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4

import pytest
from test_database_flows import db_app, one

pytestmark = pytest.mark.skipif(not os.environ.get('TEST_DATABASE_URL'), reason='Requires isolated PostgreSQL')


def payload(kind, title='Revision ગુજરાતી हिन्दी'):
    common = dict(title=title, client_id=str(uuid4()))
    if kind == 'task':
        return dict(**common, details='Line one\nગુજરાતી નોંધ\nहिन्दी नोट',
                    due_at='2027-01-02T00:15:00+05:30', priority='medium')
    return dict(**common, note='Line one\nગુજરાતી નોંધ\nहिन्दी नोट',
                next_run_at='2027-01-02T00:15:00+05:30', recurrence='once', email_enabled=False)


@pytest.mark.parametrize('kind,table', [('task', 'tasks'), ('reminder', 'reminders')])
def test_lost_response_retry_is_exact_owned_and_does_not_overwrite(db_app, kind, table):
    _, client, db = db_app
    path = '/api/' + table
    body = payload(kind)
    first = client.post(path, json=body)
    assert first.status_code == 201, first.json
    saved = first.json[kind]
    # The caller missed the first response and explicitly retries the same operation.
    retry = client.post(path, json=body)
    assert retry.status_code == 201 and retry.json[kind] == saved
    assert one(db, 'SELECT COUNT(*) n FROM ' + table)['n'] == 1
    assert client.get(path + '/' + str(saved['id'])).json[kind] == saved
    changed = client.post(path, json={**body, 'title': 'Different intended record'})
    assert changed.status_code == 409
    assert client.get(path + '/' + str(saved['id'])).json[kind] == saved
    assert one(db, 'SELECT COUNT(*) n FROM ' + table)['n'] == 1
    with client.session_transaction() as session:
        session['user_id'] = 2
    assert client.get(path + '/' + str(saved['id'])).status_code == 404
    other = client.post(path, json=body)
    assert other.status_code == 201 and other.json[kind]['id'] != saved['id']


@pytest.mark.parametrize('kind,table', [('task', 'tasks'), ('reminder', 'reminders')])
def test_concurrent_identical_creates_commit_one_record(db_app, kind, table):
    backend, _, db = db_app
    body = payload(kind)
    gate = Barrier(2)
    def send():
        with backend.app.test_client() as client:
            with client.session_transaction() as session:
                session.update(user_id=1, session_version=1, csrf_token='local-csrf')
            gate.wait(timeout=5)
            response = client.post('/api/' + table, json=body,
                                   headers={'X-CSRF-Token': 'local-csrf'})
            return response.status_code, response.json
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: send(), range(2)))
    assert [status for status, _ in results] == [201, 201], results
    assert results[0][1][kind]['id'] == results[1][1][kind]['id']
    assert one(db, 'SELECT COUNT(*) n FROM ' + table)['n'] == 1


@pytest.mark.parametrize('kind,table', [('task', 'tasks'), ('reminder', 'reminders')])
def test_legacy_creates_and_new_explicit_requests_remain_distinct(db_app, kind, table):
    _, client, db = db_app
    body = payload(kind); body.pop('client_id')
    first = client.post('/api/' + table, json=body)
    second = client.post('/api/' + table, json=body)
    assert first.status_code == second.status_code == 201
    assert first.json[kind]['id'] != second.json[kind]['id']
    assert one(db, 'SELECT COUNT(*) n FROM ' + table)['n'] == 2


@pytest.mark.parametrize('bad_id', ['not-a-uuid', None, [], 5])
def test_invalid_task_identity_creates_nothing(db_app, bad_id):
    _, client, db = db_app
    assert client.post('/api/tasks', json={**payload('task'), 'client_id': bad_id}).status_code == 400
    assert one(db, 'SELECT COUNT(*) n FROM tasks')['n'] == 0


def test_task_read_back_is_private_and_a_retry_cannot_revert_a_later_edit(db_app):
    _, client, db = db_app
    body = payload('task'); body['due_at'] = None
    created = client.post('/api/tasks', json=body).json['task']
    path = '/api/tasks/' + str(created['id'])
    assert client.post('/api/tasks', json=body).json['task'] == created
    assert client.patch(path, json={'title': 'Later deliberate edit'}).status_code == 200
    assert client.post('/api/tasks', json=body).status_code == 409
    assert client.get(path).json['task']['title'] == 'Later deliberate edit'
    assert one(db, 'SELECT COUNT(*) n FROM tasks')['n'] == 1
    with client.session_transaction() as session:
        session.clear()
    assert client.get(path).status_code == 401
