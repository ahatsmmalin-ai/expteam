/** GitHub OAuth callback for Decap CMS / Cloudflare Pages. */
function cookieValue(cookie, name) {
  const entry = cookie.split(';').map(x=>x.trim()).find(x=>x.startsWith(name+'='));
  return entry ? entry.slice(name.length+1) : '';
}
function responseError(message,status=400) {
  return new Response(message,{status,headers:{'Cache-Control':'no-store','Referrer-Policy':'no-referrer','Content-Type':'text/plain; charset=utf-8'}});
}
export async function onRequestGet({request,env}) {
  const url = new URL(request.url);
  const origin = url.origin;
  if(origin !== 'https://expteam-staging.pages.dev')return responseError('Use the canonical staging CMS URL.',403);
  if(!env.GITHUB_CLIENT_ID || !env.GITHUB_CLIENT_SECRET)return responseError('OAuth credentials not configured.',503);
  const state=url.searchParams.get('state')||'';
  const expected=cookieValue(request.headers.get('Cookie')||'','et_cms_oauth_state');
  const code=url.searchParams.get('code')||'';
  if(!state || !expected || !/^[a-f0-9]{64}$/.test(state) || state!==expected || !code)return responseError('Invalid OAuth state, or missing code. Restart login.',403);
  const api=await fetch('https://github.com/login/oauth/access_token',{
    method:'POST',headers:{'Content-Type':'application/json','Accept':'application/json','User-Agent':'ExpertTeamCMS-Cloudflare'},
    body:JSON.stringify({client_id:env.GITHUB_CLIENT_ID,client_secret:env.GITHUB_CLIENT_SECRET,code,redirect_uri:origin+'/api/callback',state})
  });
  if(!api.ok)return responseError('GitHub OAuth token exchange failed.',502);
  const result=await api.json();
  const token=typeof result.access_token==='string'?result.access_token:'';
  if(!token || !/^[A-Za-z0-9_]+$/.test(token))return responseError('GitHub OAuth access was denied.',401);
  const msg=JSON.stringify('authorization:github:success:'+JSON.stringify({token,provider:'github'}));
  const expectedOrigin=JSON.stringify(origin);
  // Decap popup handshake: opener must be the same origin; never use wildcard targetOrigin.
  const page=`<!doctype html><html lang="ru"><meta charset="utf-8"><title>Expert Team — вход выполнен</title><body><p>Авторизация завершена. Возвращаемся в редактор…</p><script>
  (function(){
    var origin=${expectedOrigin};
    var message=${msg};
    if(!window.opener){document.body.textContent='Откройте авторизацию из /admin/';return;}
    var done=false;
    function deliver(evt){
      if(done || evt.origin!==origin || evt.source!==window.opener)return;
      done=true;window.opener.postMessage(message,origin);
      setTimeout(function(){window.close()},300);
    }
    window.addEventListener('message',deliver,false);
    window.opener.postMessage('authorizing:github',origin);
  })();
  </script></body></html>`;
  return new Response(page,{headers:{
    'Content-Type':'text/html; charset=utf-8','Cache-Control':'no-store, private','Pragma':'no-cache',
    'Referrer-Policy':'no-referrer','X-Content-Type-Options':'nosniff',
    'Set-Cookie':'et_cms_oauth_state=; Max-Age=0; Path=/api; HttpOnly; Secure; SameSite=Lax'
  }});
}
