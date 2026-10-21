"""Check actual owned policy, provider payload and persisted replies together."""
import json
import os
from uuid import uuid4

import pytest

import chat_actions
from test_database_flows import db_app, one
from test_turn_source_privacy import REFUSALS

pytestmark = pytest.mark.skipif(not os.environ.get('TEST_DATABASE_URL'),
                               reason='Requires isolated PostgreSQL')


class Response:
    def json(self):
        return dict(candidates=[dict(content=dict(parts=[dict(text='A converse needs its own proof. Here are two synthetic counterexamples.')]), finishReason='STOP')])

    def iter_lines(self, **kwargs):
        yield 'data: ' + json.dumps(self.json())

    def close(self):
        pass


@pytest.mark.parametrize('query', REFUSALS)
@pytest.mark.parametrize('stream', [False, True])
def test_turn_exclusion_precedes_provider_and_does_not_change_saved_policy(
        db_app, monkeypatch, query, stream):
    backend, client, connect = db_app
    monkeypatch.setattr(backend, 'GEMINI_API_KEY', 'fixture-key')
    policy = dict.fromkeys(chat_actions.SOURCES, True)
    assert client.patch('/api/chat-context', json=policy).status_code == 200
    assert client.put('/api/personal-context/study/goal', json=dict(
        value='PRIVATE_PROFILE_MARKER', version=0, confirmed=True, use_in_ai=True)).status_code == 200
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO tasks(user_id,title,details,priority,created_at,updated_at) VALUES(1,'PRIVATE_TASK_MARKER','','medium',NOW(),NOW())")
            for uid, active, marker in [(1, True, 'PRIVATE_MEMORY_MARKER'),
                                        (1, False, 'PAUSED_MEMORY_MARKER'),
                                        (2, True, 'OTHER_ACCOUNT_MARKER')]:
                cur.execute('INSERT INTO memories(user_id,label,content,active,created_at,updated_at) VALUES(%s,%s,%s,%s,NOW(),NOW())',
                            (uid, 'Synthetic memory', marker, active))
    cid = client.post('/api/conversations', json={}).json['conversation']['id']
    with connect() as conn:
        with conn.cursor() as cur:
            for role, text in [('user', 'Use my saved sources.'), ('assistant', 'PRIVATE_HISTORY_MARKER')]:
                cur.execute('INSERT INTO messages(user_id,conversation_id,role,content,created_at) VALUES(1,%s,%s,%s,NOW())', (cid, role, text))
    captured = []

    def provider(*args, **kwargs):
        captured.append(json.dumps(args[3], ensure_ascii=False))
        return Response()

    monkeypatch.setattr(backend, 'provider_send', provider)
    path = f'/api/conversations/{cid}/messages' + ('/stream' if stream else '')
    result = client.post(path, json=dict(content=query, mode='deep_study', request_id=str(uuid4())))
    assert result.status_code == 200
    if stream:
        events = [json.loads(line) for line in result.data.splitlines()]
        assert any(event.get('type') == 'complete' for event in events), events
    assert len(captured) == 1
    for marker in ['PRIVATE_TASK_MARKER', 'PRIVATE_MEMORY_MARKER', 'PAUSED_MEMORY_MARKER',
                   'OTHER_ACCOUNT_MARKER', 'PRIVATE_HISTORY_MARKER', 'PRIVATE_PROFILE_MARKER']:
        assert marker not in captured[0]
    assert query in captured[0]
    assert client.get('/api/chat-context').json['permissions'] == policy
    stored = client.get(f'/api/conversations/{cid}/messages').json['messages']
    assert stored[-2]['content'] == query and stored[-1]['role'] == 'assistant'
    assert one(connect, 'SELECT COUNT(*) AS n FROM memories')['n'] == 3
    assert one(connect, 'SELECT COUNT(*) AS n FROM tasks')['n'] == 1
    captured.clear()
    allowed = client.post(f'/api/conversations/{cid}/messages', json=dict(
        content='Use my tasks and memories to explain another proof about nested quantifiers.',
        mode='deep_study', request_id=str(uuid4())))
    assert allowed.status_code == 200 and len(captured) == 1
    for marker in ['PRIVATE_TASK_MARKER', 'PRIVATE_MEMORY_MARKER', 'PRIVATE_PROFILE_MARKER']:
        assert marker in captured[0]
    assert 'PAUSED_MEMORY_MARKER' not in captured[0]
    assert 'OTHER_ACCOUNT_MARKER' not in captured[0]
