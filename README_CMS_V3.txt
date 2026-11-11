EXPERT TEAM CMS V3 — ВХОД ПО ЛОГИНУ И ПАРОЛЮ
================================================

Обновление к уже установленной CMS V2.1 (включая прямое сохранение).
Сотрудникам НЕ нужны GitHub-аккаунты. Они входят на:
https://expteam-staging.pages.dev/edit/

ВАЖНО: сначала настройте 4 переменные в Cloudflare, только затем загружайте патч.
Если загрузить патч до настройки, редактор V3 временно не сможет войти,
хотя обычный публичный сайт продолжит работать.

1. CLOUDFLARE — НАСТРОЙКА ПЕРЕМЕННЫХ
------------------------------------
Cloudflare Dashboard → Workers & Pages → expteam-staging →
Settings → Variables and Secrets → Add.

Выберите окружение Production. Создайте ровно эти 4 переменные:

ET_EDITOR_LOGIN          тип Text   — например expteam-editor
ET_EDITOR_PASSWORD       тип Secret — длинный уникальный пароль от 16 символов;
                                      лучше случайный, 24+ символа
ET_EDITOR_SESSION_SECRET тип Secret — независимая случайная строка 48+ символов
ET_EDITOR_GITHUB_TOKEN   тип Secret — GitHub Fine-grained personal access token

Для SESSION_SECRET создайте отдельный случайный ключ (НЕ повторяйте пароль).
В Windows PowerShell можно сгенерировать безопасное значение:
$b=New-Object byte[] 48; $rng=[Security.Cryptography.RandomNumberGenerator]::Create(); $rng.GetBytes($b); [Convert]::ToBase64String($b)

Все значения Secret сохраняйте только в Cloudflare (Encrypt). НЕ добавляйте
пароль и токен в GitHub, ZIP, чат или исходники сайта.

2. GITHUB — СЕРВЕРНЫЙ ТОКЕН
---------------------------
Зайдите в GitHub под владельцем репозитория (НЕ под сотрудником).
Settings → Developer settings → Personal access tokens → Fine-grained tokens
→ Generate new token.

Repository access: Only select repositories → ahatsmmalin-ai/expteam
Repository permissions → Contents: Read and write.
Других write-разрешений не нужно. Выберите осмысленный срок действия;
после истечения токен понадобится обновить в Cloudflare.

Скопируйте токен ОДИН РАЗ в Cloudflare как ET_EDITOR_GITHUB_TOKEN типа Secret.
Не показывайте его сотрудникам и не присылайте в чат.

3. ЗАГРУЗКА В GITHUB
--------------------
Распакуйте ZIP. Загрузите СОДЕРЖИМОЕ архива в КОРЕНЬ репозитория через
GitHub → Add file → Upload files. Структура должна получиться:

edit/index.html                    (обновляется)
edit/editor.js                     (обновляется)
functions/api/editor/[action].js   (новый файл)

Не удаляйте и не заменяйте content/, templates/, assets/, pages_build.py,
functions/api/auth.js, functions/api/callback.js и файлы обычной /admin/ CMS.
Нажмите Commit changes в main.

4. ПРОВЕРКА
------------
Cloudflare → expteam-staging → Deployments → последнее развёртывание Success.
Откройте https://expteam-staging.pages.dev/edit/ → Ctrl + Shift + R.
Должно быть CMS V3, поля Логин и Пароль.
Войдите под ET_EDITOR_LOGIN и ET_EDITOR_PASSWORD.
Выберите текст → измените → Сохранить изменения.
Проверьте появление коммита в main и обновление сайта после сборки.

БЕЗОПАСНОСТЬ
------------
• GitHub-токен используется исключительно серверной функцией;
  браузер его не получает.
• Сервер принимает записи только разрешённых текстовых полей из
  content/pages/*.json и content/global.json. Код сайта через редактор не меняется.
• Подписанная сессия в HttpOnly + Secure + SameSite=Strict cookie на 8 часов.
• Изменение ET_EDITOR_PASSWORD инвалидирует прежние сеансы.
• Защита от конфликтующих правок: при устаревшем файле нужно обновить редактор.
• Важно: общий логин не позволяет понять, какой из сотрудников сделал правку.
  Уволился сотрудник — поменяйте пароль для всей команды.
• Используйте длинный случайный пароль и при возможности ограничьте частоту
  запросов к /api/editor/login через отдельную защиту / rate limiting.
• Не публикуйте логин/пароль в общедоступных чатах, на сайте или в репозитории.
• После истечения срока токена GitHub потребуется его перевыпустить.
• Старую CMS /admin/ это обновление не отключает; её вход через GitHub
  по-прежнему доступен администраторам, которым ранее выдали права.
• Данный патч рассчитан на основной адрес expteam-staging.pages.dev. При
  переносе на другой домен серверную ORIGIN-константу потребуется изменить.

ТЕХНИЧЕСКАЯ ПРОВЕРКА
--------------------
Синтаксис обоих JS файлов проверен Node.js, сборка pages_build.py прошла:
38 CMS-страниц, 90 HTML-страниц, новая CMS V3 появилась в dist/edit/.
Локальные имитационные тесты проверили вход, отказ в неверном пароле,
подписанную сессию, чтение и сохранение JSON, защиту от устаревшей версии,
запрет неизвестного редактируемого поля, выход и инвалидирование при смене пароля.
Реальное развёртывание и API-запись с действующим токеном нужно проверить
после настройки в Cloudflare; заранее их нельзя считать подтверждёнными.
