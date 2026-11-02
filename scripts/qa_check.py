#!/usr/bin/env python3
"""Verify static site routes, SEO tags and internal links; invoke after build.py."""
import json, re, sys, xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import urlparse,unquote
from bs4 import BeautifulSoup
ROOT=Path(__file__).parents[1]
D=ROOT/'dist'
ROUTES=json.loads((ROOT/'docs/routes.generated.json').read_text(encoding='utf-8'))
paths={r['url'] for r in ROUTES}
errors=[]
for r in ROUTES:
    f=D / r['url'].strip('/') / 'index.html' if r['url'] != '/' else D/'index.html'
    if not f.exists():errors.append(f'Missing file {f}'); continue
    doc=BeautifulSoup(f.read_text(encoding='utf-8'),'html.parser')
    h1=doc.select('h1');heads=doc.select('head > title'); metas=doc.select('meta[name="description"]');canonical=doc.select('link[rel="canonical"]')
    if len(h1)!=1:errors.append(f'{r["url"]}: {len(h1)} h1s')
    if len(heads)!=1 or not heads[0].get_text(strip=True):errors.append(f'{r["url"]}: missing title')
    if not metas or len(metas[0].get('content',''))<40:errors.append(f'{r["url"]}: missing/short description')
    if len(canonical)!=1 or not canonical[0].get('href','').endswith(r['url']):errors.append(f'{r["url"]}: bad canonical')
    if not doc.select('meta[name="robots"]'): errors.append(f'{r["url"]}: no meta robots')
    for link in doc.select('a[href]'):
        href=link['href'].split('#',1)[0].split('?',1)[0]
        if not href or href.startswith(('https://','http://','mailto:','tel:')):continue
        if href.startswith('/') and not href.startswith('//') and href.endswith('/') and href not in paths and href!='/admin/':
            errors.append(f'{r["url"]}: broken internal href {href}')
try:
    root=ET.parse(D/'sitemap.xml').getroot(); sitemap_locs=[e.text for e in root.iter() if e.tag.endswith('loc')]
except Exception as e:errors.append(f'Sitemap malformed: {e}');sitemap_locs=[]
if len(sitemap_locs)!=sum(1 for r in ROUTES if r['index']):errors.append('Sitemap index count does not match route manifest')
if not (D/'robots.txt').exists():errors.append('robots.txt missing')
for r in ROUTES:
    f=D / r['url'].strip('/') / 'index.html' if r['url'] != '/' else D/'index.html'
    d=BeautifulSoup(f.read_text(encoding='utf-8'),'html.parser')
    robots=d.select_one('meta[name="robots"]')
    if r['index'] and 'noindex' in robots.get('content',''):errors.append('Index mismatch '+r['url'])
    if not r['index'] and 'noindex' not in robots.get('content',''):errors.append('Noindex mismatch '+r['url'])
print(f'Checked {len(ROUTES)} routes; {len(sitemap_locs)} indexable sitemap entries; {len(errors)} errors')
if errors:
    print('\n'.join(errors[:50]));sys.exit(1)
