"""Single bounded general-reminder dispatch, no medical schedules or credential logs."""
import json
import os
import urllib.request
from sync_classroom import NoRedirect


def run(secret,opener=None):
    if not isinstance(secret,str) or not secret or '\n' in secret or '\r' in secret:raise ValueError('Scheduler is not configured.')
    opener=opener or urllib.request.build_opener(NoRedirect())
    request=urllib.request.Request('https://saathi-md5w.onrender.com/api/cron/background-alerts',data=b'',method='POST',headers={'X-Cron-Secret':secret})
    with opener.open(request,timeout=65) as response:
        if response.status!=200:raise ValueError('Dispatch failed.')
        raw=response.read(8193)
    if len(raw)>8192:raise ValueError('Invalid dispatch response.')
    data=json.loads(raw)
    if not isinstance(data,dict) or data.get('ok') is not True or any(type(data.get(k)) is not int or data[k]<0 for k in ('sent','failed','skipped')):raise ValueError('Invalid dispatch result.')
    if data['failed']:raise ValueError('Some deliveries failed; check device setup in Account.')
    return data['sent']


if __name__=='__main__':
    try:count=run(os.environ.get('CLASSROOM_SYNC_SECRET',''))
    except (ValueError,OSError):
        print('Background dispatch failed. Check server configuration and Account delivery status. No response body was logged.')
        raise SystemExit(1)
    print(f'Push provider accepted {count} general alerts. Physical device receipt is not confirmed.')
