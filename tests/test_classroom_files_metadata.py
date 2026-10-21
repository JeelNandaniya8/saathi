"""Synthetic Classroom file metadata: no provider file reads during sync."""
import pytest
import classroom_integration as cc

def drive(file_id='fixture_pdf',title='Practice.pdf'):
    return {'driveFile':{'driveFile':{'id':file_id,'title':title,
        'alternateLink':'https://evil.example/ignored'}}}

def test_sync_requests_and_retains_file_metadata_without_reading_contents(monkeypatch):
    class Cursor:
        def __init__(self):self.calls=[]
        def execute(self,sql,params):self.calls.append((sql,params))
    cursor=Cursor()
    monkeypatch.setattr(cc,'access_token',lambda _: 'fixture')
    def pages(token,path,key,params):
        if key=='studentSubmissions':return [{'courseWorkId':'work','state':'NEW'}]
        assert 'materials' in params['fields'], 'Classroom sync currently omits attachment metadata'
        return [{'id':'work','title':'Synthetic work','materials':[drive()]}]
    monkeypatch.setattr(cc,'list_pages',pages)
    assert cc.sync_connection(cursor,{'user_id':1,'selected_courses':['course1'],'refresh_cipher':'cipher','auto_sync_enabled':False})==1
    sql,params=next((s,p) for s,p in cursor.calls if 'INSERT INTO classroom_assignments' in s)
    assert 'file_materials' in sql
    assert params[-2].adapted==[{'id':'fixture_pdf','title':'Practice.pdf','url':'https://drive.google.com/open?id=fixture_pdf'}]
    assert params[-1]=='NEW'

def test_metadata_keeps_only_selected_drive_references_and_safe_links():
    row={'materials':[drive(),{'link':{'url':'https://example.test/not-fetched'}},drive('fixture_doc','Worksheet')]}
    assert cc.file_materials(row)==[
        {'id':'fixture_pdf','title':'Practice.pdf','url':'https://drive.google.com/open?id=fixture_pdf'},
        {'id':'fixture_doc','title':'Worksheet','url':'https://drive.google.com/open?id=fixture_doc'}]

@pytest.mark.parametrize('materials',[None,{},'bad',[None],[drive('../escape')],[drive('x','x')]*21])
def test_invalid_metadata_cannot_partially_replace_a_previous_snapshot(materials):
    with pytest.raises(cc.ProviderError):cc.file_materials({'materials':materials})

def test_old_no_materials_is_checked_empty_and_duplicates_are_one_reference():
    assert cc.file_materials({})==[]
    assert len(cc.file_materials({'materials':[drive(),drive()]}))==1

def test_invalid_file_metadata_does_not_mark_old_work_unavailable(monkeypatch):
    class Cursor:
        def execute(self,*args):pytest.fail('No snapshot writes before every reference is validated')
    monkeypatch.setattr(cc,'access_token',lambda _: 'fixture')
    def pages(token,path,key,params):
        if key=='studentSubmissions':return []
        return [{'id':'work','title':'Synthetic','materials':[drive('../invalid')]}]
    monkeypatch.setattr(cc,'list_pages',pages)
    with pytest.raises(cc.ProviderError):
        cc.sync_connection(Cursor(),{'user_id':1,'selected_courses':['course1'],'refresh_cipher':'cipher','auto_sync_enabled':False})
