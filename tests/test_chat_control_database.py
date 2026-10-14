import json
import os
from datetime import datetime,timedelta,timezone
import pytest
import chat_actions as actions
from test_database_flows import db_app,one

pytestmark=pytest.mark.skipif(not os.environ.get('TEST_DATABASE_URL'),reason='Requires isolated PostgreSQL')


def seed(connect,command,draft):
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO conversations(user_id,title,created_at,updated_at) VALUES(1,'Control test',NOW(),NOW()) RETURNING id")
            cid=cur.fetchone()['id']
            cur.execute("INSERT INTO messages(user_id,conversation_id,role,content,created_at) VALUES(1,%s,'user',%s,NOW())",(cid,command))
            content='Preparing the details. <SAATHI_ACTION>'+json.dumps(draft)+'</SAATHI_ACTION>'
            cur.execute("INSERT INTO messages(user_id,conversation_id,role,content,created_at) VALUES(1,%s,'assistant',%s,NOW()) RETURNING id",(cid,content))
            return cur.fetchone()['id'],cid


def execute(client,mid):
    path='/api/chat-actions/'+str(mid)
    prepared=client.get(path).json
    return client.post(path,json=dict(confirmed=True,automatic=True,memory_consent=True,action=prepared.get('action')))


@pytest.mark.parametrize('command,kind,text', [('My birthday is 1st January','memory','My birthday is 1st January'),
    ('I live in Ahmedabad','memory','I live in Ahmedabad'),('Save this as a note','note','The formula: P(A)=n(A)/n(S)')])
def test_explicit_save_receipts_are_owned_private_and_idempotent(db_app,command,kind,text):
    _,c,connect=db_app
    mid,_=seed(connect,command,dict(kind=kind,title='Personal details',text=text))
    first=execute(c,mid);assert first.status_code==201,first.json
    assert execute(c,mid).status_code==200
    table='memories' if kind=='memory' else 'quick_notes'
    assert one(connect,'SELECT count(*) AS n FROM '+table)['n']==1
    assert one(connect,'SELECT count(*) AS n FROM chat_action_receipts')['n']==1
    with c.session_transaction() as s:s['user_id']=2
    assert c.get('/api/chat-actions/'+str(mid)).status_code==404


def test_chat_questions_cannot_authorise_model_invented_saves(db_app):
    _,c,connect=db_app
    mid,_=seed(connect,'Explain how to save a note',dict(kind='note',title='Not requested',text='No'))
    assert execute(c,mid).status_code==400
    assert one(connect,'SELECT count(*) AS n FROM quick_notes')['n']==0


def test_direct_stream_command_saves_with_reply_and_replay_never_duplicates(db_app,monkeypatch):
    b,c,connect=db_app
    monkeypatch.setattr(b,'GEMINI_API_KEY','test-key')
    cid=c.post('/api/conversations',json={}).json['conversation']['id']
    body=dict(content='I live in Ahmedabad',mode='normal',request_id='chat-control-city-1')
    response=c.post(f'/api/conversations/{cid}/messages/stream',json=body)
    assert response.status_code==200
    events=[json.loads(line) for line in response.data.splitlines()]
    complete=next(e['data'] for e in events if e['type']=='complete')
    assert complete['assistant_message']['action_receipt']['kind']=='memory'
    assert one(connect,'SELECT count(*) AS n FROM memories')['n']==1
    retry=c.post(f'/api/conversations/{cid}/messages/stream',json=body)
    assert retry.status_code==200
    assert one(connect,'SELECT count(*) AS n FROM memories')['n']==1
    loaded=c.get(f'/api/conversations/{cid}/messages').json['messages']
    assert loaded[-1]['action_receipt']['kind']=='memory'


def test_reminder_changes_match_exact_owned_snapshot_and_confirm_deletion(db_app):
    _,c,connect=db_app;future=datetime.now(timezone.utc)+timedelta(days=1)
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO reminders(user_id,title,note,next_run_at,recurrence,created_at) VALUES(1,'Morning walk','',%s,'daily',NOW()) RETURNING id",(future,));rid=cur.fetchone()['id']
    draft=dict(kind='reminder',title='Morning walk',text='',target_title='Morning walk',target_id=rid,expected_at=future.isoformat())
    for operation,command in [('pause','Pause my morning walk reminder'),('resume','Resume my morning walk reminder')]:
        mid,_=seed(connect,command,dict(draft,operation=operation))
        result=execute(c,mid);assert result.status_code==201,result.json
        assert one(connect,'SELECT active FROM reminders WHERE id=%s',(rid,))['active']==(operation=='resume')
    due=datetime.now(timezone.utc)-timedelta(minutes=1)
    with connect() as conn:
        with conn.cursor() as cur:cur.execute('UPDATE reminders SET next_run_at=%s WHERE id=%s',(due,rid))
    draft['expected_at']=due.isoformat()
    snoozed=datetime.now(timezone.utc)+timedelta(minutes=30)
    mid,_=seed(connect,'Snooze that reminder 30 minutes',dict(draft,operation='snooze',at=snoozed.isoformat()))
    assert execute(c,mid).status_code==201
    stale,_=seed(connect,'Pause my morning walk reminder',dict(draft,operation='pause'))
    assert execute(c,stale).status_code==400
    current=dict(draft,expected_at=snoozed.isoformat(),operation='delete')
    mid,_=seed(connect,'Delete my morning walk reminder',current)
    assert execute(c,mid).status_code==400
    mid,_=seed(connect,'Yes, delete my morning walk reminder',current)
    assert execute(c,mid).status_code==201
    assert one(connect,'SELECT count(*) AS n FROM reminders')['n']==0


def test_plan_tasks_are_atomic_and_task_completion_is_idempotent(db_app):
    _,c,connect=db_app
    items=[dict(title=f'Day {n}: Probability',text='Recall and practise',at=None) for n in (1,2,3)]
    mid,_=seed(connect,'Make a study plan for the next 3 days',dict(kind='plan',title='Probability plan',text='Three short sessions',items=items))
    assert execute(c,mid).status_code==201
    assert execute(c,mid).status_code==200
    assert one(connect,'SELECT count(*) AS n FROM tasks')['n']==3
    task=one(connect,'SELECT id,title FROM tasks ORDER BY id LIMIT 1')
    mid,_=seed(connect,'Mark '+task['title']+' as done',dict(kind='task',title=task['title'],target_title=task['title'],target_id=task['id'],operation='complete'))
    result=execute(c,mid);assert result.status_code==201,result.json
    assert one(connect,'SELECT completed FROM tasks WHERE id=%s',(task['id'],))['completed'] is True


def test_mindmap_is_saved_owned_and_respects_daily_limit(db_app):
    _,c,connect=db_app
    tree=dict(summary='Probability concepts',root=dict(label='Probability',desc='Chance',color='#b38b42',children=[dict(label='Events',desc='Sets of outcomes',color='#b38b42',children=[])]))
    for n in range(3):
        mid,_=seed(connect,'Make a mindmap of this chapter',dict(kind='mindmap',title='Probability',text='Study map',map=tree))
        response=execute(c,mid)
        assert response.status_code==(201 if n<2 else 400),response.json
        if n<2:assert response.json['resource']['root']['label']=='Probability'
    assert one(connect,'SELECT count(*) AS n FROM mindmaps')['n']==2


def test_one_request_context_does_not_change_persistent_permissions(db_app):
    _,_,connect=db_app
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO tasks(user_id,title,details,priority,created_at,updated_at) VALUES(1,'My task','','medium',NOW(),NOW())")
            text,labels=actions.workspace_context(cur,1,'How much work is left?')
            assert 'My task' in text and 'Requested tasks for this reply' in labels
            assert 'notes: not shared with chat' in text
            text,_=actions.workspace_context(cur,1,'Hello')
            assert 'My task' not in text
    assert one(connect,'SELECT count(*) AS n FROM chat_context_permissions')['n']==0


def test_memory_and_note_edits_require_current_owned_snapshot(db_app):
    _,c,connect=db_app
    for kind,table,column in [('memory','memories','label'),('note','quick_notes','title')]:
        created,_=seed(connect,'Remember a study goal' if kind=='memory' else 'Save a note',dict(kind=kind,title='Study goal',text='Old text'))
        receipt=execute(c,created).json['receipt'];rid=receipt['resource_id']
        row=one(connect,'SELECT * FROM '+table+' WHERE id=%s',(rid,))
        draft=dict(kind=kind,title='Study goal',text='Updated text',operation='edit',target_id=rid,target_title=row[column],expected_updated_at=row['updated_at'].isoformat())
        mid,_=seed(connect,'Update my memory' if kind=='memory' else 'Update my note',draft)
        result=execute(c,mid);assert result.status_code==201,result.json
        assert one(connect,'SELECT content FROM '+table+' WHERE id=%s',(rid,))['content']=='Updated text'
        mid,_=seed(connect,'Update my memory' if kind=='memory' else 'Update my note',draft)
        assert execute(c,mid).status_code==400


def test_note_permissions_never_auto_send_note_contents(db_app):
    b,c,connect=db_app
    mid,_=seed(connect,'Save this as a note',dict(kind='note',title='Private note',text='Owner-only formula'))
    assert execute(c,mid).status_code==201
    c.patch('/api/chat-context',json=dict(tasks=False,reminders=False,classroom=False,notes=True))
    assert 'Owner-only formula' not in b.load_active_memory_bundle(1,include_workspace=True,turn_content='Hello')[0]
    assert 'Owner-only formula' in b.load_active_memory_bundle(1,include_workspace=True,turn_content='Read my notes')[0]


def test_plan_failure_rolls_back_partial_tasks_and_keeps_reply(db_app,monkeypatch):
    _,_,connect=db_app
    draft=dict(kind='plan',title='Three days',text='Study',items=[dict(title='First',text='Recall'),dict(title='Second',text='Practice')])
    mid,_=seed(connect,'Make a study plan',draft)
    original=actions.apply_draft
    def fail_second(cur,uid,item,**kwargs):
        if item['title']=='Second':raise ValueError('Fixture failure')
        return original(cur,uid,item,**kwargs)
    monkeypatch.setattr(actions,'apply_draft',fail_second)
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute('SELECT id,content FROM messages WHERE id=%s',(mid,));message=cur.fetchone()
            actions.save_requested(cur,1,message,'Make a study plan')
            assert message['action_error']=='Fixture failure'
    assert one(connect,'SELECT count(*) AS n FROM tasks')['n']==0
    assert one(connect,'SELECT count(*) AS n FROM chat_action_receipts')['n']==0
    assert one(connect,'SELECT count(*) AS n FROM messages WHERE id=%s',(mid,))['n']==1


def test_referral_bonus_label_does_not_claim_a_paid_plus_subscription(db_app):
    _,c,connect=db_app
    import billing
    with connect() as conn:
        with conn.cursor() as cur:billing.grant_access(cur,1,'referral:fixture','plus',7)
    assert c.get('/api/me').json['user']['plan_label']=='Study bonus'
    with connect() as conn:
        with conn.cursor() as cur:billing.grant_access(cur,1,'payment:fixture','plus',7)
    assert c.get('/api/me').json['user']['plan_label']=='Saathi Plus'


def test_clarification_answers_execute_without_repeating_the_command(db_app,monkeypatch):
    b,c,connect=db_app
    cid=c.post('/api/conversations',json={}).json['conversation']['id']
    draft=dict(kind='plan',title='Maths: three days',text='Two hours each day',items=[dict(title=f'Day {n}',text='Maths revision') for n in (1,2,3)])
    replies=iter(['Which subject and how much time each day?','Preparing your plan. <SAATHI_ACTION>'+json.dumps(draft)+'</SAATHI_ACTION>'])
    def provider(messages,memory_context,*args,**kwargs):
        if messages[-1]['content']=='Maths, two hours each day':assert actions.ACTION_INSTRUCTIONS in memory_context
        yield next(replies)
        return dict(prompt_tokens=0,output_tokens=0,total_tokens=0)
    monkeypatch.setattr(b,'stream_gemini_reply',provider)
    for request_id,text in [('plan-clarification-1','Make a study plan for 3 days'),('plan-clarification-2','Maths, two hours each day')]:
        response=c.post(f'/api/conversations/{cid}/messages/stream',json=dict(content=text,mode='normal',request_id=request_id))
        events=[json.loads(line) for line in response.data.splitlines()]
        assert any(e['type']=='complete' for e in events),events
    assert one(connect,'SELECT count(*) AS n FROM tasks')['n']==3
    assert one(connect,'SELECT count(*) AS n FROM chat_action_receipts')['n']==1


def test_another_accounts_target_can_never_be_changed(db_app):
    _,c,connect=db_app
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO tasks(user_id,title,details,priority,created_at,updated_at) VALUES(2,'Probability revision','','medium',NOW(),NOW()) RETURNING id")
            rid=cur.fetchone()['id']
    mid,_=seed(connect,'Mark the probability revision as done',dict(kind='task',title='Probability revision',operation='complete',target_title='Probability revision',target_id=rid))
    assert execute(c,mid).status_code==400
    assert one(connect,'SELECT completed FROM tasks WHERE id=%s',(rid,))['completed'] is False
