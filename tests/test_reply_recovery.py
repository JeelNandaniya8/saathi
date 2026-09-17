"""Failure paths that must preserve drafts, credentials and transaction boundaries."""
from datetime import datetime, timezone
from unittest.mock import Mock
import uuid

import psycopg2
import pytest
import requests

import ai_transport as transport
import db_pool
from response_insights import timing_input, week_window


def response(status, message='', headers=None):
    result = Mock(status_code=status, headers=headers or {})
    result.json.return_value = {'error': {'message': message}}
    if status >= 400:
        result.raise_for_status.side_effect = requests.HTTPError(response=result)
    return result


@pytest.fixture(autouse=True)
def fresh_choices():
    transport._choices.clear()
    yield
    transport._choices.clear()


@pytest.mark.parametrize('status,message,code', [
    (400, 'API key not valid', 'AI_ACCESS'), (403, 'secret-provider-body', 'AI_ACCESS'),
    (429, 'secret-provider-body', 'AI_QUOTA'), (503, 'secret-provider-body', 'AI_BUSY'),
    (400, 'User location is not supported', 'AI_CONFIGURATION'),
    (400, 'secret-provider-body', 'AI_REQUEST'),
])
def test_provider_failures_are_sanitized_and_not_retried(status, message, code, caplog):
    rejected = response(status, message, {'Retry-After': '31'})
    post = Mock(return_value=rejected)
    with pytest.raises(transport.ProviderError) as caught:
        transport.send(post, 'secret-key', 'gemini-2.5-flash-lite', {}, fast=True)
    assert caught.value.code == code
    assert 'secret' not in str(caught.value) + caplog.text
    assert caught.value.retry_after == (31 if status == 429 else None)
    assert post.call_count == 1
    rejected.close.assert_called_once()


@pytest.mark.parametrize('status,detail,model', [
    (404, 'not found', 'gemini-obsolete'),
    (400, 'thinking configuration unsupported', 'gemini-2.5-flash-lite'),
])
def test_one_compatibility_retry_is_cached_without_mutating_input(status, detail, model):
    bad, good = response(status, detail), response(200)
    post = Mock(side_effect=[bad, good, good])
    payload = {'generationConfig': {'thinkingConfig': {'thinkingBudget': 0}}, 'contents': []}
    assert transport.send(post, 'fixture', model, payload, fast=True, stream=True) is good
    assert post.call_count == 2
    assert 'thinkingConfig' not in post.call_args.kwargs['json']['generationConfig']
    assert 'thinkingConfig' in payload['generationConfig']
    assert post.call_args.kwargs['stream'] is True
    transport.send(post, 'fixture', model, payload, fast=True)
    assert post.call_count == 3, 'Next request must skip the known broken configuration'
    assert 'thinkingConfig' not in post.call_args.kwargs['json']['generationConfig']
    bad.close.assert_called_once()


def test_fallback_failure_is_bounded_and_timeout_does_not_replay():
    post = Mock(side_effect=[response(404), response(404)])
    with pytest.raises(transport.ProviderError, match='model is unavailable'):
        transport.send(post, 'fixture', 'gemini-obsolete', {}, fast=True)
    assert post.call_count == 2
    post = Mock(side_effect=requests.Timeout('provider-url-with-secret'))
    with pytest.raises(transport.ProviderError) as caught:
        transport.send(post, 'fixture', 'gemini-2.5-flash', {})
    assert caught.value.code == 'AI_TIMEOUT' and post.call_count == 1
    assert 'secret' not in str(caught.value)


def test_pool_release_rolls_back_once_and_discards_broken_connections():
    pool, conn = Mock(), Mock(closed=0)
    lease = db_pool.Lease(pool, conn)
    lease.close(); lease.close()
    conn.rollback.assert_called_once()
    pool.putconn.assert_called_once_with(conn, close=False)
    with pytest.raises(psycopg2.InterfaceError):
        lease.cursor()
    conn = Mock(closed=0)
    conn.rollback.side_effect = psycopg2.OperationalError('connection lost')
    db_pool.Lease(pool, conn).close()
    pool.putconn.assert_called_with(conn, close=True)


def test_stale_pool_connection_is_replaced_before_application_queries(monkeypatch):
    stale = Mock(closed=0)
    stale.cursor.side_effect = psycopg2.OperationalError('stale')
    fresh = Mock(closed=0)
    pool = Mock(); pool.getconn.side_effect = [stale, fresh]
    factory = Mock(return_value=pool)
    monkeypatch.setattr(db_pool, '_pool', None)
    monkeypatch.setattr(db_pool, '_identity', None)
    monkeypatch.setattr(db_pool, 'ThreadedConnectionPool', factory)
    lease = db_pool.connect('local-fixture')
    pool.putconn.assert_called_once_with(stale, close=True)
    fresh.cursor.assert_not_called()
    lease.close()
    assert factory.call_count == 1


@pytest.mark.parametrize('change', [{'total_ms': True}, {'conversation_id': True},
    {'first_text_ms': 5001}, {'total_ms': 300001}, {'outcome': []}, {'error_code': []},
    {'request_id': 'invalid'}, {'error_code': 'private text'}])
def test_timing_validation_rejects_malformed_and_unbounded_values(change):
    data = {'request_id': str(uuid.uuid4()), 'conversation_id': 1, 'first_text_ms': 100,
            'total_ms': 5000, 'outcome': 'complete', **change}
    with pytest.raises(ValueError):
        timing_input(data)


def test_week_window_respects_india_midnight_and_daylight_saving():
    start, today, since = week_window(datetime(2026, 9, 16, 20, tzinfo=timezone.utc), 'Asia/Kolkata')
    assert str(today) == '2026-09-17' and str(start) == '2026-09-11'
    assert since.isoformat() == '2026-09-10T18:30:00+00:00'
    _, _, since = week_window(datetime(2026, 3, 10, 12, tzinfo=timezone.utc), 'America/New_York')
    assert since.hour == 5, 'Use the timezone offset at the start, before DST'
