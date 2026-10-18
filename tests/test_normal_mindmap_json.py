"""Normal maps must use the direct tool's JSON contract, not model action tags."""
import json
import pytest
import chat_actions

REQUEST='Create and save an interactive mindmap titled Audit18C Probability with three short branches: sample space; mutually exclusive events; fair die P(even)=1/2. Keep it concise.'


def probability_map():
    return dict(summary='Equally likely outcomes for a fair die.',root=dict(label='Probability',desc='Chance of an event.',children=[
        dict(label='Sample space',desc='All possible outcomes.',children=[]),
        dict(label='Mutually exclusive events',desc='Their intersection is empty.',children=[]),
        dict(label='Fair die',desc='P(even)=3/6=1/2.',children=[])]))


class Response:
    def __init__(self,raw):self.raw=raw
    def json(self):return dict(candidates=[dict(content=dict(parts=[dict(text=json.dumps(self.raw))]),finishReason='STOP')],usageMetadata=dict(promptTokenCount=10,candidatesTokenCount=20,totalTokenCount=30))
    def iter_lines(self,**kwargs):yield 'data: '+json.dumps(self.json())
    def close(self):pass


@pytest.mark.parametrize('stream',[False,True])
@pytest.mark.parametrize('file_only',[False,True])
def test_normal_map_accepts_valid_json_without_model_action_tags(monkeypatch,stream,file_only):
    import app
    monkeypatch.setattr(app,'GEMINI_API_KEY','fixture-key')
    calls=[]
    def provider(*args,**kwargs):
        calls.append((args[3],kwargs));return Response(probability_map())
    monkeypatch.setattr(app,'provider_send',provider)
    messages=[dict(role='user',content='OLD_CHAT_MARKER'),dict(role='user',content=REQUEST)]
    context='PRIVATE_CONTEXT_MARKER\n'+chat_actions.ACTION_INSTRUCTIONS
    if file_only:messages[-1]['attachments']=[dict(name='latest.png',mime_type='image/png',content=b'fixture')]
    if stream:
        gen=app.stream_gemini_reply(messages,context,file_only=file_only)
        reply=''
        while True:
            try:reply+=next(gen)
            except StopIteration as stopped:usage=stopped.value;break
    else:reply,usage=app.generate_gemini_reply(messages,context,include_usage=True,file_only=file_only)
    draft=chat_actions.proposal(reply)
    assert draft['kind']=='mindmap' and draft['title']=='Audit18C Probability'
    assert draft['map']['root']['children'][2]['desc']=='P(even)=3/6=1/2.'
    assert usage['total_tokens']==30 and len(calls)==1
    payload,kwargs=calls[0]
    assert payload['generationConfig']['responseMimeType']=='application/json'
    assert not kwargs.get('stream'), 'The JSON document uses the existing direct-tool provider protocol'
    if file_only:
        assert 'OLD_CHAT_MARKER' not in json.dumps(payload)
        assert 'PRIVATE_CONTEXT_MARKER' not in json.dumps(payload)
