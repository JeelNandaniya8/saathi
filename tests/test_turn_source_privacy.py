"""A refusal in the current turn must override previously allowed sources."""
import json

import pytest

import chat_actions
from test_mindmap_privacy_prefix import REQUEST, coin_map


REFUSALS = [
    'Do not use my memories or workspace sources. Explain a proof about nested quantifiers.',
    'મારી memories અને workspace data વાપરશો નહીં. એક પુરાવો સમજાવો.',
    'मेरी memories और workspace data मत पढ़ो। एक प्रमाण समझाओ।',
    'મારી યાદો અને કાર્યક્ષેત્રનો ડેટા વાપરશો નહીં. એક પુરાવો સમજાવો.',
    'मेरी यादें और कार्यक्षेत्र का डेटा मत पढ़ो। एक प्रमाण समझाओ।',
]


def shared_snapshot():
    return dict(permissions=dict.fromkeys(chat_actions.SOURCES, True),
                timezone='Asia/Kolkata', classroom_connection={'connected': True},
                sources={key: [{'title': 'PRIVATE_SOURCE_' + key}]
                         for key in chat_actions.SOURCES},
                editable_memories=[{'content': 'PRIVATE_EDITABLE_MEMORY'}],
                task_activity=[], habit_activity=[])


@pytest.mark.parametrize('query', REFUSALS)
def test_turn_refusal_overrides_consented_sources_and_stale_snapshot(query):
    snapshot = shared_snapshot()
    text, labels = chat_actions.workspace_context(None, 1, query, snapshot=snapshot)
    assert 'PRIVATE_SOURCE_' not in text
    assert not any(label.startswith(('Shared ', 'Requested ')) for label in labels)
    # This is a per-turn restriction, not a preference change.
    allowed, _ = chat_actions.workspace_context(None, 1, 'Explain a proof.', snapshot=snapshot)
    assert 'PRIVATE_SOURCE_tasks' in allowed
    assert all(snapshot['permissions'].values())


@pytest.mark.parametrize('query', REFUSALS)
def test_provider_boundary_excludes_memories_and_history_for_this_turn(monkeypatch, query):
    import app
    monkeypatch.setattr(app, 'GEMINI_API_KEY', 'fixture-key')
    payload = app.build_gemini_payload([
        dict(role='user', content='Use my saved sources.'),
        dict(role='assistant', content='PRIVATE_HISTORY_MARKER'),
        dict(role='user', content=query)],
        memory_context='PRIVATE_MEMORY_MARKER', mode='deep_study')
    encoded = json.dumps(payload, ensure_ascii=False)
    assert 'PRIVATE_MEMORY_MARKER' not in encoded
    assert 'PRIVATE_HISTORY_MARKER' not in encoded
    assert query in encoded


def test_normal_map_does_not_reappend_a_refused_memory_bundle(monkeypatch):
    import app
    monkeypatch.setattr(app, 'GEMINI_API_KEY', 'fixture-key')
    payloads = []

    def generate(payload):
        payloads.append(json.dumps(payload))
        return coin_map(), dict(prompt_tokens=1, output_tokens=1, total_tokens=2)

    monkeypatch.setattr(app, 'request_study_payload', generate)
    reply, _ = app.chat_mindmap_reply([dict(role='user', content=REQUEST)],
        'PRIVATE_MEMORY_MARKER', 'en', 'normal', False)
    assert chat_actions.proposal(reply)['kind'] == 'mindmap'
    assert len(payloads) == 1 and 'PRIVATE_MEMORY_MARKER' not in payloads[0]


@pytest.mark.parametrize('query', [
    'Do not use my tasks. Explain a proof.',
    'મારા tasks વાપરશો નહીં. એક પુરાવો સમજાવો.',
    'मेरे tasks मत पढ़ो। एक प्रमाण समझाओ।',
])
def test_a_specific_source_refusal_keeps_other_consented_sources(query):
    text, labels = chat_actions.workspace_context(None, 1, query, snapshot=shared_snapshot())
    assert 'PRIVATE_SOURCE_tasks' not in text
    assert 'PRIVATE_SOURCE_reminders' in text
    assert 'Shared tasks' not in labels


def test_task_refusal_cannot_enter_the_deterministic_planner_reader():
    class Cursor:
        def execute(self, *args):
            pytest.fail('A refused Planner source must not be queried')

    result = chat_actions.direct_reply(Cursor(), 1, [dict(role='user',
        content='Do not use my tasks. What remains today?')])
    assert result is None


@pytest.mark.parametrize('query', [
    'Which tasks have I not completed?',
    'કયાં tasks હજી પૂરાં નથી?',
    'कौन से tasks पूरे नहीं हुए?',
    'Explain a vector without dividing by zero.',
    'What unfinished tasks remain on 2026-10-15? Exclude tasks from 2026-10-14.',
    "Show today's tasks, excluding tasks from yesterday.",
])
def test_status_and_math_negations_do_not_refuse_private_sources(query):
    import chat_intents
    assert not chat_intents.excluded_sources(query)
