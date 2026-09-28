"""Performance changes must preserve privacy, session checks and response bodies."""
import gzip
import importlib
import pytest

@pytest.fixture
def backend(monkeypatch):
    monkeypatch.delenv('DATABASE_URL', raising=False)
    module = importlib.import_module('app')
    module.app.config.update(TESTING=True, SESSION_COOKIE_SECURE=False)
    return module

def test_public_asset_compression_and_revalidation(backend):
    client = backend.app.test_client()
    plain = client.get('/experience.css?v=test', headers={'Accept-Encoding': 'gzip;q=0'})
    packed = client.get('/experience.css?v=test', headers={'Accept-Encoding': 'gzip'})
    assert packed.headers['Content-Encoding'] == 'gzip'
    assert gzip.decompress(packed.data) == plain.data
    assert len(packed.data) < len(plain.data) / 2
    assert 'Accept-Encoding' in packed.headers['Vary']
    assert 'max-age=3600' in packed.headers['Cache-Control']
    assert 'app;dur=' in packed.headers['Server-Timing']
    assert 'Content-Encoding' not in plain.headers
    cached = client.get('/experience.css?v=test', headers={'Accept-Encoding': 'gzip', 'If-None-Match': packed.headers['ETag']})
    assert cached.status_code == 304

def test_private_data_and_service_worker_are_not_compressed_or_cached(backend):
    client = backend.app.test_client()
    for path in ['/api/me', '/account', '/service-worker.js']:
        response = client.get(path, headers={'Accept-Encoding': 'gzip'})
        assert 'Content-Encoding' not in response.headers
        assert 'max-age=3600' not in response.headers.get('Cache-Control', '')

def test_user_context_is_reused_only_in_same_authenticated_request(backend, monkeypatch):
    class Cursor:
        def __init__(self): self.calls = []
        def execute(self, sql, args): self.calls.append((sql, args))
        def fetchone(self): return {'session_version': 3, 'plan': 'free', 'plan_status': None, 'subscription_end_at': None, 'language': 'gu'}
        def close(self): pass
    cur = Cursor()
    class Conn:
        def cursor(self): return cur
        def close(self): pass
    monkeypatch.setattr(backend, 'get_db', lambda: Conn())
    with backend.app.test_request_context('/api/me'):
        backend.session.update(user_id=7, session_version=3)
        assert backend.require_user_id() == 7
        assert backend.active_plan_entitlement(cur, 7)[0] == 'free'
        assert backend.load_user_language(7, cur) == 'gu'
        assert len(cur.calls) == 1
    with backend.app.test_request_context('/api/me'):
        backend.session.update(user_id=7, session_version=2)
        assert backend.require_user_id() is None
        assert len(cur.calls) == 2
