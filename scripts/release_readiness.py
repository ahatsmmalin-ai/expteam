#!/usr/bin/env python3
"""Fail closed: a production/indexable site requires explicit release approval."""
from __future__ import annotations
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = {
    'legal_policy_approved': 'Утверждена политика персональных данных',
    'forms_and_crm_verified': 'Тестовые заявки доставляются в CRM безопасно',
    'cases_and_reviews_confirmed': 'Кейсы и отзывы подтверждены',
    'prices_confirmed': 'Цены и тарифы согласованы',
    'team_and_authors_confirmed': 'Согласованы реальные сотрудники и авторы',
    'seo_review_approved': 'SEO-редактор утвердил материалы и метатеги',
    'migration_redirects_checked': 'Проверена миграция URL/301-редиректы',
}


def examine():
    path = ROOT / 'content/release.json'
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
    except (FileNotFoundError, json.JSONDecodeError) as ex:
        return [f'Не удалось прочитать {path}: {ex}']
    failures = []
    if data.get('status') != 'approved':
        failures.append('Статус релиза не approved')
    if not data.get('approved_by'):
        failures.append('Не указан утвердивший релиз')
    if not data.get('approval_date'):
        failures.append('Не указана дата утверждения')
    for key, desc in REQUIRED.items():
        if data.get(key) is not True:
            failures.append(desc)
    return failures


def main():
    errors = examine()
    if errors:
        print('Эксперт Тим — публичный релиз заблокирован (ожидаемые пункты):')
        for i,e in enumerate(errors, 1):print(f'{i:02d}. {e}')
        raise SystemExit(1)
    print('Контентный чек-лист пройден. Проверьте права доступа, DNS, HTTPS и CI/CD отдельно.')

if __name__ == '__main__': main()
