from io import BytesIO
import json
import urllib.error
import pytest
from scripts.sync_classroom import run, ENDPOINT, NoRedirect


class Reply(BytesIO):
    status = 200


class Opener:
    def __init__(self, results):
        self.results = iter(results)
        self.calls = []
    def open(self, req, timeout):
        self.calls.append((req, timeout))
        return Reply(json.dumps(next(self.results)).encode())


def test_polling_stops_when_idle_and_keeps_secret_out_of_url():
    opener = Opener([{'processed': 1, 'ok': False}, {'processed': 1, 'ok': True}, {'processed': 0}])
    assert run('fixture-secret', opener) == 2
    assert len(opener.calls) == 3
    for req, timeout in opener.calls:
        assert req.full_url == ENDPOINT and req.method == 'POST' and timeout == 65
        assert req.get_header('X-cron-secret') == 'fixture-secret'


def test_polling_is_bounded_and_does_not_follow_redirects():
    opener = Opener([{'processed': 1}] * 20)
    assert run('fixture-secret', opener) == 8
    assert NoRedirect().redirect_request(None, None, 302, '', {}, 'https://example.test') is None
    opener = Opener([{'processed': 1}] * 20)
    times = iter([0, 0, 400])
    assert run('fixture-secret', opener, lambda: next(times)) == 1


@pytest.mark.parametrize('result', [{}, {'processed': True}, {'processed': -1}, {'processed': 2}, []])
def test_invalid_server_result_fails_closed(result):
    with pytest.raises(ValueError):
        run('fixture-secret', Opener([result]))


def test_failure_is_not_replayed():
    class Broken:
        calls = 0
        def open(self, req, timeout):
            self.calls += 1
            raise OSError('fixture')
    opener = Broken()
    with pytest.raises(OSError):run('fixture-secret', opener)
    assert opener.calls == 1


@pytest.mark.parametrize('secret', ['', None, 'value\nheader', 'value\rheader'])
def test_invalid_secret_never_sends_request(secret):
    with pytest.raises(ValueError):run(secret)


def test_scheduler_updates_trigger_only_main_and_keep_activation_gate():
    from pathlib import Path
    workflow=(Path(__file__).parents[1]/'.github/workflows/classroom-sync.yml').read_text()
    assert 'push:\n    branches: [main]' in workflow
    assert 'scripts/send_background_alerts.py' in workflow
    assert "github.ref == 'refs/heads/main'" in workflow
    assert "vars.CLASSROOM_SYNC_ENABLED == 'true'" in workflow
    assert "secrets.CLASSROOM_SYNC_SECRET" in workflow
    assert 'pull_request' not in workflow
