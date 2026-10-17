"""Exact PDF attribution and latest-file-only provider scope."""
import json
import pytest
import app


def pdf(name='real.pdf', text='Velocity is displacement per unit time.'):
    return dict(name=name, mime_type='application/pdf', content=b'%PDF-fixture',
                pages=[dict(page_number=1, content=text)])


@pytest.mark.parametrize('reply', [
    'Unsupported claim [invented.pdf, Page 1]',
    'Unsupported claim [another file.pdf, Page 1].',
    'Unsupported claim [real.pdf, Page 99]',
])
def test_named_citation_cannot_be_reassigned_to_another_file_or_page(reply):
    assert app.cited_source_pages(reply, [pdf()]) == []


def test_exact_named_and_bare_page_references_remain_available():
    assert app.cited_source_pages('Support [real.pdf, Page 1]; also Page 1.', [pdf()]) == [dict(name='real.pdf', page=1)]
    assert app.cited_source_pages('See Page 1.', [pdf()]) == [dict(name='real.pdf', page=1)]


def test_comma_filename_is_exact_when_multiple_pdfs_are_present():
    assert app.cited_source_pages('Support [lesson, physics.pdf, Page 1]',
        [pdf('lesson, physics.pdf'), pdf('other.pdf')]) == [dict(name='lesson, physics.pdf', page=1)]


def test_ambiguous_duplicate_filenames_do_not_get_a_verified_source_link():
    assert app.cited_source_pages('Claim [same.pdf, Page 1]',
        [pdf('same.pdf', 'First document'), pdf('SAME.pdf', 'Different document')]) == []


def test_file_only_sends_latest_file_and_question_without_prior_sources(monkeypatch):
    monkeypatch.setattr(app, 'GEMINI_API_KEY', 'fixture-key')
    messages = [
        dict(role='user', content='PRIVATE_EARLIER_QUESTION', attachments=[pdf('old.pdf', 'PRIVATE_OLD_FILE')]),
        dict(role='assistant', content='PRIVATE_EARLIER_ANSWER'),
        dict(role='user', content='Explain the current file.', attachments=[pdf('current.pdf', 'CURRENT_FILE_SUPPORT')]),
    ]
    payload = app.build_gemini_payload(messages, 'PRIVATE_MEMORY_CONTEXT', file_only=True)
    encoded = json.dumps(payload)
    assert 'CURRENT_FILE_SUPPORT' in encoded
    assert 'PRIVATE_' not in encoded, 'File-only must enforce its latest-upload scope in the payload'
    assert len(payload['contents']) == 1
    ordinary = json.dumps(app.build_gemini_payload(messages, 'PRIVATE_MEMORY_CONTEXT'))
    assert all(text in ordinary for text in ['PRIVATE_EARLIER_QUESTION', 'PRIVATE_EARLIER_ANSWER', 'PRIVATE_OLD_FILE', 'PRIVATE_MEMORY_CONTEXT'])
