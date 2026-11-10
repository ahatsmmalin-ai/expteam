#!/usr/bin/env python3
"""Expert Team 2026 redesign. Static generation from JSON/Markdown, with a staging release gate."""
from __future__ import annotations
import argparse, datetime, html, json, os, re, shutil
from pathlib import Path
from urllib.parse import quote
from xml.sax.saxutils import escape as xml_escape
import yaml
from bs4 import BeautifulSoup
from jinja2 import Environment, FileSystemLoader, select_autoescape
from markdown_it import MarkdownIt
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'dist'
C=ROOT/'content'
p=argparse.ArgumentParser()
p.add_argument('--production',action='store_true')
args=p.parse_args()
if args.production:
    approvals=json.loads((C/'release.json').read_text(encoding='utf-8'))
    required=['legal_policy_approved','forms_and_crm_verified','cases_and_reviews_confirmed','prices_confirmed','team_and_authors_confirmed','seo_review_approved','migration_redirects_checked']
    if os.environ.get('EXPERTTEAM_GO_LIVE')!='YES' or any(not approvals.get(k) for k in required):
        p.error('Production release is blocked until all corporate/legal/form/SEO approvals and EXPERTTEAM_GO_LIVE=YES')
    if not os.environ.get('EXPERTTEAM_FORM_ENDPOINT','').startswith('https://'):
        p.error('HTTPS form endpoint missing for production')
if OUT.exists():shutil.rmtree(OUT)
OUT.mkdir()
site=json.loads((C/'site.json').read_text(encoding='utf-8'))
data=json.loads((C/'redesign.json').read_text(encoding='utf-8'))
solution_map={x['slug']:x for x in data['solutions']}
old_cases={x['slug']:x for x in (json.loads(f.read_text(encoding='utf-8')) for f in (C/'cases').glob('*.json'))}
case_cards=json.loads((C/'redesign_cases.json').read_text(encoding='utf-8'))['items']
for x in data['solutions']+case_cards:
    if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*',x.get('slug','')):raise ValueError('Unsafe solution/case URL slug')
if len({x['slug'] for x in data['solutions']})!=len(data['solutions']) or len({x['slug'] for x in case_cards})!=len(case_cards):raise ValueError('Duplicate solution/case slugs')
letters=json.loads((C/'letters.json').read_text(encoding='utf-8'))['items']
team=json.loads((C/'team.json').read_text(encoding='utf-8'))['items']
md=MarkdownIt('commonmark',{'html':False,'linkify':True})
articles=[]
for f in (C/'posts').glob('*.md'):
    raw=f.read_text(encoding='utf-8')
    m=re.match(r'^---\s*\n(.*?)\n---\s*\n(.*)$',raw,re.S)
    if not m: continue
    meta=yaml.safe_load(m.group(1))
    if args.production and meta.get('published') and (meta.get('editorial_status')!='approved' or not meta.get('reviewed_by') or not meta.get('reviewed_on')):
        raise ValueError('Unapproved blog article: '+f.name)
    if args.production and not meta.get('published'):continue
    parsed=BeautifulSoup(md.render(m.group(2)),'html.parser')
    headings=[]
    for n,h in enumerate(parsed.find_all('h2')):
        anchor='section-'+str(n+1)
        h['id']=anchor
        headings.append({'id':anchor,'title':h.get_text()})
    meta['html']=str(parsed);meta['headings']=headings
    meta['date']=str(meta.get('date',''));meta['published']=bool(meta.get('published'))
    articles.append(meta)
articles.sort(key=lambda x:x['date'],reverse=True)
category_names={'marketing':'Маркетинг','lidogeneraciya':'Лидогенерация','reklama':'Реклама','sajty':'Сайты','crm':'CRM','seo':'SEO'}
custom_pages=[]
for f in (C/'pages').glob('*.md'):
    raw=f.read_text(encoding='utf-8');m=re.match(r'^---\s*\n(.*?)\n---\s*\n(.*)$',raw,re.S)
    if not m:continue
    x=yaml.safe_load(m.group(1))
    if x.get('section') not in ['stranicy','resheniya','materialy'] or not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*',x.get('slug','')) or x['slug']!=f.stem:raise ValueError('Unsafe CMS page '+f.name)
    if args.production and x.get('published') and (x.get('editorial_status')!='approved' or not x.get('reviewed_by') or not x.get('reviewed_on')):raise ValueError('Unapproved custom page '+f.name)
    if x['section']=='resheniya' and x['slug'] in {q['slug'] for q in data['solutions']}:raise ValueError('Custom page collides with paid solution: '+x['slug'])
    if args.production and not x.get('published'):continue
    x['html']=md.render(m.group(2));custom_pages.append(x)

# Cached, transparent versions of the 39 customer-provided elements are already in static/assets.
# Site is staged on pages.dev; canonical points to that staging URL for the draft, production to expertteam.pro.
base='https://expertteam.pro' if args.production else 'https://expteam-staging.pages.dev'
root=ROOT/'templates'/'redesign'
env=Environment(loader=FileSystemLoader(str(root)),autoescape=select_autoescape(['html','xml']),trim_blocks=True,lstrip_blocks=True)
env.filters['asset']=lambda n:'/assets/brand/ExpertTeam_Asset_%02d.webp'%int(n)
now=datetime.date.today().isoformat()
route_rows=[]

def render(path,template,title,description,typ,ctx=None,indexable=None):
    path='/' + path.strip('/') + '/' if path!='/' else '/'
    canonical=base+path
    indexable=(bool(args.production) if indexable is None else bool(indexable))
    context=dict(site=site,content=data,solutions=data['solutions'],cases=case_cards,letters=letters,team=team,articles=articles,category_names=category_names,now=now,year=datetime.date.today().year,base=base,meta={'title':title,'description':description},canonical=canonical,indexable=indexable,type=typ,form_endpoint=os.environ.get('EXPERTTEAM_FORM_ENDPOINT','') if args.production else '',contact_telegram=site.get('telegram',''),scripts=[])
    context.update(ctx or {})
    target=OUT/path.strip('/')/'index.html' if path!='/' else OUT/'index.html'
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(env.get_template(template).render(**context),encoding='utf-8')
    route_rows.append(dict(path=path,title=title,type=typ,indexable=indexable))

render('/','home.html','Комплексный маркетинг для B2B и производства — от 35 000 ₽ | Expert Team','Внешний отдел маркетинга: стратегия, реклама, материалы, CRM и лидогенерация. Команда от 35 000 ₽/мес. Бесплатный маркетинговый план.', 'home')
for s in data['solutions']:
    render('/resheniya/'+s['slug']+'/','solution.html',s['name']+' | Expert Team',s['intro'],'solution',dict(solution=s,focus_cases=[x for x in case_cards if (s['slug']=='kompleksnyj-marketing' or x['slug'] in ['astra','europack','homeoffice'])][:3]))
render('/marketingovyj-plan/','plan.html','Бесплатный маркетинговый план и расчёт бюджета | Expert Team','Бесплатно разберём задачу: сегменты, каналы, гипотезы, презентация и таблица маркетинговых бюджетов.','plan')
render('/kejsy/','cases.html','Кейсы маркетинга для B2B, производства и услуг | Expert Team','Кейсы по привлечению лидов и развитию маркетинга: производство, услуги, IT.','cases')
for ca in case_cards:
    render('/kejsy/'+ca['slug']+'/','case.html',ca['name']+' — кейс маркетинга | Expert Team',ca['intro'],'case',dict(case=ca))
render('/o-kompanii/','about.html','О команде Expert Team — маркетинг с 2018 года','Внешний отдел маркетинга: маркетолог, руководитель проектов и руководитель агентства. Работаем с 2018 года.','about')
render('/kontakty/','contact.html','Контакты Expert Team — обсудить маркетинг компании','Связаться с Expert Team, получить маркетинговый план или обсудить комплексный маркетинг.','contacts')
render('/blog/','blog.html','Блог Expert Team — маркетинг, лидогенерация, CRM','Практические материалы о B2B-маркетинге, поиске клиентов, рекламе, CRM и маркетинге на аутсорсе.','blog')
for a in articles:
    render('/blog/'+a['slug']+'/','article.html',a['title']+' | Expert Team',a.get('description',''),'article',dict(article=a),indexable=bool(args.production and a.get('published')))
for slug,label in category_names.items():
    render('/blog/'+slug+'/','blog.html',f'{label} — статьи Expert Team',f'Материалы Expert Team по теме «{label}».','blog',dict(filtered_category=slug),indexable=False)
render('/materialy/marketolog-ili-komanda/','compare.html','Маркетолог в штате или команда на аутсорсе: сравнение | Expert Team','Сравните штатный маркетинг и внешнюю команду: состав работы, риски и расходы. Бесплатный калькулятор затрат.','compare')
render('/kalkulyator-marketologa/','calculator.html','Калькулятор затрат: маркетолог в штате или Expert Team','Рассчитайте сценарные месячные затраты на штатного маркетолога и внешнюю команду с учётом задач и бюджета.','calculator')
for x in custom_pages:
    render('/'+x['section']+'/'+x['slug']+'/','custom.html',x['seo_title'],x['description'],'custom',dict(page=x),indexable=bool(args.production and x.get('published')))
render('/politika-konfidencialnosti/','privacy.html','Политика конфиденциальности | Expert Team','Информация об обработке персональных данных.','privacy',indexable=False)
render('/404/','404.html','Страница не найдена — Expert Team','Запрашиваемая страница не найдена.','error',indexable=False)
shutil.copy2(OUT/'404/index.html',OUT/'404.html')
# Keep legacy URLs by using Cloudflare Pages _redirects (and a JS/meta fallback for local preview).
redirects={
 '/uslugi/marketing-na-autsorse/':'/resheniya/kompleksnyj-marketing/',
 '/uslugi/marketing-pod-klyuch/':'/resheniya/kompleksnyj-marketing/',
 '/uslugi/lidogeneraciya/':'/resheniya/leadstore-koll-centr/',
 '/uslugi/nastrojka-reklamy/':'/resheniya/kompleksnyj-marketing/',
 '/uslugi/sozdanie-sajtov/':'/resheniya/kompleksnyj-marketing/',
 '/uslugi/crm-marketing/':'/resheniya/kompleksnyj-marketing/',
 '/uslugi/seo/':'/resheniya/kompleksnyj-marketing/',
 '/ceny/':'/#pricing',
 '/uslugi/':'/#solutions'
}
(OUT/'_redirects').write_text('\n'.join(k+' '+v+' 301' for k,v in redirects.items())+'\n',encoding='utf-8')
for old,new in redirects.items():
    target=OUT/old.strip('/')/'index.html';target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text('<!doctype html><html lang="ru"><meta charset="utf-8"><meta name="robots" content="noindex,nofollow"><meta http-equiv="refresh" content="0; url='+html.escape(new,quote=True)+'"><title>Страница переехала</title><p>Новый адрес: <a href="'+html.escape(new,quote=True)+'">Открыть страницу</a></p></html>',encoding='utf-8')
# Copy site static files.
(OUT/'assets').mkdir()
shutil.copy2(ROOT/'static/css/redesign.css',OUT/'assets/style.css')
shutil.copy2(ROOT/'static/js/redesign.js',OUT/'assets/site.js')
shutil.copytree(ROOT/'static/assets',OUT/'assets/brand',dirs_exist_ok=True,ignore=shutil.ignore_patterns('*.png','expertteam-original.svg'))
if (ROOT/'static/uploads').exists():shutil.copytree(ROOT/'static/uploads',OUT/'assets/uploads',dirs_exist_ok=True)
if (ROOT/'static/downloads').exists():shutil.copytree(ROOT/'static/downloads',OUT/'downloads',dirs_exist_ok=True)
(OUT/'admin').mkdir()
for file in ['index.html','config.yml']:shutil.copy2(ROOT/'static/admin'/file,OUT/'admin'/file)
(OUT/'assets/favicon.svg').write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64" rx="16" fill="#0F09FF"/><path d="M13 18h37v8H22v7h23v8H22v7h28v8H13Z" fill="#fff"/></svg>',encoding='utf-8')
(OUT/'manifest.webmanifest').write_text(json.dumps({'name':'Expert Team','short_name':'Expert Team','start_url':'/','display':'browser','theme_color':'#0F09FF','background_color':'#FFFFFF','icons':[{'src':'/assets/favicon.svg','sizes':'any','type':'image/svg+xml'}]},ensure_ascii=False),encoding='utf-8')
# OG card: never create fake proof; typography-only layout.
img=Image.new('RGB',(1200,630),'#FFFFFF');d=ImageDraw.Draw(img)
fontpath='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
fontb=ImageFont.truetype(fontpath,80) if Path(fontpath).exists() else ImageFont.load_default()
fontm=ImageFont.truetype(fontpath,35) if Path(fontpath).exists() else ImageFont.load_default()
d.rectangle([0,0,1200,17],fill='#0F09FF');d.text((70,75),'EXPERT TEAM',font=fontm,fill='#0F09FF');d.text((64,190),'MARKETING',font=fontb,fill='#000000');d.text((64,302),'FOR BUSINESS',font=fontb,fill='#0F09FF');d.text((70,520),'Комплексный маркетинг от 35 000 ₽/мес.',font=fontm,fill='#1B1B1B');img.save(OUT/'assets/og.png',optimize=True)
(OUT/'robots.txt').write_text('User-agent: *\n'+('Allow: /\nDisallow: /admin/\n' if args.production else 'Disallow: /\n')+'Sitemap: '+base+'/sitemap.xml\n',encoding='utf-8')
urls=[x for x in route_rows if x['indexable']]
(OUT/'sitemap.xml').write_text('<?xml version="1.0" encoding="utf-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'+''.join('<url><loc>'+xml_escape(base+x['path'])+'</loc><lastmod>'+now+'</lastmod></url>' for x in urls)+'</urlset>',encoding='utf-8')
(OUT/'llms.txt').write_text('# Expert Team\nВнешний отдел маркетинга для производственных и B2B-компаний.\n'+ '\n'.join(f"- {x['name']}: {base}/resheniya/{x['slug']}/" for x in data['solutions'])+'\n',encoding='utf-8')
(ROOT/'docs').mkdir(exist_ok=True)
(ROOT/'docs'/'routes.redesign.json').write_text(json.dumps(route_rows,ensure_ascii=False,indent=2),encoding='utf-8')
print(f'EXPERT TEAM REDESIGN: {len(route_rows)} content pages, {len(redirects)} redirects, {len(articles)} blog articles. Production: {args.production}.')
