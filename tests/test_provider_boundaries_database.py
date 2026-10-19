"""Multipart, retry, receipt and allowance checks in disposable PostgreSQL only."""
import copy
import io
import json
import os
import time
from datetime import datetime, timezone
from email.utils import format_datetime
from unittest.mock import Mock
from types import SimpleNamespace
from uuid import uuid4

import pytest
from pypdf import PdfWriter
import ai_transport as transport
from test_database_flows import db_app, one
from test_oct17_reliability_database import upload
from test_normal_mindmap_json import REQUEST, probability_map
from test_reply_recovery import response

pytestmark = pytest.mark.skipif(not os.environ.get('TEST_DATABASE_URL'), reason='Requires isolated PostgreSQL')


@pytest.mark.parametrize('stream', [False, True])
@pytest.mark.parametrize('kind', ['png', 'pdf', 'map'])
@pytest.mark.parametrize('code',['AI_BUSY','AI_TIMEOUT'])
def test_dated_provider_failure_then_exact_retry_saves_once(db_app, monkeypatch, stream, kind, code):
    b, c, db = db_app
    now = [1792324800]
    # Workspace context includes a current-time snapshot. Keep that fixture
    # stable while the separate provider cooldown clock advances ninety seconds.
    class ContextClock(datetime):
        @classmethod
        def now(cls, tz=None):
            fixed = datetime.fromtimestamp(1792324800, timezone.utc)
            return fixed.astimezone(tz) if tz else fixed.replace(tzinfo=None)
    monkeypatch.setattr(b.chat_actions, 'datetime', ContextClock)
    # Replacing stdlib time.time also changes Flask's signed-session clock;
    # fixtures run later than this fixed date then invalidate their own login.
    system_time=time.time
    monkeypatch.setattr(transport, 'time', SimpleNamespace(time=lambda: now[0],monotonic=time.monotonic,sleep=Mock()))
    assert time.time is system_time
    monkeypatch.setattr(transport, '_choices', {})
    monkeypatch.setattr(b, 'GEMINI_API_KEY', 'fixture')
    monkeypatch.setenv('GEMINI_MODEL', 'gemini-fixture-study')
    monkeypatch.setenv('GEMINI_FAST_MODEL', 'gemini-fixture-fast')
    monkeypatch.setattr(b, 'provider_send', transport.send)
    retry = format_datetime(datetime.fromtimestamp(now[0] + 90, timezone.utc), usegmt=True)
    rejected = response(503, headers={'Retry-After': retry})
    post = Mock(return_value=rejected,side_effect=transport.requests.Timeout() if code=='AI_TIMEOUT' else None)
    monkeypatch.setattr(b, 'provider_post', post)
    created = c.post('/api/conversations', json={})
    assert created.status_code == 201, created.json
    cid = created.json['conversation']['id']
    key = str(uuid4())
    path = f'/api/conversations/{cid}/messages' + ('/stream' if stream else '')
    pdf = io.BytesIO(); writer = PdfWriter(); writer.add_blank_page(width=200, height=200); writer.write(pdf)
    def request():
        if kind == 'map':
            return c.post(path, json=dict(content=REQUEST, mode='normal', request_id=key))
        if kind == 'png':
            return upload(c, path, key)
        return c.post(path, data=dict(content='Read the fixture code.', mode='normal', request_id=key,
                    file_only='true', attachments=(io.BytesIO(pdf.getvalue()), 'same.pdf')),
                    content_type='multipart/form-data', buffered=True)
    failed = request()
    error = json.loads(failed.data.splitlines()[-1]) if stream else failed.json
    assert error['code']==code
    assert error.get('retry_after')==(90 if code=='AI_BUSY' else None)
    assert post.call_count == 1
    assert '/gemini-fixture-study:' in post.call_args.args[0]
    original = copy.deepcopy(post.call_args.kwargs['json'])
    for table in ['messages', 'chat_attachments', 'chat_action_receipts', 'mindmaps']:
        assert one(db, 'SELECT COUNT(*) n FROM ' + table)['n'] == 0
    assert c.get('/api/me').json['chat_attachments']['remaining_today'] == 5
    assert c.get('/api/study-allowance?kind=map').json['allowance']['remaining'] == 2

    now[0] += 90
    text = json.dumps(probability_map()) if kind == 'map' else 'Fixture code read.'
    result = dict(candidates=[dict(content=dict(parts=[dict(text=text)]), finishReason='STOP')])
    good = response(200); good.json.return_value = result
    good.iter_lines.side_effect = lambda **kwargs: iter(['data: ' + json.dumps(result)])
    post.side_effect=None
    post.return_value = good
    saved = request()
    assert saved.status_code == 200, saved.data
    body = json.loads(saved.data.splitlines()[-1])['data'] if stream else saved.json
    assert body['assistant_message']['id']
    assert post.call_count == 2 and post.call_args.kwargs['json'] == original
    replay = request()
    replayed = json.loads(replay.data.splitlines()[-1])['data'] if stream else replay.json
    assert replayed['assistant_message']['id'] == body['assistant_message']['id']
    assert post.call_count == 2, 'A completed exact retry does not call the provider again'
    assert one(db, 'SELECT COUNT(*) n FROM messages')['n'] == 2
    assert one(db, "SELECT file_only FROM messages WHERE role='user'")['file_only'] is (kind != 'map')
    assert one(db, 'SELECT COUNT(*) n FROM chat_attachments')['n'] == (0 if kind == 'map' else 1)
    assert one(db, 'SELECT COUNT(*) n FROM mindmaps')['n'] == (1 if kind == 'map' else 0)
    if kind == 'map':
        mid = body['assistant_message']['action_receipt']['resource_id']
        assert c.get('/api/mindmaps/' + str(mid)).json['mindmap']['topic'] == 'Audit18C Probability'
    else:
        assert one(db, 'SELECT original_name FROM chat_attachments')['original_name'] == 'same.' + kind
    assert c.get('/api/me').json['chat_attachments']['remaining_today'] == (5 if kind == 'map' else 4)
    assert c.get('/api/study-allowance?kind=map').json['allowance']['remaining'] == (1 if kind == 'map' else 2)
    transport.time.sleep.assert_not_called()
