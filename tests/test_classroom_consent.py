"""A source refusal must survive routing, enabled auto-context and history."""
import json
import pytest
import chat_actions
import chat_intents as intents


@pytest.mark.parametrize('text', [
    'Classroom ન વાંચો. Show pending homework.',
    'Show pending homework, but don’t read Classroom.',
    'Classroom न पढ़ो। बाकी homework दिखाओ।',
    'Classroom data use nahi karna. Show pending homework.',
    'Explain vectors without "Classroom".',
    "Explain vectors without 'Classroom'.",
])
def test_explicit_source_refusal_does_not_grant_classroom(text):
    assert intents.classroom_denied(text)
    assert not intents.classroom_read(text)
    assert 'classroom' not in intents.sources(text)


@pytest.mark.parametrize('text', [
    "Explain the sentence 'Show my classroom assignments'.",
    'Explain the sentence ‘Show my classroom assignments’.',
])
def test_quoted_school_request_is_not_one_turn_consent(text):
    assert not intents.classroom_read(text)
    assert 'classroom' not in intents.sources(text)


def test_roman_gujarati_school_request_stays_local():
    text = 'School ni to-do list batav.'
    assert intents.classroom_read(text)
    assert chat_actions.direct_reply(None, 1, [dict(role='user', content=text)])['classroom_query']


def test_refusal_overrides_enabled_auto_context_and_stale_snapshot():
    snapshot = dict(permissions={'classroom': True}, timezone='Asia/Kolkata',
                    classroom_connection={'connected': True},
                    sources={k: [{'title': 'PRIVATE_SCHOOL_MARKER'}] for k in chat_actions.SOURCES})
    text, labels = chat_actions.workspace_context(None, 1,
        'Explain vectors without Classroom.', snapshot=snapshot)
    assert 'PRIVATE_SCHOOL_MARKER' not in text
    assert 'classroom' not in ' '.join(labels).lower()
    assert 'excluded for this reply' in text


def test_refusal_cannot_reuse_school_content_from_earlier_chat(monkeypatch):
    import app
    monkeypatch.setattr(app, 'GEMINI_API_KEY', 'fixture-key')
    payload = app.build_gemini_payload([
        dict(role='user', content='What homework is pending?'),
        dict(role='assistant', content='PRIVATE_SCHOOL_HISTORY'),
        dict(role='user', content='Explain vectors without Classroom.')],
        memory_context='Allowed unrelated study context')
    rendered = json.dumps(payload)
    assert 'PRIVATE_SCHOOL_HISTORY' not in rendered
    assert 'Allowed unrelated study context' in rendered


def test_not_submitted_is_a_status_question_not_a_source_refusal():
    for text in ['Which assignments have I not submitted?',
                 'કયું હોમવર્ક હજી પૂરું નથી કર્યું?', 'कौन से असाइनमेंट जमा नहीं किए?']:
        assert intents.classroom_read(text)


@pytest.mark.parametrize('language,needle',[('gu','જોડાણ'),('hi','कनेक्शन')])
def test_disconnected_classroom_recovery_uses_the_selected_language(language,needle):
    import classroom_integration as cc
    class Cursor:
        def execute(self,*args):pass
        def fetchone(self):return None
        def close(self):pass
    class Connection:
        def cursor(self):return Cursor()
        def close(self):pass
    reply=cc.chat_reply(Connection,1,'Show my assignments',language)['reply']
    assert reply.startswith('Google Classroom data could not be fetched right now')
    assert needle in reply


@pytest.mark.parametrize('language,needle',[('en','previous imports'),('gu','અગાઉનાં imports'),('hi','पिछले imports')])
def test_failed_provider_recovery_never_presents_retained_imports_as_fresh(language,needle):
    import classroom_integration as cc
    for reason in ['reconnect_required','permission_or_admin_block','quota','time_budget','too_many_items']:
        reply=cc.chat_failure(reason,language)
        assert reply.startswith('Google Classroom data could not be fetched right now')
        assert needle in reply

