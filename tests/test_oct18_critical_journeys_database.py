"""200 varied critical journeys in 20 disposable, two-account PostgreSQL schemas.

Providers are explicit fixtures. This measures neither live AI nor availability.
Each batch traverses ten different flows; failures remain in the ledger.
"""
import json
import os
from contextlib import contextmanager
from datetime import datetime, time, timedelta, timezone
from time import perf_counter
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest
from test_database_flows import db_app, one
from test_audit_reliability_database import send
from test_chat_control_database import seed, execute
from test_oct17_reliability_database import fixture_reply, upload
from test_oct17_reliability import vector_map

pytestmark = pytest.mark.skipif(not os.environ.get('TEST_DATABASE_URL'), reason='Requires isolated PostgreSQL')
ROWS = []


@contextmanager
def journey(kind, variant, language, zone):
    row = dict(kind=kind, variant=variant, language=language, timezone=zone, outcome='failed')
    ROWS.append(row)
    started = perf_counter()
    try:
        yield
        row['outcome'] = 'passed'
    finally:
        row['ms'] = round((perf_counter() - started) * 1000, 1)


def owner(client, uid):
    with client.session_transaction() as session:
        session['user_id'] = uid


@pytest.mark.parametrize('variant', range(20))
def test_varied_critical_batch(db_app, monkeypatch, variant):
    b, c, connect = db_app
    lang = ['en', 'gu', 'hi'][variant % 3]
    zone = ['Asia/Kolkata', 'America/New_York', 'Pacific/Kiritimati', 'Europe/London'][variant % 4]
    title = ['Recall', 'પુનરાવર્તન', 'दोहराव'][variant % 3] + ' ' + str(variant)
    streamed = bool(variant % 2)
    assert c.patch('/api/workspace/preferences', json=dict(timezone=zone, language=lang)).status_code == 200
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute('UPDATE users SET language=%s WHERE id=1', (lang,))

    with journey('note_conflict_replay_ownership', variant, lang, zone):
        cid = c.post('/api/conversations', json={}).json['conversation']['id']
        key = str(uuid4())
        command = f'Save a note. Title: {title}; Content: NOTE_MARKER_{variant}'
        saved = send(c, cid, command, streamed, key)['assistant_message']
        nid = saved['action_receipt']['resource_id']
        assert send(c, cid, command, streamed, key)['assistant_message']['id'] == saved['id']
        path = '/api/quick-notes/' + str(nid)
        note = c.get(path).json['note']
        assert note['title'] == title and note['content'] == f'NOTE_MARKER_{variant}'
        edited = c.patch(path, json=dict(title=title, content=f'EDITED_NOTE_{variant}', version=note['version']))
        assert edited.status_code == 200
        assert c.patch(path, json=dict(content='stale', version=note['version'])).status_code == 409
        assert c.get(path).json['note']['content'] == f'EDITED_NOTE_{variant}'
        owner(c, 2)
        assert c.get(path).status_code == 404
        owner(c, 1)
        assert one(connect, 'SELECT COUNT(*) AS n FROM quick_notes')['n'] == 1

    with journey('clean_memory_pause', variant, lang, zone):
        cid = c.post('/api/conversations', json={}).json['conversation']['id']
        fact = f'MEMORY_MARKER_{variant}'
        saved = send(c, cid, f'Remember that my preferred practice topic is {fact}. Save this as a memory.', streamed)['assistant_message']
        mid = saved['action_receipt']['resource_id']
        row = one(connect, 'SELECT content FROM memories WHERE id=%s', (mid,))
        assert fact in row['content'] and 'Save this as a memory' not in row['content']
        assert c.patch('/api/memories/' + str(mid), json=dict(active=False)).status_code == 200
        assert fact not in b.load_active_memory_bundle(1, include_workspace=True)[0]

    with journey('planner_zero_duplicates_midnight', variant, lang, zone):
        local = ZoneInfo(zone)
        start = datetime.combine(datetime.now(local).date(), time.min, local)
        n = variant % 3
        same_title = 'TODAY_' + title
        entries = [(1, same_title, start + timedelta(seconds=i * 86399), False) for i in range(n)]
        entries += [(1, 'OVERDUE_MARKER', start - timedelta(seconds=1), False),
                    (1, 'UNDATED_MARKER', None, False),
                    (1, 'TOMORROW_MARKER', start + timedelta(days=1), False),
                    (1, 'COMPLETED_MARKER', start, True), (2, 'FOREIGN_TASK_MARKER', start, False)]
        with connect() as conn:
            with conn.cursor() as cur:
                for uid, name, at, done in entries:
                    cur.execute("INSERT INTO tasks(user_id,title,details,due_at,completed,priority,created_at,updated_at) VALUES(%s,%s,'',%s,%s,'medium',NOW(),NOW())", (uid, name, at, done))
        cid = c.post('/api/conversations', json={}).json['conversation']['id']
        reply = send(c, cid, 'What remains today?', streamed)['assistant_message']['content'].replace('\\_', '_')
        if n:
            assert reply.startswith(str(n) + ' '), reply
        else:
            assert {'en':'No unfinished Planner tasks', 'gu':'આ તારીખે કરવાનાં સાચવેલાં કામ નથી', 'hi':'इस तारीख के लिए सहेजे काम बाकी नहीं हैं'}[lang] in reply
        assert reply.count(same_title) == n
        assert all(name not in reply for name in ['OVERDUE_MARKER', 'UNDATED_MARKER', 'TOMORROW_MARKER', 'COMPLETED_MARKER', 'FOREIGN_TASK_MARKER'])
        tasks = c.get('/api/tasks').json['tasks']
        due = [t for t in tasks if not t['completed'] and t['due_at'] and datetime.fromisoformat(t['due_at']).astimezone(local).date() == start.date()]
        assert len(due) == n

    with journey('reminder_preview_confirm_future_snooze', variant, lang, zone):
        cid = c.post('/api/conversations', json={}).json['conversation']['id']
        preview = send(c, cid, f'Remind me on 25 December 2030 at 7 PM to revise {title}', streamed)['assistant_message']
        assert not preview.get('action_receipt')
        assert one(connect, 'SELECT COUNT(*) AS n FROM reminders')['n'] == 0
        key = str(uuid4())
        confirmed = send(c, cid, 'Confirm reminder', streamed, key)['assistant_message']
        rid = confirmed['action_receipt']['resource_id']
        assert send(c, cid, 'Confirm reminder', streamed, key)['assistant_message']['id'] == confirmed['id']
        before = one(connect, 'SELECT next_run_at FROM reminders WHERE id=%s', (rid,))['next_run_at']
        assert c.patch('/api/reminders/' + str(rid), json=dict(action='snooze', minutes=30)).status_code == 409
        assert one(connect, 'SELECT next_run_at FROM reminders WHERE id=%s', (rid,))['next_run_at'] == before
        assert one(connect, 'SELECT COUNT(*) AS n FROM reminders')['n'] == 1

    with journey('plan_atomic_receipt_exact_tasks', variant, lang, zone):
        items = [dict(title=title + ' ' + str(i), text='Recall for ten minutes', at=None) for i in (1, 2)]
        mid, cid = seed(connect, 'Create a two-day study plan', dict(kind='plan', title=title, text='Two manageable steps', items=items))
        before = one(connect, 'SELECT COUNT(*) AS n FROM tasks')['n']
        saved = execute(c, mid)
        assert saved.status_code == 201, saved.json
        assert execute(c, mid).status_code == 200
        assert one(connect, 'SELECT COUNT(*) AS n FROM tasks')['n'] == before + 2
        ids = saved.json['receipt']['resource_ids']
        assert len(ids) == 2 and len(set(ids)) == 2
        loaded = c.get(f'/api/conversations/{cid}/messages').json['messages'][-1]
        assert loaded['action_receipt']['resource_ids'] == ids

    with journey('map_ready_exact_job_invalid_rollback', variant, lang, zone):
        monkeypatch.setattr(b, 'generate_study_json', lambda *a: vector_map('Dot product gives a scalar.'))
        body = dict(job_id=str(uuid4()), topic=title, language=lang)
        saved = c.post('/api/mindmaps/generate', json=body)
        assert saved.status_code == 200, saved.json
        rid = saved.json['mindmap']['id']
        assert c.post('/api/mindmaps/generate', json=body).status_code == 202
        assert c.post('/api/mindmaps/generate', json={**body, 'topic':'changed'}).status_code == 409
        job = c.get('/api/study-jobs?kind=map&job_id=' + body['job_id']).json['jobs'][0]
        assert job['status'] == 'ready' and job['result_id'] == rid
        remaining = c.get('/api/study-allowance?kind=map').json['allowance']['remaining']
        monkeypatch.setattr(b, 'generate_study_json', lambda *a: dict(root=None))
        assert c.post('/api/mindmaps/generate', json={**body, 'job_id':str(uuid4())}).status_code == 400
        assert c.get('/api/study-allowance?kind=map').json['allowance']['remaining'] == remaining
        assert one(connect, 'SELECT COUNT(*) AS n FROM mindmaps')['n'] == 1
        owner(c, 2)
        assert c.get('/api/mindmaps/' + str(rid)).status_code == 404
        owner(c, 1)

    with journey('attachment_exact_retry_changed_input', variant, lang, zone):
        fixture_reply(b, monkeypatch, 'Owned upload fixture answer.')
        cid = c.post('/api/conversations', json={}).json['conversation']['id']
        path = f'/api/conversations/{cid}/messages' + ('/stream' if streamed else '')
        key = str(uuid4())
        assert upload(c, path, key).status_code == 200
        assert upload(c, path, key).status_code == 200
        for changed in [dict(color='blue'), dict(file_only=False), dict(mode='explain')]:
            assert upload(c, path, key, **changed).status_code == 409
        assert one(connect, 'SELECT COUNT(*) AS n FROM messages WHERE conversation_id=%s', (cid,))['n'] == 2
        assert one(connect, 'SELECT COUNT(*) AS n FROM chat_attachments')['n'] == 1

    with journey('stop_before_and_after_save', variant, lang, zone):
        cid = c.post('/api/conversations', json={}).json['conversation']['id']
        key = str(uuid4())
        path = f'/api/conversations/{cid}/messages' + ('/stream' if streamed else '')
        assert c.post(f'/api/conversations/{cid}/cancel', json=dict(request_id=key)).json['cancelled']
        assert c.post(path, json=dict(content='Bounded stop fixture', mode='normal', request_id=key), buffered=True).status_code == 409
        assert one(connect, 'SELECT COUNT(*) AS n FROM messages WHERE conversation_id=%s', (cid,))['n'] == 0
        fixture_reply(b, monkeypatch)
        key = str(uuid4())
        saved = send(c, cid, 'Bounded ordinary answer fixture', streamed, key)['assistant_message']
        stopped = c.post(f'/api/conversations/{cid}/cancel', json=dict(request_id=key)).json
        assert not stopped['cancelled'] and stopped['completed']['assistant_message']['id'] == saved['id']

    with journey('off_paused_private_sources_ownership', variant, lang, zone):
        with connect() as conn:
            with conn.cursor() as cur:
                cur.execute("INSERT INTO memories(user_id,label,content,active,created_at,updated_at) VALUES(1,'Paused','PAUSED_MARKER',FALSE,NOW(),NOW()),(2,'Foreign','FOREIGN_MEMORY_MARKER',TRUE,NOW(),NOW())")
        text = b.load_active_memory_bundle(1, include_workspace=True, turn_content='Hello')[0]
        assert all(secret not in text for secret in ['PAUSED_MARKER', 'FOREIGN_MEMORY_MARKER', f'EDITED_NOTE_{variant}', 'TODAY_' + title])
        requested = b.load_active_memory_bundle(1, include_workspace=True, turn_content='Read my notes')[0]
        assert f'EDITED_NOTE_{variant}' in requested
        assert 'PAUSED_MARKER' not in requested and 'FOREIGN_MEMORY_MARKER' not in requested
        assert f'EDITED_NOTE_{variant}' not in b.load_active_memory_bundle(2, include_workspace=True, turn_content='Read my notes')[0]
        assert not any(c.get('/api/chat-context').json['permissions'].values())

    with journey('correction_source_revision_replay_conflict', variant, lang, zone):
        cid = c.post('/api/conversations', json={}).json['conversation']['id']
        front = title + ' template reading?'
        old = '[FLASHCARDS]\nFront: ' + front + '\nBack: 5′→3′\n[/FLASHCARDS]'
        with connect() as conn:
            with conn.cursor() as cur:
                cur.execute("INSERT INTO messages(user_id,conversation_id,role,content,created_at,ai_mode) VALUES(1,%s,'assistant',%s,NOW(),'flashcards') RETURNING id", (cid, old))
                mid = cur.fetchone()['id']
                cur.execute("INSERT INTO revision_items(user_id,message_id,item_index,topic,front,back) VALUES(1,%s,0,'DNA',%s,'5′→3′')", (mid, front))
        path = f'/api/messages/{mid}/flashcards/0'
        body = dict(front=front, back='3′→5′', expected_front=front, expected_back='5′→3′')
        corrected = c.patch(path, json=body)
        assert corrected.status_code == 200, corrected.json
        assert c.patch(path, json=body).json['replayed']
        assert c.patch(path, json={**body, 'expected_back':'stale', 'back':'Changed'}).status_code == 409
        assert one(connect, 'SELECT back FROM revision_items WHERE message_id=%s', (mid,))['back'] == '3′→5′'
        loaded = c.get(f'/api/conversations/{cid}/messages').json['messages'][-1]
        assert loaded['content'] == corrected.json['content']
        assert loaded['study_progress']['progress']['corrected_indices'] == [0]
        owner(c, 2)
        assert c.patch(path, json=body).status_code == 404
        owner(c, 1)


@pytest.mark.parametrize('kind', ['user', 'plain_assistant', 'quiz'])
def test_missing_progress_does_not_authorize_other_content(db_app, kind):
    _, c, connect = db_app
    cid = c.post('/api/conversations', json={}).json['conversation']['id']
    content = 'Ordinary answer' if kind == 'plain_assistant' else '[FLASHCARDS]\nFront: Question\nBack: Original\n[/FLASHCARDS]'
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute('INSERT INTO messages(user_id,conversation_id,role,content,created_at) VALUES(1,%s,%s,%s,NOW()) RETURNING id', (cid, 'user' if kind == 'user' else 'assistant', content))
            mid = cur.fetchone()['id']
            if kind == 'quiz':
                cur.execute("INSERT INTO study_progress(user_id,conversation_id,message_id,kind,progress,created_at,updated_at) VALUES(1,%s,%s,'quiz','{}',NOW(),NOW())", (cid, mid))
    response = c.patch(f'/api/messages/{mid}/flashcards/0', json=dict(front='Question', back='Corrected', expected_front='Question', expected_back='Original'))
    assert response.status_code == 404
    assert one(connect, 'SELECT content FROM messages WHERE id=%s', (mid,))['content'] == content
    assert one(connect, 'SELECT COUNT(*) AS n FROM study_progress')['n'] == (1 if kind == 'quiz' else 0)


def test_critical_journey_sample_ledger(capsys):
    passed = [r for r in ROWS if r['outcome'] == 'passed']
    timings = sorted(r['ms'] for r in passed)
    summary = dict(planned=200, attempted=len(ROWS), passed=len(passed), failed=len(ROWS)-len(passed),
        not_attempted=200-len(ROWS), categories=sorted({r['kind'] for r in ROWS}),
        languages=sorted({r['language'] for r in ROWS}), schemas=20,
        p95_journey_ms=timings[int(.95*len(timings))-1] if timings else None,
        scope='Isolated Flask/PostgreSQL; provider fixtures; not live availability or first-word latency')
    with capsys.disabled():
        print('STAGING_CRITICAL_JOURNEYS ' + json.dumps(summary))
    assert summary['passed'] == summary['planned'] and summary['failed'] == 0
