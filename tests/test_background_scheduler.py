from io import BytesIO
import json
import pytest
from scripts.send_background_alerts import run


class Reply(BytesIO):
    status = 200


class Opener:
    def __init__(self, results):
        self.results = iter(results)
        self.calls = []

    def open(self, req, timeout):
        self.calls.append((req, timeout))
        result = next(self.results)
        if isinstance(result, Exception):
            raise result
        return Reply(json.dumps(result).encode())


def batch(sent=0, failed=0, skipped=0):
    return dict(ok=True, sent=sent, failed=failed, skipped=skipped)


def test_drains_full_batches_then_stops_without_leaking_secret():
    opener = Opener([batch(10), batch(10), batch(3)])
    assert run('fixture', opener) == 23
    assert len(opener.calls) == 3
    for req, timeout in opener.calls:
        assert req.full_url == 'https://saathi-md5w.onrender.com/api/cron/background-alerts'
        assert req.method == 'POST' and req.get_header('X-cron-secret') == 'fixture'
        assert 0 < timeout <= 65


def test_batch_count_and_wall_time_are_bounded():
    opener = Opener([batch(10)] * 20)
    assert run('fixture', opener) == 60
    assert len(opener.calls) == 6
    opener = Opener([batch(10)] * 20)
    times = iter([0, 0, 115, 121])
    assert run('fixture', opener, lambda: next(times)) == 20
    assert [timeout for _, timeout in opener.calls] == [65, 5]


@pytest.mark.parametrize('result', [batch(), batch(skipped=10)])
def test_idle_or_contended_batch_stops(result):
    opener = Opener([result])
    assert run('fixture', opener) == 0
    assert len(opener.calls) == 1


@pytest.mark.parametrize('result', [batch(failed=1), batch(sent=11), batch(sent=True),
                                  batch(sent=10, skipped=1), {}, []])
def test_invalid_or_failed_delivery_is_not_replayed(result):
    opener = Opener([result])
    with pytest.raises(ValueError):
        run('fixture', opener)
    assert len(opener.calls) == 1


def test_ambiguous_network_failure_is_not_replayed():
    opener = Opener([OSError('fixture')])
    with pytest.raises(OSError):
        run('fixture', opener)
    assert len(opener.calls) == 1


@pytest.mark.parametrize('secret', ['', None, 'value\nheader', 'value\rheader'])
def test_invalid_secret_never_calls_dispatcher(secret):
    opener = Opener([])
    with pytest.raises(ValueError):
        run(secret, opener)
    assert not opener.calls
