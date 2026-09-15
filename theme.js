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
