#!/usr/bin/env python3
"""Expert Team CMS v1: builds the site from editable JSON + Markdown.

Cloudflare Pages: pip install -r requirements.txt && python pages_build.py
Output: dist/. The original designs live in templates/, content in content/.
No change to commercial copy unless a CMS content file changes.
"""
from pathlib import Path
import json, re, html, shutil, os, posixpath
from urllib.parse import urlparse

ROOT=Path(__file__).resolve().parent
DIST=ROOT/'dist'
TEMPLATES=ROOT/'templates'
CONTENT=ROOT/'content'
MANIFEST=json.loads((ROOT/'cms_pages_manifest.json').read_text('utf-8'))
VALID_LINK=re.compile(r'^\[\[ET(G?):([A-Za-z0-9_]+)\]\]$')
LINK_PATTERN=re.compile(r'\[\[ET(G?):([A-Za-z0-9_]+)\]\]')

def load_json(path):return json.loads(path.read_text('utf-8'))

def nested_text(page):
 result={}
 for section in page.get('sections',[]):
  for item in section.get('items',[]):
   if item['id'] in result:raise ValueError(f"duplicate text key {item['id']} in {page['name']}")
   result[item['id']]=str(item.get('value',''))
 return result

def render_text(template, data, global_data):
 d={'meta_title':str(data.get('meta_title','')),'meta_description':str(data.get('meta_description',''))}
 d.update(nested_text(data))
 def sub(m):
  global_flag,key=m.group(1),m.group(2)
  source=global_data if global_flag else d
  if key not in source:raise ValueError(f'Undefined CMS variable: {m.group(0)}')
  return html.escape(source[key],quote=True)
 return LINK_PATTERN.sub(sub,template)

def render_visual_text(template, page, global_data):
 """Render editor-only preview with stable identifiers for actual visible text fragments.
 This is not the published HTML. No scripts are enabled in the sandboxed iframe.
 """
 from bs4 import BeautifulSoup, NavigableString
 data={'meta_title':str(page.get('meta_title','')),
       'meta_description':str(page.get('meta_description',''))}
 data.update(nested_text(page))
 soup=BeautifulSoup(template,'html.parser')
 for node in list(soup.find_all(string=True)):
  if node.parent and node.parent.name in ('script','style','noscript'):
   continue
  raw=str(node)
  found=list(LINK_PATTERN.finditer(raw))
  if not found: continue
  bits=[];pos=0
  for m in found:
   if m.start()>pos:bits.append(NavigableString(raw[pos:m.start()]))
   scope='global' if m.group(1) else 'page'
   key=m.group(2)
   source=global_data if scope=='global' else data
   if key not in source:raise ValueError(f'Undefined visual editor token {scope}:{key}')
   if key.startswith('meta_') or node.parent.name in ('title',):
    bits.append(NavigableString(source[key]))
   else:
    marker=soup.new_tag('span')
    marker['data-et-key']=key
    marker['data-et-scope']=scope
    marker['class']='et-visual-fragment'
    marker.string=source[key]
    bits.append(marker)
   pos=m.end()
  if pos<len(raw):bits.append(NavigableString(raw[pos:]))
  node.replace_with(*bits)
 # Attribute placeholders (meta description, aria-label etc) must be rendered too.
 return LINK_PATTERN.sub(lambda m:html.escape((global_data if m.group(1) else data)[m.group(2)],quote=True),str(soup))

def normalize_asset(path, output):
 if not path: return ''
 url=urlparse(path)
 if url.scheme or path.startswith('//') or path.startswith('data:'):
  return path
 path=path.split('#')[0].split('?')[0].lstrip('/')
 if not path.startswith('assets/uploads/'):
  return ''
 src=ROOT/path
 if not src.is_file():
  print(f'WARNING: image not found: {path}')
  return ''
 depth=len(output.relative_to(DIST).parts)-1
 return '../'*depth+path

def apply_media(html_text, output, media):
 # Optional uploads, never invent images and never change main styling without file.
 if not any(media.get(k) for k in ('logo','team','letters','case_images','case_screenshots','plan_preview','report_preview')):return html_text
 from bs4 import BeautifulSoup
 soup=BeautifulSoup(html_text,'html.parser')
 logo=normalize_asset(media.get('logo',''), output)
 if logo:
  for mark in soup.select('.wordmark'):
   mark.clear()
   tag=soup.new_tag('img',src=logo,alt='Expert Team',width='175',height='58')
   tag['class']='et-cms-logo'
   mark.append(tag)
 team=media.get('team',[])
 for i,card in enumerate(soup.select('.team-grid .team-card')):
  if i>=len(team):break
  obj=team[i]
  photo=normalize_asset(obj.get('photo',''),output)
  if photo:
   image=card.select_one('img.team-icon')
   if image:
    image['src']=photo;image['alt']=obj.get('name') or obj.get('role') or 'Участник команды'
    image['class']='team-icon et-cms-team-photo'
  name=obj.get('name','').strip()
  if name:
   h=card.select_one('h3');
   if h:
    role=h.get_text(' ',strip=True)
    h.string=name
    line=soup.new_tag('p');line['class']='et-cms-team-role';line.string=role
    h.insert_after(line)
 letters=media.get('letters',[])
 for i,card in enumerate(soup.select('.letters-grid .letter-placeholder')):
  if i>=len(letters):break
  obj=letters[i]
  if not obj.get('approved',False):continue
  photo=normalize_asset(obj.get('scan',''),output)
  if not photo:continue
  card['class']=['letter-placeholder','v4-letter-brand','et-cms-real-letter']
  card.clear()
  a=soup.new_tag('a',href=photo,target='_blank',rel='noopener noreferrer')
  img=soup.new_tag('img',src=photo,alt=obj.get('alt') or ('Благодарственное письмо — '+obj.get('company','клиент')),loading='lazy')
  a.append(img)
  t=soup.new_tag('span');t.string=obj.get('company','Благодарственное письмо');a.append(t)
  card.append(a)
 for card in soup.select('a.case-card'):
  href=card.get('href','')
  slug=href.split('/')[-2] if '/' in href else ''
  src=normalize_asset(media.get('case_images',{}).get(slug,''),output)
  if src:
   img=card.select_one('.case-card-image img')
   if img: img['src']=src;img['alt']='Иллюстрация кейса '+slug;img['class']='case-asset et-cms-case-cover'
 # Case detail: approved original screenshots, only uploaded image paths from repo.
  # The collection list is empty until the company supplies originals.
 plan_image=normalize_asset(media.get('plan_preview',''),output)
 if plan_image:
  for preview in soup.select('.et-lm-preview'):
   preview.clear()
   img=soup.new_tag('img',src=plan_image,alt='Пример маркетингового плана',loading='lazy')
   img['class']='et-cms-plan-preview';preview.append(img)
 report_image=normalize_asset(media.get('report_preview',''),output)
 if report_image:
  preview=soup.select_one('.report-section .report-table')
  if preview:
   preview.clear()
   img=soup.new_tag('img',src=report_image,alt='Пример рабочего отчёта и таблицы',loading='lazy')
   img['class']='et-cms-report-preview';preview.append(img)
 for case_slug, photos in media.get('case_screenshots',{}).items():
  if f'/kejsy/{case_slug}/' not in '/'+output.relative_to(DIST).as_posix():
   continue
  body=soup.select_one('main .case-story')
  if not body:continue
  for i,raw in enumerate(photos):
   path=normalize_asset(raw,output)
   if not path:continue
   fig=soup.new_tag('figure');fig['class']='et-cms-case-screenshot'
   img=soup.new_tag('img',src=path,alt=f'Подтверждающий материал кейса {case_slug} — {i+1}',loading='lazy')
   fig.append(img);body.append(fig)
 return str(soup)

def apply_navigation(html_text, output, nav):
 links=nav.get('links',[])
 if not links:return html_text
 from bs4 import BeautifulSoup
 soup=BeautifulSoup(html_text,'html.parser')
 depth=len(output.relative_to(DIST).parts)-1
 prefix='../'*depth
 for item in links:
  title=str(item.get('title','')).strip()
  route=str(item.get('path','')).strip().lstrip('/')
  if not title or not route or '..' in route.split('/') or ':' in route or route.startswith('//'):
   continue
  target=ROOT/'templates'/route
  parts=route.split('/')
  new_page_slug=parts[1] if len(parts)>1 else ''
  if not (target.is_file() or (new_page_slug and (CONTENT/'cms_new_pages'/(new_page_slug+'.md')).is_file())):
   # Dynamic posts are allowed too; route will be validated by the generated file after build.
   if not route.startswith(('stranicy/','blog/')):continue
  if not route.endswith('.html') and not route.endswith('/'):
   route+='/index.html'
  for css in ('.top-nav','.mobile-nav'):
   container=soup.select_one(css)
   if not container:continue
   a=soup.new_tag('a',href=prefix+route);a.string=title
   # Insert before contacts for consistency.
   last=container.select_one('a[href*="kontakty/"]')
   if last:last.insert_before(a)
   else:container.append(a)
 return str(soup)

def apply_seo_meta(html_text, page):
 from bs4 import BeautifulSoup
 soup=BeautifulSoup(html_text,'html.parser')
 for prop,field in (('og:title','meta_title'),('og:description','meta_description')):
  meta=soup.select_one('meta[property="'+prop+'"]')
  if meta and page.get(field):meta['content']=str(page[field])
 return str(soup)

def apply_contact_links(html_text, contacts):
 email=str(contacts.get('email') or '').strip()
 telegram=str(contacts.get('telegram') or '').strip()
 phone=str(contacts.get('phone') or '').strip()
 if not (email or telegram or phone):return html_text
 from bs4 import BeautifulSoup
 soup=BeautifulSoup(html_text,'html.parser')
 for link in soup.select('a[href]'):
  href=link.get('href','')
  if email and href.startswith('mailto:'):
   link['href']='mailto:'+email
   if '@' in link.get_text(' ',strip=True):
    for node in list(link.strings):
     if '@' in str(node):node.replace_with(re.sub(r'[A-Za-z0-9_.+%-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}',email,str(node)))
  elif telegram.startswith('https://t.me/') and href.startswith('https://t.me/'):
   link['href']=telegram
  elif phone and href.startswith('tel:'):
   link['href']='tel:'+re.sub(r'[^+0-9]','',phone)
 return str(soup)

def write_articles():
 import yaml,mistune
 posts=CONTENT/'cms_posts'
 posts.mkdir(exist_ok=True)
 added=[]
 for path in sorted(posts.glob('*.md')):
  text=path.read_text('utf-8')
  if not text.startswith('---\n'):
   raise ValueError(f'{path.name}: expected YAML front matter')
  head,sep,body=text[4:].partition('\n---\n')
  if not sep: raise ValueError(f'{path.name}: missing closing front matter')
  meta=yaml.safe_load(head) or {}
  slug=meta.get('slug') or path.stem
  if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*',slug):raise ValueError(f'Bad slug {slug!r} in {path}')
  if meta.get('published') is False:continue
  title=str(meta.get('title') or '').strip()
  if not title or not body.strip():continue
  output=DIST/'blog'/slug/'index.html'
  if output.exists():raise ValueError('New article conflicts with existing page: '+slug)
  sample=DIST/'blog/pochemu-reklama-ne-rabotaet/index.html'
  from bs4 import BeautifulSoup
  soup=BeautifulSoup(sample.read_text('utf-8'),'html.parser')
  soup.title.string=title+' — Expert Team'
  for sel,value in [('meta[property="og:title"]',title+' — Expert Team'),('meta[property="og:description"]',str(meta.get('description') or title)),('meta[property="og:url"]','https://expteam-staging.pages.dev/blog/'+slug+'/'),('link[rel="canonical"]','https://expteam-staging.pages.dev/blog/'+slug+'/')]:
   el=soup.select_one(sel)
   if el:el['href' if el.name=='link' else 'content']=value
  crumbs=soup.select('.breadcrumbs > span')
  if crumbs:crumbs[-1].string=title
  d=soup.find('meta',attrs={'name':'description'})
  if d:d['content']=str(meta.get('description') or title)
  h=soup.find('h1')
  if h:h.string=title
  prose=soup.select_one('.article-body-section .prose')
  if prose:
   prose.clear()
   image=normalize_asset(str(meta.get('cover_image','')), output)
   if image:
    fig=soup.new_tag('figure');img=soup.new_tag('img',src=image,alt=str(meta.get('image_alt') or title),loading='lazy');fig.append(img);prose.append(fig)
   body_html=mistune.create_markdown(plugins=['table','strikethrough'])(body)
   fragment=BeautifulSoup(body_html,'html.parser')
   for child in list(fragment.contents):prose.append(child)
  # prevent inherited unrelated article TOC and metadata from misinforming visitors
  sidebar=soup.select_one('.article-sidebar')
  if sidebar:sidebar.decompose()
  soup.body['class']=list(set(soup.body.get('class',[])+['et-cms-added-article']))
  # Old sidebar anchor labels refer to a different article; remove them rather than mislead.
  for anchor in soup.select('a[href^="#section-"]'):
   anchor.decompose()
  author=soup.select_one('.article-author')
  if author:author.string=str(meta.get('author') or 'Редакция Expert Team')
  output.parent.mkdir(parents=True,exist_ok=True)
  output.write_text(str(soup),'utf-8')
  added.append({'slug':slug,'title':title,'description':str(meta.get('description') or ''),'category':str(meta.get('category') or 'Маркетинг')})
 if added:
  catalog=DIST/'blog/index.html'
  from bs4 import BeautifulSoup
  soup=BeautifulSoup(catalog.read_text('utf-8'),'html.parser')
  grid=soup.select_one('.article-grid')
  for post in added:
   a=soup.new_tag('a',href=post['slug']+'/index.html');a['class']='article-card'
   visual=soup.new_tag('div');visual['class']='article-visual';badge=soup.new_tag('span');badge.string=post['category'];visual.append(badge);a.append(visual)
   inner=soup.new_tag('div');inner['class']='article-card-content';h=soup.new_tag('h3');h.string=post['title'];inner.append(h);p=soup.new_tag('p');p.string=post['description'];inner.append(p);a.append(inner)
   if grid:grid.append(a)
  catalog.write_text(str(soup),'utf-8')
 return len(added)

def write_new_pages():
 import yaml,mistune
 from bs4 import BeautifulSoup
 source=CONTENT/'cms_new_pages'
 source.mkdir(exist_ok=True)
 count=0
 for path in sorted(source.glob('*.md')):
  raw=path.read_text('utf-8')
  if not raw.startswith('---\n'):raise ValueError(f'Bad front matter in {path.name}')
  front,sep,body=raw[4:].partition('\n---\n')
  if not sep:raise ValueError(f'Missing front matter closure in {path.name}')
  meta=yaml.safe_load(front) or {}
  slug=meta.get('slug') or path.stem
  if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*',slug):raise ValueError(f'Invalid slug: {slug}')
  title=str(meta.get('title') or '').strip()
  if not title or not body.strip():continue
  output=DIST/'stranicy'/slug/'index.html'
  if output.exists():raise ValueError(f'Page URL already exists: {slug}')
  sample=DIST/'stranicy/primer-cms/index.html'
  soup=BeautifulSoup(sample.read_text('utf-8'),'html.parser')
  soup.title.string=str(meta.get('seo_title') or title+' — Expert Team')
  d=soup.find('meta',attrs={'name':'description'})
  if d:d['content']=str(meta.get('description') or title)
  for sel,val in [('meta[property="og:title"]',soup.title.string),('meta[property="og:description"]',str(meta.get('description') or title)),('meta[property="og:url"]','https://expteam-staging.pages.dev/stranicy/'+slug+'/'),('link[rel="canonical"]','https://expteam-staging.pages.dev/stranicy/'+slug+'/')]:
   el=soup.select_one(sel)
   if el:el['href' if el.name=='link' else 'content']=val
  hero=soup.select_one('main .inner-hero h1')
  if hero:hero.string=title
  intro=soup.select_one('main .inner-hero p')
  if intro:intro.string=str(meta.get('intro') or '')
  crumbs=soup.select('.breadcrumbs > span')
  if crumbs:crumbs[-1].string=title
  textblock=soup.select_one('main .narrow-copy.prose')
  if textblock:
   textblock.clear()
   fragment=BeautifulSoup(mistune.create_markdown(plugins=['table','strikethrough'])(body),'html.parser')
   for child in list(fragment.contents):textblock.append(child)
  output.parent.mkdir(parents=True,exist_ok=True)
  output.write_text(str(soup),'utf-8')
  count+=1
 return count

def main():
 if DIST.exists():shutil.rmtree(DIST)
 DIST.mkdir()
 for directory in ('assets','admin','downloads','edit'):
  src=ROOT/directory
  if src.exists():shutil.copytree(src,DIST/directory)
 for parent in ('uslugi','ceny','404'):
  src=ROOT/parent
  if src.exists():shutil.copytree(src,DIST/parent)
 if (TEMPLATES/'404.html').exists():shutil.copy2(TEMPLATES/'404.html',DIST/'404.html')
 shared=load_json(CONTENT/'global.json')
 globals={item['id']:str(item.get('value','')) for item in shared['entries']}
 media=load_json(CONTENT/'media.json') if (CONTENT/'media.json').exists() else {}
 nav=load_json(CONTENT/'navigation.json') if (CONTENT/'navigation.json').exists() else {'links':[]}
 contacts=load_json(CONTENT/'contacts.json') if (CONTENT/'contacts.json').exists() else {}
 for entry in MANIFEST:
  tmpl=TEMPLATES/entry['template']
  json_file=CONTENT/'pages'/entry['json']
  page=load_json(json_file)
  outfile=DIST/entry['template']
  outfile.parent.mkdir(parents=True,exist_ok=True)
  rendered=render_text(tmpl.read_text('utf-8'),page,globals)
  rendered=apply_media(rendered,outfile,media)
  rendered=apply_navigation(rendered,outfile,nav)
  rendered=apply_contact_links(rendered,contacts)
  rendered=apply_seo_meta(rendered,page)
  if '[[' in rendered and 'ET:' in rendered: raise ValueError('Unrendered CMS token in '+str(outfile))
  outfile.write_text(rendered,'utf-8')
 n_posts=write_articles()
 n_pages=write_new_pages()
 # Editor-only annotated copies. Real public HTML remains byte-for-byte unaffected by markers.
 # An isolated sandboxed iframe loads these pages while editor controls run in /edit/.
 preview_root=DIST/'edit-preview'
 preview_index={}
 for entry in MANIFEST:
  rel=entry['template']
  template=TEMPLATES/rel
  page=load_json(CONTENT/'pages'/entry['json'])
  preview_file=preview_root/rel
  preview_file.parent.mkdir(parents=True,exist_ok=True)
  preview=render_visual_text(template.read_text('utf-8'),page,globals)
  preview=apply_media(preview,DIST/rel,media)
  preview=apply_navigation(preview,DIST/rel,nav)
  preview=apply_contact_links(preview,contacts)
  preview=apply_seo_meta(preview,page)
  from bs4 import BeautifulSoup
  preview_soup=BeautifulSoup(preview,'html.parser')
  head=preview_soup.head
  if head:
   base=preview_soup.new_tag('base')
   route='/' if rel=='index.html' else '/'+rel[:-len('index.html')]
   base['href']=route
   head.insert(0,base)
   extra_css=preview_soup.new_tag('link',rel='stylesheet',href='/edit/preview.css')
   head.append(extra_css)
  preview_file.write_text(str(preview_soup),'utf-8')
  route='/' if rel=='index.html' else '/'+rel[:-len('index.html')]
  preview_index[route]={'path':'content/pages/'+entry['json'],
                        'preview':'/edit-preview/'+rel,
                        'title':str(page.get('meta_title') or page.get('name') or route)}
 (DIST/'edit'/'manifest.json').write_text(json.dumps({
   'version':2,'repo':'ahatsmmalin-ai/expteam','pages':preview_index,
   'global':'content/global.json'
 },ensure_ascii=False,indent=2)+'\n','utf-8')
 (DIST/'_routes.json').write_text(json.dumps({'version':1,'include':['/api/*'],'exclude':[]},ensure_ascii=False)+'\n','utf-8')
 (DIST/'robots.txt').write_text('User-agent: *\nDisallow: /\n','utf-8')
 (DIST/'_headers').write_text('/*\n  X-Robots-Tag: noindex, nofollow, noarchive\n','utf-8')
 print(f'Expert Team CMS build complete: {len(MANIFEST)} CMS pages, {n_posts} new blog articles, {n_pages} new pages, {len(list(DIST.rglob("*.html")))} HTML files')

if __name__=='__main__':main()
