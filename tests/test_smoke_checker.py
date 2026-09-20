"""HTTP header names are case-insensitive, including behind hosting proxies."""
from email.message import Message
from io import BytesIO
from urllib.error import HTTPError
import pytest
from scripts import smoke_test


@pytest.mark.parametrize('name', ['X-Content-Type-Options', 'x-content-type-options'])
@pytest.mark.parametrize('status', [200, 404])
def test_header_lookup_is_case_insensitive_on_success_and_error(monkeypatch, name, status):
    headers = Message()
    headers[name] = 'nosniff'

    class Response(BytesIO):
        pass

    def open_fixture(request, timeout):
        if status == 404:
            raise HTTPError(request.full_url, 404, 'Not Found', headers, BytesIO(b'not found'))
        response = Response(b'ok')
        response.status = 200
        response.headers = headers
        return response

    monkeypatch.setattr(smoke_test, 'urlopen', open_fixture)
    received, _, result = smoke_test.fetch('https://example.test', '/', 1)
    assert received == status
    assert result.get('X-Content-Type-Options') == 'nosniff'
