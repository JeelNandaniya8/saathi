from unittest.mock import Mock
import pytest
import requests
import ai_transport
import assessment_quality
import study_reference


def test_transcription_template_polarity_is_rejected():
    assert study_reference.flashcard_direction_error([('Which DNA strand is the transcription template?','The template strand has 5′→3′ polarity.')])


def test_zero_vector_angle_cannot_be_marked_as_ninety_degrees():
    question=dict(question='Find the angle between vectors a=(0,0,0) and b=(1,2,3).',options={'A':'90 degrees','B':'0 degrees','C':'180 degrees','D':'Undefined'},correct_option='A',explanation='The zero dot product gives a right angle.')
    with pytest.raises(ValueError):assessment_quality.validate(question)


def test_file_analysis_uses_the_working_study_model(monkeypatch):
    import app
    monkeypatch.setattr(app,'GEMINI_API_KEY','fixture')
    monkeypatch.setenv('GEMINI_FAST_MODEL','gemini-fixture-busy')
    monkeypatch.setenv('GEMINI_MODEL','gemini-fixture-study')
    seen=[]
    def send(*args,**kwargs):
        seen.append((args[2],kwargs.get('fast')))
        if args[2]=='gemini-fixture-busy':raise ai_transport.ProviderError('AI_BUSY','Fixture fast model is unavailable',503)
        return Mock(json=lambda:{'candidates':[{'content':{'parts':[{'text':'Fixture code read.'}]},'finishReason':'STOP'}]},close=lambda:None)
    monkeypatch.setattr(app,'provider_send',send)
    attachment=dict(name='page.png',mime_type='image/png',content=b'fixture',size_bytes=7)
    text=app.generate_gemini_reply([dict(role='user',content='Read the fixture code',attachments=[attachment])],file_only=True)
    assert text=='Fixture code read.' and seen==[('gemini-fixture-study',False)]


@pytest.mark.parametrize('question,expected',[
 ('Find a unit vector of a=(0,0,0).',True),
 ('Find the projection of a=(1,2,3) onto b=(0,0,0).',True),
 ('Find the projection of a=(0,0,0) onto b=(1,2,3).',False),
 ('Find a unit vector of a=(1,0,0), given b=(0,0,0).',None),
 ('Find the angle between a=(1,0,0) and b=(0,1,0).',None),
])
def test_vector_domain_cases(question,expected):
    result=assessment_quality.vector_zero_case(question)
    assert (result['undefined'] if result else None)==expected


@pytest.mark.parametrize('back,wrong',[
 (r'The template strand has $5^{\prime} \to 3^{\prime}$ polarity.',True),
 ('RNA polymerase reads the template 3′→5′ and synthesizes RNA 5′→3′.',False),
 ('The coding strand is 5′→3′; the template strand is 3′→5′.',False),
])
def test_transcription_guard_keeps_correct_distinctions(back,wrong):
    assert bool(study_reference.flashcard_direction_error([('Which DNA strand is the transcription template?',back)]))==wrong


@pytest.mark.parametrize('language,text,needle',[
 ('en','I am overwhelmed about my exam','two minutes'),
 ('gu','પરીક્ષાની ચિંતા થાય છે','બે મિનિટ'),
 ('hi','परीक्षा की चिंता है','दो मिनट'),
])
def test_exam_stress_gets_one_bounded_ten_minute_step(language,text,needle):
    reply=study_reference.answer([dict(role='user',content=text)],language)
    assert needle in reply and '10' in reply
    assert not any(word in reply.casefold() for word in ['guarantee','lazy','definitely pass'])
    assert study_reference.answer([dict(role='user',content=text,attachments=[{}])],language) is None


def test_exam_stress_step_does_not_intercept_crisis_or_other_requests():
    assert study_reference.exam_stress_step([dict(content='I am stressed about an exam and want to kill myself')]) is None
    assert study_reference.exam_stress_step([dict(content='Save this note: exam stress')]) is None
    assert study_reference.exam_stress_step([dict(content='Explain exam registration')]) is None
