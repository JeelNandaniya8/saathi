/* Apply appearance before the first paint, without depending on account data. */
(function(){
  'use strict';
  const media=window.matchMedia('(prefers-color-scheme: dark)');
  let choice=null;
  try{choice=localStorage.getItem('saathi-theme')}catch(_){}
  if(!['light','dark'].includes(choice))choice=null;
  function current(){return choice||(media.matches?'dark':'light')}
  function refresh(){
    const theme=current();document.documentElement.dataset.theme=theme;
    document.documentElement.style.colorScheme=theme;
    document.querySelector('meta[name="theme-color"]')?.setAttribute('content',theme==='dark'?'#101622':'#f4f6fb');
    document.querySelectorAll('[data-theme-toggle]').forEach(button=>{
      const label=theme==='dark'?'Switch to light mode':'Switch to dark mode';
      button.setAttribute('aria-label',label);button.setAttribute('aria-pressed',String(theme==='dark'));button.title=label;
      if(button.hasAttribute('data-theme-label'))button.textContent=theme==='dark'?'Light appearance':'Dark appearance';
    });
  }
  function apply(theme){if(!['light','dark'].includes(theme))return;choice=theme;try{localStorage.setItem('saathi-theme',theme)}catch(_){}refresh()}
  window.SaathiTheme={current,refresh,apply,toggle:()=>apply(current()==='dark'?'light':'dark')};
  media.addEventListener('change',()=>{if(!choice)refresh()});
  window.addEventListener('storage',event=>{if(event.key==='saathi-theme'){choice=['light','dark'].includes(event.newValue)?event.newValue:null;refresh()}});
  document.addEventListener('DOMContentLoaded',()=>{refresh();document.querySelectorAll('[data-theme-action]').forEach(button=>button.addEventListener('click',window.SaathiTheme.toggle))});
  refresh();
})();

/* A device preference, chosen explicitly and applied before account loading. */
(function(){
  let large=false;try{large=localStorage.getItem('saathi-large-text')==='on'}catch(_){}
  function refresh(){
    document.documentElement.dataset.textSize=large?'large':'normal';
    const language=document.documentElement.lang||'en';
    const copy={en:['Use larger text','Use standard text'],gu:['મોટા અક્ષરો રાખો','સામાન્ય અક્ષરો રાખો'],hi:['बड़े अक्षर रखें','सामान्य अक्षर रखें']}[language]||['Use larger text','Use standard text'];
    document.querySelectorAll('[data-large-text]').forEach(button=>{button.textContent=copy[large?1:0];button.setAttribute('aria-pressed',String(large))});
  }
  function apply(enabled){large=Boolean(enabled);try{localStorage.setItem('saathi-large-text',large?'on':'off')}catch(_){}refresh()}
  window.SaathiTextSize={refresh,apply};
  window.addEventListener('storage',event=>{if(event.key==='saathi-large-text'){large=event.newValue==='on';refresh()}});
  document.addEventListener('DOMContentLoaded',()=>{refresh();document.querySelectorAll('[data-large-text]').forEach(button=>button.addEventListener('click',()=>apply(!large)))});
  refresh();
})();
