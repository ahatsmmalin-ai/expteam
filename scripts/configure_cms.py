#!/usr/bin/env python3
"""Configure Github + OAuth / hosted Decap Turbo without storing any secrets."""
import argparse, re
from pathlib import Path
import yaml
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser(description='Заполнить конфигурацию редактора Expert Team')
p.add_argument('--repo',help='GitHub: owner/repo; нужно для обычного GitHub backend')
p.add_argument('--branch',default='main',help='Публикационная ветка (обычно main)')
p.add_argument('--auth-base-url',help='https://auth.example.com (если OAuth работает на отдельном сервере)')
p.add_argument('--turbo-site-id',help='ID сайта из Decap Turbo; вместо отдельного OAuth')
a=p.parse_args()
if bool(a.repo)==bool(a.turbo_site_id):p.error('Выберите либо --repo, либо --turbo-site-id')
if a.repo and not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+',a.repo):p.error('--repo должен быть формата owner/repo')
if a.auth_base_url and not re.fullmatch(r'https://[A-Za-z0-9_.:-]+/?',a.auth_base_url):p.error('OAuth URL должен быть HTTPS и без пути /auth')
if a.turbo_site_id and not re.fullmatch(r'[a-fA-F0-9-]{20,60}',a.turbo_site_id):p.error('Turbo site ID должен быть UUID')
if a.turbo_site_id and a.auth_base_url:p.error('В режиме Turbo отдельный OAuth base_url не используется')
config=ROOT/'static/admin/config.yml';data=yaml.safe_load(config.read_text(encoding='utf-8'))
if a.turbo_site_id:data['backend']={'name':'turbo-github','turbo_site_id':a.turbo_site_id,'branch':a.branch}
else:
    data['backend']={'name':'github','repo':a.repo,'branch':a.branch,'squash_merges':True}
    if a.auth_base_url:data['backend']['base_url']=a.auth_base_url.rstrip('/')
config.write_text('# Конфигурация Decap CMS. Секреты OAuth нельзя хранить здесь.\n'+yaml.safe_dump(data,sort_keys=False,allow_unicode=True,width=100),encoding='utf-8')
print('CMS настроена для',data['backend']['name'],a.repo or a.turbo_site_id)
print('Далее: проверьте права репозитория, OAuth/Turbo и тестовую сборку /admin/.')
