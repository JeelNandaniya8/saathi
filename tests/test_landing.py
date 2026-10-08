import json
from pathlib import Path
from unittest.mock import MagicMock
import pytest
import app as backend

@pytest.fixture
def client():
    backend.app.config.update(TESTING=True, SESSION_COOKIE_SECURE=False)
    return backend.app.test_client()

@pytest.mark.parametrize('lang', ['en','gu','hi'])
def test_localized_share_metadata(client,lang):
    html=client.get('/?lang='+lang).get_data(as_text=True)
    metadata=json.loads((Path(backend.PROJECT_ROOT)/'landing-meta.json').read_text())[lang]
    assert f'lang="{lang}"' in html
    assert metadata['title'] in html
    assert metadata['description'] in html
    assert '{{' not in html
    assert '/saathi-social.png' in html

def test_waitlist_validation_and_save(client,monkeypatch):
    db=MagicMock()
    monkeypatch.setattr(backend,'get_db',lambda:db)
    monkeypatch.setattr(backend,'limited',lambda *args:None)
    for data in [[],{}, {'email':[], 'plan':'plus'}, {'email':'bad','plan':'family'}, {'email':'a@b.co','plan':'paid'}]:
        assert client.post('/api/waitlist',json=data).status_code==400
    assert not db.commit.called
    for _ in range(2):
        assert client.post('/api/waitlist',json={'email':' A@B.co ','plan':'plus','language':'gu'}).json=={'ok':True}
    args=db.cursor.return_value.__enter__.return_value.execute.call_args.args
    assert args[1]==('a@b.co','plus','gu')
    assert 'ON CONFLICT (email, plan) DO NOTHING' in args[0]
    assert db.commit.call_count==2
    assert db.close.call_count==2

def test_waitlist_failure_and_rate_limit(client,monkeypatch):
    monkeypatch.setattr(backend,'limited',lambda *args:None)
    def fail(): raise backend.psycopg2.OperationalError('private details')
    monkeypatch.setattr(backend,'get_db',fail)
    response=client.post('/api/waitlist',json={'email':'a@b.co','plan':'plus'})
    assert response.status_code==503
    assert 'private details' not in response.text
    monkeypatch.setattr(backend,'limited',lambda *args:({'error':'Please wait'},429))
    assert client.post('/api/waitlist',json={'email':'a@b.co','plan':'plus'}).status_code==429

def test_waitlist_csrf(client):
    with client.session_transaction() as session:
        session['user_id']=7
    assert client.post('/api/waitlist',json={'email':'a@b.co','plan':'plus'}).status_code==403


def test_landing_static_translation_coverage():
    from html.parser import HTMLParser
    source=Path('landing-locales.js').read_text()
    data=json.loads(source[source.index('{',source.index('const catalog=')):source.index(';const nodes=')])
    assert data['gu'].keys()==data['hi'].keys()
    class Text(HTMLParser):
        def __init__(self):super().__init__();self.skip=0;self.body=False;self.rows=set()
        def handle_starttag(self,tag,attrs):
            if tag=='body':self.body=True
            if tag in {'script','style'}:self.skip+=1
        def handle_endtag(self,tag):
            if tag in {'script','style'}:self.skip-=1
        def handle_data(self,value):
            value=value.strip()
            if self.body and not self.skip and any(c.isalpha() for c in value):self.rows.add(value)
    parser=Text();parser.feed(Path('saathi.html').read_text())
    brand={'Saathi','SAATHI','S','EN','ગુજ','हिं'}
    assert parser.rows-brand<=data['gu'].keys()
