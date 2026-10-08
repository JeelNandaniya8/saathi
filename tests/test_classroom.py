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


@pytest.mark.parametrize('coursework', [cc.SCOPES[1], 'https://www.googleapis.com/auth/classroom.student-submissions.me.readonly'])
def test_google_readonly_scope_names_are_accepted(coursework):
    assert cc.has_required_scopes('  '+coursework+'\t'+cc.SCOPES[0]+'  ')


@pytest.mark.parametrize('scope', [None, [], '', cc.SCOPES[0], cc.SCOPES[1],
    cc.SCOPES[0]+' https://www.googleapis.com/auth/classroom.coursework.me',
    cc.SCOPES[0]+' https://www.googleapis.com/auth/classroom.student-submissions.students.readonly',
    cc.SCOPES[0]+' https://www.googleapis.com/auth/classroom.student-submissions.me.readonly.evil'])
def test_missing_or_unrelated_permissions_are_rejected(scope):
    assert not cc.has_required_scopes(scope)


def test_partial_pagination_never_becomes_complete_snapshot(monkeypatch):
    monkeypatch.setattr(cc,'provider_json',lambda *a,**k:{'courseWork':[{'id':'1'}],'nextPageToken':'again'})
    with pytest.raises(cc.ProviderError) as err:cc.list_pages('fake','courses/1/courseWork','courseWork')
    assert err.value.code=='too_many_items'


def test_bad_encryption_configuration_is_disabled(monkeypatch):
    monkeypatch.setenv('CLASSROOM_ENABLED','true');monkeypatch.setenv('CLASSROOM_TOKEN_KEY','invalid')
    assert cc.configuration() is None


def test_provider_budget_is_context_local_and_never_calls_after_deadline(monkeypatch):
    called=[]
    class Reply:
        status_code=200
        def json(self):return {}
    def request(*a,**kw):called.append(kw['timeout']);return Reply()
    monkeypatch.setattr(cc.requests,'request',request)
    with cc.provider_budget(2):cc.provider_json('GET',cc.API+'courses')
    assert 0<called[0][0]<=1 and 0<called[0][1]<=1
    with cc.provider_budget(-1):
        with pytest.raises(cc.ProviderError) as error:cc.provider_json('GET',cc.API+'courses')
    assert error.value.code=='time_budget' and len(called)==1
    cc.provider_json('GET',cc.API+'courses');assert called[-1]==(5,10)
