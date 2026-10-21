"""Colloquial queries resolve actual owned fixtures through both chat endpoints."""
import json
import os
from uuid import uuid4
import pytest
import classroom_integration as cc
import chat_actions
from test_database_flows import db_app, one
from test_classroom_database import configured
from test_classroom_chat_database import school_fixture

pytestmark = pytest.mark.skipif(not os.environ.get('TEST_DATABASE_URL'), reason='Requires isolated PostgreSQL')
CASES = [
    ('en', 'mare ketli assigment baki che?', '1 pending assignments'),
    ('gu', 'મારા ક્લાસરૂમમાં કયાં અસાઇન્મેન્ટ છે?', '1 બાકી અસાઇનમેન્ટ'),
    ('hi', 'मेरे कॉलेज के असाइनमेंट बताओ', '1 बाकी असाइनमेंट'),
]


def request(client, cid, query, stream, key):
    path = f'/api/conversations/{cid}/messages' + ('/stream' if stream else '')
    response = client.post(path, json=dict(content=query, mode='care', request_id=key))
    assert response.status_code == 200
    if not stream:
        return response.json
    events = [json.loads(line) for line in response.data.splitlines()]
    result = next(e['data'] for e in events if e['type'] == 'complete')
    if not result.get('replayed'):
        assert any(e['type'] == 'ready' and e.get('stage') == 'classroom' for e in events)
    return result


@pytest.mark.parametrize('stream', [False, True])
@pytest.mark.parametrize('language,query,heading', CASES)
def test_colloquial_owned_read_overrides_stale_denial_without_ai_or_policy_changes(db_app, configured, monkeypatch, stream, language, query, heading):
    backend, client, connect = db_app
    calls, _ = school_fixture(client, monkeypatch)
    monkeypatch.setattr(backend, 'GEMINI_API_KEY', '')
    monkeypatch.setattr(backend, 'provider_send', lambda *a, **k: pytest.fail('Classroom read must never reach Gemini'))
    assert client.patch('/api/chat-context', json=dict.fromkeys(chat_actions.SOURCES, False)).status_code == 200
    cid = client.post('/api/conversations', json={}).json['conversation']['id']
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute('UPDATE users SET language=%s WHERE id=1', (language,))
            for role, text in [('user', 'Do not use Classroom. Explain gravity.'), ('assistant', 'I do not have access to your classroom data.')]:
                cur.execute('INSERT INTO messages(user_id,conversation_id,role,content,created_at) VALUES(1,%s,%s,%s,NOW())', (cid, role, text))
            cur.execute("INSERT INTO classroom_assignments(user_id,course_id,external_id,title) VALUES(2,'course1','foreign','FOREIGN_ASSIGNMENT_MARKER')")
    key = str(uuid4())
    result = request(client, cid, query, stream, key)
    reply = result['assistant_message']['content']
    assert heading in reply and 'School pending' in reply
    assert 'School sent' not in reply and 'FOREIGN_ASSIGNMENT_MARKER' not in reply
    assert 'do not have access' not in reply
    assert result['assistant_message']['memory_labels'] == ['Requested classroom for this reply']
    assert result['assistant_message']['ai_mode'] == 'normal'
    assert result['user_message']['content'] == query
    again = request(client, cid, query, stream, key)
    assert again['assistant_message']['id'] == result['assistant_message']['id']
    assert len(calls) == 2 and one(connect, 'SELECT COUNT(*) n FROM ai_usage_events')['n'] == 0
    assert one(connect, 'SELECT COUNT(*) n FROM messages WHERE conversation_id=%s', (cid,))['n'] == 4
    assert not any(client.get('/api/chat-context').json['permissions'].values())


@pytest.mark.parametrize('stream', [False, True])
@pytest.mark.parametrize('language,query,_heading', CASES)
def test_colloquial_read_reports_real_google_failure_without_model_fallback(db_app, configured, monkeypatch, stream, language, query, _heading):
    backend, client, connect = db_app
    school_fixture(client, monkeypatch)
    monkeypatch.setattr(backend, 'GEMINI_API_KEY', '')
    monkeypatch.setattr(backend, 'provider_send', lambda *a, **k: pytest.fail('Google failure must not become generic AI denial'))
    def unavailable(*args, **kwargs):
        raise cc.ProviderError('reconnect_required')
    monkeypatch.setattr(cc, 'list_pages', unavailable)
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute('UPDATE users SET language=%s WHERE id=1', (language,))
    cid = client.post('/api/conversations', json={}).json['conversation']['id']
    reply = request(client, cid, query, stream, str(uuid4()))['assistant_message']['content']
    assert reply.startswith('Google Classroom data could not be fetched right now.')
    assert 'do not have access' not in reply
    assert one(connect, 'SELECT last_error FROM classroom_connections WHERE user_id=1')['last_error'] == 'reconnect_required'
    assert one(connect, 'SELECT COUNT(*) n FROM ai_usage_events')['n'] == 0
