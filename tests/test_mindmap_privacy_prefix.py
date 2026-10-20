"""Privacy refusals must not hide a later explicit Normal mindmap command."""
import pytest
import chat_intents as intents
import chat_actions
from test_normal_mindmap_json import Response

PREFIX = 'Do not use my Classroom, notes, memories or workspace sources. '
REQUEST = PREFIX + ('Create and save a mindmap titled SAATHI-LIVE-MAP21 '
                    'about sample spaces and complements for two fair coin tosses.')


def coin_map():
    return dict(summary='Two fair coin tosses.', root=dict(
        label='Two Fair Coin Tosses', desc='Four equally likely outcomes.', children=[
            dict(label='Sample space', desc='{HH, HT, TH, TT}', children=[]),
            dict(label='Total outcomes', desc='2^2 = 4', children=[]),
            dict(label='Complements', desc='At least one Head: {HH, HT, TH}; complement: {TT}.',
                 children=[])]))


def test_refusing_sources_keeps_the_following_mindmap_permission_only():
    assert intents.automatic(REQUEST, 'mindmap')
    assert intents.classroom_denied(REQUEST)
    assert 'classroom' not in intents.sources(REQUEST)
    assert 'notes' not in intents.sources(REQUEST)
    for kind in ('note', 'memory', 'task', 'reminder', 'journal'):
        assert not intents.automatic(REQUEST, kind)


@pytest.mark.parametrize('suffix', [
    'Create a mindmap about coins. Do not save.',
    'Create a mindmap about coins. Preview only.',
    'Here is an example: create and save a mindmap about coins.',
    '"Create and save a mindmap about coins."',
    'Explain how to create and save a mindmap about coins.',
    'Do not create a mindmap about coins.',
    'How do I save a mindmap about coins?',
    'Create a draft mindmap about coins.',
])
def test_source_refusal_does_not_remove_save_vetoes_or_quoted_examples(suffix):
    assert not intents.automatic(PREFIX + suffix, 'mindmap')


@pytest.mark.parametrize('stream', [False, True])
@pytest.mark.parametrize('file_only', [False, True])
def test_prefixed_map_keeps_the_working_json_study_provider_contract(monkeypatch, stream, file_only):
    import app
    monkeypatch.setattr(app, 'GEMINI_API_KEY', 'fixture-key')
    monkeypatch.setenv('GEMINI_FAST_MODEL', 'gemini-fixture-busy')
    monkeypatch.setenv('GEMINI_MODEL', 'gemini-fixture-study')
    calls = []

    def provider(*args, **kwargs):
        calls.append((args[2], args[3], kwargs))
        if args[2] == 'gemini-fixture-busy':
            raise app.ProviderError('AI_BUSY', 'Fixture fast model unavailable', 503)
        return Response(coin_map())

    monkeypatch.setattr(app, 'provider_send', provider)
    messages = [dict(role='user', content='OLD_CLASSROOM_HISTORY'),
                dict(role='user', content=REQUEST)]
    if file_only:
        messages[-1]['attachments'] = [dict(
            name='synthetic.png', mime_type='image/png', content=b'fixture')]
    if stream:
        reply = ''.join(app.stream_gemini_reply(messages, file_only=file_only))
    else:
        reply = app.generate_gemini_reply(messages, file_only=file_only)
    draft = chat_actions.proposal(reply)
    assert draft['kind'] == 'mindmap' and draft['title'] == 'SAATHI-LIVE-MAP21'
    assert draft['map']['root']['children'][0]['desc'] == '{HH, HT, TH, TT}'
    assert len(calls) == 1
    model, payload, options = calls[0]
    assert model == 'gemini-fixture-study' and not options.get('fast')
    assert payload['generationConfig']['responseMimeType'] == 'application/json'
