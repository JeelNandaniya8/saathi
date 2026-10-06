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
