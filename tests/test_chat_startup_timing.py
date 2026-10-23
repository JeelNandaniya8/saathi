"""Separate preparation stalls from provider time without logging owned content."""
import io
import json
import logging
from unittest.mock import MagicMock

import pytest

from test_core import backend


@pytest.mark.parametrize('attachment', [False, True])
@pytest.mark.parametrize('provider_failure', [False, True])
def test_startup_timing_locates_stalls_and_excludes_provider_and_private_data(
        backend, monkeypatch, caplog, attachment, provider_failure):
    b = backend
    clock = [0.0]
    def wait(seconds, result):
        clock[0] += seconds
        return result
    monkeypatch.setattr(b, 'monotonic', lambda: clock[0])
    monkeypatch.setattr(b, 'require_user_id', lambda: wait(.1, 471))
    monkeypatch.setattr(b, 'get_db', MagicMock())
    monkeypatch.setattr(b, 'chat_conversation_snapshot', lambda *a:
                        wait(.6, dict(id=284, user_id=471, title='PRIVATE_TITLE', recent_messages=[])))
    monkeypatch.setattr(b, 'active_plan_entitlement', lambda *a: ('free', b.PLAN_ENTITLEMENTS['free']))
    prepare = b.prepare_chat_attachments
    monkeypatch.setattr(b, 'prepare_chat_attachments', lambda *a: wait(.2, prepare(*a)))
    monkeypatch.setattr(b, 'completed_chat_request', lambda *a: None)
    monkeypatch.setattr(b, 'limited', lambda *a: wait(.4, None))
    monkeypatch.setattr(b, 'attachment_usage_today', lambda *a: 0)
    monkeypatch.setattr(b, 'load_user_language', lambda *a: wait(.3, 'en'))
    monkeypatch.setattr(b.chat_actions, 'direct_reply', lambda *a: None)
    monkeypatch.setattr(b.study_reference, 'short_study', lambda *a: True)
    monkeypatch.setattr(b.study_reference, 'answer', lambda *a: None)
    def provider(*args, **kwargs):
        clock[0] += 9
        if provider_failure:
            raise b.ProviderError('AI_TIMEOUT', 'Fixture timeout')
        yield 'Fixture answer'
        return {}
    monkeypatch.setattr(b, 'stream_gemini_reply', provider)
    saved = dict(user_message={'id': 1}, assistant_message={'id': 2})
    persist = MagicMock(return_value=saved)
    monkeypatch.setattr(b, 'persist_streamed_exchange', persist)
    client = b.app.test_client()
    data = dict(content='PRIVATE_PROMPT', request_id='private-request-471', mode='normal')
    kwargs = {'json': data}
    if attachment:
        data.update(file_only='true', attachments=(io.BytesIO(b'\x89PNG\r\n\x1a\nfixture'), 'PRIVATE_FILE.png'))
        kwargs = dict(data=data, content_type='multipart/form-data')
    with caplog.at_level(logging.INFO, logger=b.app.logger.name + '.ai_timing'):
        result = client.post('/api/conversations/284/messages/stream', **kwargs)
        events = [json.loads(line) for line in result.data.splitlines()]
    assert result.status_code == 200
    metrics = dict(item.strip().split(';dur=') for header in result.headers.getlist('Server-Timing')
                   for item in header.split(','))
    assert float(metrics['chat_auth']) == 100
    assert float(metrics['chat_snapshot']) == 600
    assert float(metrics['chat_attachments']) == 200
    assert float(metrics['chat_checks']) == 400
    assert float(metrics['chat_context']) == 300
    assert sum(float(v) for k, v in metrics.items() if k.startswith('chat_')) == 1600
    assert 'app' in metrics, 'Keep the existing aggregate preparation measurement'
    startup = [r.getMessage() for r in caplog.records if 'chat_startup_timing' in r.getMessage()]
    assert len(startup) == 1 and 'ready_ms=1600.0' in startup[0]
    assert set(metrics) == {'app', 'chat_auth', 'chat_input', 'chat_snapshot',
                            'chat_attachments', 'chat_checks', 'chat_context', 'chat_reference'}
    for secret in ('PRIVATE_PROMPT', 'PRIVATE_FILE', 'PRIVATE_TITLE', 'private-request-471',
                   'user_id', 'conversation_id', 'request_id'):
        assert secret not in startup[0] and secret not in ','.join(result.headers.getlist('Server-Timing'))
    assert result.headers['Cache-Control'] == 'no-store, no-transform'
    if provider_failure:
        assert events[-1]['type'] == 'error' and events[-1]['code'] == 'AI_TIMEOUT'
        persist.assert_not_called()
    else:
        assert events[-1] == dict(type='complete', data=saved)
        persist.assert_called_once()


def test_unauthenticated_request_does_not_run_or_report_owned_startup_stages(backend, monkeypatch):
    monkeypatch.setattr(backend, 'require_user_id', lambda: None)
    database = MagicMock()
    monkeypatch.setattr(backend, 'get_db', database)
    result = backend.app.test_client().post('/api/conversations/284/messages/stream', json={})
    assert result.status_code == 401
    assert 'chat_' not in ','.join(result.headers.getlist('Server-Timing'))
    database.assert_not_called()
