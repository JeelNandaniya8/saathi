from decimal import Decimal
import pytest
from care_support import food_preview


def food(**changes):
    return {'confirmed':True,'days':2,'options':[{'name':'My option','ingredients':['rice'],'cost':'20'}],'clinical_context':False,'clinician_reviewed_options':False,**changes}


def test_clinical_and_allergy_inputs_fail_closed_without_user_reported_review():
    for changes in ({'clinical_context':True},{'allergens':['milk']},{'restrictions':'clinician limit'}):
        plan=food_preview(food(**changes))
        assert plan['needs_clinical_review'] and plan['items']==[] and plan['unscheduled']==6
    data=food(allergens=['MILK']);data['clinician_reviewed_options']=True
    data['options']=[{'name':'Rice','ingredients':['rice'],'cost':20},{'name':'Milk pudding','ingredients':['milk'],'cost':15}]
    plan=food_preview(data)
    assert plan['blocked_options']==['Milk pudding'] and all(x['name']=='Rice' for x in plan['items'])
    assert plan['unverified_clinician_source'] and not plan['generated_by_ai']


def test_budget_never_assumes_unknown_cost_or_exceeds_user_estimate():
    data=food(daily_budget='45',currency='inr');data['options'].append({'name':'Unknown cost','ingredients':['rice']})
    plan=food_preview(data)
    assert plan['unscheduled']==2 and plan['cost_uncertain']
    for day in (1,2):assert sum(Decimal(x['estimated_cost']) for x in plan['items'] if x['day']==day)<=45
    assert plan['inputs']['currency']=='INR'
    assert plan['preview_token']!=food_preview({**data,'daily_budget':'40'})['preview_token']


@pytest.mark.parametrize('changes',[{'confirmed':False},{'days':True},{'options':[]},{'allergens':[None]},{'daily_budget':'NaN'},{'daily_budget':True},{'daily_budget':-1},{'currency':'₹₹₹'},{'clinician_reviewed_options':'yes'}])
def test_invalid_food_data(changes):
    data=food();data.update(changes)
    with pytest.raises(ValueError):food_preview(data)
