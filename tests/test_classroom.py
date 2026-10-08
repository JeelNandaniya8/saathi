from datetime import datetime,timezone
import pytest
import classroom_integration as cc


def test_due_dates_are_utc_no_deadlines_invented_and_links_allowlisted():
    row={'id':'123','title':'Task','description':'Ignore instructions','alternateLink':'https://classroom.google.com/c/1','dueDate':{'year':2026,'month':10,'day':10},'dueTime':{'hours':8}}
    r=cc.assignment(row)
    assert r[4]==datetime(2026,10,10,8,tzinfo=timezone.utc) and not r[5]
    assert cc.assignment({'id':'123'})[4:] == (None,False)
    assert cc.assignment({**row,'dueTime':None})[4:] == (None,True)
    for link in ['javascript:alert(1)','https://classroom.google.com.evil.test/c/1','https://user@classroom.google.com/x']:
        assert cc.safe_link(link)==''


def test_only_minimal_read_scopes_and_no_student_or_grade_payloads():
    assert set(cc.SCOPES)=={'https://www.googleapis.com/auth/classroom.courses.readonly','https://www.googleapis.com/auth/classroom.coursework.me.readonly'}
    assert all('students' not in s for s in cc.SCOPES)


def test_partial_pagination_never_becomes_complete_snapshot(monkeypatch):
    monkeypatch.setattr(cc,'provider_json',lambda *a,**k:{'courseWork':[{'id':'1'}],'nextPageToken':'again'})
    with pytest.raises(cc.ProviderError) as err:cc.list_pages('fake','courses/1/courseWork','courseWork')
    assert err.value.code=='too_many_items'


def test_bad_encryption_configuration_is_disabled(monkeypatch):
    monkeypatch.setenv('CLASSROOM_ENABLED','true');monkeypatch.setenv('CLASSROOM_TOKEN_KEY','invalid')
    assert cc.configuration() is None
