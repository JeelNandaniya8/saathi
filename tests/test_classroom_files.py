"""Provider-free checks of selected Drive bytes, limits and redirect handling."""
import pytest
import classroom_files as files

class Response:
    def __init__(self,body=b'%PDF-1.4\nSynthetic',status=200,headers=None,chunks=None):
        self.body=body;self.status_code=status;self.headers=headers or {};self.chunks=chunks;self.closed=False
    def iter_content(self,size):yield from self.chunks if self.chunks is not None else [self.body]
    def close(self):self.closed=True

def test_read_is_fixed_host_no_redirect_and_bounded(monkeypatch):
    response=Response()
    def get(url,**kwargs):
        assert url==files.DRIVE+'fixture_pdf'
        assert kwargs['allow_redirects'] is False and kwargs['stream'] is True
        assert kwargs['params']=={'alt':'media'}
        assert kwargs['headers']=={'Authorization':'Bearer short-lived-fixture'}
        return response
    monkeypatch.setattr(files.requests,'get',get)
    assert files.bounded_download('short-lived-fixture','fixture_pdf','application/pdf')==(response.body,'application/pdf')
    assert response.closed

@pytest.mark.parametrize('mime',sorted(files.NATIVE))
def test_google_documents_export_pdf_without_fetching_the_original_url(monkeypatch,mime):
    def get(url,**kwargs):
        assert url==files.DRIVE+'fixture_doc/export' and kwargs['params']=={'mimeType':'application/pdf'}
        return Response()
    monkeypatch.setattr(files.requests,'get',get)
    assert files.bounded_download('fixture','fixture_doc',mime)[1]=='application/pdf'

@pytest.mark.parametrize('response,error',[
    (Response(status=302),'file_provider'),(Response(status=403),'file_permission'),
    (Response(headers={'Content-Length':'5242881'}),'file_size'),
    (Response(chunks=[b'%PDF-',b'x'*files.MAX_BYTES]),'file_size'),
    (Response(body=b''),'file_empty'),(Response(body=b'<script>not a PDF</script>'),'file_type')])
def test_failure_never_returns_partial_or_mislabeled_content(monkeypatch,response,error):
    monkeypatch.setattr(files.requests,'get',lambda *a,**kw:response)
    with pytest.raises(ValueError,match=error):files.bounded_download('fixture','fixture_pdf','application/pdf')
    assert response.closed

@pytest.mark.parametrize('fid,mime',[('../x','application/pdf'),('https://evil.example','application/pdf'),('x','text/html'),('x','application/zip'),('x',[]),('x',None)])
def test_invalid_ids_and_unsupported_types_never_make_a_network_request(monkeypatch,fid,mime):
    monkeypatch.setattr(files.requests,'get',lambda *a,**kw:pytest.fail('No provider call allowed'))
    with pytest.raises(ValueError):files.bounded_download('fixture',fid,mime)

def test_exact_metadata_changes_invalidate_grant():
    row={'id':1,'course_id':'c','external_id':'w','file_materials':[{'id':'f','title':'Original'}]}
    before=files.source_hash(row)
    assert files.source_hash({**row,'version':99})==before
    row['file_materials'][0]['title']='Changed'
    assert files.source_hash(row)!=before
