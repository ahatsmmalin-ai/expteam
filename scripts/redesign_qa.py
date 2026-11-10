#!/usr/bin/env python3
"""Static QA for the 2026 Expert Team redesign; run after `python build.py`."""
from __future__ import annotations
import json,re,sys
from pathlib import Path
from urllib.parse import urlparse, unquote
from bs4 import BeautifulSoup
import yaml
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'dist'
fail=[]

def ensure(condition,message):
 if not condition:fail.append(message)

pages=list(OUT.rglob('*.html'))
ensure(len(pages)>=40,f'Expected >=40 HTML files, found {len(pages)}')
ensure((OUT/'assets/style.css').is_file(),'Missing CSS')
ensure((OUT/'assets/site.js').is_file(),'Missing JS')
ensure((OUT/'robots.txt').is_file(),'Missing robots')
ensure((OUT/'_redirects').is_file(),'Missing redirects')
ensure(len(list((OUT/'assets/brand').glob('ExpertTeam_Asset_*.webp')))==39,'Not all 39 graphic assets found')
for a in (OUT/'assets/brand').glob('*.webp'): ensure(a.stat().st_size>500,'Empty brand asset: '+a.name)
ensure(len(list((ROOT/'content/posts').glob('*.md')))==10,'10 preserved articles expected')
config=yaml.safe_load((OUT/'admin/config.yml').read_text('utf8'))
ensure(config['backend']['name']=='github','Decap backend mismatch')
ensure(config.get('cms_auth_ready') is False,'CMS auth falsely marked ready')
for file in pages:
 soup=BeautifulSoup(file.read_text('utf8'),'html.parser')
 if file.name=='index.html' and '/admin/' not in str(file) and '/uslugi/' not in str(file) and '/ceny/' not in str(file):
  title=soup.find('title')
  ensure(title and title.get_text(strip=True),f'Missing title {file}')
  ensure(soup.find('meta',attrs={'name':'description'}) is not None,f'Missing description {file}')
  ensure(soup.find('h1') is not None,f'Missing H1 {file}')
  for img in soup.find_all('img'):
   src=img.get('src','')
   ensure(bool(img.get('alt') is not None),f'Missing image alt {file}:{src}')
   if src.startswith('/'):
    ensure((OUT/src.lstrip('/')).is_file(),f'Broken image {file.relative_to(OUT)} -> {src}')
  for a in soup.find_all('a'):
   href=a.get('href',''); target=a.get('target')
   if href.startswith('/'):
    path=urlparse(href).path;resolved=OUT/path.lstrip('/')
    valid=(resolved/'index.html').exists() or resolved.is_file() or (resolved==OUT)
    ensure(valid,f'Broken internal href {file.relative_to(OUT)} -> {href}')
    if target=='_blank' and href.endswith('/'):
     fail.append(f'Internal page opens in new tab: {file.relative_to(OUT)} -> {href}')
   if href.startswith('https://') and target=='_blank':ensure('noopener' in a.get('rel',[]),f'External new tab without noopener {file}:{href}')
  # Staging build must never let Google index pages.
  if 'EXPERTTEAM_GO_LIVE' not in __import__('os').environ:
   m=soup.find('meta',attrs={'name':'robots'})
   ensure(m and 'noindex' in m.get('content',''),f'Staging indexing not blocked {file.relative_to(OUT)}')
home=BeautifulSoup((OUT/'index.html').read_text('utf8'),'html.parser')
sections=['.hero','.pain-section','.scope-section','.pricing-section','.product-section-light','.product-section-alt','.cases-section','.letters-section','.process-section','.team-section','.faq-section','.blog-preview','.leadmag-section','.footer-offer','.site-footer']
positions=[]
for sel in sections:
 node=home.select_one(sel)
 ensure(node is not None,f'Home missing section {sel}')
 if node:positions.append(str(node.sourceline))
ensure(len(home.select('.home-case-grid .case-card'))==8,'Homepage should have 2x4 case grid')
ensure(len(home.select('.letters-grid .letter-placeholder'))==6,'6 original letters placeholders expected')
ensure(len(home.select('.team-grid .team-card'))==3,'3 team roles expected')
ensure((OUT/'kalkulyator-marketologa/index.html').is_file(),'Calculator page absent')
ensure((OUT/'marketingovyj-plan/index.html').is_file(),'Lead magnet page absent')
ensure('Disallow: /' in (OUT/'robots.txt').read_text('utf8'),'Staging robots must disallow')
ensure('35 000' in (OUT/'index.html').read_text('utf8'),'Primary price missing')
ensure('150 000' in (OUT/'index.html').read_text('utf8'),'150k comparison scenario missing')
ensure('СЦЕНАРИЙ' in (OUT/'resheniya/reaktivaciya-bazy/index.html').read_text('utf8'),'Reactivation scenario disclosure missing')
if fail:
 print('REDESIGN QA FAILED:',len(fail))
 for f in fail[:80]:print(' -',f)
 sys.exit(1)
print('REDESIGN QA OK:',len(pages),'HTML files, 39 visual assets, 10 articles, 8 home case cards, 6 letters, CMS schema, noindex')
