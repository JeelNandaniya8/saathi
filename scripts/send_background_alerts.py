"""Drain a bounded general-alert backlog; never replay ambiguous failures."""
import json
import os
import urllib.request
import time
if __package__:
    from .sync_classroom import NoRedirect
else:
    from sync_classroom import NoRedirect


def run(secret,opener=None,clock=time.monotonic):
    if not isinstance(secret,str) or not secret or '\n' in secret or '\r' in secret:raise ValueError('Scheduler is not configured.')
    opener=opener or urllib.request.build_opener(NoRedirect())
    request=urllib.request.Request('https://saathi-md5w.onrender.com/api/cron/background-alerts',data=b'',method='POST',headers={'X-Cron-Secret':secret})
    deadline=clock()+120
    sent=0
    for _ in range(6):
        remaining=deadline-clock()
        if remaining<=0:break
        with opener.open(request,timeout=min(65,remaining)) as response:
            if response.status!=200:raise ValueError('Dispatch failed.')
            raw=response.read(8193)
        if len(raw)>8192:raise ValueError('Invalid dispatch response.')
        data=json.loads(raw)
        if not isinstance(data,dict) or data.get('ok') is not True or any(type(data.get(k)) is not int or not 0<=data[k]<=10 for k in ('sent','failed','skipped')) or sum(data[k] for k in ('sent','failed','skipped'))>10:raise ValueError('Invalid dispatch result.')
        if data['failed']:raise ValueError('Some deliveries failed; check device setup in Account.')
        sent+=data['sent']
        # A full batch may leave more work. Server-side claims prevent duplicate
        # sends across calls. Stop when idle or another dispatcher holds claims.
        if data['sent']==0 or data['sent']+data['skipped']<10:break
    return sent


if __name__=='__main__':
    try:count=run(os.environ.get('CLASSROOM_SYNC_SECRET',''))
    except (ValueError,OSError):
        print('Background dispatch failed. Check server configuration and Account delivery status. No response body was logged.')
        raise SystemExit(1)
    print(f'Push provider accepted {count} general alerts. Physical device receipt is not confirmed.')
