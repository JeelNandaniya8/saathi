/* Account-owned sidebar notes, Google avatars and optional background alerts. */
(function(){
  'use strict';
  const state={user:null,api:null,notify:()=>{},notes:[],loaded:false,selected:null,clientId:null,dirty:false,busy:false,pushConfig:null,pushId:null,pushBusy:false};
  let dialog,ui={};
  function uuid(){if(crypto.randomUUID)return crypto.randomUUID();const b=crypto.getRandomValues(new Uint8Array(16));b[6]=(b[6]&15)|64;b[8]=(b[8]&63)|128;return Array.from(b,(v,i)=>([4,6,8,10].includes(i)?'-':'')+v.toString(16).padStart(2,'0')).join('')}
  function status(text,error=false){ui.status.textContent=text;ui.status.classList.toggle('error',error)}
  function renderAvatar(container,user){
    if(!container)return;
    const initial=(user?.name?.trim()?.[0]||'S').toUpperCase();container.replaceChildren();container.textContent=initial;
    if(!user?.avatar_url)return;
    try{const url=new URL(user.avatar_url);if(url.protocol!=='https:'||!url.hostname.endsWith('.googleusercontent.com')||url.username||url.password)return}catch(_){return}
    const img=document.createElement('img');img.className='profile-photo';img.alt='';img.referrerPolicy='no-referrer';img.decoding='async';
    img.addEventListener('error',()=>{if(img.parentNode===container){container.replaceChildren();container.textContent=initial}});
    img.src=user.avatar_url;container.replaceChildren(img);
  }
  function buildDialog(){
    if(dialog)return;
    dialog=document.createElement('dialog');dialog.className='quick-notes-dialog';dialog.setAttribute('aria-labelledby','quickNotesTitle');
    dialog.innerHTML='<header class="qn-header"><div><h2 id="quickNotesTitle">Quick notes</h2><p>Private notes, close at hand.</p></div><button type="button" data-qn="close" aria-label="Close quick notes">×</button></header><div class="qn-toolbar"><button type="button" data-qn="new">New note</button><button type="button" data-qn="reload">Refresh</button><button type="button" data-qn="exportpdf" title="Export current note as PDF">Export PDF</button><input type="search" data-qn="search" placeholder="Find a note" aria-label="Search quick notes"></div><div class="qn-layout"><div class="qn-list" data-qn="list" aria-label="Saved notes"></div><form class="qn-editor" data-qn="form"><label>Title<input data-qn="title" maxlength="80" placeholder="A title, if you like"></label><label class="qn-content-label">Note<textarea data-qn="content" maxlength="10000" required placeholder="An idea, a question, something to remember…"></textarea></label><div class="qn-meta"><span data-qn="counter">0 / 10,000</span><span>Only visible to you</span></div><p class="qn-status" data-qn="status" role="status" aria-live="polite"></p><div class="qn-actions"><button class="qn-save" data-qn="save" type="submit">Save note</button><button data-qn="discard" type="button" hidden>Discard edits</button><button class="qn-delete" data-qn="delete" type="button" hidden>Delete note</button></div></form></div>';
    document.body.append(dialog);dialog.querySelectorAll('[data-qn]').forEach(node=>ui[node.dataset.qn]=node);
    ui.close.onclick=()=>dialog.close();dialog.addEventListener('click',event=>{if(event.target===dialog){const box=dialog.getBoundingClientRect();if(event.clientX<box.left||event.clientX>box.right||event.clientY<box.top||event.clientY>box.bottom)dialog.close()}});
    ui.new.onclick=()=>selectNote(null);ui.reload.onclick=()=>loadNotes(true);ui.search.oninput=renderList;
    ui.exportpdf.onclick=exportCurrentNotePdf;
    ui.form.addEventListener('submit',saveNote);ui.delete.onclick=deleteNote;
    ui.discard.onclick=()=>{window.SaathiRecovery?.removeDraft('note',noteDraftKey());state.dirty=false;selectNote(state.notes.find(note=>note.id===state.selected?.id)||state.selected,true)};
    for(const input of [ui.title,ui.content])input.addEventListener('input',()=>{state.dirty=true;ui.discard.hidden=false;ui.counter.textContent=ui.content.value.length+' / 10,000';status('Unsaved changes');state.confirmDelete=false;ui.delete.textContent='Delete note';saveNoteDraft()});
    ui.content.addEventListener('keydown',event=>{if((event.ctrlKey||event.metaKey)&&event.key==='Enter'){event.preventDefault();ui.form.requestSubmit()}});
    window.addEventListener('beforeunload',event=>{if(state.dirty){event.preventDefault();event.returnValue=''}});
    selectNote(null,true);
  }
  function noteDraftKey(){return state.selected?.id||'new'}
  function saveNoteDraft(){if(state.dirty)window.SaathiRecovery?.saveDraft('note',noteDraftKey(),{title:ui.title.value,content:ui.content.value,version:state.draftVersion??state.selected?.version,client_id:state.clientId})}
  function canSwitch(){if(!state.dirty)return true;status('Save or discard your edits before opening another note.',true);ui.save.focus();return false}
  function selectNote(note,force=false){
    if(state.busy||(!force&&!canSwitch()))return;
    state.selected=note;state.clientId=note?.client_id||uuid();state.dirty=false;state.draftVersion=null;
    ui.title.value=note?.title||'';ui.content.value=note?.content||'';ui.delete.hidden=!note;ui.discard.hidden=true;state.confirmDelete=false;ui.delete.textContent='Delete note';
    ui.counter.textContent=ui.content.value.length+' / 10,000';status(note?'Saved to your account.':'Capture a thought. Save when you’re ready.');renderList();
    const draft=window.SaathiRecovery?.getDraft('note',noteDraftKey());
    if(draft&&typeof draft.content==='string'&&typeof draft.title==='string'){ui.title.value=draft.title.slice(0,80);ui.content.value=draft.content.slice(0,10000);state.clientId=draft.client_id||state.clientId;state.draftVersion=Number.isInteger(draft.version)?draft.version:null;state.dirty=true;ui.discard.hidden=false;ui.counter.textContent=ui.content.value.length+' / 10,000';status('Browser draft recovered. Review it before saving.')}
    if(dialog.open)ui.content.focus();
  }
  function renderList(){
    if(!ui.list)return;ui.list.replaceChildren();const query=ui.search.value.trim().toLocaleLowerCase();
    const notes=state.notes.filter(note=>(note.title+' '+note.content).toLocaleLowerCase().includes(query));
    if(!notes.length){const p=document.createElement('p');p.className='qn-empty';p.textContent=query?'No matching notes.':state.loaded?'Your saved notes will appear here.':'Loading notes…';ui.list.append(p);return}
    notes.forEach(note=>{const button=document.createElement('button');button.type='button';button.className='qn-note';button.classList.toggle('active',state.selected?.id===note.id);button.setAttribute('aria-pressed',String(state.selected?.id===note.id));
      const title=document.createElement('b'),preview=document.createElement('span'),date=document.createElement('small');title.textContent=note.title;preview.textContent=note.content.slice(0,90);date.textContent=new Date(note.updated_at).toLocaleDateString();button.append(title,preview,date);button.onclick=()=>selectNote(note);ui.list.append(button)});
  }
  async function loadNotes(force=false){
    if(state.busy||(force&&!canSwitch()))return;
    ui.reload.disabled=true;status('Loading saved notes…');
    try{const result=await state.api('/api/quick-notes');state.notes=result.notes||[];state.loaded=true;renderList();
      if(force&&state.selected&&!state.dirty)selectNote(state.notes.find(note=>note.id===state.selected.id)||null,true);
      else status(state.dirty?'Unsaved changes':state.notes.length+' saved notes.');
    }catch(error){status(error.message||'Notes could not load. Select Refresh to retry.',true)}finally{ui.reload.disabled=false}
  }
  async function openNotes(){if(!state.user)return;buildDialog();if(!dialog.open)dialog.showModal();if(!state.loaded)await loadNotes();ui.content.focus()}
  async function openNote(id){await openNotes();if(state.loaded&&canSwitch()){const note=state.notes.find(item=>item.id===id);if(note)selectNote(note);else status("This note is no longer available. Refresh your notes.",true)}}
  async function saveNote(event){
    event.preventDefault();if(state.busy)return;if(!ui.content.value.trim()){status('Write something before saving.',true);return}
    state.busy=true;ui.save.disabled=true;ui.delete.disabled=true;status('Saving…');
    const draftKey=noteDraftKey(),draft={title:ui.title.value,content:ui.content.value};const path=state.selected?'/api/quick-notes/'+state.selected.id:'/api/quick-notes';
    const body={...draft,...(state.selected?{version:state.draftVersion??state.selected.version}:{client_id:state.clientId})};
    try{const result=await state.api(path,{method:state.selected?'PATCH':'POST',body:JSON.stringify(body)});const note=result.note;
      state.notes=[note,...state.notes.filter(item=>item.id!==note.id)];state.selected=note;state.loaded=true;
      const replayChanged=result.replayed&&(note.content!==draft.content.trim()||(draft.title.trim()&&note.title!==draft.title.trim()));
      state.dirty=Boolean(replayChanged)||ui.title.value!==draft.title||ui.content.value!==draft.content;
      window.SaathiRecovery?.removeDraft('note',draftKey);state.draftVersion=note.version;if(state.dirty)saveNoteDraft();
      if(!state.dirty){ui.title.value=note.title;ui.content.value=note.content}ui.discard.hidden=!state.dirty;ui.delete.hidden=false;renderList();status(state.dirty?'Earlier changes saved. New edits are unsaved.':'Saved to your account.');
    }catch(error){status(error.message||'Your note could not save. Your draft is still here.',true)}finally{state.busy=false;ui.save.disabled=false;ui.delete.disabled=false}
  }
  async function deleteNote(){
    if(!state.selected||state.busy)return;
    if(!state.confirmDelete){state.confirmDelete=true;ui.delete.textContent='Confirm delete';status('Delete this saved note? Select Confirm delete to remove it.',true);return}
    state.busy=true;ui.delete.disabled=true;
    try{await state.api('/api/quick-notes/'+state.selected.id,{method:'DELETE',body:JSON.stringify({version:state.selected.version})});window.SaathiRecovery?.removeDraft('note',noteDraftKey());state.notes=state.notes.filter(note=>note.id!==state.selected.id);state.dirty=false;state.busy=false;selectNote(null,true);status('Note deleted.')}catch(error){status(error.message,true)}finally{state.busy=false;ui.delete.disabled=false;state.confirmDelete=false;ui.delete.textContent='Delete note'}
  }
  function exportCurrentNotePdf(){
    if(!ui.content.value.trim()){status('Note is empty.',true);return;}
    const escapeHtml=value=>String(value).replace(/[&<>"']/g,char=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
    const title = escapeHtml(ui.title.value.trim() || 'Saathi Note');
    const content = escapeHtml(ui.content.value.trim());
    // Using a new window to print text nicely as PDF
    const win = window.open('','_blank');
    if(!win) { status('Popup blocked. Cannot export PDF.',true); return; }
    win.document.write(`
      <!DOCTYPE html>
      <html>
      <head>
        <title>${title}</title>
        <style>
          body { font-family: system-ui, -apple-system, sans-serif; line-height: 1.6; color: #111; max-width: 800px; margin: 40px auto; padding: 20px; white-space: pre-wrap; }
          h1 { font-size: 24px; margin-bottom: 30px; border-bottom: 2px solid #e2e8f0; padding-bottom: 10px; }
          .meta { color: #64748b; font-size: 12px; margin-bottom: 40px; }
          @media print { body { margin: 0; padding: 0; max-width: none; } }
        </style>
      </head>
      <body>
        <h1>${title}</h1>
        <div class="meta">Exported from Saathi on ${new Date().toLocaleDateString()}</div>
        <div>${content}</div>
        <script>window.onload=()=>setTimeout(()=>{window.print();window.close();},500);<\/script>
      </body>
      </html>
    `);
    win.document.close();
  }
  function pushSupported(){return window.isSecureContext&&'Notification'in window&&'PushManager'in window&&'serviceWorker'in navigator}
  function renderPush(){
    let label='Enable alerts',message='Receive a private reminder alert on this device, even when this tab is closed.',disabled=false;
    if(!pushSupported()){label='Not supported';message='This browser cannot receive background alerts here. On iPhone, add Saathi to your Home Screen and open it there.';disabled=true}
    else if(state.pushConfig===null){label='Retry setup check';message='Could not check background alerts. Retry when your connection is ready.'}
    else if(!state.pushConfig.enabled){label='Not set up yet';message='Background alerts are not set up on this server. Reminders remain available in Saathi.';disabled=true}
    else if(Notification.permission==='denied'){label='Permission blocked';message='Allow notifications in your browser’s site settings, then reload this page.';disabled=true}
    else if(state.pushId){label='Disable on this device';message='Background reminder alerts are enabled on this device. Private reminder details stay inside Saathi.'}
    document.querySelectorAll('[data-push-toggle]').forEach(button=>{button.textContent=state.pushBusy?'Please wait…':label;button.disabled=disabled||state.pushBusy;button.setAttribute('aria-pressed',String(Boolean(state.pushId)))});
    document.querySelectorAll('[data-push-status]').forEach(node=>{node.textContent=message});
  }
  async function endpointHash(endpoint){const hash=await crypto.subtle.digest('SHA-256',new TextEncoder().encode(endpoint));return Array.from(new Uint8Array(hash),byte=>byte.toString(16).padStart(2,'0')).join('')}
  function keyBytes(key){return Uint8Array.from(atob(key.replace(/-/g,'+').replace(/_/g,'/')+'='.repeat((4-key.length%4)%4)),char=>char.charCodeAt(0))}
  async function registration(){
    let timer;
    try{return await Promise.race([(async()=>{await navigator.serviceWorker.register('/service-worker.js');return navigator.serviceWorker.ready})(),new Promise((_,reject)=>{timer=setTimeout(()=>reject(Error('Notification setup took too long. Please retry.')),12000)})])}
    finally{clearTimeout(timer)}
  }
  async function loadPush(){
    if(!pushSupported()){renderPush();return}
    try{state.pushConfig=await state.api('/api/push/config');const reg=await registration();const sub=await reg.pushManager.getSubscription();state.pushId=null;
      if(sub){const hash=await endpointHash(sub.endpoint);const saved=state.pushConfig.subscriptions.find(row=>row.endpoint_hash===hash);state.pushId=saved?.id||null}
    }catch(_){state.pushConfig=null;state.pushId=null}renderPush();
  }
  async function togglePush(){
    if(state.pushBusy||!pushSupported())return;
    if(state.pushConfig===null)return loadPush();
    if(!state.pushConfig.enabled)return;
    state.pushBusy=true;renderPush();
    try{
      // Request permission directly from the click, before any network await.
      const permission=state.pushId?Notification.permission:await Notification.requestPermission();
      if(permission!=='granted'){state.notify('Notification permission was not enabled.');return}
      const reg=await registration();let sub=await reg.pushManager.getSubscription();
      if(state.pushId){await state.api('/api/push/subscriptions/'+state.pushId,{method:'DELETE'});await sub?.unsubscribe();state.pushId=null;for(const note of await reg.getNotifications())note.close();state.notify('Background alerts disabled on this device.');return}
      // An unlinked subscription may belong to a previous account on a shared browser.
      if(sub){await sub.unsubscribe();sub=null}
      sub=await reg.pushManager.subscribe({userVisibleOnly:true,applicationServerKey:keyBytes(state.pushConfig.public_key)});
      try{const saved=await state.api('/api/push/subscriptions',{method:'POST',body:JSON.stringify(sub.toJSON())});state.pushId=saved.id}
      catch(error){await sub.unsubscribe();throw error}
      state.notify('Background reminder alerts enabled on this device.');
    }catch(error){state.notify(error.message||'Notifications could not be enabled. Please try again.','error')}
    finally{state.pushBusy=false;renderPush()}
  }
  async function prepareLogout(){
    if(state.dirty){await openNotes();status('Save or discard your note edits before logging out.',true);return false}
    if(state.pushId){await state.api('/api/push/subscriptions/'+state.pushId,{method:'DELETE'});state.pushId=null}
    try{if('serviceWorker'in navigator){const reg=await navigator.serviceWorker.getRegistration();if(reg){await(await reg.pushManager?.getSubscription())?.unsubscribe();if(reg.getNotifications)for(const notification of await reg.getNotifications())notification.close()}}}catch(_){/* Server subscription was removed; browser cleanup must not block sign-out. */}
    return true;
  }
  function connect(options){
    state.api=options.api;state.notify=options.notify||(()=>{});
    if(state.user?.id===options.user?.id)return;
    state.user=options.user;state.notes=[];state.loaded=false;
    document.querySelectorAll('[data-quick-notes]').forEach(button=>{button.onclick=openNotes});
    document.querySelectorAll('[data-push-toggle]').forEach(button=>{button.onclick=togglePush});
    loadPush();
  }
  window.SaathiWorkspace={connect,renderAvatar,openNotes,openNote,togglePush,prepareLogout,pushActive:()=>Boolean(state.pushId),pushConfigured:()=>Boolean(state.pushConfig?.enabled)};
})();
