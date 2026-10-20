"""Owned read-back, exact busy retry and quota enforcement for prefixed maps."""
import json
import os
from uuid import uuid4
import pytest
from test_database_flows import db_app, one
from test_audit_reliability_database import send
from test_mindmap_privacy_prefix import REQUEST, Response, coin_map

pytestmark = pytest.mark.skipif(
    not os.environ.get('TEST_DATABASE_URL'), reason='Requires isolated PostgreSQL')


@pytest.mark.parametrize('stream', [False, True])
@pytest.mark.parametrize('busy_first', [False, True])
def test_prefixed_normal_map_saves_once_after_exact_retry(db_app, monkeypatch, stream, busy_first):
    backend, client, connect = db_app
    monkeypatch.setattr(backend, 'GEMINI_API_KEY', 'fixture-key')
    monkeypatch.setenv('GEMINI_FAST_MODEL', 'gemini-fixture-busy')
    monkeypatch.setenv('GEMINI_MODEL', 'gemini-fixture-study')
    busy = [busy_first]
    calls = []

    def provider(*args, **kwargs):
        calls.append((args[2], kwargs.get('fast')))
        assert args[2] == 'gemini-fixture-study' and not kwargs.get('fast')
        if busy[0]:
            raise backend.ProviderError('AI_BUSY', 'Fixture study provider busy', 503)
        return Response(coin_map())

    monkeypatch.setattr(backend, 'provider_send', provider)
    cid = client.post('/api/conversations', json={}).json['conversation']['id']
    key = str(uuid4())
    if busy_first:
        path = f'/api/conversations/{cid}/messages' + ('/stream' if stream else '')
        failed = client.post(path, json=dict(content=REQUEST, mode='normal', request_id=key))
        if stream:
            events = [json.loads(line) for line in failed.data.splitlines()]
            assert any(e.get('type') == 'error' and e.get('code') == 'AI_BUSY' for e in events)
            assert not any(e.get('type') == 'complete' for e in events)
        else:
            assert failed.status_code == 503 and failed.json['code'] == 'AI_BUSY'
        for table in ('messages', 'mindmaps', 'chat_action_receipts'):
            assert one(connect, 'SELECT COUNT(*) AS n FROM ' + table)['n'] == 0
        assert client.get('/api/study-allowance?kind=map').json['allowance']['remaining'] == 2
        busy[0] = False
    saved = send(client, cid, REQUEST, stream, key)['assistant_message']
    assert not saved.get('action_error')
    receipt = saved['action_receipt']
    assert receipt['kind'] == 'mindmap' and type(receipt['resource_id']) is int
    rid = receipt['resource_id']
    for _ in range(2):
        row = client.get(f'/api/mindmaps/{rid}').json['mindmap']
        assert row['topic'] == 'SAATHI-LIVE-MAP21'
        assert row['data']['root']['children'][0]['desc'] == '{HH, HT, TH, TT}'
    loaded = client.get(f'/api/conversations/{cid}/messages').json['messages']
    assert loaded[0]['content'] == REQUEST and loaded[-1]['action_receipt'] == receipt
    assert send(client, cid, REQUEST, stream, key)['assistant_message']['id'] == saved['id']
    assert len(calls) == (2 if busy_first else 1)
    assert one(connect, 'SELECT COUNT(*) AS n FROM mindmaps')['n'] == 1
    assert one(connect, 'SELECT COUNT(*) AS n FROM chat_action_receipts')['n'] == 1
    assert client.get('/api/study-allowance?kind=map').json['allowance']['remaining'] == 1
    with client.session_transaction() as session:
        session['user_id'] = 2
    assert client.get(f'/api/mindmaps/{rid}').status_code == 404


@pytest.mark.parametrize('stream', [False, True])
def test_prefixed_map_cannot_bypass_an_exhausted_fixture_allowance(db_app, monkeypatch, stream):
    backend, client, connect = db_app
    monkeypatch.setattr(backend, 'provider_send', lambda *a, **k: pytest.fail(
        'Exhausted fixture map allowance must stop before provider access'))
    with connect() as conn:
        with conn.cursor() as cur:
            for index in range(2):
                cur.execute('INSERT INTO mindmaps(user_id,topic,data_json,created_at) VALUES(1,%s,%s,NOW())',
                            (f'Existing fixture {index}', json.dumps(coin_map())))
    cid = client.post('/api/conversations', json={}).json['conversation']['id']
    path = f'/api/conversations/{cid}/messages' + ('/stream' if stream else '')
    response = client.post(path, json=dict(content=REQUEST, mode='normal', request_id=str(uuid4())))
    if stream:
        events = [json.loads(line) for line in response.data.splitlines()]
        assert any(e.get('type') == 'error' and e.get('code') == 'AI_QUOTA' for e in events)
        assert not any(e.get('type') == 'complete' for e in events)
    else:
        assert response.status_code == 429 and response.json['code'] == 'AI_QUOTA'
    assert one(connect, 'SELECT COUNT(*) AS n FROM mindmaps')['n'] == 2
    assert one(connect, 'SELECT COUNT(*) AS n FROM messages')['n'] == 0
    assert one(connect, 'SELECT COUNT(*) AS n FROM chat_action_receipts')['n'] == 0
    assert client.get('/api/study-allowance?kind=map').json['allowance']['remaining'] == 0
