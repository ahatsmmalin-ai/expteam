(()=>{'use strict';const dialog=document.getElementById('leadDialog');const mobile=document.getElementById('mobileMenu');const menuBtn=document.querySelector('.mobile-toggle');const banner=document.getElementById('slideBanner');const navDrop=document.querySelector('.nav-dropdown');const dropBtn=document.querySelector('.nav-dropdown-trigger');let shown=false;function track(name,details={}){try{window.dataLayer?.push({event:name,...details});if(typeof window.ym==='function'&&window.EXPERT_METRIKA_ID)window.ym(window.EXPERT_METRIKA_ID,'reachGoal',name)}catch(e){}}function openDialog(){if(!dialog)return;dialog.showModal();document.body.style.overflow='hidden';track('lead_open');dialog.querySelector('input[type=tel]')?.focus();if(banner)banner.hidden=true}function closeDialog(){dialog?.close();document.body.style.overflow=''}document.querySelectorAll('[data-open-lead]').forEach(b=>b.addEventListener('click',openDialog));document.querySelectorAll('[data-close-lead]').forEach(b=>b.addEventListener('click',closeDialog));dialog?.addEventListener('click',e=>{if(e.target===dialog)closeDialog()});dialog?.addEventListener('close',()=>document.body.style.overflow='');menuBtn?.addEventListener('click',()=>{const expanding=mobile.hidden;mobile.hidden=!expanding;menuBtn.setAttribute('aria-expanded',String(expanding));document.body.style.overflow=expanding?'hidden':''});mobile?.querySelectorAll('a').forEach(a=>a.addEventListener('click',()=>{mobile.hidden=true;document.body.style.overflow=''}));dropBtn?.addEventListener('click',()=>{const open=navDrop.classList.toggle('open');dropBtn.setAttribute('aria-expanded',String(open))});document.addEventListener('click',e=>{if(!navDrop?.contains(e.target)){navDrop?.classList.remove('open');dropBtn?.setAttribute('aria-expanded','false')}});document.querySelectorAll('[data-lead-form]').forEach(form=>form.addEventListener('submit',async e=>{
 e.preventDefault();
 const phone=form.querySelector('input[name=phone]');
 const consent=form.querySelector('input[name=consent]');
 const honeypot=form.querySelector('input[name=company_website]');
 const status=form.querySelector('.form-status');
 const button=form.querySelector('button[type=submit]');
 if(!phone?.checkValidity()){phone?.reportValidity();return}
 if(!consent?.checked){consent?.reportValidity();return}
 if(honeypot?.value){status.textContent='Пожалуйста, попробуйте ещё раз.';return}
 const endpoint=window.EXPERTTEAM_FORM_ENDPOINT;
 if(typeof endpoint!=='string'||!/^https:\/\//.test(endpoint)){
   status.textContent='Это демоверсия: заявка не отправлена. Подключите CRM и утверждённую политику обработки данных.';
   status.style.color='#454d35';track('lead_demo_attempt',{source:location.pathname});return;
 }
 const wasDisabled=button?.disabled;
 if(button)button.disabled=true;
 status.textContent='Отправляем заявку…';
 status.style.color='#454d35';
 try{
   const r=await fetch(endpoint,{
     method:'POST',mode:'cors',credentials:'omit',redirect:'error',
     headers:{'Content-Type':'application/json'},
     body:JSON.stringify({phone:phone.value.trim(),consent:true,source:location.pathname})
   });
   if(!r.ok)throw Error('Request not accepted');
   status.textContent='Спасибо! Заявка принята. Мы свяжемся с вами.';
   form.reset();
   track('lead_submit_success',{source:location.pathname});
 }catch(_e){
   status.textContent='Заявку не удалось отправить. Пожалуйста, напишите нам в Telegram.';
   status.style.color='#8a3428';
   track('lead_submit_error',{source:location.pathname});
 }finally{if(button)button.disabled=Boolean(wasDisabled)}
}));const prog=document.querySelector('.site-progress');function onScroll(){const max=document.documentElement.scrollHeight-innerHeight;const pct=max>0?Math.max(0,Math.min(1,scrollY/max)):0;if(prog)prog.style.width=(pct*100)+'%';if(pct>.60&&!shown&&banner&&!sessionStorage.getItem('et_banner_closed')&&window.innerWidth>900&&!dialog?.open){shown=true;banner.hidden=false;track('scroll_60')}}window.addEventListener('scroll',onScroll,{passive:true});document.querySelector('[data-hide-banner]')?.addEventListener('click',()=>{banner.hidden=true;sessionStorage.setItem('et_banner_closed','1')});let leaveShown=false;document.addEventListener('mouseout',e=>{if(e.clientY<=0&&e.relatedTarget===null&&!leaveShown&&window.innerWidth>900&&!dialog?.open&&!sessionStorage.getItem('et_exit')){leaveShown=true;sessionStorage.setItem('et_exit','1');/* Exit-intent intentionally unobtrusive in prototype: use banner, not forced popup. */if(banner){banner.hidden=false;banner.querySelector('b').textContent='Бесплатный маркетинговый план для вас';}}});const industryFilter=document.getElementById('caseFilterIndustry');const serviceFilter=document.getElementById('caseFilterService');function applyCaseFilters(){const industry=industryFilter?.value||'all';const service=serviceFilter?.value||'all';let visible=0;document.querySelectorAll('[data-case-industry]').forEach(card=>{const show=(industry==='all'||industry===card.dataset.caseIndustry)&&(service==='all'||service===card.dataset.caseService);card.hidden=!show;if(show)visible++});const summary=document.getElementById('caseFilterCount');if(summary)summary.textContent='Кейсов: '+visible;const empty=document.getElementById('caseFilterEmpty');if(empty)empty.hidden=visible!==0}industryFilter?.addEventListener('change',applyCaseFilters);serviceFilter?.addEventListener('change',applyCaseFilters);if(industryFilter||serviceFilter)applyCaseFilters();document.querySelectorAll('a[href^="tel:"]').forEach(a=>a.addEventListener('click',()=>track('phone_click')));document.querySelectorAll('a[href*="t.me/"]').forEach(a=>a.addEventListener('click',()=>track('telegram_click')));})();
