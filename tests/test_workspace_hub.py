from datetime import datetime, timedelta, timezone
import pytest
from workspace_hub import focus_elapsed, search_pattern


def test_focus_uses_elapsed_server_time_and_never_exceeds_duration():
    now = datetime(2026, 9, 19, tzinfo=timezone.utc)
    row = dict(status='running', elapsed_seconds=60, duration_seconds=1500,
               last_started_at=now-timedelta(seconds=85))
    assert focus_elapsed(row, now) == 145
    assert focus_elapsed(row, now+timedelta(hours=3)) == 1500
    row['status'] = 'paused'
    assert focus_elapsed(row, now+timedelta(hours=3)) == 60
    row.update(status='running', last_started_at=now+timedelta(seconds=20))
    assert focus_elapsed(row, now) == 60


def test_search_treats_wildcards_as_literal_text():
    assert search_pattern('  50%_off\\sale  ') == '%50\\%\\_off\\\\sale%'
    assert search_pattern('ગુજરાતી') == '%ગુજરાતી%'
    for value in ('', 'a', '  ', 'a'*101):
        with pytest.raises(ValueError):
            search_pattern(value)
