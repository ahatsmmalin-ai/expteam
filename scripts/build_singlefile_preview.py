#!/usr/bin/env python3
"""Embed every rendered page into one offline HTML, reusing original approved preview UI."""
from pathlib import Path
from bs4 import BeautifulSoup
import json,re,base64
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'reference/approved_preview.html'
OUT=ROOT/'ExpertTeam_content_cms_preview.html'
source=BASE.read_text(encoding='utf-8')
obj=json.loads(re.search(r'const DATA=(.*?);\s*\n',source,re.S).group(1))
routes=json.loads((ROOT/'docs/routes.generated.json').read_text(encoding='utf-8'))
assert len(routes)>=32, len(routes)
for r in routes:
    url=r['url']; htmlfile=ROOT/'dist'/url.strip('/')/'index.html' if url!='/' else ROOT/'dist'/'index.html'
    soup=BeautifulSoup(htmlfile.read_text(encoding='utf-8'),'html.parser')
    body=soup.body
    for script in body.find_all('script'):script.decompose()
    for img in body.select('img[src^="/assets/uploads/articles/"]'):
        path=ROOT/'dist'/img['src'].lstrip('/')
        if path.is_file() and path.suffix=='.webp':
            img['src']='data:image/webp;base64,'+base64.b64encode(path.read_bytes()).decode('ascii')
    obj['pages'][url]=body.decode_contents()
    obj['titles'][url]=soup.title.get_text(strip=True)
    obj['classes'][url]=repr((body.get('class') or []))
obj['downloads']={'/downloads/shablon-marketingovogo-otcheta.html':(ROOT/'dist/downloads/shablon-marketingovogo-otcheta.html').read_text(encoding='utf-8')}
js_json=json.dumps(obj,ensure_ascii=False,separators=(',',':')).replace('</','<\\/')
source,n=re.subn(r'const DATA=.*?;\s*\nconst root=',lambda m:'const DATA='+js_json+';\nconst root=',source,count=1,flags=re.S)
assert n==1
# Preserve original review bar + the approved original site visual system (only new CSS for filters).
base_style=source[source.index('<style>')+len('<style>'):source.index('</style>')]
original_css=(ROOT/'static/css/style.css').read_text(encoding='utf-8')
review_style=base_style[base_style.find('/* Unobtrusive review toolbar'):]
# If present, keep tool bar CSS independently. This prevents losing controls in a newly bundled file.
source=source[:source.index('<style>')]+ '<style>'+ original_css+'\n'+review_style +source[source.index('</style>'):]
# Standalone preview routes are hash-based. For embedded downloadable assets, create blob only on click.
needle="document.addEventListener('click',e=>{\n const a=e.target.closest('a[href]');"
addition="""document.addEventListener('click',e=>{
 const a=e.target.closest('a[href]');
 if(a&&DATA.downloads?.[a.getAttribute('href')]){e.preventDefault();const content=DATA.downloads[a.getAttribute('href')];const blob=new Blob([content],{type:'text/html;charset=utf-8'});const link=document.createElement('a');link.href=URL.createObjectURL(blob);link.download='ExpertTeam_Шаблон_отчета.html';link.click();setTimeout(()=>URL.revokeObjectURL(link.href),2500);return;}
"""
assert needle in source
source=source.replace(needle,addition,1)
# Keep interactive case filters in local SPA, which is not the site's actual JS bundle.
needle="document.addEventListener('submit',e=>{"
filter_js='''function etApplyFilters(){const industry=document.getElementById('caseFilterIndustry')?.value||'all';const service=document.getElementById('caseFilterService')?.value||'all';let visible=0;document.querySelectorAll('[data-case-industry]').forEach(el=>{const show=(industry==='all'||el.dataset.caseIndustry===industry)&&(service==='all'||el.dataset.caseService===service);el.hidden=!show;if(show)visible++});const counter=document.getElementById('caseFilterCount');if(counter)counter.textContent='Кейсов: '+visible;const empty=document.getElementById('caseFilterEmpty');if(empty)empty.hidden=visible!==0;}
document.addEventListener('change',e=>{if(e.target.matches('#caseFilterIndustry,#caseFilterService'))etApplyFilters()});
'''
assert needle in source
source=source.replace(needle,filter_js+needle,1)
# JS downloads are preview-only: actual site includes real downloadable static URL.
OUT.write_text(source,encoding='utf-8')
print('Created',OUT,OUT.stat().st_size,'bytes;',len(obj['pages']),'pages')
