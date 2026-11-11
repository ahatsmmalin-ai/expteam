/* Expert Team CMS V2.1 — direct save to main. No OAuth tokens are persisted. */
(() => {
  'use strict';
  const ORIGIN = location.origin;
  const CANONICAL = 'https://expteam-staging.pages.dev';
  const REPO = 'ahatsmmalin-ai/expteam';
  const API = `https://api.github.com/repos/${REPO}`;
  const $ = id => document.getElementById(id);
  const frame = $('siteFrame');
  const app = {
    manifest: null, token: null, popup: null, username: '', route: '/',
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
    if(withLink){const a=document.createElement('a');a.href=withLink;a.target='_blank';a.rel='noopener noreferrer';a.textContent='Посмотреть коммит в GitHub ↗';box.appendChild(document.createElement('br'));box.appendChild(a)}
    box.classList.toggle('error',isError);show('result',!!message);
  };
  const arrPage = data => (data?.sections||[]).flatMap(section=>section.items||[]);
  const arrGlobal = data => data?.entries||[];
  function getItem(scope,key,which='draft'){
    const data=app[which][scope];
    return (scope==='global'?arrGlobal(data):arrPage(data)).find(x=>x.id===key)||null;
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
    const logged=!!app.token;
    show('loginButton',!logged);show('logoutButton',logged);
    show('guestPanel',!logged);show('savePanel',logged);
    show('selectPanel',logged&&!app.selected);show('editPanel',logged&&!!app.selected);
    $('identity').textContent=logged?`GitHub: ${app.username}`:'Вход не выполнен';
    $('infoText').textContent=logged?'Наведите курсор на текст и нажмите ✎, чтобы изменить его.':'Войдите через GitHub, чтобы править тексты на сайте.';
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
    const res=await fetch((path.startsWith('http')?path:API+path),{
      method:options.method||'GET',
      headers:{'Accept':'application/vnd.github+json','Authorization':'Bearer '+app.token,
        'X-GitHub-Api-Version':'2022-11-28', ...(options.body?{'Content-Type':'application/json'}:{})},
      body:options.body?JSON.stringify(options.body):undefined,credentials:'omit',cache:'no-store'
    });
    let response;
    try{response=await res.json()}catch(_){response={}}
    if(!res.ok){throw new Error((response?.message||'Ошибка GitHub')+` (HTTP ${res.status})`)}
    return response;
  };
  function decodeBase64Utf8(text){
    const binary=atob(text.replace(/\s/g,''));
    const bytes=Uint8Array.from(binary, ch=>ch.charCodeAt(0));
    return new TextDecoder().decode(bytes);
  }
  function encodeUtf8Base64(text){
    const bytes=new TextEncoder().encode(text);
    let bin='';const chunk=8192;
    for(let i=0;i<bytes.length;i+=chunk)bin+=String.fromCharCode(...bytes.subarray(i,i+chunk));
    return btoa(bin);
  }
  async function getFile(path,ref='main'){
    const item=await request('/contents/'+path.split('/').map(encodeURIComponent).join('/')+'?ref='+encodeURIComponent(ref));
    if(item.type!=='file'||typeof item.content!=='string')throw new Error('Не удалось прочитать '+path);
    return {data:JSON.parse(decodeBase64Utf8(item.content)),sha:item.sha};
  }
  async function loadGithubContent(){
    if(!app.token)return;
    const info=app.manifest.pages[app.route];
    if(!info)throw new Error('Неизвестный маршрут страницы');
    const [page,global]=await Promise.all([getFile(info.path),getFile(app.files.global)]);
    app.files.page=info.path;
    app.sha.page=page.sha;app.sha.global=global.sha;
    app.original.page=page.data;app.original.global=global.data;
    app.draft.page=deepClone(page.data);app.draft.global=deepClone(global.data);
    app.selected=null;authUI();
  }
  function updatePreview(scope,key,value){
    const d=frame.contentDocument;
    if(!d)return;
    d.querySelectorAll(`[data-et-scope="${scope}"][data-et-key="${key}"]`).forEach(n=>{n.textContent=value});
  }
  function chooseItem(scope,key){
    if(!app.token){status('Сначала войдите через GitHub.');return}
    const item=getItem(scope,key);
    if(!item){status('Текст не найден в данных страницы. Перезагрузите редактор.',true);return}
    app.selected={scope,key};
    $('editLabel').textContent=caption(item.label||item.value,140)||'Текст';
    $('editScope').textContent=scope==='global'?'Общий текст — на всех страницах':'Текст этой страницы';
    $('editValue').value=String(item.value??'');
    frame.contentDocument?.querySelectorAll('.et-edit-selected').forEach(n=>n.classList.remove('et-edit-selected'));
    frame.contentDocument?.querySelectorAll(`[data-et-scope="${scope}"][data-et-key="${key}"]`).forEach(n=>n.classList.add('et-edit-selected'));
    authUI();
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
    if(app.token){
      try{await loadGithubContent()}catch(e){status('Не удалось загрузить контент из GitHub: '+e.message,true)}
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
        chooseItem(marker.dataset.etScope,marker.dataset.etKey);return;
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
    if(ORIGIN!==CANONICAL){status('Вход в редактор разрешён только на '+CANONICAL+'/edit/',true);return}
    if(app.popup&&!app.popup.closed){app.popup.focus();return}
    status('Авторизация через GitHub…');
    app.popup=window.open('/api/auth?provider=github&site_id=expteam-staging.pages.dev&scope=repo',
      'expertteam_visual_oauth','width=630,height=720,resizable=yes,scrollbars=yes');
    if(!app.popup)status('Браузер заблокировал окно входа. Разрешите всплывающие окна для сайта.',true);
  }
  window.addEventListener('message',async ev=>{
    if(ev.origin!==ORIGIN||!app.popup||ev.source!==app.popup||typeof ev.data!=='string')return;
    if(ev.data==='authorizing:github'){
      app.popup.postMessage('authorizing:github',ORIGIN);return;
    }
    if(ev.data.startsWith('authorization:github:success:')){
      try{
        const data=JSON.parse(ev.data.slice('authorization:github:success:'.length));
        if(typeof data.token!=='string'||!data.token)throw new Error('Токен не получен');
        app.token=data.token;data.token=null;
        const [user,repo]=await Promise.all([request('https://api.github.com/user'),request('')]);
        if(!repo.permissions?.push){app.token=null;throw new Error('У аккаунта нет права записи в репозиторий '+REPO)}
        app.username=user.login;
        await loadGithubContent();
        authUI();status('Вход выполнен. Наведите курсор на нужный текст и нажмите на него.');
      }catch(e){app.token=null;app.username='';authUI();status('Не удалось войти: '+e.message,true)}
    }
    if(ev.data.startsWith('authorization:github:error:'))status('Авторизация не удалась. Попробуйте войти ещё раз.',true);
  });
  function logout(){
    if(allChanges().length&&!confirm('Выйти и отменить несохранённые изменения?'))return;
    app.token=null;app.username='';app.original.page=null;app.original.global=null;
    app.draft.page=null;app.draft.global=null;app.selected=null;
    authUI();status('Сеанс редактора завершён.');
    frame.src=app.manifest.pages[app.route].preview;
  }
  async function save(){
    const changes=allChanges();
    if(!changes.length||!app.token||app.busy)return;
    app.busy=true;
    syncControls();
    status('Проверяю актуальность файлов и сохраняю изменения…');
    try{
      const scopes=[...new Set(changes.map(c=>c.scope))];
      // Take the main branch tip; do not overwrite somebody else's new version.
      const ref=await request('/git/ref/heads/main');
      const headSha=ref.object?.sha;
      if(!headSha)throw new Error('Не удалось прочитать актуальный коммит main');
      const head=await request('/git/commits/'+encodeURIComponent(headSha));
      if(!head.tree?.sha)throw new Error('Не удалось прочитать дерево файлов main');
      const latest=await Promise.all(scopes.map(scope=>getFile(app.files[scope])));
      const treeEntries=[];
      for(let i=0;i<scopes.length;i++){
        const scope=scopes[i];
        if(latest[i].sha!==app.sha[scope]){
          throw new Error('Файл «'+app.files[scope]+'» уже был изменён другим сотрудником. Перезагрузите редактор перед сохранением, чтобы не затереть его правки.');
        }
        const text=JSON.stringify(app.draft[scope],null,2)+'\n';
        treeEntries.push({path:app.files[scope],mode:'100644',type:'blob',content:text});
      }
      // Atomic commit: save both the page and shared texts together if needed.
      const tree=await request('/git/trees',{
        method:'POST',body:{base_tree:head.tree.sha,tree:treeEntries}
      });
      const pageName=app.manifest.pages[app.route]?.title||app.route;
      const commit=await request('/git/commits',{
        method:'POST',body:{
          message:'CMS visual: '+pageName+' ('+changes.length+' изменений)',
          tree:tree.sha,parents:[headSha]
        }
      });
      // force:false enforces a fast-forward update, and respects branch protection.
      await request('/git/refs/heads/main',{
        method:'PATCH',body:{sha:commit.sha,force:false}
      });
      const selected=app.selected;
      try{
        await loadGithubContent();
        if(selected&&getItem(selected.scope,selected.key)){
          chooseItem(selected.scope,selected.key);
        }
      }catch(refreshError){
        // GitHub already confirmed the commit; do not misreport a successful save
        // as a failed write if the immediate readback encounters a temporary issue.
        app.original.page=deepClone(app.draft.page);
        app.original.global=deepClone(app.draft.global);
        status('Изменения сохранены в GitHub, но автоматическое обновление данных редактора пока недоступно. Перед следующей правкой обновите страницу.',false,`https://github.com/${REPO}/commit/${commit.sha}`);
        return;
      }
      status('Изменения сохранены в GitHub! Cloudflare автоматически обновит сайт после успешной сборки. Ничего согласовывать или объединять вручную не нужно.',false,`https://github.com/${REPO}/commit/${commit.sha}`);
    }catch(e){
      let msg=String(e.message||e);
      if(/HTTP 403|HTTP 422/.test(msg)){
        msg+=' Проверьте, разрешены ли прямые коммиты в ветку main и не появились ли параллельные правки. Если правила ветки требуют pull request, прямое сохранение будет недоступно.';
      }
      status('Не удалось сохранить изменения: '+msg,true);
    }finally{
      app.busy=false;
      syncControls();
    }
  }
  $('loginButton').addEventListener('click',login);
  $('guestLoginButton').addEventListener('click',login);
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
      await loadRoute(initial&&app.manifest.pages[initial]?initial:'/');
    }catch(e){status('Не удалось загрузить редактор: '+e.message,true)}
  })();
})();
