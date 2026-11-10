(()=>{'use strict';
const $=(s,scope=document)=>scope.querySelector(s),$$=(s,scope=document)=>Array.from(scope.querySelectorAll(s));
function event(name,extra={}){try{window.dataLayer?.push({event:name,...extra});if(typeof window.ym==='function'&&window.EXPERT_METRIKA_ID)window.ym(window.EXPERT_METRIKA_ID,'reachGoal',name)}catch(_e){}}
// Navigation: same tab for internal URLs, keyboard-friendly menu.
const nav=$('.nav-dropdown'),navBtn=$('.nav-trigger'),menu=$('#mobileNav'),mobileBtn=$('.mobile-menu-btn');
function closeDropdown(){nav?.classList.remove('is-open');navBtn?.setAttribute('aria-expanded','false')}
navBtn?.addEventListener('click',()=>{const open=!nav.classList.contains('is-open');nav.classList.toggle('is-open',open);navBtn.setAttribute('aria-expanded',String(open))});
document.addEventListener('click',e=>{if(nav&&!nav.contains(e.target))closeDropdown()});
function closeMobile(){if(menu){menu.hidden=true;mobileBtn?.setAttribute('aria-expanded','false');document.body.style.overflow=''}}
mobileBtn?.addEventListener('click',()=>{if(!menu)return;const opening=menu.hidden;menu.hidden=!opening;mobileBtn.setAttribute('aria-expanded',String(opening));document.body.style.overflow=opening?'hidden':''});
$$('.mobile-nav a').forEach(a=>a.addEventListener('click',closeMobile));
document.addEventListener('keydown',e=>{if(e.key==='Escape'){closeDropdown();closeMobile()}});
// Lead modal: never show fake success on static staging. Only a verified POST response counts.
const modal=$('#leadModal');function openLead(){if(!modal)return;closeMobile();if(typeof modal.showModal==='function')modal.showModal();else modal.setAttribute('open','');$('#leadName',modal)?.focus();event('lead_form_open',{page:location.pathname})}function closeLead(){modal?.close?.()}
$$('[data-open-lead]').forEach(b=>b.addEventListener('click',openLead));$$('[data-close-lead]').forEach(b=>b.addEventListener('click',closeLead));modal?.addEventListener('click',e=>{if(e.target===modal)closeLead()});
$$('[data-lead-form]').forEach(form=>form.addEventListener('submit',async e=>{
 e.preventDefault();const name=$('input[name="name"]',form),phone=$('input[name="phone"]',form),website=$('input[name="website"]',form),consent=$('input[name="consent"]',form),status=$('.form-status',form),button=$('button[type="submit"]',form),trap=$('input[name="extra_check"]',form);
 if(!form.reportValidity())return;
 if(trap?.value)return;
 const endpoint=window.EXPERTTEAM_FORM_ENDPOINT;
 if(typeof endpoint!=='string'||!/^https:\/\//.test(endpoint)){
  status.textContent='Тестовая версия: данные не отправлены и не сохранены. Пожалуйста, свяжитесь с нами в Telegram.';
  status.style.color='#0F09FF';event('lead_demo_attempt',{page:location.pathname});return;
 }
 let params=new URLSearchParams(location.search),utm={};['utm_source','utm_medium','utm_campaign','utm_content','utm_term'].forEach(k=>{if(params.has(k))utm[k]=params.get(k).slice(0,200)});
 button.disabled=true;status.textContent='Отправляем заявку…';status.style.color='#525569';
 try{const response=await fetch(endpoint,{method:'POST',mode:'cors',credentials:'omit',redirect:'error',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:name.value.trim(),phone:phone.value.trim(),website:website?.value.trim()||'',consent:consent.checked,source_page:location.pathname,utm})});
  if(!response.ok)throw new Error('HTTP '+response.status);
  status.textContent='Заявка принята. Мы свяжемся с вами после обработки запроса.';status.style.color='#075a2a';form.reset();event('lead_submit_success',{page:location.pathname});
 }catch(_err){status.textContent='Не получилось отправить заявку. Напишите нам в Telegram.';status.style.color='#B00020';event('lead_submit_error',{page:location.pathname})}finally{button.disabled=false}
}));
// Case filter: visible cards only. All case links stay in current tab.
const filters=$$('[data-case-filter]'),cards=$$('[data-industry]');function applyCaseFilter(cat){let count=0;cards.forEach(card=>{const visible=cat==='all'||card.dataset.industry===cat;card.hidden=!visible;if(visible)count++});filters.forEach(btn=>{const active=btn.dataset.caseFilter===cat;btn.classList.toggle('is-active',active);btn.setAttribute('aria-pressed',String(active))});const summary=$('#caseCount');if(summary)summary.textContent='Кейсов: '+count;const empty=$('#emptyCases');if(empty)empty.hidden=count>0}
filters.forEach(b=>b.addEventListener('click',()=>applyCaseFilter(b.dataset.caseFilter)));
// Price comparison calculator, no tracking / upload of numeric inputs.
const calc=$('#marketingCalc');if(calc){const initial={salary:150000,contributions:30,staffContractors:30000,staffSoftware:10000,agencyFee:60000,agencyContractors:0,agencySoftware:10000};const nf=new Intl.NumberFormat('ru-RU',{maximumFractionDigits:0});const cur=n=>nf.format(Math.round(n))+' ₽';const nonneg=k=>Math.max(0,Math.min(Number(calc.elements.namedItem(k)?.value)||0,1e9));let last={};function recalc(){const staff=nonneg('salary')*(1+nonneg('contributions')/100)+nonneg('staffContractors')+nonneg('staffSoftware');const agency=nonneg('agencyFee')+nonneg('agencyContractors')+nonneg('agencySoftware');const diff=staff-agency;last={staff,agency,diff};$('#calcStaff').textContent=cur(staff);$('#calcAgency').textContent=cur(agency);$('#calcDifference').textContent=(diff>=0?'':'−')+cur(Math.abs(diff));$('#calcVerdictTitle').textContent=diff>0?'Разница в пользу внешней команды':diff<0?'Разница в пользу штатной модели':'Одинаковая сумма затрат';$('#calcVerdict').textContent=diff>0?'По указанным расходам внешняя команда дешевле на '+cur(diff)+' в месяц. Состав работ и результат сравните отдельно.':diff<0?'По указанным расходам штатный вариант дешевле на '+cur(-diff)+' в месяц. Состав задач и загрузка могут отличаться.':'По указанным цифрам расходы совпадают. Сравните компетенции и ответственность.';let max=Math.max(staff,agency,1);$('#calcStaffBar').style.width=(100*staff/max)+'%';$('#calcAgencyBar').style.width=(100*agency/max)+'%'}
 calc.addEventListener('input',recalc);$('#resetCalc')?.addEventListener('click',()=>{for(const [key,value] of Object.entries(initial))calc.elements.namedItem(key).value=value;recalc()});$('#copyCalc')?.addEventListener('click',async()=>{const txt=`Expert Team — сценарное сравнение в месяц\nШтатный маркетинг: ${cur(last.staff)}\nВнешняя команда: ${cur(last.agency)}\nРазница: ${cur(Math.abs(last.diff))}.\nРасчёт не учитывает рекламный бюджет, качество и производительность.`;try{await navigator.clipboard.writeText(txt);$('#copyCalc').textContent='Расчёт скопирован ✓';setTimeout(()=>$('#copyCalc').textContent='Скопировать расчёт ↗',2000)}catch(_e){$('#copyCalc').textContent='Копирование недоступно'}});recalc();}
$$('a[href^="tel:"]').forEach(a=>a.addEventListener('click',()=>event('phone_click',{page:location.pathname})));$$('a[href*="t.me/"]').forEach(a=>a.addEventListener('click',()=>event('telegram_click',{page:location.pathname})));
})();
