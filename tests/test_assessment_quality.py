import pytest
import assessment_quality as quality
import study_tools


def dice():
    return dict(question='Three fair dice are rolled. What is the probability of a sum of at least 16?',
        options=dict(A='1/36',B='5/108',C='10/216',D='1/18'),correct_option='A',
        explanation='10 favourable outcomes out of 216. Probability = 5/108. Option B is correct.')


@pytest.mark.parametrize('a,b',[('5/108','10/216'),('0.5','50%'),(r'\frac{1}{2}','2/4'),('2**3','8'),('1.6e-19','16e-20'),('૧/૨','2/4'),('१०/२१६','5/108')])
def test_exact_equivalent_options(a,b):assert quality.equivalent(a,b)


def test_expressions_cannot_execute_code_or_unbounded_work():
    for text in ["__import__('os').system('false')",'10**1000000','1/0','1e309','1+','True']:
        assert quality.numeric_value(text) is None
    assert not quality.equivalent('1.0000000000000001','1')


@pytest.mark.parametrize('n,condition,expected',[(2,'exactly 7','1/6'),(2,'at most 3','1/12'),(3,'at least 17','1/54'),(3,'at least 18','1/216'),(3,'at least 19','0'),(3,'at least 3','1')])
def test_known_fair_dice_boundaries(n,condition,expected):
    assert quality.dice_probability(f'{n} fair dice are rolled. What is the probability of a sum of {condition}?')[0]==quality.numeric_value(expected)


def test_audit_dice_answer_gets_credit_and_a_consistent_explanation():
    question=study_tools.validate_questions([dice()],quality=False)
    for answer in ('B','C'):
        result=study_tools.grade(question,{'1':answer},10)
        assert result['attempt']['score']==1 and result['review'][0]['is_correct']
        assert result['review'][0]['correct_answer']=='B' and result['review'][0]['answer_verified']
        assert '10 favourable' in result['review'][0]['explanation'] and '1/36' not in result['review'][0]['explanation']
    assert study_tools.grade(question,{'1':'A'},10)['attempt']['score']==0
    with pytest.raises(ValueError,match='equivalent'):study_tools.validate_questions([dice()])
    repaired=dice();repaired['options']['C']='1/54'
    with pytest.raises(ValueError,match='inconsistent'):study_tools.validate_questions([repaired])


def test_unresolved_contradictions_are_not_scored_or_used_for_revision():
    from daily_workspace import mock_revision_rows
    q=dict(question='Which definition applies?',options=dict(A='First',B='Second',C='Third',D='Fourth'),correct_option='A',explanation='Option B is correct.')
    with pytest.raises(ValueError,match='inconsistent'):study_tools.validate_questions([q])
    result=study_tools.grade(study_tools.validate_questions([q],quality=False),{'1':'B'},10)
    assert result['attempt']['total_questions']==0 and result['attempt']['excluded_questions']==1
    assert result['review'][0]['is_correct'] is None and result['review'][0]['correct_answer'] is None
    assert mock_revision_rows(1,1,'Definitions',result['review'])==[]


def test_conditional_dice_wording_never_uses_an_unconditional_calculation():
    assert quality.dice_probability('Three fair dice are rolled. Given one is odd, what is the probability of a sum of at least 16?') is None
    assert quality.dice_probability('Three fair dice with eight faces are rolled. What is the probability of a sum of at least 16?') is None
