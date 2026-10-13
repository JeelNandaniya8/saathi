import pytest
import chat_intents as intents


@pytest.mark.parametrize('text,kind', [
    ('My birthday is 1st January','memory'), ('I live in Ahmedabad','memory'),
    ('Remember that my maths exam is on 15 November','memory'),
    ('Remind me about this at 8 PM','reminder'),
    ('Remind me every day at 7:30 to revise chemistry','reminder'),
    ('Snooze that reminder 30 minutes','reminder'),
    ('Pause my morning walk reminder','reminder'),
    ('Save this as a note','note'), ('Make a note of the formula I just wrote','note'),
    ('Put this in my notes','note'), ('Make a study plan for the next 3 days','plan'),
    ('Mark the probability revision as done','task'),
    ('Turn this explanation into a mindmap','mindmap'),
    ('આને નોંધમાં સાચવો','note'), ('इसे नोट में सेव करें','note')])
def test_explicit_commands_authorise_only_the_requested_kind(text,kind):
    operation='snooze' if text.startswith('Snooze') else 'pause' if text.startswith('Pause') else 'complete' if text.startswith('Mark') else 'create'
    assert intents.automatic(text,kind,operation)
    assert not intents.automatic(text,'journal')


@pytest.mark.parametrize('text', ['How do I save a note?', 'Explain how reminders work',
    'Here is an example: create a task', '> Save this as a note', '"Remember my birthday"'])
def test_examples_questions_and_quoted_data_do_not_execute(text):
    assert not any(intents.automatic(text,k) for k in ('task','reminder','note','memory'))


def test_deletion_requires_a_separate_explicit_confirmation():
    assert not intents.automatic('Delete my walk reminder','reminder','delete')
    assert intents.automatic('Yes, delete my walk reminder','reminder','delete')


def test_one_turn_sources_do_not_implicitly_share_private_notes():
    assert intents.sources('How much work is left?')=={'tasks'}
    assert intents.sources('What messages came in the classroom?')=={'classroom'}
    assert intents.sources("What's my activity today?")=={'tasks','reminders','habits'}
    assert 'notes' not in intents.sources('How much work is left?')
    assert 'notes' not in intents.sources('Save this as a note')
    assert intents.sources('Read my notes')=={'notes'}
    assert intents.sources('Summarise my notes')=={'notes'}
    assert intents.sources('Make flashcards from my notes')=={'notes'}
    assert 'notes' not in intents.sources('Make a note of this formula')
    assert 'notes' not in intents.sources('આની નોંધ બનાવો')
    assert 'notes' not in intents.sources('इसका नोट बनाओ')
    assert 'notes' in intents.sources('મારી નોંધ વાંચો')
    assert 'notes' in intents.sources('मेरे नोट पढ़ो')


@pytest.mark.parametrize('text,mode', [('Make flashcards of this','flashcards'),
    ('Turn these points into flashcards','flashcards'),('Summarise this PDF','summarise'),
    ('Make a study plan for the next 3 days','study_plan')])
def test_modes_follow_the_user_command(text,mode):
    assert intents.mode(text)==mode
    assert intents.mode('I like flashcards')=='normal'


def test_quotes_do_not_switch_modes_or_read_sources():
    assert intents.mode('> Make flashcards')=='normal'
    assert intents.sources('> Read my notes')==set()
    assert not intents.automatic('Add a task: Read chapter. Show the save preview.','task')


def test_mutations_do_not_authorise_a_different_operation():
    assert not intents.automatic('Pause my walk reminder','reminder','create')
    assert not intents.automatic('Pause my walk reminder','reminder','resume')
    assert intents.automatic('Pause my walk reminder','reminder','pause')
    assert intents.mode('Pause my walk reminder','flashcards')=='normal'


def test_clarification_continuation_is_cancelable_and_cannot_replace_new_intent():
    recent=[dict(role='user',content='Make a study plan for 3 days'),dict(role='assistant',content='Which subjects and how much time each day?')]
    assert intents.continuation(recent,'Maths, 2 hours each day')==recent[0]['content']
    for answer in ['Cancel','No thanks','> Use this instead','Save this as a note']:
        assert intents.continuation(recent,answer)==''
    assert intents.continuation([dict(role='user',content='Make a study plan'),dict(role='assistant',content='Plan ready <SAATHI_ACTION>{}</SAATHI_ACTION>')],'Yes')==''
