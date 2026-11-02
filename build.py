#!/usr/bin/env python3
"""Expert Team: static SEO-first prototype. Run: python build.py [--production]."""
import json, re, shutil, argparse, os, html, datetime, unicodedata
from pathlib import Path
from urllib.parse import quote
import yaml
from jinja2 import Environment, FileSystemLoader, select_autoescape
from markdown_it import MarkdownIt
from bs4 import BeautifulSoup
from PIL import Image, ImageDraw, ImageFont
ROOT=Path(__file__).parent.resolve()
CONTENT=ROOT/'content'; OUT=ROOT/'dist'
parser=argparse.ArgumentParser()
parser.add_argument('--production',action='store_true',help='Enable indexing for approved pages. Draft blog articles remain noindex.')
args=parser.parse_args()
if args.production:
    import sys
    sys.path.insert(0, str(ROOT / 'scripts'))
    from release_readiness import examine
    failures = examine()
    if os.environ.get('EXPERTTEAM_GO_LIVE') != 'YES':
        failures.insert(0, 'Требуется явное EXPERTTEAM_GO_LIVE=YES от ответственного за запуск')
    if not os.environ.get('EXPERTTEAM_FORM_ENDPOINT','').startswith('https://'):
        failures.append('Не указан HTTPS-приёмник заявок EXPERTTEAM_FORM_ENDPOINT')
    for f in (CONTENT/'cases').glob('*.json'):
        case = json.loads(f.read_text(encoding='utf-8'))
        if not case.get('client_approved') or not case.get('evidence'):
            failures.append(f'Не утверждены данные кейса {case.get("slug", f.name)}')
    if failures:
        parser.error('Публикация заблокирована до согласования:\n - '+'\n - '.join(failures))
if OUT.exists():shutil.rmtree(OUT)
OUT.mkdir()
site=json.loads((CONTENT/'site.json').read_text(encoding='utf-8'))
services=sorted([json.loads(f.read_text(encoding='utf-8')) for f in (CONTENT/'services').glob('*.json')],key=lambda x:x['code'])
cases=[json.loads(f.read_text(encoding='utf-8')) for f in (CONTENT/'cases').glob('*.json')]
case_map={c['slug']:c for c in cases}; service_map={s['slug']:s for s in services}
cases=sorted(cases,key=lambda x:['mfc-moya-ipoteka','europack','cinemarental'].index(x['slug']) if x['slug'] in ('mfc-moya-ipoteka','europack','cinemarental') else 100)
faq_home=json.loads((CONTENT/'home_faq.json').read_text(encoding='utf-8'))['items']
prices=json.loads((CONTENT/'prices.json').read_text(encoding='utf-8'))
seo_static=json.loads((CONTENT/'seo.json').read_text(encoding='utf-8'))
seo_guides={p.stem:[[s['title'],s['text']] for s in json.loads(p.read_text(encoding='utf-8'))['sections']] for p in (CONTENT/'guides').glob('*.json')}
category_names={'marketing':'Маркетинг','lidogeneraciya':'Лидогенерация','reklama':'Реклама','sajty':'Создание сайтов','crm':'CRM и автоматизация','seo':'SEO'}
md=MarkdownIt('commonmark',{'html':False,'linkify':True})
def slugify_ru(s):
    trans=str.maketrans('абвгдеёзийклмнопрстуфхцчшщъыьэюя','abvgdeezijklmnoprstufhccss_y_eua')
    s=s.lower().translate(trans);s=re.sub('[^a-z0-9]+','-',s).strip('-')
    return s[:72] or 'section'
articles=[]
for f in (CONTENT/'posts').glob('*.md'):
    raw=f.read_text(encoding='utf-8'); match=re.match(r'^---\s*\n(.*?)\n---\s*\n(.*)$',raw,re.S)
    if not match: raise ValueError(f'No YAML frontmatter: {f}')
    meta=yaml.safe_load(match.group(1)); body=match.group(2)
    if args.production and not meta.get('published',False):continue
    if args.production and meta.get('published') and (meta.get('editorial_status')!='approved' or not meta.get('reviewed_by') or not meta.get('reviewed_on')):
        raise ValueError(f'Article publication lacks editorial approval: {f.name}')
    text=md.render(body)
    soup=BeautifulSoup(text,'html.parser'); heads=[]
    for h in soup.select('h2'):
        anchor=slugify_ru(h.get_text());h['id']=anchor
        heads.append({'id':anchor,'title':h.get_text()})
    meta['html']=str(soup);meta['headings']=heads;meta['word_count']=len(body.split());meta['related']=[service_map[s] for s in meta.get('related_services',[]) if s in service_map]
    meta['date']=str(meta.get('date',''));meta['modified']=str(meta.get('modified',meta['date']))
    meta['published']=meta.get('published',False);articles.append(meta)
articles.sort(key=lambda x:x['date'],reverse=True)
# CMS-managed standalone pages: a separate, allowlisted URL namespace avoids
# shadowing the approved 7 service URLs, blog, admin, cases, or static assets.
custom_pages=[]
for f in sorted((CONTENT/'pages').glob('*.md')):
    raw=f.read_text(encoding='utf-8');m=re.match(r'^---\s*\n(.*?)\n---\s*\n(.*)$',raw,re.S)
    if not m:raise ValueError(f'Missing page frontmatter: {f}')
    meta=yaml.safe_load(m.group(1))
    if meta.get('section') not in ('stranicy','resheniya','materialy'):
        raise ValueError(f'Invalid new page section in {f.name}')
    if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*',str(meta.get('slug',''))) or meta['slug']!=f.stem:
        raise ValueError(f'Invalid new page slug in {f.name}')
    if args.production and not meta.get('published',False):continue
    if args.production and meta.get('published') and (meta.get('editorial_status')!='approved' or not meta.get('reviewed_by') or not meta.get('reviewed_on') or not meta.get('source_notes')):
        raise ValueError(f'New page publication lacks editorial approval: {f.name}')
    parsed=BeautifulSoup(md.render(m.group(2)),'html.parser');heads=[];used=set()
    for h in parsed.select('h2'):
        base=slugify_ru(h.get_text());anchor=base;n=2
        while anchor in used:anchor=f'{base}-{n}';n+=1
        used.add(anchor);h['id']=anchor;heads.append({'id':anchor,'title':h.get_text()})
    meta['html']=str(parsed);meta['headings']=heads
    meta['related']=[service_map[x] for x in meta.get('related_services',[]) if x in service_map]
    custom_pages.append(meta)

env=Environment(loader=FileSystemLoader(str(ROOT/'templates')),autoescape=select_autoescape(['html','xml']),trim_blocks=True,lstrip_blocks=True)
base_url=site['domain'].rstrip('/')
org={"@context":"https://schema.org","@type":"Organization","@id":base_url+"/#organization","name":"Expert Team","url":base_url,"email":site['email'],"foundingDate":site['founded'],"logo":base_url+"/assets/og.png","sameAs":[site['telegram']]}
website={"@context":"https://schema.org","@type":"WebSite","@id":base_url+"/#website","url":base_url,"name":"Expert Team","publisher":{"@id":base_url+"/#organization"}}
# Do not emit SearchAction until on-site search exists: no fake actions.
now=datetime.date.today().isoformat();year=datetime.date.today().year
routes=[]
def crumbs_schema(path,items):
    chain=[{'name':'Главная','url':base_url+'/'}]+items
    return {'@context':'https://schema.org','@type':'BreadcrumbList','itemListElement':[{'@type':'ListItem','position':n+1,'name':c['name'],'item':c['url']} for n,c in enumerate(chain)]}
def html_page(path,template,title,desc,typ='static',extra=None,schema=None,indexable=None):
    path='/' + path.strip('/')+'/' if path!='/' else '/'
    canonical=base_url+path
    is_indexable=(args.production if indexable is None else bool(indexable))
    ctx={'site':site,'services':services,'cases':cases,'articles':articles,'domain':base_url,'year':year,'type':typ,'canonical':canonical,'indexable':is_indexable,'meta':{'title':title,'description':desc},'category_names':category_names,'schemas':[org,website], 'form_endpoint':os.environ.get('EXPERTTEAM_FORM_ENDPOINT','') if args.production else ''}
    if schema:ctx['schemas']+=schema
    ctx.update(extra or {})
    ctx['meta']['og_image']=(base_url+ctx['article']['cover_image']) if typ=='article' and ctx['article'].get('cover_image','').startswith('/') else base_url+'/assets/og.png'
    target=OUT/path.strip('/')/'index.html' if path!='/' else OUT/'index.html';target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(env.get_template(template).render(**ctx),encoding='utf-8')
    routes.append({'url':path,'title':title,'type':typ,'index':is_indexable,'lastmod':now,'priority':'1.0' if path=='/' else '0.8' if typ=='service' else '0.6','changefreq':'weekly' if typ=='blog' else 'monthly'})

html_page('/','home.html',seo_static['home']['title'],seo_static['home']['description'],typ='home',extra={'home_faq':faq_home},schema=[{'@context':'https://schema.org','@type':'WebPage','name':'Маркетинговое агентство Expert Team','url':base_url+'/'}])
for s in services:
    path=f"/uslugi/{s['slug']}/"
    service_schema={'@context':'https://schema.org','@type':'Service','@id':base_url+path+'#service','name':s['name'],'description':s['description'],'serviceType':s['keyword'],'provider':{'@id':base_url+'/#organization'},'areaServed':{'@type':'Country','name':'Россия'},'url':base_url+path}
    # Confirmed starting price applies to outsourced marketing only.
    if s['slug']=='marketing-na-autsorse':service_schema['offers']={'@type':'Offer','price':'35000','priceCurrency':'RUB','description':'Стартовая стоимость за месяц; состав работ уточняется'}
    crumbs=[{'name':'Услуги','url':base_url+'/#services'},{'name':s['name'],'url':base_url+path}]
    faq_schema={'@context':'https://schema.org','@type':'FAQPage','mainEntity':[{'@type':'Question','name':x['q'],'acceptedAnswer':{'@type':'Answer','text':x['a']}} for x in s['faqs']]}
    # FAQPage is the semantically appropriate type for a publisher-written list of FAQs. QAPage is for single question with community answers; Google rich result eligibility is limited.
    featured=next((c for c in cases if c['related']==s['slug']),cases[0])
    related=[service_map[x] for x in s['related'] if x in service_map]
    html_page(path,'service.html',s['title'],s['description'],typ='service',extra={'service':s,'seo_guides':[(a,b) for a,b in seo_guides.get(s['slug'],[])],'featured_case':featured,'case_index':cases.index(featured)+1,'related':related},schema=[crumbs_schema(path,crumbs),service_schema,faq_schema])
html_page('/kejsy/','cases.html',seo_static['cases']['title'],seo_static['cases']['description'],typ='cases',extra={'industries':sorted({c['industry'] for c in cases})},schema=[crumbs_schema('/kejsy/',[{'name':'Кейсы','url':base_url+'/kejsy/'}])])
for c in cases:
    path='/kejsy/'+c['slug']+'/'
    case_schema={'@context':'https://schema.org','@type':'Article','headline':'Кейс '+c['name'],'description':c['intro'],'author':{'@id':base_url+'/#organization'},'publisher':{'@id':base_url+'/#organization'},'mainEntityOfPage':base_url+path,'image':base_url+'/assets/og.png'}
    html_page(path,'case.html',c.get('seo_title') or f"{c['name']} — кейс маркетинга | Expert Team",c.get('seo_description') or c['intro'],typ='case',extra={'case':c},schema=[crumbs_schema(path,[{'name':'Кейсы','url':base_url+'/kejsy/'},{'name':c['name'],'url':base_url+path}]),case_schema])
html_page('/o-kompanii/','about.html',seo_static['about']['title'],seo_static['about']['description'],typ='about',schema=[crumbs_schema('/o-kompanii/',[{'name':'О компании','url':base_url+'/o-kompanii/'}])])
html_page('/ceny/','prices.html',seo_static['prices']['title'],seo_static['prices']['description'],typ='prices',extra={'prices':prices},schema=[crumbs_schema('/ceny/',[{'name':'Цены','url':base_url+'/ceny/'}])])
html_page('/kontakty/','contact.html',seo_static['contacts']['title'],seo_static['contacts']['description'],typ='contacts',schema=[crumbs_schema('/kontakty/',[{'name':'Контакты','url':base_url+'/kontakty/'}]),{'@context':'https://schema.org','@type':'ContactPage','name':'Контакты Expert Team'}])
html_page('/blog/','blog.html',seo_static['blog']['title'],seo_static['blog']['description'],typ='blog',extra={'active_category':None},indexable=bool(args.production and articles),schema=[crumbs_schema('/blog/',[{'name':'Блог','url':base_url+'/blog/'}])])
for slug,label in category_names.items():
    matches=[a for a in articles if a['category']==slug]
    html_page('/blog/'+slug+'/','blog.html',f'{label}: статьи и руководства | Expert Team',f'Статьи и материалы Expert Team на тему {label.lower()}.',typ='blog',extra={'active_category':slug,'articles':matches},indexable=bool(args.production and matches),schema=[crumbs_schema('/blog/'+slug+'/',[{'name':'Блог','url':base_url+'/blog/'},{'name':label,'url':base_url+'/blog/'+slug+'/'}])])
for a in articles:
    path='/blog/'+a['slug']+'/'
    article_schema={'@context':'https://schema.org','@type':'Article','headline':a['title'],'description':a['description'],'datePublished':a['date'],'dateModified':a['modified'],'author':{'@type':'Organization' if a['author'].startswith('Редакция ') else 'Person','name':a['author']},'publisher':{'@id':base_url+'/#organization'},'mainEntityOfPage':base_url+path,'image':(base_url+a['cover_image'] if a.get('cover_image','').startswith('/') else base_url+'/assets/og.png')}
    html_page(path,'article.html',f"{a['title']} | Expert Team",a['description'],typ='article',extra={'article':a},schema=[crumbs_schema(path,[{'name':'Блог','url':base_url+'/blog/'},{'name':category_names[a['category']],'url':base_url+'/blog/'+a['category']+'/'},{'name':a['title'],'url':base_url+path}]),article_schema],indexable=bool(args.production and a['published']))
for p in custom_pages:
    path=f"/{p['section']}/{p['slug']}/"
    custom_schema={'@context':'https://schema.org','@type':'WebPage','name':p['h1'],'description':p['description'],'url':base_url+path}
    html_page(path,'page.html',p['seo_title'],p['description'],typ='page',
              extra={'page':p},schema=[crumbs_schema(path,[{'name':p['title'],'url':base_url+path}]),custom_schema],
              indexable=bool(args.production and p.get('published',False)))
html_page('/politika-konfidencialnosti/','privacy.html' ,'Политика конфиденциальности | Expert Team','Страница политики конфиденциальности Expert Team.',typ='legal',indexable=False)
html_page('/404/','404.html','Страница не найдена — 404 | Expert Team','Ошибка 404. Перейти на главную страницу Expert Team.',typ='error',indexable=False)
shutil.copyfile(OUT/'404'/'index.html',OUT/'404.html')
(OUT/'assets').mkdir(exist_ok=True)
shutil.copyfile(ROOT/'static/css/style.css',OUT/'assets/style.css')
shutil.copyfile(ROOT/'static/js/site.js',OUT/'assets/site.js')
if (ROOT/'static/downloads').exists(): shutil.copytree(ROOT/'static/downloads',OUT/'downloads',dirs_exist_ok=True)
if (ROOT/'static/uploads').exists():shutil.copytree(ROOT/'static/uploads',OUT/'assets/uploads',dirs_exist_ok=True)
(OUT/'admin').mkdir(exist_ok=True)
shutil.copyfile(ROOT/'static/admin/index.html',OUT/'admin/index.html') if (ROOT/'static/admin/index.html').exists() else None
shutil.copyfile(ROOT/'static/admin/config.yml',OUT/'admin/config.yml') if (ROOT/'static/admin/config.yml').exists() else None
# Static assets: responsive SVG/PNG logo, Open Graph preview.
(OUT/'assets/favicon.svg').write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 80 80"><rect width="80" height="80" rx="15" fill="#101410"/><path d="M20 22H62V31H30V37H55V46H30V54H62V63H20Z" fill="#d5ff45"/></svg>',encoding='utf-8')
im=Image.new('RGB',(64,64),'#111410');d=ImageDraw.Draw(im);d.rectangle((14,14,50,22),fill='#d5ff45');d.rectangle((14,14,22,51),fill='#d5ff45');d.rectangle((14,28,43,36),fill='#d5ff45');d.rectangle((14,43,50,51),fill='#d5ff45');im.save(OUT/'assets/favicon.png')
im=Image.new('RGB',(1200,630),'#111410');d=ImageDraw.Draw(im)
for x in range(0,1200,70):d.line([(x,0),(x,630)],fill='#242b22',width=1)
for y in range(0,630,70):d.line([(0,y),(1200,y)],fill='#242b22',width=1)
fontpath='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
fontbig=ImageFont.truetype(fontpath,94) if Path(fontpath).is_file() else ImageFont.load_default(size=94)
fontmid=ImageFont.truetype(fontpath,37) if Path(fontpath).is_file() else ImageFont.load_default(size=37)
d.ellipse((930,105,1190,365),outline='#d5ff45',width=6);d.ellipse((965,140,1155,330),outline='#738b2e',width=3)
d.text((80,84),'EXPERT TEAM',fill='#d5ff45',font=fontmid)
d.text((72,208),'MARKETING',fill='#fffef7',font=fontbig);d.text((72,325),'THAT WORKS.',fill='#d5ff45',font=fontbig)
d.text((80,525),'СТРАТЕГИЯ  /  ТРАФИК  /  CRM  /  SEO',fill='#e0e5d7',font=ImageFont.truetype(fontpath,24) if Path(fontpath).is_file() else ImageFont.load_default(size=24))
im.save(OUT/'assets/og.png',optimize=True)
# Technical SEO files
robots=("User-agent: *\n"+("Allow: /\nDisallow: /admin/\nDisallow: /api/\nDisallow: /search/\nDisallow: /*?*sort=\nDisallow: /*?*filter=\nDisallow: /*?*utm_\n" if args.production else "Disallow: /\n")+"\nUser-agent: GPTBot\n"+("Allow: /\n" if args.production else "Disallow: /\n")+"User-agent: ChatGPT-User\n"+("Allow: /\n" if args.production else "Disallow: /\n")+"User-agent: PerplexityBot\n"+("Allow: /\n" if args.production else "Disallow: /\n")+"User-agent: ClaudeBot\n"+("Allow: /\n" if args.production else "Disallow: /\n")+f"Sitemap: {base_url}/sitemap.xml\n")
(OUT/'robots.txt').write_text(robots,encoding='utf-8')
from xml.sax.saxutils import escape as xml_escape
urls=[r for r in routes if r['index']]
urls_xml=''.join(f"<url><loc>{xml_escape(base_url+r['url'])}</loc><lastmod>{r['lastmod']}</lastmod><changefreq>{r['changefreq']}</changefreq><priority>{r['priority']}</priority></url>" for r in urls)
(OUT/'sitemap.xml').write_text('<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'+urls_xml+'</urlset>',encoding='utf-8')
llms='# Expert Team — маркетинговая команда для бизнеса\n\nЭкспертиза: маркетинг на аутсорсе, создание сайтов, лидогенерация, реклама, маркетинг под ключ, CRM-маркетинг, SEO. С 2018 года, работает удалённо по России.\n\n## Услуги\n'
llms+='\n'.join(f"- [{s['name']}]({base_url}/uslugi/{s['slug']}/): {s['short']}" for s in services)
llms+=f'\n\n## Полезное\n- [Блог]({base_url}/blog/)\n- [Кейсы]({base_url}/kejsy/)\n- [Цены]({base_url}/ceny/)\n\n## Контакты\n- Email: {site["email"]}\n- Telegram: {site["telegram"]}\n'
(OUT/'llms.txt').write_text(llms,encoding='utf-8')
(OUT/'manifest.webmanifest').write_text(json.dumps({'name':'Expert Team','short_name':'Expert Team','start_url':'/','display':'browser','background_color':'#111410','theme_color':'#111410','icons':[{'src':'/assets/favicon.png','sizes':'64x64','type':'image/png'}]},ensure_ascii=False),encoding='utf-8')
(ROOT/'docs/routes.generated.json').write_text(json.dumps(routes,ensure_ascii=False,indent=2),encoding='utf-8')
print(f'Built {len(routes)} HTML routes, {len(services)} services, {len(articles)} visible articles, {len(custom_pages)} custom pages. Production SEO: {args.production}. Indexed sitemap entries: {len(urls)}')
