EXPERT TEAM — CMS v1 / ПОСЛЕ ВЕРСИИ V8
====================================

ЭТО ИСХОДНЫЙ ПРОЕКТ ДЛЯ GITHUB + CLOUDFLARE PAGES.
Его НЕ открывают двойным кликом на index.html:
страницы собираются из templates/ + content/ командой pages_build.py.

1. Распакуйте ZIP и загрузите его содержимое в корень GitHub:
   https://github.com/ahatsmmalin-ai/expteam (ветка main).
   Старые файлы в репозитории можно не удалять: новый pages_build.py использует только templates/ и content/.
   НЕ загружайте секреты OAuth в GitHub.

2. В Cloudflare Pages проект expteam-staging:
   Build command: pip install -r requirements.txt && python pages_build.py
   Build output directory: dist
   Root directory: пусто
   Environment: Production
   PYTHON_VERSION: 3.12

3. Подключите авторизацию GitHub по инструкции CMS_SETUP.md.
   Пока ключи не добавлены, /admin/ уже открывается, но вход не заработает.

4. Админка после настройки OAuth:
   https://expteam-staging.pages.dev/admin/

5. Файл content/pages/home.json — тексты главной. Остальные файлы — разделы,
   кейсы и статьи. content/global.json — общее меню/подвал/формы.
   content/media.json — реальный логотип, фото, письма, кейсы.
   content/contacts.json — контактные ссылки.

6. Файлы в templates/ — внешний вид HTML.
   Изменения в них не должны перезаписывать content/.

7. Это публичный тестовый сайт с noindex, а не закрытая корпоративная панель.
   Не загружайте конфиденциальные клиентские данные, если репозиторий публичный.
   Подключение CMS не включает интеграцию с CRM или приём заявок.

Сначала проверьте тестовую публикацию и сделайте ОДНО контрольное редактирование
в админке; затем приглашайте редакторов.
