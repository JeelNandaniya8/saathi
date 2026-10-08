from datetime import datetime,timedelta,timezone
import pytest
import chat_actions as actions


def test_action_validation_and_clarification():
    future=(datetime.now(timezone.utc)+timedelta(days=1)).isoformat()
    assert actions.validate_action(dict(kind='reminder',title='Read chapter',at=future))['at']==future
    for at in (None,'tomorrow','2029-01-01T08:00:00','2000-01-01T08:00:00Z'):
        with pytest.raises(ValueError):actions.validate_action(dict(kind='reminder',title='Read',at=at))
    for kind,title in [('reminder','Take insulin'),('memory','મારી દવા'),('reminder','दवा लेना')]:
        with pytest.raises(ValueError):actions.validate_action(dict(kind=kind,title=title,text='saved',at=future))
    with pytest.raises(ValueError):actions.proposal('<SAATHI_ACTION>{}</SAATHI_ACTION>')
    for draft in [dict(kind='delete',title='Everything'),dict(kind=[],title='x'),dict(kind='task',title='x',priority=[]),dict(kind='task',title='x',recurrence={})]:
        with pytest.raises(ValueError):actions.validate_action(draft)


def test_context_queries_only_explicit_permissions():
    class Cursor:
        def __init__(self,permissions):self.permissions=permissions;self.queries=[]
        def execute(self,q,p):self.queries.append((q,p))
        def fetchone(self):return self.permissions if len(self.queries)==1 else {'timezone':'Asia/Kolkata'}
        def fetchall(self):return [{'title':'My own task'}]
    cur=Cursor({});text,labels=actions.workspace_context(cur,7)
    assert len(cur.queries)==2 and not labels and 'tasks: not shared' in text
    cur=Cursor({'tasks':True});text,labels=actions.workspace_context(cur,7)
    assert len(cur.queries)==3 and labels==['Shared tasks'] and 'My own task' in text
    assert all(p==(7,) for _,p in cur.queries)


def test_hindi_gujarati_names_and_no_symbols():
    import app
    for name in ['राहुल शर्मा','नील जोशी','જીલ નંદાણીયા']:assert app.validate_name(name) is None
    for name in ['J1','😀😀','\u0301\u0301','A\nB']:assert app.validate_name(name)


def test_explicit_commands_work_without_provider_and_keep_ambiguity():
    import app
    context=actions.ACTION_INSTRUCTIONS
    for text,kind,title in [('Add a task: Revise fractions. No deadline. Show the save preview.','task','Revise fractions'),('કામ ઉમેરો: ગણિતનો અભ્યાસ','task','ગણિતનો અભ્યાસ'),('नोट सेव करें: मेरा विचार','note','मेरा विचार'),('Add daily habit: Read ten pages','habit','Read ten pages')]:
        messages=[dict(role='user',content=text)]
        reply,usage=app.generate_gemini_reply(messages,context,include_usage=True)
        assert usage['local_action'] and usage['total_tokens']==0
        draft=actions.proposal(reply)
        assert draft['kind']==kind and draft['title']==title
        chunks=app.stream_gemini_reply(messages,context);assert next(chunks)==reply
        with pytest.raises(StopIteration) as stopped:next(chunks)
        assert stopped.value.value['local_action']
    for text in ['Add task: Study tomorrow','Please explain how tasks work','Add daily habit: Take insulin','Add a task: Revise at 8:00']:
        assert actions.local_reply([dict(role='user',content=text)],context) is None
    assert actions.local_reply([dict(role='user',content='Add task: Read')],'') is None
    assert actions.local_reply([dict(role='user',content='Add task: Read',attachments=[{}])],context) is None
    assert actions.local_reply([dict(role='user',content='Add task: Read')],context,file_only=True) is None
