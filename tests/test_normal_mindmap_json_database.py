import os
import json
from uuid import uuid4
import pytest
from test_database_flows import db_app,one
from test_audit_reliability_database import send
from test_normal_mindmap_json import REQUEST,Response,probability_map

pytestmark=pytest.mark.skipif(not os.environ.get('TEST_DATABASE_URL'),reason='Requires isolated PostgreSQL')


@pytest.mark.parametrize('stream',[False,True])
def test_normal_map_json_commits_once_reopens_exactly_and_replays(db_app,monkeypatch,stream):
    b,c,db=db_app;calls=[]
    monkeypatch.setattr(b,'GEMINI_API_KEY','fixture-key')
    def provider(*args,**kwargs):calls.append(1);return Response(probability_map())
    monkeypatch.setattr(b,'provider_send',provider)
    cid=c.post('/api/conversations',json={}).json['conversation']['id'];key=str(uuid4())
    result=send(c,cid,REQUEST,stream,key)
    message=result['assistant_message']
    assert not message.get('action_error') and message['action_receipt']['kind']=='mindmap'
    mid=message['action_receipt']['resource_id']
    assert one(db,'SELECT COUNT(*) n FROM mindmaps')['n']==1
    reopened=c.get('/api/mindmaps/'+str(mid)).json['mindmap']
    assert reopened['topic']=='Audit18C Probability'
    assert reopened['data']['root']['children'][2]['desc']=='P(even)=3/6=1/2.'
    assert send(c,cid,REQUEST,stream,key)['replayed']
    assert len(calls)==1 and one(db,'SELECT COUNT(*) n FROM mindmaps')['n']==1
    assert c.get('/api/study-allowance?kind=map').json['allowance']['remaining']==1


@pytest.mark.parametrize('stream',[False,True])
@pytest.mark.parametrize('failure',['provider','invalid_json_document'])
def test_normal_map_failure_has_no_saved_records_or_quota_charge(db_app,monkeypatch,stream,failure):
    b,c,db=db_app;monkeypatch.setattr(b,'GEMINI_API_KEY','fixture-key')
    def provider(*args,**kwargs):
        if failure=='provider':raise b.ProviderError('AI_BUSY','Fixture provider busy')
        return Response(dict(summary='Missing root'))
    monkeypatch.setattr(b,'provider_send',provider)
    cid=c.post('/api/conversations',json={}).json['conversation']['id']
    path=f'/api/conversations/{cid}/messages'+('/stream' if stream else '')
    response=c.post(path,json=dict(content=REQUEST,mode='normal',request_id=str(uuid4())))
    expected='AI_BUSY' if failure=='provider' else 'AI_FORMAT'
    if stream:
        events=[json.loads(line) for line in response.data.splitlines()]
        assert any(event.get('type')=='error' and event.get('code')==expected for event in events),events
        assert not any(event.get('type')=='complete' for event in events)
    else:assert response.status_code>=400 and response.json['code']==expected
    for table in ['mindmaps','chat_action_receipts','messages']:
        assert one(db,'SELECT COUNT(*) n FROM '+table)['n']==0
    assert c.get('/api/study-allowance?kind=map').json['allowance']['remaining']==2
