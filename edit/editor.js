/* Expert Team CMS V3.1 — reliable text selection, page data sync, private server API. */
(() => {
  'use strict';
  const ORIGIN = location.origin;
  const API = '/api/editor';
  const $ = id => document.getElementById(id);
  const frame = $('siteFrame');
  const app = {
    manifest: null, loggedIn: false, username: '', route: '/',
    original: {page:null, global:null}, draft:{page:null,global:null},
    files: {page:null, global:'content/global.json'}, sha:{page:null,global:null},
    selected:null, busy:false
  };
  const deepClone = obj => JSON.parse(JSON.stringify(obj));
  const caption = (value, max=76) => String(value||'').trim().slice(0,max);
  const show = (id,yes) => $(id).classList.toggle('hidden',!yes);
  const status = (message,isError=false,withLink=null) => {
    const box=$('result'); box.replaceChildren();
    box.appendChild(document.createTextNode(message));
    if(withLink){const a=document.createElement('a');a.href=withLink;a.target='_blank';a.rel='noopener noreferrer';a.textContent='Посмотреть историю изменений ↗';box.appendChild(document.createElement('br'));box.appendChild(a)}
    box.classList.toggle('error',isError);show('result',!!message);
  };
  const arrPage = data => Array.isArray(data?.sections)
    ? data.sections.flatMap(section => Array.isArray(section.items) ? section.items : []) : [];
  const arrGlobal = data => Array.isArray(data?.entries) ? data.entries : [];
  const scopeItems = (scope, data) => scope==='global' ? arrGlobal(data) : arrPage(data);
  function getItem(scope,key,which='draft'){
    const data=app[which][scope];
    return scopeItems(scope,data).find(x=>String(x.id)===String(key))||null;
  }
  const allChanges = () => {
    const changes=[];
    for (const scope of ['page','global']) {
      for (const item of (scope==='page'?arrPage(app.draft.page):arrGlobal(app.draft.global))){
        const old=getItem(scope,item.id,'original');
        if(old && String(item.value??'')!==String(old.value??''))changes.push({scope,id:item.id,label:item.label||item.id,old:old.value,new:item.value});
      }
    }
    return changes;
  };
  function syncControls(){
    const count=allChanges().length;
    $('changeCount').textContent=count+' '+(count===1?'изменение':count>=2&&count<=4?'изменения':'изменений');
    $('changeSummary').textContent=count?`Изменено фрагментов: ${count}. Нажмите «Сохранить изменения», чтобы опубликовать.`:'Изменений нет';
    $('saveButton').disabled=count===0||app.busy;
    $('discardButton').disabled=count===0||app.busy;
  }
  function authUI(){
    const logged=app.loggedIn;
    show('loginButton',!logged);show('logoutButton',logged);
    show('guestPanel',!logged);show('savePanel',logged);
    show('selectPanel',logged&&!app.selected);show('editPanel',logged&&!!app.selected);
    $('identity').textContent=logged?`Редактор: ${app.username}`:'Вход не выполнен';
    $('infoText').textContent=logged?'Наведите курсор на текст и нажмите ✎, чтобы изменить его.':'Войдите по логину и паролю, чтобы править тексты на сайте.';
    syncControls();
  }
  function pageRoute(url){
    if(url.origin!==ORIGIN)return null;
    let path=url.pathname.replace(/\/index\.html$/,'/');
    if(path.endsWith('.html')&&path!=='/index.html')return null;
    if(!path.endsWith('/'))path+='/';
    return app.manifest?.pages?.[path]?path:null;
  }
  const request = async (path,options={}) => {
    const res = await fetch(API + path, {
      method: options.method || 'GET',
      credentials: 'same-origin',
      cache: 'no-store',
      headers: {
        'Accept':'application/json',
        ...(options.body ? {'Content-Type':'application/json', 'X-ET-Editor':'v3'} : {})
      },
      body: options.body ? JSON.stringify(options.body) : undefined
    });
    let response;
    try {response = await res.json()} catch(_) {response = {}}
    if (!res.ok) {
      if (res.status === 401 && path !== '/login') {
        app.loggedIn = false;
        app.username = '';
        authUI();
      }
      throw new Error(response?.error || `Ошибка сервера (HTTP ${res.status})`);
    }
    return response;
  };
  async function loadGithubContent(){
    if(!app.loggedIn)return;
    const info=app.manifest.pages[app.route];
    if(!info)throw new Error('Неизвестный маршрут страницы');
    const result=await request('/content?route='+encodeURIComponent(app.route));
    app.files.page=info.path;
    app.sha.page=result.page.sha; app.sha.global=result.global.sha;
    if(!Array.isArray(result.page?.data?.sections) || !Array.isArray(result.global?.data?.entries)) {
      throw new Error('Ответ содержит неправильную структуру текстов. Проверьте content/pages и content/global.json в GitHub.');
    }
    app.original.page=result.page.data; app.original.global=result.global.data;
    app.draft.page=deepClone(result.page.data); app.draft.global=deepClone(result.global.data);
    app.selected=null;authUI();
  }
  function updatePreview(scope,key,value){
    const d=frame.contentDocument;
    if(!d)return;
    // In the unlikely case that a preview came from an earlier build, keep
    // its marker key separate from the current GitHub content ID.
    const visibleKey=app.selected?.scope===scope && app.selected?.key===key
      ? app.selected.previewKey : key;
    d.querySelectorAll(`[data-et-scope="${scope}"][data-et-key="${visibleKey}"]`).forEach(n=>{n.textContent=value});
  }
  let selectionVersion=0;
  async function chooseItem(scope,key,marker=null){
    if(!app.loggedIn){status('Сначала войдите по логину и паролю.');return}
    if(scope!=='page' && scope!=='global')return;
    key=String(key||'');
    const version=++selectionVersion;
    let item=getItem(scope,key);
    // This happens when the user clicks before Github content finishes loading,
    // or when Cloudflare's HTML and Github main are momentarily out of sync.
    if(!item && !app.busy && allChanges().length===0){
      status('Синхронизирую тексты страницы…');
      try {await loadGithubContent()} catch(e) {
        status('Не удалось загрузить тексты страницы: '+e.message,true);return;
      }
      if(version!==selectionVersion || !app.loggedIn)return;
      item=getItem(scope,key);
    }
    let resolvedKey=key;
    if(!item && marker){
      // Fallback only for a *unique exact* text match, never for approximate
      // similarity. Otherwise there is a risk of changing the wrong field.
      const text=String(marker.textContent||'').trim();
      const matches=scopeItems(scope,app.draft[scope]).filter(x=>String(x.value??'').trim()===text);
      if(text && matches.length===1){item=matches[0];resolvedKey=String(item.id)}
    }
    if(!item){
      const pageCount=arrPage(app.draft.page).length;
      const globalCount=arrGlobal(app.draft.global).length;
      status(`Не удалось связать этот текст с CMS (страница ${app.route}, поле ${scope}:${key}; загружено ${pageCount} текстов страницы и ${globalCount} общих). Обновите редактор. Если ошибка останется — сообщите эти цифры.`,true);
      return;
    }
    app.selected={scope,key:resolvedKey,previewKey:key};
    $('editLabel').textContent=caption(item.label||item.value,140)||'Текст';
    $('editScope').textContent=scope==='global'?'Общий текст — на всех страницах':'Текст этой страницы';
    $('editValue').value=String(item.value??'');
    frame.contentDocument?.querySelectorAll('.et-edit-selected').forEach(n=>n.classList.remove('et-edit-selected'));
    frame.contentDocument?.querySelectorAll(`[data-et-scope="${scope}"][data-et-key="${key}"]`).forEach(n=>n.classList.add('et-edit-selected'));
    authUI();
    status('');
  }
  async function loadRoute(route,ignoreChanges=false){
    if(!app.manifest?.pages?.[route]){status('Эта страница пока не поддерживается визуальным редактором. Её можно открыть в обычной CMS.',true);return}
    if(!ignoreChanges&&allChanges().length&&!confirm('Есть несохранённые изменения. Перейти на другую страницу и отменить их?'))return;
    app.route=route;app.selected=null;
    const entry=app.manifest.pages[route];
    $('pageTitle').textContent=entry.title;
    $('currentUrl').textContent=route;
    $('pagePicker').value=route;
    status('');
    frame.src=entry.preview;
    if(app.loggedIn){
      try{await loadGithubContent()}catch(e){status('Не удалось загрузить тексты страницы: '+e.message,true)}
    }
    authUI();
  }
  function bindFrame(){
    let d;
    try{d=frame.contentDocument;if(!d||!d.body)return}catch(_){status('Нет доступа к предпросмотру. Откройте редактор на основном адресе staging.',true);return}
    d.addEventListener('click',evt=>{
      const marker=evt.target.closest?.('[data-et-key]');
      if(marker){
        evt.preventDefault();evt.stopPropagation();
        chooseItem(marker.dataset.etScope,marker.dataset.etKey,marker);return;
      }
      const navToggle=evt.target.closest?.('.nav-trigger');
      if(navToggle){
        evt.preventDefault();evt.stopPropagation();
        const parent=navToggle.closest('.nav-dropdown');
        const open=!parent?.classList.contains('is-open');
        parent?.classList.toggle('is-open',open);
        navToggle.setAttribute('aria-expanded',String(open));
        return;
      }
      const mobileToggle=evt.target.closest?.('.mobile-menu-btn');
      if(mobileToggle){
        evt.preventDefault();evt.stopPropagation();
        const menu=d.getElementById('mobileNav');
        if(menu){menu.hidden=!menu.hidden;mobileToggle.setAttribute('aria-expanded',String(!menu.hidden))}
        return;
      }
      const a=evt.target.closest?.('a[href]');
      if(a){
        const u=new URL(a.href,d.baseURI);
        if(u.origin!==ORIGIN){evt.preventDefault();evt.stopPropagation();window.open(u.href,'_blank','noopener,noreferrer');return}
        const route=pageRoute(u);
        if(route){evt.preventDefault();evt.stopPropagation();
          if(route===app.route && u.hash){d.getElementById(decodeURIComponent(u.hash.slice(1)))?.scrollIntoView();return}
          loadRoute(route);return;
        }
        if(u.pathname.startsWith('/edit-preview/')||u.pathname.startsWith('/admin/'))return;
        evt.preventDefault();evt.stopPropagation();
        status('Эту страницу удобнее открыть в обычной CMS: '+u.pathname,true);
      }
    },true);
    const current=app.selected;
    if(current){
      const selected=getItem(current.scope,current.key);
      if(selected)updatePreview(current.scope,current.key,String(selected.value??''));
    }
  }
  async function login(){
    const username=$('loginUsername').value.trim();
    const password=$('loginPassword').value;
    if (!username || !password) {status('Введите логин и пароль.',true);return}
    $('guestLoginButton').disabled=true;
    status('Проверяю логин и пароль…');
    try{
      const result=await request('/login',{method:'POST',body:{username,password}});
      app.loggedIn=true; app.username=result.username;
      $('loginPassword').value='';
      await loadGithubContent();
      authUI();status('Вход выполнен. Выберите текст на странице и измените его.');
    }catch(e){
      app.loggedIn=false;app.username='';authUI();
      status('Не удалось войти: '+e.message,true);
    }finally{$('guestLoginButton').disabled=false}
  }
  async function logout(){
    if(allChanges().length&&!confirm('Выйти и отменить несохранённые изменения?'))return;
    try {await request('/logout',{method:'POST',body:{}})} catch(_) {}
    app.loggedIn=false;app.username='';app.original.page=null;app.original.global=null;
    app.draft.page=null;app.draft.global=null;app.selected=null;
    authUI();status('Вы вышли из редактора.');
    frame.src=app.manifest.pages[app.route].preview;
  }
  async function save(){
    const changes=allChanges();
    if(!changes.length||!app.loggedIn||app.busy)return;
    app.busy=true;
    syncControls();
    status('Сохраняю изменения…');
    try{
      const result=await request('/save',{
        method:'POST',
        body:{
          route:app.route,
          sha:app.sha,
          changes:changes.map(c=>({scope:c.scope,id:c.id,value:String(c.new)}))
        }
      });
      const selected=app.selected;
      try{
        await loadGithubContent();
        if(selected&&getItem(selected.scope,selected.key))await chooseItem(selected.scope,selected.previewKey,frame.contentDocument?.querySelector(`[data-et-scope="${selected.scope}"][data-et-key="${selected.previewKey}"]`));
      }catch(refreshError){
        app.original.page=deepClone(app.draft.page);
        app.original.global=deepClone(app.draft.global);
        status('Изменения сохранены. Обновите редактор перед следующей правкой.',false,result.commitUrl);
        return;
      }
      status('Изменения сохранены! Cloudflare автоматически обновит сайт после сборки.',false,result.commitUrl);
    }catch(e){status('Не удалось сохранить изменения: '+e.message,true)}
    finally{app.busy=false;syncControls()}
  }
  $('loginButton').addEventListener('click',()=>{$('loginUsername').focus();$('guestPanel').scrollIntoView({block:'nearest',behavior:'smooth'})});
  $('loginForm').addEventListener('submit',ev=>{ev.preventDefault();login()});
  $('logoutButton').addEventListener('click',logout);
  $('siteFrame').addEventListener('load',bindFrame);
  $('editValue').addEventListener('input',ev=>{
    if(!app.selected)return;
    const {scope,key}=app.selected;
    const item=getItem(scope,key);
    if(!item)return;
    item.value=ev.target.value;
    updatePreview(scope,key,item.value);
    syncControls();
  });
  $('resetField').addEventListener('click',()=>{
    if(!app.selected)return;
    const {scope,key}=app.selected;
    const item=getItem(scope,key),original=getItem(scope,key,'original');
    if(!item||!original)return;
    item.value=String(original.value??'');
    $('editValue').value=item.value;updatePreview(scope,key,item.value);syncControls();
  });
  $('discardButton').addEventListener('click',()=>{
    if(!confirm('Отменить все несохранённые правки на этой странице?'))return;
    app.draft.page=deepClone(app.original.page);app.draft.global=deepClone(app.original.global);
    frame.src=app.manifest.pages[app.route].preview;
    app.selected=null;authUI();status('Изменения отменены.');
  });
  $('saveButton').addEventListener('click',save);
  $('pagePicker').addEventListener('change',ev=>loadRoute(ev.target.value));
  window.addEventListener('beforeunload',ev=>{if(allChanges().length){ev.preventDefault();ev.returnValue=''}});
  (async()=>{
    try{
      const r=await fetch('/edit/manifest.json',{cache:'no-store'});
      if(!r.ok)throw new Error('Нет карты страниц');
      app.manifest=await r.json();
      if(!app.manifest.pages['/'])throw new Error('Отсутствует главная');
      const picker=$('pagePicker');picker.replaceChildren();
      const names=Object.keys(app.manifest.pages).sort((a,b)=>a==='/'?-1:b==='/'?1:a.localeCompare(b,'ru'));
      for(const route of names){const opt=document.createElement('option');opt.value=route;opt.textContent=(route==='/'?'Главная':route.replace(/^\//,'').replace(/\/$/,'').replace(/-/g,' '));picker.appendChild(opt)}
      const initial=new URLSearchParams(location.search).get('page');
      try{
        const session=await request('/session');
        app.loggedIn=true;app.username=session.username;
      }catch(e){
        app.loggedIn=false;app.username='';
        if(!e.message.includes('Необходимо войти'))status(e.message,true);
      }
      await loadRoute(initial&&app.manifest.pages[initial]?initial:'/');
    }catch(e){status('Не удалось загрузить редактор: '+e.message,true)}
  })();
})();
