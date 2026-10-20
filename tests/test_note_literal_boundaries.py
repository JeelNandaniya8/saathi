"""Literal note boundaries must preserve user text before any save occurs."""
import pytest
import chat_commands as commands


CONTENT = 'Probability revision\nગુજરાતી નોંધ\nहिन्दी नोट\nMarker: SYNTHETIC-NOTE-BOUNDARY'


@pytest.mark.parametrize('title,separator', [
    ('Saathi live verification 2026-10-20 21:36', '. Content: '),
    ('Probability: conditional events', '; Content: '),
    ('Ratio 3:2', ' with content '),
    ('पुनरावृत्ति 21:36', ' and text '),
    ('નોંધ 21:36', '\nContent: '),
])
def test_explicit_content_boundary_keeps_colons_in_note_title(title, separator):
    command = 'Save this as a private note titled ' + title + separator + CONTENT
    assert commands.parse(command) == dict(kind='note', title=title, text=CONTENT)


@pytest.mark.parametrize('title,content', [
    ('Probability', 'Read the text carefully.\nગુજરાતી નોંધ'),
    ('Chemistry', 'Explain with content from chapter 2.'),
    ('Reminder wording', 'Use Content: as a literal heading.'),
])
def test_short_colon_form_does_not_promote_body_words_to_title(title, content):
    assert commands.parse(f'Save a note titled {title}: {content}') == dict(
        kind='note', title=title, text=content)


def test_quoted_title_and_labeled_fields_keep_existing_boundaries():
    title = 'Revision 21:36'
    for command in [
        f'Save a note titled "{title}" with content {CONTENT}',
        f'Save a note. Title: {title}; Content: {CONTENT}',
    ]:
        assert commands.parse(command) == dict(kind='note', title=title, text=CONTENT)
