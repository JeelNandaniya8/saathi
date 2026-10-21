"""Students' natural school-work requests must not fall through to model guesses."""
import pytest
import chat_actions
import chat_intents as intents


QUERIES = [
    'mare ketli assigment baki che?',
    'mara classroom ma su assignment aavya che?',
    'mara assignments kaya che?',
    'mara college na assignment',
    'my classroom assignments',
    'mere college ke assignments batao',
    'college assignment btao',
    'મારા ક્લાસરૂમમાં કયાં અસાઇન્મેન્ટ છે?',
    'મારા કોલેજનાં અસાઈન્મેન્ટ બતાવ',
    'મારા અસાઈનમેન્ટ બતાવ',
    'મારા એસાઇન્મેન્ટ કયા બાકી છે?',
    'મારા અસાઈનમેન્ટ',
    'મારા ક્લાસરૂમનાં અસાઈનમેન્ટ',
    'मेरे कॉलेज के असाइनमेंट बताओ',
    'मेरे असाईनमेंट दिखाओ',
    'मेरे कॉलेज के असाइनमेंट',
]


@pytest.mark.parametrize('query', QUERIES)
def test_colloquial_school_requests_use_owned_read_without_ai(query):
    assert intents.classroom_read(query)
    assert 'classroom' in intents.sources(query)
    for selected in ['normal', 'wellbeing', 'care', 'explain', 'deep_study', 'quiz', 'flashcards']:
        assert intents.mode(query, selected) == 'normal'
    direct = chat_actions.direct_reply(None, 1, [dict(role='user', content=query)])
    assert direct and direct.get('classroom_query') == query
    assert direct['reply'] == ''


@pytest.mark.parametrize('query', [
    'my assignments are examples for a grammar exercise',
    'Help me write my college assignment',
    'What is an assignment?',
    'assignment su che?',
    'assignment kya hota hai?',
    'અસાઈન્મેન્ટ શું છે?',
    'असाइनमेंट क्या है?',
    'How does my classroom work?',
    'Make flashcards about assignments',
    'Save a note. Title: mara college na assignment; Content: sample',
    'Example: mare ketli assigment baki che?',
    '"mara assignments kaya che?"',
    "Explain 'mare ketli assigment baki che?'",
    'mara assigment batavsho nahi',
    'mere assignments batao mat',
    'mere assignments nahi batao',
    'મારા અસાઇન્મેન્ટ બતાવશો નહીં',
    'मेरे असाइनमेंट मत बताओ',
])
def test_colloquial_matching_preserves_refusals_quotes_and_other_requests(query):
    assert not intents.classroom_read(query)


@pytest.mark.parametrize('query', ['mara assigment batavsho nahi', 'mere assignments batao mat', 'mere assignments nahi batao', 'મારા અસાઇન્મેન્ટ બતાવશો નહીં', 'मेरे असाइनमेंट मत बताओ'])
def test_colloquial_refusals_also_block_automatic_sharing(query):
    assert intents.classroom_denied(query)
    assert 'classroom' not in intents.sources(query)
