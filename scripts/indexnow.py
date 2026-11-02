"""Publish changed URLs to IndexNow after production deployment.
Usage: INDEXNOW_KEY=... python scripts/indexnow.py https://expertteam.pro/blog/example/
The key must exist as https://expertteam.pro/{key}.txt before calling API.
Never run from preview; only after site is live and approved.
"""
import os,sys,json,urllib.request
from urllib.parse import urlparse
key=os.environ.get('INDEXNOW_KEY','')
urls=sys.argv[1:]
if not key or not urls:raise SystemExit('Set INDEXNOW_KEY and pass one or more public URLs')
host='expertteam.pro'
if not all(urlparse(u).netloc==host and urlparse(u).scheme=='https' for u in urls):raise SystemExit('Only https://expertteam.pro URLs are allowed')
data=json.dumps({'host':host,'key':key,'keyLocation':f'https://{host}/{key}.txt','urlList':urls}).encode()
req=urllib.request.Request('https://api.indexnow.org/indexnow',data=data,headers={'Content-Type':'application/json; charset=utf-8'},method='POST')
with urllib.request.urlopen(req,timeout=15) as r:print('IndexNow HTTP',r.status)
