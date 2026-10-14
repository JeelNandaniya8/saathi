import json
import os
from datetime import datetime
from uuid import uuid4
import pytest
from test_database_flows import db_app,one
from test_reliability import questions
from test_assessment_quality import dice
from test_audit_reliability_database import send

pytestmark=pytest.mark.skipif(not os.environ.get('TEST_DATABASE_URL'),reason='Requires isolated PostgreSQL')


def test_invalid_generation_never_starts_a_saved_exam(db_app,monkeypatch):
    b,c,connect=db_app;raw=questions();raw[-1]=dice()
    monkeypatch.setattr(b,'generate_study_json',lambda *a:raw)
    key=str(uuid4())
    response=c.post('/api/mock-tests/generate',json=dict(topic='Dice',question_count=5,time_limit_minutes=5,job_id=key))
    assert response.status_code==400 and 'equivalent' in response.json['error']
    assert one(connect,'SELECT COUNT(*) AS n FROM mock_tests')['n']==0
    assert one(connect,'SELECT status FROM study_jobs WHERE id=%s',(key,))['status']=='failed'
    assert c.get('/api/study-allowance?kind=mock').json['allowance']['remaining']==1


def test_legacy_dice_score_history_and_revision_are_reconciled(db_app):
    _,c,connect=db_app;raw=questions();raw[-1]=dice();answers={str(n):'A' for n in range(1,6)};answers['5']='C'
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO mock_tests(user_id,topic,question_count,time_limit_minutes,questions_json,created_at) VALUES(1,'Audit dice',5,5,%s,NOW()) RETURNING id",(json.dumps(raw),));tid=cur.fetchone()['id']
            cur.execute('INSERT INTO mock_test_attempts(test_id,user_id,score,total_questions,accuracy_percentage,time_taken_seconds,answers_json,created_at) VALUES(%s,1,4,5,80,20,%s,NOW())',(tid,json.dumps(answers)))
            cur.execute("INSERT INTO revision_items(user_id,test_id,item_index,topic,front,back) VALUES(1,%s,5,'Audit dice','Dice question','Old wrong answer')",(tid,))
    history=c.get('/api/mock-tests/history').json['tests'][0]
    assert history['score']==5 and history['accuracy']==100
    result=c.get(f'/api/mock-tests/{tid}').json['result']
    assert result['attempt']['score']==5 and result['review'][-1]['is_correct']
    assert result['review'][-1]['accepted_answers']==['B','C']
    assert one(connect,'SELECT score FROM mock_test_attempts')['score']==5
    assert one(connect,'SELECT COUNT(*) AS n FROM revision_items')['n']==0
    assert c.post(f'/api/mock-tests/{tid}/submit',json=dict(answers={'5':'A'})).json==result
    assert one(connect,'SELECT COUNT(*) AS n FROM mock_test_attempts')['n']==1


def test_plan_receipt_reads_every_owned_task_and_retry_does_not_duplicate(db_app,monkeypatch):
    b,c,connect=db_app
    items=[dict(title='Day '+str(n),text='Revision',at=f'2026-11-{n:02}T18:00:00+05:30') for n in (1,2)]
    draft=dict(kind='plan',title='Two-day plan',text='Two revision tasks',items=items)
    monkeypatch.setattr(b,'generate_gemini_reply',lambda *a,**k:('<SAATHI_ACTION>'+json.dumps(draft)+'</SAATHI_ACTION>',{}))
    cid=c.post('/api/conversations',json={}).json['conversation']['id'];key=str(uuid4())
    text='Make a study plan with two tasks for the next two days'
    reply=send(c,cid,text,False,key)['assistant_message'];resource=reply['action_resource']
    assert resource['count']==resource['expected_count']==2 and resource['available']
    assert [item['title'] for item in resource['items']]==['Day 1','Day 2']
    for actual,expected in zip(resource['items'],items):assert datetime.fromisoformat(actual['due_at'])==datetime.fromisoformat(expected['at'])
    send(c,cid,text,False,key)
    assert one(connect,'SELECT COUNT(*) AS n FROM tasks')['n']==2
    stored=c.get(f'/api/conversations/{cid}/messages').json['messages'][-1]
    assert stored['action_resource']['items']==resource['items']
    second=resource['items'][1]['id'];assert c.delete(f'/api/tasks/{second}').status_code==200
    path=f"/api/chat-actions/{reply['id']}";receipt=c.get(path).json
    assert receipt['saved'] is False and receipt['resource']['count']==1
    assert c.post(path,json=dict(confirmed=True)).status_code==410
    assert one(connect,'SELECT COUNT(*) AS n FROM tasks')['n']==1
