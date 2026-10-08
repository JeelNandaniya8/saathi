"""Public HTTP timing only; no login, prompts, tokens or response bodies."""
import argparse
import json
import statistics
import time
from urllib.parse import urlparse
import requests


def measure(base, samples=5):
    parsed = urlparse(base)
    if parsed.scheme != 'https' or not parsed.netloc or parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path not in ('','/'):
        raise ValueError('Use an HTTPS origin without credentials, query or fragment.')
    if not 1 <= samples <= 20:
        raise ValueError('Use 1–20 samples.')
    rows=[]
    with requests.Session() as session:
        for path in ['/api/health', '/account', '/theme.js?v=20261008']:
            runs=[]
            for _ in range(samples):
                started=time.perf_counter()
                try:
                    response=session.get(base.rstrip('/')+path,timeout=(5,90),allow_redirects=False,headers={'Accept-Encoding':'gzip'})
                    runs.append({'ms':round((time.perf_counter()-started)*1000,1),'status':response.status_code,'server_timing':response.headers.get('Server-Timing','')})
                    response.close()
                except requests.RequestException:
                    runs.append({'ms':round((time.perf_counter()-started)*1000,1),'status':'unavailable'})
            warm=[r['ms'] for r in runs[1:] if r['status']==200]
            rows.append({'path':path,'first':runs[0],'warm_median_ms':statistics.median(warm) if warm else None,'samples':runs})
    return rows


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--base-url',required=True);parser.add_argument('--samples',type=int,default=5)
    args=parser.parse_args();print(json.dumps(measure(args.base_url,args.samples),indent=2))
