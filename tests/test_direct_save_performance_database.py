"""Bound database round trips without weakening local-save trust guarantees."""
import os
from uuid import uuid4

import pytest
from app import limited as real_limited
from test_database_flows import db_app, one
from test_audit_reliability_database import send

pytestmark = pytest.mark.skipif(not os.environ.get('TEST_DATABASE_URL'), reason='Requires isolated PostgreSQL')


@pytest.mark.parametrize('stream', [False, True])
@pytest.mark.parametrize('command,table,budget', [
    ('Save a note. Title: Fast note; Content: Private probability checklist', 'quick_notes', 10),
    ('Remember that I prefer Physics with worked examples', 'memories', 10),
    ('Add a task. Title: Fast task; Details: Revise; Due: 2026-11-03T09:00:00+05:30', 'tasks', 10),
])
def test_direct_saves_use_one_lease_at_a_time_and_bounded_round_trips(db_app, monkeypatch, stream, command, table, budget):
    b, client, connect = db_app
    cid = client.post('/api/conversations', json={}).json['conversation']['id']
    counters = dict(active=0, maximum=0, queries=0)

    class Cursor:
        def __init__(self, cursor): self.cursor = cursor
        def __getattr__(self, name): return getattr(self.cursor, name)
        def execute(self, *args):
            counters['queries'] += 1
            return self.cursor.execute(*args)

    class Connection:
        def __init__(self):
            self.connection = connect()
            counters['active'] += 1
            counters['maximum'] = max(counters['maximum'], counters['active'])
        def __getattr__(self, name): return getattr(self.connection, name)
        def cursor(self): return Cursor(self.connection.cursor())
        def close(self):
            counters['active'] -= 1
            self.connection.close()

    def no_model(*args, **kwargs): pytest.fail('A direct save must not call a model')
    monkeypatch.setattr(b, 'get_db', Connection)
    monkeypatch.setattr(b, 'limited', real_limited)
    monkeypatch.setattr(b.secrets, 'randbelow', lambda _: 1)
    monkeypatch.setattr(b, 'generate_gemini_reply', no_model)
    monkeypatch.setattr(b, 'stream_gemini_reply', no_model)
    key = str(uuid4())
    result = send(client, cid, command, stream, key)
    assert result['assistant_message']['action_receipt']
    assert counters['maximum'] == 1 and counters['active'] == 0
    assert counters['queries'] <= budget, counters
    assert one(connect, 'SELECT COUNT(*) AS n FROM request_attempts')['n'] == 1
    assert one(connect, 'SELECT COUNT(*) AS n FROM ' + table)['n'] == 1
    loaded = client.get(f'/api/conversations/{cid}/messages').json['messages']
    assert [m['role'] for m in loaded] == ['user', 'assistant']
    assert loaded[-1]['action_receipt'] == result['assistant_message']['action_receipt']
    assert loaded[-1]['action_resource'] == result['assistant_message']['action_resource']
    assert send(client, cid, command, stream, key)['replayed'] is True
    assert one(connect, 'SELECT COUNT(*) AS n FROM ' + table)['n'] == 1
    assert one(connect, 'SELECT COUNT(*) AS n FROM ai_usage_events')['n'] == 0


def test_borrowed_limiter_connection_stays_open_and_attempts_survive_rollback(db_app, monkeypatch):
    b, _, connect = db_app
    monkeypatch.setattr(b.secrets, 'randbelow', lambda _: 1)
    conn = connect()
    try:
        for expected in [True, True, False]:
            assert b.consume_rate_limit('local-save', 'owner', 2, 5, conn) is expected
            assert not conn.closed
            conn.rollback()
        assert one(connect, 'SELECT COUNT(*) AS n FROM request_attempts')['n'] == 2
    finally:
        conn.close()


@pytest.mark.parametrize('stream', [False, True])
def test_reused_request_id_cannot_receipt_a_different_command(db_app, stream):
    _, client, connect = db_app
    cid = client.post('/api/conversations', json={}).json['conversation']['id']
    key = str(uuid4())
    send(client, cid, 'Save a note. Title: Original; Content: Original content', stream, key)
    response = client.post(f'/api/conversations/{cid}/messages' + ('/stream' if stream else ''), json=dict(
        content='Save a note. Title: Changed; Content: Changed content', mode='normal', request_id=key))
    assert response.status_code == 409 and 'already used' in response.json['error']
    assert one(connect, 'SELECT title,content FROM quick_notes') == dict(title='Original', content='Original content')


@pytest.mark.parametrize('stream', [False, True])
def test_fast_note_insert_keeps_limit_and_failure_receipt_honest(db_app, stream):
    _, client, connect = db_app
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO quick_notes(user_id,client_id,title,content) SELECT 1,md5(n::text)::uuid,'Note '||n,'Saved' FROM generate_series(1,100) n")
    cid = client.post('/api/conversations', json={}).json['conversation']['id']
    result = send(client, cid, 'Save a note. Title: Over limit; Content: Must not save', stream)['assistant_message']
    assert result['content'].startswith('Failed:') and not result.get('action_receipt')
    assert one(connect, 'SELECT COUNT(*) AS n FROM quick_notes')['n'] == 100
    assert one(connect, 'SELECT COUNT(*) AS n FROM chat_action_receipts')['n'] == 0



def test_idle_health_probe_keeps_real_database_writes_transactional(db_app, monkeypatch):
    from collections import OrderedDict
    import db_pool
    from psycopg2.extensions import TRANSACTION_STATUS_IDLE, TRANSACTION_STATUS_INTRANS

    monkeypatch.setattr(db_pool, '_pool', None)
    monkeypatch.setattr(db_pool, '_identity', None)
    monkeypatch.setattr(db_pool, '_checked', OrderedDict())
    lease = db_pool.connect(os.environ['TEST_DATABASE_URL'])
    pool = db_pool._pool
    try:
        assert not lease.autocommit
        assert lease.get_transaction_status() == TRANSACTION_STATUS_IDLE
        cur = lease.cursor()
        cur.execute('CREATE TEMP TABLE idle_probe_rollback (value INTEGER)')
        lease.commit()
        cur.execute('INSERT INTO idle_probe_rollback VALUES (1)')
        assert lease.get_transaction_status() == TRANSACTION_STATUS_INTRANS
        lease.rollback()
        cur.execute('SELECT COUNT(*) AS n FROM idle_probe_rollback')
        assert cur.fetchone()['n'] == 0
        cur.close()
    finally:
        lease.close()
        pool.closeall()
