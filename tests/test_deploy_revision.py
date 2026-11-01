"""A healthy old deploy is not verification of the intended commit."""
import json
import pytest
from scripts import smoke_test


@pytest.mark.parametrize('actual,expected,passes', [
    ('a' * 40, 'a' * 40, True),
    ('b' * 40, 'a' * 40, False),
    (None, 'a' * 40, False),
])
def test_smoke_rejects_stale_or_unidentified_deploy(monkeypatch, actual, expected, passes):
    def fetch(_base, path, _timeout):
        if path == '/api/health':
            body = {'status': 'ok', 'release': smoke_test.EXPECTED_RELEASE, 'revision': actual}
        elif path == '/api/plans':
            body = {'checkout_enabled': False}
        else:
            return (200 if path in ('/', '/privacy', '/terms', '/limitations', '/support') else 404), b'', {'X-Content-Type-Options': 'nosniff'}
        return 200, json.dumps(body).encode(), {}
    monkeypatch.setattr(smoke_test, 'fetch', fetch)
    failures = smoke_test.run('https://example.test', 1, expected_revision=expected)
    assert (not failures) is passes
    if not passes:
        assert len(failures) == 1 and 'revision=' in failures[0]
