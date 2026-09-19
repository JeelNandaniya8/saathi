/* Search and focus are loaded only when opened. Today uses the existing data loader. */
(function(){
  'use strict';
  const state={api:null,user:null,notify:()=>{},openView:null,openTask:null};
  const t=value=>window.SaathiI18n?.t(value)||value;
  function node(tag,text,cls){const el=document.createElement(tag);if(text!=null)el.textContent=text;if(cls)el.className=cls;return el}
  function button(label,action,cls='secondary'){const el=node('button',t(label),cls);el.type='button';el.onclick=action;return el}
  function dialog(title){const d=node('dialog',null,'hub-dialog'),head=node('header'),h=node('h2',t(title));h.id='hub-title-'+crypto.randomUUID();d.setAttribute('aria-labelledby',h.id);head.append(h,button('Close',()=>d.close()));d.append(head);document.body.append(d);d.addEventListener('close',()=>d.remove());return d}
  function showError(box,error){box.textContent=t(error.message||'Something went wrong.');box.setAttribute('role','alert')}
  async function openItem(item){
    if(item.kind==='conversation'){location.href='/chat?conversation='+item.id;return}
    if(item.kind==='note'){await window.SaathiWorkspace.openNote(item.id);return}
    if(state.openTask){await state.openTask(item.id);return}
    location.href='/dashboard?task='+item.id+'#tasks';
  }
  function search(){
    if(!state.user)return;
    const d=dialog('Search your workspace'),input=node('input'),list=node('div',null,'hub-results'),message=node('p',t('Search chats, notes and tasks.'),'helper');
    input.type='search';input.maxLength=100;input.placeholder=t('Search chats, notes and tasks.');input.setAttribute('aria-label',t('Search your workspace'));message.setAttribute('role','status');
    d.append(input,message,list);let timeout,controller,sequence=0;
    async function run(){
      const query=input.value.trim(),turn=++sequence;controller?.abort();list.replaceChildren();
      if(query.length<2){message.textContent=t('Type at least two characters.');return}
      controller=new AbortController();message.textContent=t('Searching…');
      try{const data=await state.api('/api/workspace/search?q='+encodeURIComponent(query),{signal:controller.signal});if(turn!==sequence||!d.open)return;
        message.textContent=data.items.length?t('Results from your account.'):t('No matching items.');
        for(const item of data.items){const entry=node('button',null,'hub-result');entry.type='button';entry.append(node('small',t({conversation:'Conversation',note:'Note',task:'Task'}[item.kind])),node('strong',item.title),node('span',item.excerpt));entry.onclick=()=>{d.close();openItem(item).catch(error=>state.notify(t(error.message),'error'))};list.append(entry)}
      }catch(error){if(error.name!=='AbortError'&&turn===sequence)showError(message,error)}
    }
    input.oninput=()=>{clearTimeout(timeout);controller?.abort();sequence++;timeout=setTimeout(run,250)};
    input.onkeydown=event=>{if(event.key==='Enter'){event.preventDefault();clearTimeout(timeout);run()}};
    d.addEventListener('close',()=>{sequence++;clearTimeout(timeout);controller?.abort()});d.showModal();input.focus();
  }
  async function focus(taskId=null){
    const d=dialog('Focus session'),form=node('form'),label=node('label',t('Choose a task')),tasks=node('select'),lengthLabel=node('label',t('Session length')),length=node('select'),clock=node('p','25:00','hub-clock'),status=node('p',t('Loading…'),'helper'),actions=node('div',null,'care-actions');
    tasks.setAttribute('aria-label',t('Choose a task'));length.setAttribute('aria-label',t('Session length'));
    for(const minutes of [25,50]){const option=node('option',minutes+' '+t('minutes'));option.value=String(minutes);length.append(option)}
    label.append(tasks);lengthLabel.append(length);form.append(label,lengthLabel);d.append(form,clock,status,actions);d.showModal();
    let current=null,remaining=0,measured=Date.now(),interval,busy=false,settling=false,clientId=crypto.randomUUID();
    function tick(){const seconds=Math.max(0,remaining-(current?.status==='running'?Math.floor((Date.now()-measured)/1000):0));clock.textContent=String(Math.floor(seconds/60)).padStart(2,'0')+':'+String(seconds%60).padStart(2,'0');if(!seconds&&current?.status==='running'&&!settling){settling=true;refresh().catch(error=>showError(status,error))}}
    function render(session){current=session;remaining=session?.remaining_seconds??Number(length.value||25)*60;measured=Date.now();settling=false;const active=['running','paused'].includes(session?.status);tasks.disabled=length.disabled=active;
      status.textContent=t({running:'One task at a time. Your timer continues if this panel closes.',paused:'Paused. Continue when you are ready.',completed:'Session complete. Take a short break.',cancelled:'Session ended. Start again when you are ready.'}[session?.status]||'Choose one manageable task.');
      actions.replaceChildren();if(active){actions.append(button(session.status==='running'?'Pause':'Resume',()=>change(session.status==='running'?'pause':'resume')),button('End session',()=>change('end')))}else actions.append(button('Start focus',start,'primary'));
      actions.append(button('Refresh',()=>refresh().catch(error=>showError(status,error))));tick();clearInterval(interval);interval=setInterval(tick,1000);
    }
    async function refresh(){const data=await state.api('/api/focus');if(d.open)render(data.session)}
    async function operate(action){if(busy)return;busy=true;actions.querySelectorAll('button').forEach(el=>el.disabled=true);try{await action()}catch(error){showError(status,error)}finally{busy=false;actions.querySelectorAll('button').forEach(el=>el.disabled=false)}}
    function start(){return operate(async()=>{const data=await state.api('/api/focus',{method:'POST',body:JSON.stringify({minutes:Number(length.value),task_id:tasks.value?Number(tasks.value):null,client_id:clientId})});clientId=crypto.randomUUID();if(d.open)render(data.session)})}
    function change(action){return operate(async()=>{const data=await state.api('/api/focus/'+current.id,{method:'PATCH',body:JSON.stringify({action,version:current.version})});if(d.open)render(data.session)})}
    form.onsubmit=event=>{event.preventDefault();if(!current||!['running','paused'].includes(current.status))start()};length.onchange=()=>{remaining=Number(length.value)*60;tick()};
    const visible=()=>{if(!document.hidden&&d.open)refresh().catch(error=>showError(status,error))};document.addEventListener('visibilitychange',visible);d.addEventListener('close',()=>{clearInterval(interval);document.removeEventListener('visibilitychange',visible)});
    try{const [saved,planner]=await Promise.all([state.api('/api/focus'),state.api('/api/tasks')]);if(!d.open)return;const none=node('option',t('No task selected'));none.value='';tasks.append(none);for(const task of planner.tasks.filter(task=>!task.completed)){const option=node('option',task.title);option.value=task.id;option.setAttribute('data-user-content','');tasks.append(option)}tasks.value=String(saved.session?.task_id||taskId||'');render(saved.session)}catch(error){showError(status,error);actions.append(button('Retry',()=>{d.close();focus(taskId)}))}
  }
  function renderToday(data){
    const box=document.getElementById('todayTasks');if(!box)return;box.replaceChildren();
    if(!data.tasks.length)box.append(node('p',t('No tasks due. Add a small next step or leave room for rest.'),'helper'));
    for(const task of data.tasks){const row=node('div',null,'hub-task'),title=node('button',task.title,'hub-task-title');title.type='button';title.onclick=()=>openItem({kind:'task',id:task.id});const done=button('Complete',async()=>{done.disabled=true;try{await state.api('/api/tasks/'+task.id,{method:'PATCH',body:JSON.stringify({completed:true})});await state.refreshToday()}catch(error){done.disabled=false;state.notify(t(error.message),'error')}});row.append(title,button('Focus',()=>focus(task.id)),done);box.append(row)}
    const revisionLabel=node('span','Revision ready');revisionLabel.setAttribute('data-ui-text','');document.getElementById('todayRevision').replaceChildren(revisionLabel,node('span',': '+data.revision_due));
    const recent=document.getElementById('todayResume');recent.replaceChildren();if(data.recent_chat){const link=node('a',data.recent_chat.title,'secondary');link.href='/chat?conversation='+data.recent_chat.id;recent.append(link)}else recent.append(node('p',t('Your latest conversation will appear here.'),'helper'));
  }
  function connect(options){Object.assign(state,options);document.querySelectorAll('[data-workspace-search]').forEach(el=>el.onclick=search);document.querySelectorAll('[data-focus-session]').forEach(el=>el.onclick=()=>focus());}
  document.addEventListener('keydown',event=>{if((event.ctrlKey||event.metaKey)&&event.key.toLowerCase()==='k'&&!document.querySelector('dialog[open]')){event.preventDefault();search()}});
  window.SaathiHub={connect,search,focus,renderToday};
})();
