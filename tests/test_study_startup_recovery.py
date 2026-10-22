"""No network or real waits: reproduce the live pre-header study timeout."""
import copy
from unittest.mock import Mock

import pytest
import requests

import ai_transport as transport
from test_reply_recovery import response


@pytest.fixture(autouse=True)
def isolated_provider(monkeypatch):
    monkeypatch.setattr(transport, '_choices', {})
    monkeypatch.setattr(transport, 'discover_model', Mock(return_value=None))
    monkeypatch.setattr(transport.time, 'sleep', Mock())
    monkeypatch.delenv('GEMINI_FALLBACK_MODEL', raising=False)


@pytest.mark.parametrize('stream', [False, True])
@pytest.mark.parametrize('failure', ['timeout', 'busy'])
def test_study_lite_recovers_once_without_losing_file_or_reasoning(stream, failure):
    good = response(200)
    first = requests.ReadTimeout('private-provider-detail') if failure == 'timeout' else response(503)
    post = Mock(side_effect=[first, good, good])
    payload = {
        'contents': [{'role': 'user', 'parts': [
            {'text': 'મૂળ વિનંતી · मूल अनुरोध'},
            {'inlineData': {'mimeType': 'image/png', 'data': 'SFlO'}}]}],
        'systemInstruction': {'parts': [{'text': 'FILE-ONLY MODE'}]},
        'generationConfig': {'maxOutputTokens': 3300, 'temperature': 0.45,
                             'thinkingConfig': {'thinkingLevel': 'high'}},
    }
    original = copy.deepcopy(payload)
    assert transport.send(post, 'fixture', 'gemini-3.5-flash-lite', payload,
                          fast=False, stream=stream, fallback_payload={'contents': []}) is good
    assert post.call_count == 2
    assert '/gemini-3.1-flash-lite:' in post.call_args.args[0]
    assert post.call_args.kwargs['json'] == original, 'Study recovery keeps the complete file/context and reasoning'
    assert post.call_args_list[0].kwargs['timeout'][1] <= 15, 'Do not spend 45 seconds on a stalled Lite startup'
    assert payload == original
    transport.send(post, 'fixture', 'gemini-3.5-flash-lite', payload, fast=False, stream=stream)
    assert post.call_count == 3 and '/gemini-3.1-flash-lite:' in post.call_args.args[0]
    assert post.call_args.kwargs['json']['generationConfig']['thinkingConfig'] == original['generationConfig']['thinkingConfig']


def test_two_study_lite_timeouts_are_bounded_and_sanitized(caplog):
    post = Mock(side_effect=requests.ReadTimeout('private-provider-detail'))
    with pytest.raises(transport.ProviderError) as caught:
        transport.send(post, 'fixture', 'gemini-3.5-flash-lite', {}, stream=True)
    assert caught.value.code == 'AI_TIMEOUT' and post.call_count == 2
    assert 'private-provider-detail' not in str(caught.value) + caplog.text


@pytest.mark.parametrize('status', [403, 429])
def test_study_fallback_never_works_around_access_or_quota(status):
    post = Mock(return_value=response(status))
    with pytest.raises(transport.ProviderError):
        transport.send(post, 'fixture', 'gemini-3.5-flash-lite', {}, stream=True)
    assert post.call_count == 1
    transport.discover_model.assert_not_called()


def test_study_output_failure_is_not_replayed():
    good = response(200)
    good.iter_lines.side_effect = requests.ReadTimeout('after headers')
    post = Mock(return_value=good)
    result = transport.send(post, 'fixture', 'gemini-3.5-flash-lite', {}, stream=True)
    with pytest.raises(requests.ReadTimeout):
        list(result.iter_lines())
    assert post.call_count == 1


@pytest.mark.parametrize('model', ['gemini-3.5-flash-lite', 'gemini-3.6-flash', 'gemini-3.8-flash'])
def test_new_api_models_receive_no_removed_sampling_parameters(model):
    payload = {'contents': [], 'generationConfig': {
        'temperature': 0.45, 'topP': 0.9, 'topK': 20,
        'maxOutputTokens': 1500, 'thinkingConfig': {'thinkingLevel': 'high'}}}
    original = copy.deepcopy(payload)
    post = Mock(return_value=response(200))
    transport.send(post, 'fixture', model, payload)
    config = post.call_args.kwargs['json']['generationConfig']
    assert not {'temperature', 'topP', 'topK'}.intersection(config)
    assert config['maxOutputTokens'] == 1500 and config['thinkingConfig']['thinkingLevel'] == 'high'
    assert payload == original


def test_existing_custom_study_model_is_not_silently_downgraded():
    post = Mock(side_effect=requests.ReadTimeout())
    with pytest.raises(transport.ProviderError):
        transport.send(post, 'fixture', 'gemini-fixture-study', {})
    assert post.call_count == 1


def test_older_model_keeps_supported_sampling_parameters():
    payload = {'generationConfig': {'temperature': 0.45, 'topP': 0.9, 'topK': 20}}
    post = Mock(return_value=response(200))
    transport.send(post, 'fixture', 'gemini-3.1-flash-lite', payload)
    assert post.call_args.kwargs['json'] == payload
