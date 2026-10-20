"""Exact EN/GU/HI pending-work queries against one owned synthetic snapshot."""
import os

import pytest
import classroom_integration as classroom
from test_database_flows import db_app, one
from test_classroom_database import configured, selected_setup
from test_audit_reliability_database import send

pytestmark = pytest.mark.skipif(
    not os.environ.get('TEST_DATABASE_URL'), reason='Requires isolated PostgreSQL')


@pytest.mark.parametrize('language,query,heading,overdue,undated', [
    ('en', 'What assignments are pending in Google Classroom?',
     '6 pending assignments', 'Overdue', 'No due date'),
    ('gu', 'Google Classroomમાં કયું હોમવર્ક બાકી છે?',
     '6 બાકી અસાઇનમેન્ટ', 'સમયમર્યાદા વીતી', 'છેલ્લી તારીખ નથી'),
    ('hi', 'Google Classroom में कौन से असाइनमेंट बाकी हैं?',
     '6 बाकी असाइनमेंट', 'समयसीमा बीती', 'समयसीमा नहीं'),
])
@pytest.mark.parametrize('stream', [False, True])
def test_owned_classroom_language_count_title_and_deadline_parity(
        db_app, configured, monkeypatch, language, query, heading, overdue, undated, stream):
    backend, client, connect = db_app
    selected_setup(client, monkeypatch)
    monkeypatch.setattr(backend, 'GEMINI_API_KEY', '')
    monkeypatch.setattr(backend, 'provider_send', lambda *a, **k: pytest.fail(
        'Pending-work reads must not send teacher material to AI'))
    titles = ['Past one', 'Past two', 'Future one', 'Undated one', 'Undated two', 'Undated three']
    calls = []

    def pages(token, path, key, params):
        calls.append(key)
        if key == 'courseWork':
            rows = [dict(id=str(n), title=title) for n, title in enumerate(titles)]
            for index, year in [(0, 2020), (1, 2021), (2, 2040)]:
                rows[index].update(dueDate=dict(year=year, month=10, day=20),
                                   dueTime=dict(hours=18, minutes=29))
            return rows
        assert key == 'studentSubmissions' and params['userId'] == 'me'
        return [dict(courseWorkId=str(n), state='NEW') for n in range(6)]

    monkeypatch.setattr(classroom, 'list_pages', pages)
    assert client.post('/api/classroom/sync', json=dict(confirmed=True)).json['imported'] == 6
    rows = client.get('/api/classroom/assignments').json['assignments']
    assert len(rows) == 6 and sum(row['due_at'] is None for row in rows) == 3
    assert {row['title'] for row in rows} == set(titles)
    assert client.patch('/api/workspace/preferences', json=dict(timezone='Asia/Calcutta')).status_code == 200
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute('UPDATE users SET language=%s WHERE id=1', (language,))
            cur.execute("""INSERT INTO classroom_assignments(user_id,course_id,external_id,title)
                           VALUES(2,'course1','not-owner','OTHER USER PRIVATE WORK')""")
    cid = client.post('/api/conversations', json={}).json['conversation']['id']
    reply = send(client, cid, query, stream)['assistant_message']['content']
    assert heading in reply
    for title in titles:
        assert reply.count(title) == 1
    assert reply.count(overdue) == 2 and reply.count(undated) == 3
    for year in (2020, 2021, 2040):
        assert f'{year}-10-20, 11:59 PM · Asia/Calcutta' in reply
    assert 'OTHER USER PRIVATE WORK' not in reply
    assert calls == ['courseWork', 'studentSubmissions'], 'Reuse the fresh owned snapshot'
    assert one(connect, 'SELECT COUNT(*) AS n FROM ai_usage_events')['n'] == 0
    assert one(connect, 'SELECT COUNT(*) AS n FROM tasks')['n'] == 0
