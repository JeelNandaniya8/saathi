/* Small, on-demand recovery and insights. No chat/note text enters timing records. */
(function(){
  'use strict';
  const state={user:null,api:null,notify:()=>{}};
  const prefix=()=>`saathi-draft-v1:${state.user?.id}:`;
  const key=(kind,id)=>prefix()+kind+':'+id;
  function removeDraft(kind,id){try{localStorage.removeItem(key(kind,id))}catch(_){}}
  function getDraft(kind,id){
    if(!state.user)return null;
    try{const raw=localStorage.getItem(key(kind,id));if(!raw||raw.length>30000)return null;const data=JSON.parse(raw);if(!data)return null;if(!Number.isFinite(data.saved_at)||Date.now()-data.saved_at>86400000||data.saved_at>Date.now()){removeDraft(kind,id);return null}return data}catch(_){removeDraft(kind,id);return null}
  }
  function saveDraft(kind,id,data){
    if(!state.user||id==null)return false;
    const value={...data,saved_at:Date.now()};
    try{
      const raw=JSON.stringify(value);if(raw.length>30000)return false;
      localStorage.setItem(key(kind,id),raw);
      const keys=Object.keys(localStorage).filter(k=>k.startsWith(prefix()));
      const savedAt=name=>{try{return JSON.parse(localStorage.getItem(name)||'{}').saved_at||0}catch(_){return 0}};
      if(keys.length>12){keys.sort((a,b)=>savedAt(a)-savedAt(b));for(const old of keys.slice(0,-12))localStorage.removeItem(old)}
      return true;
    }catch(_){return false}
  }
  function clearDrafts(){try{for(const name of Object.keys(localStorage))if(name.startsWith(prefix()))localStorage.removeItem(name)}catch(_){}}
  function forgetAccount(){const user=state.user?.id;clearDrafts();state.user=null;try{localStorage.setItem('saathi-draft-logout',JSON.stringify({user,at:Date.now()}))}catch(_){}}
  window.addEventListener('storage',event=>{if(event.key!=='saathi-draft-logout')return;try{if(JSON.parse(event.newValue||'{}').user===state.user?.id){clearDrafts();state.user=null}}catch(_){}});
  function id(){if(window.crypto?.randomUUID)return window.crypto.randomUUID();const bytes=window.crypto.getRandomValues(new Uint8Array(16));bytes[6]=(bytes[6]&15)|64;bytes[8]=(bytes[8]&63)|128;return Array.from(bytes,(b,i)=>([4,6,8,10].includes(i)?'-':'')+b.toString(16).padStart(2,'0')).join('')}
  const clock=()=>window.performance?.now?.()??Date.now();
  function measureStart(url){const match=url.match(/\/conversations\/(\d+)\//);if(!state.user||!match)return null;return {request_id:id(),conversation_id:Number(match[1]),started:clock(),first_text_ms:null,user:state.user.id}}
  function measureDelta(sample){if(sample&&sample.first_text_ms===null)sample.first_text_ms=Math.min(300000,Math.max(0,Math.round(clock()-sample.started)))}
  function measureEnd(sample,outcome,error){
    if(!sample||sample.user!==state.user?.id||!state.api)return;
    const total_ms=Math.min(300000,Math.max(0,Math.round(clock()-sample.started)));
    const code=error?.code||'CLIENT_ERROR';
    const error_code=/^AI_(ACCESS|QUOTA|MODEL|CONFIGURATION|BUSY|REQUEST|TIMEOUT|CONNECTION|FORMAT)$/.test(code)?code:(outcome==='error'?'CLIENT_ERROR':'');
    Promise.resolve().then(()=>{if(sample.user===state.user?.id)return state.api('/api/response-timings',{method:'POST',body:JSON.stringify({request_id:sample.request_id,conversation_id:sample.conversation_id,first_text_ms:sample.first_text_ms,total_ms,outcome,error_code})})}).catch(()=>{});
  }
  function voiceFor(language){const voices=window.speechSynthesis?.getVoices?.()||[],base=String(language||'en').split('-')[0].toLowerCase();return voices.find(v=>v.lang?.toLowerCase()===String(language).toLowerCase())||voices.find(v=>v.lang?.toLowerCase().split('-')[0]===base)||null}
  function node(tag,text,className){const el=document.createElement(tag);if(text!=null)el.textContent=text;if(className)el.className=className;return el}
  function button(label,action){const el=node('button',label,'secondary');el.type='button';el.onclick=action;return el}
  function metric(label,value){const card=node('article',null,'recovery-metric');card.append(node('span',label),node('strong',value));return card}
  const seconds=value=>value==null?'No sample':(value/1000).toFixed(1)+' s';
  async function insights(kind){
    const isWeekly=kind==='weekly',dialog=node('dialog',null,'recovery-dialog'),header=node('header'),content=node('div');
    const title=node('h2',isWeekly?'Your week, at a glance':'Reply performance');title.id='recoveryDialogTitle';dialog.setAttribute('aria-labelledby',title.id);
    const close=button('Close',()=>dialog.close());header.append(title,close);dialog.append(header,content);document.body.append(dialog);
    dialog.addEventListener('close',()=>dialog.remove());dialog.showModal();close.focus();
    async function load(){
      content.replaceChildren(node('p','Loading…','helper'));
      try{
        const data=await state.api(isWeekly?'/api/weekly-review':'/api/response-timings');if(!dialog.open)return;
        const summary=data.summary,grid=node('div',null,'recovery-grid');content.replaceChildren();
        if(isWeekly){
          content.append(node('p',data.start+' to '+data.end+' · '+data.timezone,'helper'));
          grid.append(metric('Tasks completed',summary.completed_tasks),metric('Habit check-offs',summary.habit_completions),metric('Practice attempts',summary.practice_attempts),metric('Practice accuracy',summary.practice_accuracy==null?'No attempts':summary.practice_accuracy+'%'));
          content.append(grid,node('p',summary.open_tasks?`${summary.open_tasks} tasks remain open. Choose one manageable next step when you are ready.`:'You have no open tasks. You can leave space for rest.'));
          content.append(node('p',data.note,'helper'),node('p','Based on saved activity. No estimated study hours or AI analysis of private journal entries.','helper'));
        }else{
          content.append(node('p','Your latest 100 attempts within 30 days. Timings are measured in your browser and include network, server and AI waiting time.','helper'));
          grid.append(metric('Typical first words',seconds(summary.first_text_ms)),metric('Typical full reply',seconds(summary.total_ms)),metric('Completed',summary.completed+'/'+summary.attempts),metric('Errors / stopped',summary.errors+' / '+summary.cancelled));
          content.append(grid,node('p',summary.completed?'95% of successful replies started within '+seconds(summary.p95_first_text_ms)+'. With few samples, this may vary.':'Send a message to collect the first timing sample.','helper'));
          const list=node('ul',null,'recovery-results');for(const item of data.recent)list.append(node('li',`${item.outcome} · first words ${seconds(item.first_text_ms)} · total ${seconds(item.total_ms)}${item.error_code?' · '+item.error_code:''}`));content.append(list);
          content.append(node('p','Only durations, outcomes and error codes are recorded. Message and file contents are not included.','helper'));
          content.append(button('Clear timing history',async()=>{try{await state.api('/api/response-timings',{method:'DELETE',body:'{}'});await load()}catch(error){state.notify(error.message,'error')}}));
        }
      }catch(error){content.replaceChildren(node('p',error.message,'helper'),button('Retry',load))}
    }
    await load();
  }
  function connect(options){Object.assign(state,options);document.querySelectorAll('[data-weekly-review]').forEach(el=>{el.onclick=()=>insights('weekly')});document.querySelectorAll('[data-response-timings]').forEach(el=>{el.onclick=()=>insights('timings')});document.querySelectorAll('[data-clear-drafts]').forEach(el=>{el.onclick=()=>{clearDrafts();state.notify('Browser draft copies cleared. New typing will save a new draft.')}})}
  window.SaathiRecovery={connect,getDraft,saveDraft,removeDraft,clearDrafts,forgetAccount,measureStart,measureDelta,measureEnd,voiceFor};
})();
