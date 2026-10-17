import os
import json
from uuid import uuid4
import pytest
from test_database_flows import db_app,one
from test_audit_reliability_database import send

pytestmark=pytest.mark.skipif(not os.environ.get('TEST_DATABASE_URL'),reason='Requires isolated PostgreSQL')


@pytest.mark.parametrize('stream',[False,True])
def test_context_reminder_confirmation_reads_back_bound_subject(db_app,monkeypatch,stream):
    b,c,connect=db_app
    monkeypatch.setattr(b,'provider_send',lambda *a,**k:pytest.fail('A contextual reminder must not need AI'))
    cid=c.post('/api/conversations',json={}).json['conversation']['id']
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO messages(user_id,conversation_id,role,content,created_at) VALUES(1,%s,'assistant','DNA replication copies DNA before cell division.',NOW())",(cid,))
    question=send(c,cid,'Remind me about this',stream)['assistant_message']
    assert not question.get('action_receipt')
    preview=send(c,cid,'On 2030-10-16 at 8:30 PM IST',stream)['assistant_message']
    assert 'DNA replication' in preview['content'] and not preview.get('action_receipt')
    assert one(connect,'SELECT COUNT(*) AS n FROM reminders')['n']==0
    saved=send(c,cid,'Confirm reminder',stream)['assistant_message']
    assert saved['action_receipt']['kind']=='reminder'
    row=one(connect,'SELECT title,note,next_run_at FROM reminders')
    assert row['title']=='DNA replication copies DNA before cell division.'
    assert row['note'].startswith('From your chat: DNA replication')
    assert row['next_run_at'].isoformat()=='2030-10-16T15:00:00+00:00'


@pytest.mark.parametrize('stream',[False,True])
@pytest.mark.parametrize('missing_item',[False,True])
def test_context_reminder_resolves_only_the_current_owned_plan(db_app,monkeypatch,stream,missing_item):
    import chat_actions
    b,c,connect=db_app
    monkeypatch.setattr(b,'provider_send',lambda *a,**k:pytest.fail('Receipt-bound reminder needs no AI'))
    cid=c.post('/api/conversations',json={}).json['conversation']['id']
    with connect() as conn:
        with conn.cursor() as cur:
            ids=[]
            for title,when in [('Release17 Vectors Day 1','2030-10-19T13:30:00+00:00'),('Release17 Vectors Day 2','2030-10-20T13:30:00+00:00')]:
                cur.execute('INSERT INTO tasks(user_id,title,due_at,created_at,updated_at) VALUES(1,%s,%s,NOW(),NOW()) RETURNING id',(title,when))
                ids.append(cur.fetchone()['id'])
            draft=dict(kind='plan',title='Study plan',items=[dict(title='Release17 Vectors Day 1'),dict(title='Release17 Vectors Day 2')])
            cur.execute("INSERT INTO messages(user_id,conversation_id,role,content,created_at) VALUES(1,%s,'assistant',%s,NOW()) RETURNING id",(cid,chat_actions.saved_content(draft)))
            mid=cur.fetchone()['id']
            chat_actions.store_receipt(cur,1,mid,chat_actions.make_receipt('plan',ids))
            cur.execute("UPDATE tasks SET title='Updated vector recall' WHERE id=%s",(ids[0],))
            cur.execute("INSERT INTO tasks(user_id,title,created_at,updated_at) VALUES(2,'Other-account private task',NOW(),NOW())")
            if missing_item:cur.execute('DELETE FROM tasks WHERE id=%s',(ids[1],))
    preview=send(c,cid,'Remind me about this on 2030-10-18 at 6 PM IST',stream)['assistant_message']
    assert one(connect,'SELECT COUNT(*) AS n FROM reminders')['n']==0
    assert 'Other-account' not in preview['content']
    if missing_item:
        assert 'Which topic' in preview['content']
        return
    assert 'Updated vector recall' in preview['content'] and 'Release17 Vectors Day 2' in preview['content']
    assert '2030-10-19, 07:00 PM' in preview['content']
    saved=send(c,cid,'Confirm reminder',stream)['assistant_message']
    assert saved['action_receipt']['kind']=='reminder'
    row=one(connect,'SELECT title,note,next_run_at FROM reminders')
    assert row['title']=='Study plan: Updated vector recall / Release17 Vectors Day 2'
    assert 'Updated vector recall — 2030-10-19, 07:00 PM' in row['note']
    assert row['next_run_at'].isoformat()=='2030-10-18T12:30:00+00:00'


@pytest.mark.parametrize('stream',[False,True])
def test_wrong_direction_never_becomes_saved_flashcards(db_app,monkeypatch,stream):
    b,c,connect=db_app
    reply='[FLASHCARDS]\nFront: Which direction is the DNA template read?\nBack: 5′→3′.\n[/FLASHCARDS]'
    monkeypatch.setattr(b,'generate_gemini_reply',lambda *a,**k:(reply,{}))
    def chunks(*a,**k):yield reply;return {}
    monkeypatch.setattr(b,'stream_gemini_reply',chunks)
    cid=c.post('/api/conversations',json={}).json['conversation']['id']
    response=c.post(f'/api/conversations/{cid}/messages'+('/stream' if stream else ''),json=dict(content='Make flashcards about DNA replication',mode='flashcards',request_id=str(uuid4())))
    if stream:
        events=[json.loads(line) for line in response.data.splitlines()]
        assert events[-1]['type']=='error' and events[-1]['code']=='AI_ACCURACY'
        assert not any(event['type']=='complete' for event in events)
    else:assert response.status_code==502 and 'were not saved' in response.json['error']
    assert one(connect,'SELECT COUNT(*) AS n FROM messages')['n']==0
    assert one(connect,'SELECT COUNT(*) AS n FROM study_progress')['n']==0


def test_card_correction_updates_source_revision_and_survives_retry_and_progress(db_app):
    _,c,connect=db_app
    cid=c.post('/api/conversations',json={}).json['conversation']['id']
    original='[FLASHCARDS]\nFront: Template reading?\nBack: 5′→3′\n---\nFront: New DNA?\nBack: 5′→3′\n[/FLASHCARDS]'
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO messages(user_id,conversation_id,role,content,created_at,ai_mode) VALUES(1,%s,'assistant',%s,NOW(),'flashcards') RETURNING id",(cid,original));mid=cur.fetchone()['id']
            cur.execute("INSERT INTO study_progress(user_id,conversation_id,message_id,kind,progress,created_at,updated_at) VALUES(1,%s,%s,'flashcards',%s,NOW(),NOW())",(cid,mid,json.dumps(dict(current_index=0,known_indices=[0],review_indices=[1]))))
            cur.execute("INSERT INTO revision_items(user_id,message_id,item_index,topic,front,back) VALUES(1,%s,0,'DNA','Template reading?','5′→3′')",(mid,))
    path=f'/api/messages/{mid}/flashcards/0'
    data=dict(front='Template reading?',back='3′→5′',expected_front='Template reading?',expected_back='5′→3′')
    with c.session_transaction() as session:session['user_id']=2
    assert c.patch(path,json=data).status_code==404
    with c.session_transaction() as session:session['user_id']=1
    result=c.patch(path,json=data)
    assert result.status_code==200,result.json
    progress=result.json['study_progress']['progress']
    assert progress['corrected_indices']==[0] and progress['known_indices']==[] and progress['review_indices']==[0,1]
    assert one(connect,'SELECT back FROM revision_items')['back']=='3′→5′'
    version=one(connect,'SELECT version FROM revision_items')['version']
    replay=c.patch(path,json=data)
    assert replay.status_code==200 and replay.json['replayed']
    assert one(connect,'SELECT version FROM revision_items')['version']==version
    stale=c.patch(path,json={**data,'expected_back':'outdated','back':'Another correction'})
    assert stale.status_code==409
    assert c.patch(path,json={**data,'back':'Back: invalid control marker'}).status_code==400
    updated=c.patch(f'/api/messages/{mid}/study-progress',json=dict(progress=dict(current_index=1,known_indices=[0],review_indices=[1])))
    assert updated.status_code==200 and updated.json['study_progress']['progress']['corrected_indices']==[0]
    loaded=c.get(f'/api/conversations/{cid}/messages').json['messages'][-1]
    assert loaded['content']==result.json['content'] and loaded['study_progress']['progress']['corrected_indices']==[0]
    assert one(connect,'SELECT COUNT(*) AS n FROM revision_items')['n']==2
