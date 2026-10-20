"""Synthetic exact-note receipt/read-back/retry coverage, with no provider calls."""
import os
from uuid import uuid4

import pytest
from test_database_flows import db_app, one
from test_audit_reliability_database import send

pytestmark = pytest.mark.skipif(
    not os.environ.get('TEST_DATABASE_URL'), reason='Requires isolated PostgreSQL')


@pytest.mark.parametrize('language', ['en', 'gu', 'hi'])
@pytest.mark.parametrize('stream', [False, True])
def test_timestamp_note_survives_receipt_reload_and_exact_retry(db_app, monkeypatch, language, stream):
    backend, client, connect = db_app
    monkeypatch.setattr(backend, 'GEMINI_API_KEY', '')
    monkeypatch.setattr(backend, 'provider_send', lambda *a, **k: pytest.fail(
        'Explicit note saves must not contact an AI provider'))
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute('UPDATE users SET language=%s WHERE id=1', (language,))
    title = 'Saathi live verification 2026-10-20 21:36'
    content = 'Probability revision\nગુજરાતી નોંધ\nहिन्दी नोट\nMarker: SYNTHETIC-NOTE-BOUNDARY'
    command = f'Save this as a private note titled {title}. Content: {content}'
    cid = client.post('/api/conversations', json={}).json['conversation']['id']
    key = str(uuid4())
    saved = send(client, cid, command, stream, key)['assistant_message']
    receipt = saved['action_receipt']
    assert receipt['kind'] == 'note'
    nid = receipt['resource_id']
    path = f'/api/quick-notes/{nid}'
    for _ in range(2):
        note = client.get(path).json['note']
        assert (note['id'], note['title'], note['content']) == (nid, title, content)
    assert client.get(f'/chat?note={nid}').status_code == 200
    loaded = client.get(f'/api/conversations/{cid}/messages').json['messages']
    assert loaded[0]['content'] == command
    assert loaded[-1]['action_receipt'] == receipt
    repeated = send(client, cid, command, stream, key)['assistant_message']
    assert repeated['id'] == saved['id']
    assert one(connect, 'SELECT COUNT(*) AS n FROM quick_notes')['n'] == 1
    assert one(connect, 'SELECT COUNT(*) AS n FROM chat_action_receipts')['n'] == 1
    assert one(connect, 'SELECT COUNT(*) AS n FROM ai_usage_events')['n'] == 0
    with client.session_transaction() as session:
        session['user_id'] = 2
    assert client.get(path).status_code == 404
