/**
 * Expert Team CMS V3, Cloudflare Pages Functions.
 * Single shared username/password with signed, HttpOnly session cookies.
 * The GitHub Contents-write credential NEVER reaches the browser.
 * Required production Cloudflare bindings (all Secrets except username):
 * ET_EDITOR_LOGIN, ET_EDITOR_PASSWORD, ET_EDITOR_SESSION_SECRET, ET_EDITOR_GITHUB_TOKEN.
 */
const ORIGIN = 'https://expteam-staging.pages.dev';
const REPO = 'ahatsmmalin-ai/expteam';
const GH_API = `https://api.github.com/repos/${REPO}`;
const COOKIE = '__Host-et_editor_v3';
const TTL_SECONDS = 8 * 60 * 60;
const te = new TextEncoder();
const td = new TextDecoder();

function json(data, status = 200, extraHeaders = {}) {
  return new Response(JSON.stringify(data), {
    status,
    headers: {
      'Content-Type': 'application/json; charset=utf-8',
      'Cache-Control': 'no-store, max-age=0',
      'X-Content-Type-Options': 'nosniff',
      'Referrer-Policy': 'no-referrer',
      ...extraHeaders
    }
  });
}
function error(message, status = 400) { return json({error: message}, status); }
function required(env) {
  return typeof env.ET_EDITOR_LOGIN === 'string' && env.ET_EDITOR_LOGIN.length >= 2 &&
    typeof env.ET_EDITOR_PASSWORD === 'string' && env.ET_EDITOR_PASSWORD.length >= 16 &&
    typeof env.ET_EDITOR_SESSION_SECRET === 'string' && env.ET_EDITOR_SESSION_SECRET.length >= 32 &&
    typeof env.ET_EDITOR_GITHUB_TOKEN === 'string' && env.ET_EDITOR_GITHUB_TOKEN.length >= 20;
}
function b64url(bytes) {
  let binary = '';
  for (let i = 0; i < bytes.length; i += 8192) {
    binary += String.fromCharCode(...bytes.subarray(i, i + 8192));
  }
  return btoa(binary).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/g, '');
}
function fromB64url(value) {
  if (!/^[\w-]{1,2400}$/.test(value)) throw new Error('bad encoding');
  let s = value.replace(/-/g, '+').replace(/_/g, '/');
  s += '='.repeat((4 - s.length % 4) % 4);
  const binary = atob(s);
  return Uint8Array.from(binary, c => c.charCodeAt(0));
}
async function digest(value) {
  return new Uint8Array(await crypto.subtle.digest('SHA-256', te.encode(value)));
}
function equalBytes(a, b) {
  if (a.length !== b.length) return false;
  let different = 0;
  for (let i = 0; i < a.length; i++) different |= a[i] ^ b[i];
  return different === 0;
}
async function equalStrings(a, b) {
  return equalBytes(await digest(a), await digest(b));
}
async function signingKey(env) {
  return crypto.subtle.importKey('raw', te.encode(env.ET_EDITOR_SESSION_SECRET),
    {name: 'HMAC', hash: 'SHA-256'}, false, ['sign', 'verify']);
}
async function sign(env, value) {
  return new Uint8Array(await crypto.subtle.sign('HMAC', await signingKey(env), te.encode(value)));
}
async function passwordVersion(env) {
  const proof = await sign(env, 'password-version:' + env.ET_EDITOR_PASSWORD);
  return b64url(proof.subarray(0, 16));
}
async function createCookie(env) {
  const payload = {
    sub: env.ET_EDITOR_LOGIN,
    exp: Math.floor(Date.now() / 1000) + TTL_SECONDS,
    ver: await passwordVersion(env)
  };
  const data = b64url(te.encode(JSON.stringify(payload)));
  return `${data}.${b64url(await sign(env, data))}`;
}
function cookieFrom(request) {
  const header = request.headers.get('Cookie') || '';
  const entry = header.split(';').map(x => x.trim()).find(x => x.startsWith(COOKIE + '='));
  return entry ? entry.slice(COOKIE.length + 1) : null;
}
async function currentUser(request, env) {
  const raw = cookieFrom(request);
  if (!raw || raw.length > 2500) return null;
  const parts = raw.split('.');
  if (parts.length !== 2) return null;
  try {
    const key = await signingKey(env);
    const okay = await crypto.subtle.verify('HMAC', key, fromB64url(parts[1]), te.encode(parts[0]));
    if (!okay) return null;
    const payload = JSON.parse(td.decode(fromB64url(parts[0])));
    if (!payload || !Number.isInteger(payload.exp) || payload.exp <= Date.now() / 1000) return null;
    if (payload.exp > Date.now() / 1000 + TTL_SECONDS + 30) return null;
    if (payload.sub !== env.ET_EDITOR_LOGIN || payload.ver !== await passwordVersion(env)) return null;
    return payload.sub;
  } catch (_) { return null; }
}
const sessionCookie = value =>
  `${COOKIE}=${value}; Path=/; HttpOnly; Secure; SameSite=Strict; Max-Age=${TTL_SECONDS}`;
const clearCookie = `${COOKIE}=; Path=/; HttpOnly; Secure; SameSite=Strict; Max-Age=0`;

async function bodyJSON(request, limit = 1000000) {
  if (!(request.headers.get('Content-Type') || '').toLowerCase().startsWith('application/json')) {
    throw new Error('Требуется JSON');
  }
  const len = Number(request.headers.get('Content-Length') || 0);
  if (len > limit) throw new Error('Слишком большой запрос');
  const raw = await request.text();
  if (raw.length > limit) throw new Error('Слишком большой запрос');
  try { return JSON.parse(raw); } catch (_) { throw new Error('Некорректный JSON'); }
}
async function github(env, path, options = {}) {
  const response = await fetch(GH_API + path, {
    method: options.method || 'GET',
    headers: {
      'Accept': 'application/vnd.github+json',
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${env.ET_EDITOR_GITHUB_TOKEN}`,
      'X-GitHub-Api-Version': '2022-11-28',
      'User-Agent': 'ExpertTeam-Visual-CMS'
    },
    body: options.body ? JSON.stringify(options.body) : undefined,
    redirect: 'error'
  });
  let data;
  try { data = await response.json(); } catch (_) { data = {}; }
  if (!response.ok) {
    const publicMessage = response.status === 403 ? 'GitHub не разрешает запись в main. Проверьте права токена и защиту ветки.' :
      response.status === 409 || response.status === 422 ? 'Параллельное обновление GitHub. Перезагрузите редактор.' :
      response.status === 401 ? 'Неверный или просроченный серверный токен GitHub.' :
      'GitHub вернул ошибку HTTP ' + response.status;
    const e = new Error(publicMessage);
    e.status = response.status >= 500 ? 502 : 409;
    throw e;
  }
  return data;
}
function decodeContent(s) {
  const binary = atob(s.replace(/\s/g, ''));
  const bytes = Uint8Array.from(binary, c => c.charCodeAt(0));
  return JSON.parse(td.decode(bytes));
}
async function getFile(env, path) {
  const url = '/contents/' + path.split('/').map(encodeURIComponent).join('/') + '?ref=main';
  const out = await github(env, url);
  if (out.type !== 'file' || typeof out.content !== 'string') throw new Error('Нет файла контента');
  return {data: decodeContent(out.content), sha: out.sha};
}
async function getPagePath(context, route) {
  if (typeof route !== 'string' || route.length > 200 || !route.startsWith('/') || !route.endsWith('/')) return null;
  // Only editor-supported routes may be changed; the manifest is from the site's deployed assets.
  const url = new URL('/edit/manifest.json', ORIGIN);
  const asset = await context.env.ASSETS.fetch(new Request(url, {headers:{'Accept':'application/json'}}));
  if (!asset.ok) throw new Error('Не удалось прочитать карту страниц редактора');
  const manifest = await asset.json();
  const path = manifest?.pages?.[route]?.path;
  if (typeof path !== 'string' || !/^content\/pages\/[a-zA-Z0-9_-]+\.json$/.test(path)) return null;
  return path;
}
function editableArray(data, scope) {
  return scope === 'global' ? data?.entries : data?.sections?.flatMap(section => section.items || []);
}
function applyChanges(doc, changes, scope) {
  const items = editableArray(doc, scope);
  if (!Array.isArray(items)) throw new Error('Ошибка структуры контента');
  const ids = new Map(items.map(item => [item.id, item]));
  for (const change of changes) {
    const item = ids.get(change.id);
    if (!item) throw new Error('Неизвестный редактируемый фрагмент');
    if (typeof item.value !== 'string') throw new Error('Поле нельзя редактировать');
    item.value = change.value;
  }
}
async function save(context, username) {
  const {request, env} = context;
  const payload = await bodyJSON(request);
  if (!payload || typeof payload !== 'object' || !Array.isArray(payload.changes) ||
      payload.changes.length < 1 || payload.changes.length > 200 || typeof payload.route !== 'string') {
    return error('Некорректный список изменений');
  }
  const path = await getPagePath(context, payload.route);
  if (!path) return error('Страница не разрешена для редактирования', 403);
  const grouped = {page: [], global: []};
  const seen = new Set();
  for (const item of payload.changes) {
    if (!item || !['page', 'global'].includes(item.scope) ||
      typeof item.id !== 'string' || item.id.length > 80 ||
      typeof item.value !== 'string' || item.value.length > 20000 ||
      seen.has(item.scope + ':' + item.id)) return error('Некорректный текст изменения');
    seen.add(item.scope + ':' + item.id);
    grouped[item.scope].push(item);
  }
  const scopes = ['page', 'global'].filter(s => grouped[s].length);
  const paths = {page:path, global:'content/global.json'};
  const expected = payload.sha || {};
  for (const scope of scopes) if (typeof expected[scope] !== 'string' || !/^[a-f0-9]{40}$/.test(expected[scope])) {
    return error('Некорректная версия файла');
  }
  const ref = await github(env, '/git/ref/heads/main');
  const head = ref.object?.sha;
  if (!head) throw new Error('Не удалось прочитать состояние main');
  const commitDetails = await github(env, '/git/commits/' + head);
  const current = await Promise.all(scopes.map(scope => getFile(env, paths[scope])));
  const treeEntries = [];
  for (let i = 0; i < scopes.length; i++) {
    const scope = scopes[i];
    if (current[i].sha !== expected[scope]) {
      return error('Этот файл уже изменил другой сотрудник. Обновите страницу перед сохранением.', 409);
    }
    const doc = current[i].data;
    applyChanges(doc, grouped[scope], scope);
    treeEntries.push({path: paths[scope], mode:'100644', type:'blob', content:JSON.stringify(doc, null, 2) + '\n'});
  }
  const tree = await github(env, '/git/trees', {
    method:'POST', body:{base_tree:commitDetails.tree.sha, tree:treeEntries}
  });
  const commit = await github(env, '/git/commits', {
    method:'POST', body:{
      message:`CMS: ${payload.route.slice(0, 110)} (${payload.changes.length} изменений; ${username})`,
      tree:tree.sha, parents:[head]
    }
  });
  await github(env, '/git/refs/heads/main', {method:'PATCH', body:{sha:commit.sha, force:false}});
  return json({ok:true, commit:commit.sha, commitUrl:`https://github.com/${REPO}/commit/${commit.sha}`});
}

export async function onRequest(context) {
  const {request, env, params} = context;
  const action = params.action;
  const url = new URL(request.url);
  if (url.origin !== ORIGIN) return error('Используйте основной адрес редактора', 403);
  if (!['login', 'session', 'logout', 'content', 'save'].includes(action)) return error('Не найдено', 404);
  if (!required(env)) return error('Сервер CMS V3 ещё не настроен: проверьте секреты Cloudflare', 503);
  if (request.method !== (['login', 'logout', 'save'].includes(action) ? 'POST' : 'GET')) {
    return error('Метод не поддерживается', 405);
  }
  if (request.method === 'POST') {
    if (request.headers.get('Origin') !== ORIGIN || request.headers.get('X-ET-Editor') !== 'v3') {
      return error('Недопустимый источник запроса', 403);
    }
  }
  try {
    if (action === 'login') {
      const input = await bodyJSON(request, 2048);
      const user = typeof input?.username === 'string' ? input.username : '';
      const pass = typeof input?.password === 'string' ? input.password : '';
      if (user.length > 100 || pass.length > 256) return error('Неверный логин или пароль', 401);
      // Generic reply for both wrong login/password. Credentials are stored only in encrypted CF secrets.
      const [userOK, passOK] = await Promise.all([
        equalStrings(user, env.ET_EDITOR_LOGIN),
        equalStrings(pass, env.ET_EDITOR_PASSWORD)
      ]);
      if (!userOK || !passOK) return error('Неверный логин или пароль', 401);
      return json({ok:true, username:env.ET_EDITOR_LOGIN}, 200,
        {'Set-Cookie':sessionCookie(await createCookie(env))});
    }
    if (action === 'logout') return json({ok:true}, 200, {'Set-Cookie':clearCookie});
    const user = await currentUser(request, env);
    if (!user) return error('Необходимо войти в редактор', 401);
    if (action === 'session') return json({ok:true, username:user});
    if (action === 'content') {
      const path = await getPagePath(context, url.searchParams.get('route'));
      if (!path) return error('Страница не разрешена для редактирования', 403);
      const [page, global] = await Promise.all([getFile(env, path), getFile(env, 'content/global.json')]);
      return json({page, global});
    }
    if (action === 'save') return await save(context, user);
  } catch (e) {
    const response = e?.status || 500;
    // Server-side diagnostics: never print request bodies, cookies, credentials or tokens.
    console.error('[ExpertTeam CMS V3]', 'action=' + action, 'status=' + response,
      'error=' + String(e?.name || 'Error'), 'message=' + String(e?.message || 'Unknown error'),
      'stack=' + String(e?.stack || 'not available'));
    const message = response === 500 ? 'Внутренняя ошибка редактора; проверьте журналы функций Cloudflare.' : String(e.message);
    return error(message, response);
  }
  return error('Не найдено', 404);
}
