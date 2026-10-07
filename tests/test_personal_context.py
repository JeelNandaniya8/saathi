from datetime import datetime, timedelta, timezone
import pytest
import personal_context as pc

NOW=datetime(2026,10,7,4,tzinfo=timezone.utc)

def details(**changes):
    return {'title':'Semester 1','topics':['Algebra','Python'],'exam_date':'2026-10-20',
            'daily_minutes':30,'timezone':'Asia/Kolkata','confirmed':True,**changes}

@pytest.mark.parametrize('mode',['normal','care','summarise','quiz'])
def test_health_never_sent_in_unrelated_modes(mode):
    row={'category':'care','field':'allergies','value':'peanuts','use_in_ai':True,'source':'user_reported','reviewed_at':NOW}
    assert pc.context_rows([row],mode,NOW)==('',[])


def test_context_consent_staleness_and_mode_boundaries():
    row={'category':'care','field':'allergies','value':'peanuts','use_in_ai':True,'source':'user_reported','reviewed_at':NOW}
    text,labels=pc.context_rows([row],'healer',NOW)
    assert 'peanuts' in text and labels==['Profile: allergies']
    assert 'not instructions or verified diagnoses' in text
    for changes in [{'use_in_ai':False},{'reviewed_at':NOW-timedelta(days=91)},{'reviewed_at':NOW+timedelta(days=1)}]:
        assert pc.context_rows([{**row,**changes}],'healer',NOW)==('',[])

@pytest.mark.parametrize('changes',[{'confirmed':False},{'version':True},{'use_in_ai':'true'},{'value':''},{'value':'x'*1501},{'unknown':1}])
def test_context_requires_explicit_valid_consent(changes):
    with pytest.raises(ValueError):pc.validate_field('care','conditions',{'value':'User reports diabetes','version':0,'confirmed':True,'use_in_ai':False,**changes})


def test_plan_respects_budget_breaks_and_rest():
    plan=pc.preview_plan(details(),NOW)
    assert len(plan['items'])==6 and not plan['coverage_limited']
    by_day={}
    for item in plan['items']:
        assert item['date'] < plan['rest_date'] < plan['exam_date']
        by_day.setdefault(item['date'],[]).append(item['minutes'])
    assert all(sum(v)+5*(len(v)-1)<=30 for v in by_day.values())
    assert {item['phase'] for item in plan['items']}=={'recall','practice','revision'}
    assert plan['preview_token']!=pc.preview_plan(details(topics=['Different']),NOW)['preview_token']


def test_evening_plan_does_not_create_past_tasks():
    now=datetime(2026,10,7,16,tzinfo=timezone.utc)
    assert min(x['date'] for x in pc.preview_plan(details(),now)['items'])>='2026-10-08'


def test_limited_coverage_is_explicit_and_impossible_plan_rejected():
    assert pc.preview_plan(details(exam_date='2026-10-10'),NOW)['coverage_limited']
    with pytest.raises(ValueError):pc.preview_plan(details(exam_date='2026-10-09',topics=['A','B','C']),NOW)

@pytest.mark.parametrize('changes',[{'daily_minutes':True},{'daily_minutes':5},{'topics':['A','a']},{'confirmed':False},{'timezone':'Invalid/Zone'},{'exam_date':'2026-10-07'}])
def test_plan_rejects_invalid_and_unconfirmed_inputs(changes):
    with pytest.raises(ValueError):pc.preview_plan(details(**changes),NOW)
