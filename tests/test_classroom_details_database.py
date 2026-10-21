"""Both transports read one owned description without AI or duplicate writes."""
import os
from uuid import uuid4
import pytest
import classroom_integration as cc
import chat_actions
from test_database_flows import db_app, one
from test_classroom_database import configured
from test_classroom_chat_database import school_fixture
from test_classroom_colloquial_database import request

pytestmark = pytest.mark.skipif(not os.environ.get('TEST_DATABASE_URL'), reason='Requires isolated PostgreSQL')
BODY = 'Read the synthetic passage.\nWrite five original sentences.\nગુજરાતી નોંધ\nहिन्दी नोट'
CASES = [
    ('en', 'What do I have to do in "School pending" assignment?', 'Original instructions', 'What do I do in this assignment?'),
    ('gu', 'School pending અસાઇનમેન્ટમાં શું કરવાનું છે?', 'મૂળ સૂચનાઓ', 'આમાં શું કરવાનું છે?'),
    ('hi', 'School pending असाइनमेंट में क्या करना है?', 'मूल निर्देश', 'इस असाइनमेंट में क्या करना है?'),
]


def detail_fixture(client, monkeypatch):
    calls, _ = school_fixture(client, monkeypatch)
    original = cc.list_pages
    def pages(*args, **kwargs):
        rows = original(*args, **kwargs)
        if args[2] == 'courseWork':
            for row in rows:
                row['description'] = BODY if row['id'] == 'pending' else 'UNSELECTEDDESCRIPTION'
                row['alternateLink'] = 'https://classroom.google.com/c/synthetic/a/' + row['id'] + '/details'
        return rows
    monkeypatch.setattr(cc, 'list_pages', pages)
    return calls


@pytest.mark.parametrize('stream', [False, True])
@pytest.mark.parametrize('language,query,heading,followup', CASES)
def test_named_and_contextual_details_persist_with_sources_and_replay_without_ai(db_app, configured, monkeypatch, stream, language, query, heading, followup):
    backend, client, connect = db_app
    calls = detail_fixture(client, monkeypatch)
    monkeypatch.setattr(backend, 'GEMINI_API_KEY', '')
    monkeypatch.setattr(backend, 'provider_send', lambda *a, **k: pytest.fail('Teacher instructions must not reach Gemini'))
    assert client.patch('/api/chat-context', json=dict.fromkeys(chat_actions.SOURCES, False)).status_code == 200
    cid = client.post('/api/conversations', json={}).json['conversation']['id']
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute('UPDATE users SET language=%s WHERE id=1', (language,))
            for role, text in [('user', 'Do not use Classroom. Explain gravity.'), ('assistant', 'I cannot access descriptions or instructions.')]:
                cur.execute('INSERT INTO messages(user_id,conversation_id,role,content,created_at) VALUES(1,%s,%s,%s,NOW())', (cid, role, text))
            for uid, course in [(2, 'course1'), (1, 'unselected')]:
                cur.execute("INSERT INTO classroom_assignments(user_id,course_id,external_id,title,instructions) VALUES(%s,%s,'foreign','School pending','FOREIGNDESCRIPTION')", (uid, course))
    key = str(uuid4())
    result = request(client, cid, query, stream, key)
    reply = result['assistant_message']['content']
    assert heading in reply and 'School pending' in reply
    assert '\n'.join('> ' + line for line in BODY.splitlines()) in reply
    assert 'UNSELECTEDDESCRIPTION' not in reply and 'FOREIGNDESCRIPTION' not in reply
    assert result['assistant_message']['memory_labels'] == ['Requested classroom for this reply']
    assert result['assistant_message']['ai_mode'] == 'normal' and result['user_message']['content'] == query
    assert not result['assistant_message'].get('action_receipt')
    again = request(client, cid, query, stream, key)
    assert again['assistant_message']['id'] == result['assistant_message']['id']
    readback = client.get(f'/api/conversations/{cid}/messages').json['messages'][-1]
    assert readback['content'] == reply and readback['id'] == result['assistant_message']['id']
    next_reply = request(client, cid, followup, stream, str(uuid4()))['assistant_message']['content']
    assert heading in next_reply and 'synthetic passage' in next_reply
    assert client.post(f'/api/conversations/{cid}/regenerate', json={'request_id': str(uuid4())}).status_code == 409
    assert len(calls) == 2
    assert one(connect, 'SELECT COUNT(*) n FROM messages WHERE conversation_id=%s', (cid,))['n'] == 6
    assert one(connect, 'SELECT COUNT(*) n FROM ai_usage_events')['n'] == 0
    for table in ['tasks', 'reminders', 'quick_notes']:
        assert one(connect, 'SELECT COUNT(*) n FROM ' + table)['n'] == 0
    assert not any(client.get('/api/chat-context').json['permissions'].values())


@pytest.mark.parametrize('stream', [False, True])
def test_list_followup_clarifies_instead_of_guessing_or_inventing_a_description(db_app, configured, monkeypatch, stream):
    backend, client, connect = db_app
    detail_fixture(client, monkeypatch)
    monkeypatch.setattr(backend, 'provider_send', lambda *a, **k: pytest.fail('Ambiguity must not reach AI'))
    cid = client.post('/api/conversations', json={}).json['conversation']['id']
    request(client, cid, 'List my pending assignments', stream, str(uuid4()))
    reply = request(client, cid, 'What do I do in this assignment?', stream, str(uuid4()))['assistant_message']['content']
    assert 'Which assignment' in reply and 'School pending' in reply
    assert 'synthetic passage' not in reply and 'UNSELECTEDDESCRIPTION' not in reply
    # A new named request resolves that clarification in the same conversation.
    named = request(client, cid, 'Show the instructions for the assignment "School pending"', stream, str(uuid4()))['assistant_message']['content']
    assert 'synthetic passage' in named
    assert one(connect, 'SELECT COUNT(*) n FROM ai_usage_events')['n'] == 0


@pytest.mark.parametrize('stream', [False, True])
def test_detail_refresh_failure_never_returns_retained_instructions_as_current(db_app, configured, monkeypatch, stream):
    backend, client, connect = db_app
    detail_fixture(client, monkeypatch)
    assert client.post('/api/classroom/sync', json={'confirmed': True}).status_code == 200
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute('UPDATE classroom_connections SET submission_sync_at=NULL WHERE user_id=1')
    monkeypatch.setattr(backend, 'provider_send', lambda *a, **k: pytest.fail('A fetch failure must not reach AI'))
    def failed(*args, **kwargs):raise cc.ProviderError('reconnect_required')
    monkeypatch.setattr(cc, 'list_pages', failed)
    cid = client.post('/api/conversations', json={}).json['conversation']['id']
    result = request(client, cid, 'Explain the School pending assignment', stream, str(uuid4()))
    assert result['assistant_message']['content'].startswith('Google Classroom data could not be fetched right now.')
    assert 'synthetic passage' not in result['assistant_message']['content']
    assert result['assistant_message']['memory_labels'] == []
    assert one(connect, "SELECT instructions FROM classroom_assignments WHERE user_id=1 AND external_id='pending'")['instructions'] == BODY
