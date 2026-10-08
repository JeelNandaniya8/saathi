"""Bounded, best-effort Classroom polling; never log credentials or response bodies."""
import json
import os
import time
import urllib.error
import urllib.request

ENDPOINT = 'https://saathi-md5w.onrender.com/api/cron/classroom'


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def run(secret, opener=None, clock=time.monotonic):
    if not isinstance(secret, str) or not secret or '\n' in secret or '\r' in secret:
        raise ValueError('Classroom scheduler secret is missing or invalid.')
    opener = opener or urllib.request.build_opener(NoRedirect())
    deadline = clock() + 420
    processed = 0
    for _ in range(8):
        remaining = deadline - clock()
        if remaining < 65:
            break
        req = urllib.request.Request(ENDPOINT, data=b'', method='POST',
            headers={'X-Cron-Secret': secret, 'Accept': 'application/json'})
        with opener.open(req, timeout=65) as response:
            if response.status != 200:
                raise ValueError('Classroom scheduler returned an unexpected status.')
            raw = response.read(8193)
        if len(raw) > 8192:
            raise ValueError('Classroom scheduler response exceeded its limit.')
        result = json.loads(raw)
        if not isinstance(result, dict) or type(result.get('processed')) is not int or result['processed'] not in (0, 1):
            raise ValueError('Classroom scheduler returned an invalid result.')
        processed += result['processed']
        if not result['processed']:
            break
    return processed


if __name__ == '__main__':
    try:
        count = run(os.environ.get('CLASSROOM_SYNC_SECRET', ''))
    except (ValueError, OSError, urllib.error.HTTPError):
        print('Classroom refresh failed. Check scheduler configuration and service availability; no response body was logged.')
        raise SystemExit(1)
    print(f'Classroom refresh completed: {count} due accounts processed. Device notifications are not part of this job.')
