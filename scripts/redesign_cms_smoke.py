#!/usr/bin/env python3
"""Test content-to-page propagation without GitHub OAuth or actual publishing."""
from __future__ import annotations
import json,os,subprocess,sys,tempfile,shutil
from pathlib import Path
import yaml
ROOT=Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(prefix='et-redesign-cms-') as d:
 t=Path(d)
 (t/'docs').mkdir()
 for name in ['build.py','templates','content','static']:
  p=ROOT/name
  shutil.copytree(p,t/name,ignore=shutil.ignore_patterns('__pycache__')) if p.is_dir() else shutil.copy2(p,t/name)
 data=t/'content/redesign.json';j=json.loads(data.read_text('utf8'))
 j['hero_title']='ТЕСТ_CMS_ИЗМЕНЕНИЕ_ПЕРВОГО_ЭКРАНА'
 j['solutions'][0]['headline']='ТЕСТ_CMS_НОВЫЙ_ЗАГОЛОВОК_УСЛУГИ'
 data.write_text(json.dumps(j,ensure_ascii=False,indent=2),'utf8')
 case=t/'content/redesign_cases.json';j=json.loads(case.read_text('utf8'))
 j['items'][0]['metric']='ТЕСТ_КЕЙСА_CMS'
 case.write_text(json.dumps(j,ensure_ascii=False,indent=2),'utf8')
 l=t/'content/letters.json';j=json.loads(l.read_text('utf8'));j['items'][0]['name']='ТЕСТ_ПИСЬМА_CMS';l.write_text(json.dumps(j,ensure_ascii=False,indent=2),'utf8')
 p=t/'content/pages/proverka-redaktora.md'
 p.write_text('---\n'+yaml.safe_dump(dict(title='Проверка CMS',slug='proverka-redaktora',section='materialy',seo_title='Проверка CMS',description='Проверка, что страницы появляются после сборки',h1='ТЕСТ_НОВОЙ_CMS_СТРАНИЦЫ',intro='Новый материал',published=False,editorial_status='draft'),allow_unicode=True)+'---\n## Новый материал\n\nСоздано для внутренней проверки.',encoding='utf8')
 result=subprocess.run([sys.executable,'build.py'],cwd=t,env={**os.environ,'EXPERTTEAM_GO_LIVE':''},text=True,capture_output=True)
 assert result.returncode==0,result.stderr
 assert 'ТЕСТ_CMS_ИЗМЕНЕНИЕ_ПЕРВОГО_ЭКРАНА' in (t/'dist/index.html').read_text('utf8')
 assert 'ТЕСТ_CMS_НОВЫЙ_ЗАГОЛОВОК_УСЛУГИ' in (t/'dist/resheniya/kompleksnyj-marketing/index.html').read_text('utf8')
 assert 'ТЕСТ_КЕЙСА_CMS' in (t/'dist/kejsy/gorodskoj-evakuator/index.html').read_text('utf8')
 assert 'ТЕСТ_ПИСЬМА_CMS' in (t/'dist/index.html').read_text('utf8')
 assert 'ТЕСТ_НОВОЙ_CMS_СТРАНИЦЫ' in (t/'dist/materialy/proverka-redaktora/index.html').read_text('utf8')
 assert 'noindex' in (t/'dist/index.html').read_text('utf8')
 deny=subprocess.run([sys.executable,'build.py','--production'],cwd=t,env={**os.environ,'EXPERTTEAM_GO_LIVE':''},text=True,capture_output=True)
 assert deny.returncode!=0,'Production build incorrectly unblocked'
print('CMS DATA SMOKE OK: solution, case, letter, new page; production guard. GitHub OAuth NOT tested.')
