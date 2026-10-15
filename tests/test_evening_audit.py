"""Regression cases from the October 15 evening audit."""
import pytest
import chat_actions
import study_reference


@pytest.mark.parametrize('clarified',[False,True])
def test_contextual_reminder_quotes_its_source_not_the_timezone(monkeypatch,clarified):
    monkeypatch.setattr(chat_actions,'account_timezone',lambda *a:'Asia/Kolkata')
    messages=[dict(role='user',content='Explain DNA replication'),dict(role='assistant',content='DNA replication copies DNA before cell division.')]
    if clarified:
        messages.extend([dict(role='user',content='Remind me about this'),dict(role='assistant',content='Which date and time? For example: tomorrow at 7 PM.')])
        command='On 2030-10-16 at 8:30 PM IST'
    else:command='Remind me about this on 2030-10-16 at 8:30 PM IST'
    result=chat_actions.direct_reply(None,1,messages+[dict(role='user',content=command)])
    assert result['preview']['title']=='DNA replication copies DNA before cell division.'
    assert result['preview']['at']=='2030-10-16T15:00:00+00:00'
    assert result['preview']['text']=='From your chat: DNA replication copies DNA before cell division.'
    assert 'From your chat:' in result['reply'] and 'IST'!=result['preview']['title']


def test_contextual_reminder_with_no_source_asks_instead_of_guessing():
    result=chat_actions.direct_reply(None,1,[dict(role='user',content='Remind me about this at 8 PM')])
    assert 'Which topic' in result['reply'] and 'preview' not in result


@pytest.mark.parametrize('front,back,wrong',[
 ('In which direction is the DNA template read?','5′→3′.',True),
 ('DNA replication direction?','The template strand is read in the 5\' to 3\' direction.',True),
 ('DNA polymerase?','DNA polymerase moves along the template strand in the 5′→3′ direction.',True),
 ('New DNA direction?','DNA is synthesized from 3′ to 5′.',True),
 ('In which direction is the DNA template read?','3′→5′.',False),
 ('DNA replication?','The template with polarity 5′→3′ supports discontinuous synthesis.',False),
 ('In which direction is the DNA template read?','DNA is synthesized 5′→3′ while the template is read 3′→5′.',False),
 ('DNA template reading?','Not 5′→3′; it is read 3′→5′.',False),
 ('Replication products?','Each daughter DNA contains one parental strand and one new strand.',False),
])
def test_ncert_replication_direction_assertions(front,back,wrong):
    assert study_reference.flashcard_direction_error([(front,back)]) is wrong


def test_grounding_is_bounded_and_file_only_is_not_overridden(monkeypatch):
    import app
    assert 'NCERT' in study_reference.flashcard_grounding([dict(content='Explain DNA replication')])
    assert study_reference.flashcard_grounding([dict(content='Explain gravity')])==''
    text='[FLASHCARDS]\nFront: Which direction is the DNA template read?\nBack: 5′→3′.\n[/FLASHCARDS]'
    with pytest.raises(app.ProviderError,match='were not saved'):app.validate_study_reply('flashcards',text)
    app.validate_study_reply('flashcards',text,file_only=True)
