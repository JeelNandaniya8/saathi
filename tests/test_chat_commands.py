from datetime import datetime,timezone
import pytest
import chat_commands as commands
import study_reference


def test_task_deadline_uses_account_time_without_ai():
    now=datetime(2026,10,13,20,0,tzinfo=timezone.utc)
    draft=commands.parse('Add a task titled Revise physics due tomorrow at 7 PM','Asia/Kolkata',now)
    assert draft['title']=='Revise physics' and draft['at']=='2026-10-15T19:00:00+05:30'
    assert commands.parse('Add a task. Title: Read chapter; Details: Five questions')['text']=='Five questions'


def test_fact_has_short_label_and_reminder_drops_command_verb():
    assert commands.parse('Remember that I prefer studying Physics with short worked examples')['title']=='Study preference'
    assert commands.parse('Remind me tomorrow at 8 PM to do organic chemistry revision')['title']=='organic chemistry revision'


@pytest.mark.parametrize('text',[
 'Save this as a private note titled Audit probability: P(E) = favourable / total',
 'Save a note titled "Audit probability" with content P(E) = favourable / total',
 'Save this as a note with title Audit probability and content P(E) = favourable / total',
 'Save a note. Title: Audit probability; Content: P(E) = favourable / total'])
def test_named_note_preserves_supplied_private_content(text):
    assert commands.parse(text)==dict(kind='note',title='Audit probability',text='P(E) = favourable / total')


def test_birthday_is_clean_and_does_not_keep_instructions():
    draft=commands.parse('Remember that my birthday is 1st January. Save this personal fact to memory. This is a demo audit fact.')
    assert draft==dict(kind='memory',title='Birthday',text='Birthday: 1 January')
    assert commands.parse('Remember that my birthday is 31st February').get('question')
    assert commands.parse('> Remember that my birthday is 1st January') is None


def test_reminder_uses_account_midnight_and_asks_for_confirmation():
    now=datetime(2026,10,13,20,0,tzinfo=timezone.utc)
    draft=commands.parse('Remind me tomorrow at 7 PM to revise probability','Asia/Kolkata',now)
    assert draft['at']=='2026-10-15T19:00:00+05:30'
    assert '15 October 2026' in draft['confirm_time'] and draft['title']=='revise probability'
    assert commands.parse('Remind me at 7 to revise','Asia/Kolkata',now).get('question')
    assert commands.parse('Remind me today at 12 AM to revise','Asia/Kolkata',now).get('question')


@pytest.mark.parametrize('language',['en','gu','hi'])
def test_core_explanation_has_source_and_formula_assumptions(language):
    text=study_reference.answer([dict(role='user',content='Explain Newton’s second law in two sentences')],language)
    assert 'F_net = ma' in text and 'ncert.nic.in/textbook/pdf/keph104.pdf' in text
    assert study_reference.answer([dict(role='user',content='Explain the probability formula')],language)
    assert study_reference.answer([dict(role='user',content='Explain Newton’s second law',attachments=[{}])],language) is None
    assert study_reference.answer([dict(role='user',content='Calculate acceleration under Newton’s second law')],language) is None
    assert study_reference.answer([dict(role='user',content='Explain the conditional probability formula')],language) is None
    assert study_reference.answer([dict(role='user',content='Explain Newton’s second law for variable mass')],language) is None
    if language=='hi':
        assert 'F_net = ma' in study_reference.answer([dict(role='user',content='न्यूटन के दूसरे नियम को दो वाक्यों में समझाइए।')],language)
        assert study_reference.answer([dict(role='user',content='न्यूटन का दूसरा नियम क्यों लागू होता है?')],language) is None
    if language=='gu':
        assert 'F_net = ma' in study_reference.answer([dict(role='user',content='ન્યૂટનનો બીજો નિયમ બે વાક્યમાં સમજાવો.')],language)


def test_reference_explanations_and_new_assets_work_without_provider(monkeypatch):
    import app as backend
    monkeypatch.setattr(backend,'provider_send',lambda *a,**k:(_ for _ in ()).throw(AssertionError('Core explanation must stay available')))
    for language in ('en','gu','hi'):
        message=[dict(role='user',content='Explain Newton’s second law in two sentences')]
        assert 'F_net = ma' in backend.generate_gemini_reply(message,language=language)
        assert 'F_net = ma' in ''.join(backend.stream_gemini_reply(message,language=language))
    client=backend.app.test_client()
    assert client.get('/account-clock.js').status_code==200
    assert client.get('/study-jobs.js').status_code==200


@pytest.mark.parametrize('language,question',[
 ('en','Explain photosynthesis in two short sentences.'),
 ('gu','પ્રકાશસંશ્લેષણ બે ટૂંકા વાક્યમાં સમજાવો.'),
 ('hi','प्रकाश संश्लेषण को दो छोटे वाक्यों में समझाइए।')])
@pytest.mark.parametrize('mode',['normal','explain'])
def test_short_generation_keeps_only_current_study_question(monkeypatch,language,question,mode):
    from types import SimpleNamespace
    import app as backend
    sent=[]
    monkeypatch.setattr(backend,'GEMINI_API_KEY','fixture-key')
    def send(*args,**kwargs):
        sent.append((args[3],kwargs['fallback_payload']))
        return SimpleNamespace(json=lambda:{'candidates':[{'content':{'parts':[{'text':'Study answer.'}]}}]},close=lambda:None)
    monkeypatch.setattr(backend,'provider_send',send)
    messages=[dict(role='user',content='Private earlier conversation.'),dict(role='assistant',content='Earlier reply.'),dict(role='user',content=question)]
    assert backend.generate_gemini_reply(messages,memory_context='Private memory.',language=language,mode=mode)=='Study answer.'
    primary,fallback=sent[0]
    assert primary==fallback
    assert primary['contents']==[dict(role='user',parts=[dict(text=question)])]
    assert 'Private' not in str(primary)
    assert primary['generationConfig']['maxOutputTokens']<=900


@pytest.mark.parametrize('message',[
 dict(role='user',content='Explain this from my notes.'),
 dict(role='user',content='Explain photosynthesis.',attachments=[{'name':'chapter.pdf'}])])
def test_compact_generation_does_not_discard_requested_context(message):
    assert study_reference.compact_payload({'contents':[]},[message],'en','normal') is None
