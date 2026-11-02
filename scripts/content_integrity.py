#!/usr/bin/env python3
"""Validate CMS-managed content before building; no third-party account needed."""
from __future__ import annotations
from pathlib import Path
from datetime import date
import json, re, sys
import yaml
ROOT = Path(__file__).resolve().parents[1]
D = ROOT / 'content'
errors=[]
services={}

def err(path,msg):errors.append(f'{path}: {msg}')

def data_file(path):
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except Exception as ex:
        err(path.relative_to(ROOT),f'JSON invalid: {ex}')
        return None

def good_slug(x):return isinstance(x,str) and re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*',x)

def valid_date(x):
    try:date.fromisoformat(str(x));return True
    except (TypeError,ValueError):return False

site=data_file(D/'site.json')
if site:
    for k in ('brand','domain','hero_title','home_h1','email','telegram','form_title'):
        if not site.get(k):err('content/site.json',f'{k} is empty')
    if not str(site.get('domain','')).startswith('https://'):err('content/site.json','domain must be https')

for f in sorted((D/'services').glob('*.json')):
    d=data_file(f)
    if not d:continue
    slug=d.get('slug')
    if not good_slug(slug):err(f.name,'invalid service slug')
    elif f.stem!=slug:err(f.name,'slug must match filename')
    elif slug in services:err(f.name,'duplicate slug')
    services[slug]=d
    for key in ('name','code','title','description','h1','lead','price','keyword','short'):
        if not d.get(key):err(f.name,f'empty {key}')
    for key in ('includes','segments','steps','faqs','related'):
        if not isinstance(d.get(key),list) or not d[key]:err(f.name,f'{key} must be nonempty list')
if len(services)!=7:err('services',f'expected 7, got {len(services)}')
for slug,s in services.items():
    for related in s.get('related',[]):
        if related not in services:err(slug,f'unknown related service {related}')
    guide=data_file(D/'guides'/f'{slug}.json')
    if guide and (not isinstance(guide.get('sections'),list) or len(guide['sections'])<2):err(slug,'needs SEO guide sections')

for f in sorted((D/'cases').glob('*.json')):
    d=data_file(f)
    if d:
        if not good_slug(d.get('slug')) or d['slug']!=f.stem:err(f.name,'case slug mismatch')
        if d.get('related') not in services:err(f.name,'invalid related service')
        if not d.get('name') or not d.get('metric'):err(f.name,'missing name/metric')
        # Public case permission is checked by a human; never infer approval from a headline.
        if d.get('client_approved') is True and not d.get('evidence'):
            err(f.name,'case is approved but evidence is empty')

article_count=0; published_count=0
for f in sorted((D/'posts').glob('*.md')):
    text=f.read_text(encoding='utf-8')
    m=re.match(r'^---\s*\n(.*?)\n---\s*\n(.*)$',text,re.S)
    if not m:err(f.name,'missing frontmatter');continue
    try:meta=yaml.safe_load(m.group(1))
    except yaml.YAMLError as e:err(f.name,f'YAML invalid: {e}');continue
    if not isinstance(meta,dict):err(f.name,'metadata must be mapping');continue
    article_count+=1
    if not good_slug(meta.get('slug')) or meta['slug']!=f.stem:err(f.name,'article slug mismatch')
    if meta.get('category') not in ('marketing','lidogeneraciya','reklama','sajty','crm','seo'):err(f.name,'invalid category')
    for k in ('title','description','author','keyword'):
        if not meta.get(k):err(f.name,f'missing {k}')
    for k in ('date','modified'):
        if not valid_date(meta.get(k)):err(f.name,f'invalid {k}')
    related=meta.get('related_services',[])
    if not isinstance(related,list) or len(set(related))<2 or any(x not in services for x in related):
        err(f.name,'requires two distinct existing related_services')
    if meta.get('published') is True:
        published_count+=1
        if len(m.group(2).split())<1500:err(f.name,'published article has fewer than 1500 body words')
        if meta.get('author','').startswith('Редакция ') or not meta.get('author_bio'):
            err(f.name,'published article lacks confirmed named author/bio')
        if not meta.get('cover_image') or not meta.get('image_alt'):
            err(f.name,'published article lacks cover image/alt')
        if meta.get('editorial_status') != 'approved' or not meta.get('reviewed_by') or not valid_date(meta.get('reviewed_on')):
            err(f.name,'published article requires approved editorial_status, reviewer and valid review date')
        if not meta.get('source_notes'):
            err(f.name,'published article requires editorial source/fact-check notes')

# Independent CMS pages: ensure safe routes and publication approval before build.
page_routes=set()
for f in sorted((D/'pages').glob('*.md')):
    text=f.read_text(encoding='utf-8');m=re.match(r'^---\s*\n(.*?)\n---\s*\n(.*)$',text,re.S)
    if not m:err(f.name,'new page: missing frontmatter');continue
    try:meta=yaml.safe_load(m.group(1))
    except yaml.YAMLError as e:err(f.name,f'new page: invalid YAML {e}');continue
    if not isinstance(meta,dict):err(f.name,'new page: metadata must be mapping');continue
    if not good_slug(meta.get('slug')) or meta.get('slug')!=f.stem:err(f.name,'new page: invalid or mismatched slug')
    section=meta.get('section')
    if section not in ('stranicy','resheniya','materialy'):err(f.name,'new page: disallowed section/URL')
    route=f'/{section}/{meta.get("slug")}/'
    if route in page_routes:err(f.name,'new page: duplicated URL')
    page_routes.add(route)
    for k in ('title','seo_title','description','h1','intro'):
        if not isinstance(meta.get(k),str) or not meta[k].strip():err(f.name,f'new page: missing {k}')
    if len(m.group(2).split())<25:err(f.name,'new page: content too short to review')
    related=meta.get('related_services',[])
    if not isinstance(related,list) or any(x not in services for x in related):err(f.name,'new page: invalid related services')
    if meta.get('cover_image') and not meta.get('image_alt'):err(f.name,'new page: image requires alt')
    if meta.get('published') is True:
        if meta.get('editorial_status')!='approved' or not meta.get('reviewed_by') or not valid_date(meta.get('reviewed_on')):
            err(f.name,'new page: publication requires an approved editorial review')
        if not meta.get('source_notes'):err(f.name,'new page: publication requires source/fact check notes')

seo=data_file(D/'seo.json')
if seo:
    for k in ('home','cases','about','prices','contacts','blog'):
        block=seo.get(k)
        if not isinstance(block,dict):err('seo.json',f'missing {k}');continue
        if not block.get('title') or len(block.get('description',''))<40:
            err('seo.json',f'empty/short SEO fields for {k}')

prices=data_file(D/'prices.json')
if prices:
    packages=prices.get('packages',[])
    if not isinstance(packages,list) or len(packages)!=3:err('prices.json','must have 3 packages')
    for p in packages:
        if not p.get('price') or not p.get('name'):err('prices.json','missing package name/price')

print(f'CMS content integrity: {len(services)} services, {article_count} article drafts ({published_count} published), {len(errors)} errors')
for e in errors:print('ERROR',e)
if errors:sys.exit(1)
