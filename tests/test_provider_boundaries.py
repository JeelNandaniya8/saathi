"""Provider failure fixtures only: no network, production limits or wall sleeps."""
from datetime import datetime, timezone
from email.utils import format_datetime
from unittest.mock import Mock

import pytest
import ai_transport as transport
from test_reply_recovery import response


@pytest.fixture(autouse=True)
def isolated_provider(monkeypatch):
    monkeypatch.setattr(transport, '_choices', {})
    monkeypatch.setattr(transport, 'discover_model', Mock(return_value=None))
    monkeypatch.setattr(transport.time, 'sleep', Mock())


@pytest.mark.parametrize('fast', [False, True])
@pytest.mark.parametrize('stream', [False, True])
@pytest.mark.parametrize('status,code', [(503, 'AI_BUSY'), (429, 'AI_QUOTA')])
def test_provider_http_date_cooldown_is_not_retried_early(monkeypatch, fast, stream, status, code):
    now = 1792324800
    monkeypatch.setattr(transport.time, 'time', lambda: now)
    retry = format_datetime(datetime.fromtimestamp(now + 90, timezone.utc), usegmt=True)
    rejected = response(status, 'private-provider-detail', {'Retry-After': retry})
    post = Mock(return_value=rejected)
    with pytest.raises(transport.ProviderError) as caught:
        transport.send(post, 'fixture', 'gemini-fixture', {}, fast=fast, stream=stream)
    assert post.call_count == 1, 'A dated provider cooldown forbids an immediate automatic retry'
    assert caught.value.code == code and caught.value.retry_after == 90
    rejected.close.assert_called_once()
    transport.time.sleep.assert_not_called()


@pytest.mark.parametrize('retry', ['not-a-date', '9' * 100])
def test_unusable_retry_header_never_triggers_an_immediate_retry(retry):
    post = Mock(return_value=response(503, headers={'Retry-After': retry}))
    with pytest.raises(transport.ProviderError) as caught:
        transport.send(post, 'fixture', 'gemini-fixture', {}, fast=True)
    assert post.call_count == 1 and caught.value.retry_after is None
    transport.time.sleep.assert_not_called()


def test_long_numeric_quota_delay_is_not_shortened():
    error = transport.provider_error(response(429, headers={'Retry-After': '7200'}))
    assert error.code == 'AI_QUOTA' and error.retry_after == 7200


@pytest.mark.parametrize('fast,limit', [(False, 65), (True, 40)])
def test_compatibility_retry_cannot_start_after_its_budget(monkeypatch, fast, limit):
    clock = [0.0]
    monkeypatch.setattr(transport.time, 'monotonic', lambda: clock[0])
    def reject(*args, **kwargs):
        clock[0] = limit + 1
        return response(404)
    post = Mock(side_effect=reject)
    with pytest.raises(transport.ProviderError) as caught:
        transport.send(post, 'fixture', 'gemini-fixture', {}, fast=fast)
    assert post.call_count == 1, 'No provider request may start after the retry budget expires'
    assert caught.value.code == 'AI_TIMEOUT'
    transport.discover_model.assert_not_called()


@pytest.mark.parametrize('fast,limit', [(False, 65), (True, 40)])
def test_retry_connect_and_read_timeouts_share_the_remaining_budget(monkeypatch, fast, limit):
    clock = [0.0]
    monkeypatch.setattr(transport.time, 'monotonic', lambda: clock[0])
    def first(*args, **kwargs):
        clock[0] = limit - 2
        return response(404)
    calls = []
    def send(*args, **kwargs):
        calls.append(kwargs)
        return first() if len(calls) == 1 else response(200)
    transport.send(send, 'fixture', 'gemini-fixture', {}, fast=fast)
    connect, read = calls[1]['timeout']
    assert connect > 0 and read > 0 and connect + read <= 2
