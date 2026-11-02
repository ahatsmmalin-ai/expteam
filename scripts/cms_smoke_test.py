#!/usr/bin/env python3
"""Hermetic smoke test: new CMS page, edit existing content, reject unsafe routes."""
from pathlib import Path
import tempfile, subprocess, shutil, json, sys
import yaml

ROOT=Path(__file__).resolve().parents[1]

def run(root,*args,success=True):
    p=subprocess.run([sys.executable,*args],cwd=root,text=True,capture_output=True)
    if (p.returncode==0)!=success:
        raise AssertionError('Unexpected result: '+' '.join(args)+'\n'+p.stdout+'\n'+p.stderr)
    return p

with tempfile.TemporaryDirectory(prefix='expertteam-cms-qa-') as d:
    tmp=Path(d)
    for name in ['build.py','templates','content','static','scripts']:
        src=ROOT/name
        if src.is_dir():shutil.copytree(src,tmp/name,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
        else:shutil.copy2(src,tmp/name)
    (tmp/'docs').mkdir()
    # 1. Existing service text is sourced from editable JSON.
    f=tmp/'content/services/seo.json';service=json.loads(f.read_text(encoding='utf-8'))
    service['lead']='ТЕСТ_РЕДАКТИРОВАНИЯ_УСЛУГИ_CMS'
    f.write_text(json.dumps(service,ensure_ascii=False,indent=2),encoding='utf-8')
    # 2. New page, created as a CMS frontmatter file, becomes a real route.
    p=tmp/'content/pages/proverka-publikacii.md'
    meta={'slug':'proverka-publikacii','section':'materialy','title':'Проверка публикации',
          'seo_title':'CMS — проверка новой страницы | Expert Team',
          'description':'Проверка добавления новой страницы через CMS с корректными метаданными и содержимым.',
          'h1':'ПРОВЕРКА_НОВОЙ_СТРАНИЦЫ_CMS','intro':'Проверка текстового редактора.','published':False,
          'editorial_status':'draft','related_services':['seo'],'cover_image':'','image_alt':'',
          'reviewed_by':'','reviewed_on':'','source_notes':''}
    body='## Новый раздел\n\n' + ('Обычный текст CMS для тестирования блока страницы. ' * 10)
    p.write_text('---\n'+yaml.safe_dump(meta,allow_unicode=True,sort_keys=False)+'---\n'+body,encoding='utf-8')
    run(tmp,'scripts/content_integrity.py')
    run(tmp,'build.py')
    run(tmp,'scripts/qa_check.py')
    text=(tmp/'dist/materialy/proverka-publikacii/index.html').read_text(encoding='utf-8')
    assert 'ПРОВЕРКА_НОВОЙ_СТРАНИЦЫ_CMS' in text
    assert 'noindex,nofollow' in text
    assert 'ТЕСТ_РЕДАКТИРОВАНИЯ_УСЛУГИ_CMS' in (tmp/'dist/uslugi/seo/index.html').read_text(encoding='utf-8')
    assert 'proverka-publikacii' not in (tmp/'dist/sitemap.xml').read_text(encoding='utf-8')
    print('OK: custom CMS page generated at /materialy/proverka-publikacii/; service JSON updated; noindex retained')
    # 3. Unsafe route prefix rejected before build.
    unsafe=p.read_text(encoding='utf-8').replace('section: materialy','section: uslugi')
    p.write_text(unsafe,encoding='utf-8')
    run(tmp,'scripts/content_integrity.py',success=False)
    print('OK: reserved service namespace rejected')
    # 4. Impossible to mark a page as publishable without reviewer + source notes.
    p.write_text(p.read_text(encoding='utf-8').replace('section: uslugi','section: materialy').replace('published: false','published: true'),encoding='utf-8')
    run(tmp,'scripts/content_integrity.py',success=False)
    print('OK: unapproved publication rejected')
    # 5. Production build also blocked when release authorization is absent.
    run(tmp,'build.py','--production',success=False)
    print('OK: production release gate works')
print('ALL CMS SMOKE TESTS PASSED')
