// Execute shared production controllers against a minimal DOM. No network or notifications.
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const {webcrypto}=require('node:crypto');
class Element {
  constructor(){this.value='';this.children=[];this.dataset={};this.events={};this.attrs={};this.hidden=false;this.disabled=false;this.textContent='';this.style={};this.open=false;this.classList={toggle(){}}}
  setAttribute(k,v){this.attrs[k]=v}hasAttribute(k){return k in this.attrs}
  addEventListener(k,fn){this.events[k]=fn}focus(){}getBoundingClientRect(){return {left:0,right:600,top:0,bottom:700}}
  replaceChildren(...nodes){this.children=nodes;nodes.forEach(node=>node.parentNode=this);this.textContent=''}
  append(...nodes){nodes.forEach(node=>node.parentNode=this);this.children.push(...nodes)}
  set innerHTML(value){this.html=value;this.parts={};for(const name of value.matchAll(/data-qn="([^"]+)"/g)){const el=new Element();el.dataset.qn=name[1];this.parts[name[1]]=el}}
  querySelectorAll(){return Object.values(this.parts)}showModal(){this.open=true}close(){this.open=false}
}
const tick=()=>new Promise(resolve=>setImmediate(resolve));
function workspaceEnvironment(api,storage=null){
  const body=new Element(),trigger=new Element(),pushButton=new Element(),pushStatus=new Element(),events={};
  const document={body,createElement:()=>new Element(),querySelectorAll:selector=>selector==='[data-quick-notes]'?[trigger]:selector==='[data-push-toggle]'?[pushButton]:selector==='[data-push-status]'?[pushStatus]:[]};
  const window={addEventListener:(name,fn)=>events[name]=fn};
  const ctx={window,document,navigator:{},crypto:webcrypto,URL,TextEncoder,Uint8Array,atob,setTimeout,clearTimeout,Date};
  vm.createContext(ctx);vm.runInContext(fs.readFileSync('workspace.js','utf8'),ctx);
  if(storage){ctx.localStorage=storage;window.crypto=webcrypto;vm.runInContext(fs.readFileSync('recovery.js','utf8'),ctx);window.SaathiRecovery.connect({user:{id:1},api})}
  return {ctx,body,trigger,pushButton,pushStatus,events,api,controller:window.SaathiWorkspace};
}
(async()=>{
  let notes=[],lost=true,requests=[],failConflict=false,pendingRefresh;
  const env=workspaceEnvironment(async(path,options={})=>{
    requests.push([path,options.method||'GET']);
    if(path==='/api/quick-notes'&&!options.method){if(pendingRefresh)return pendingRefresh;return {notes:notes.map(n=>({...n}))}}
    const data=JSON.parse(options.body||'{}');
    if(options.method==='POST'){
      if(notes.length)return {note:{...notes[0]},replayed:true};
      const note={...data,id:1,version:1,updated_at:new Date().toISOString()};notes.push(note);
      if(lost){lost=false;throw Error('Connection interrupted')}
      return {note};
    }
    if(options.method==='PATCH'){
      if(failConflict)throw Error('This note changed on another device');
      assert.equal(data.version,notes[0].version);notes[0]={...notes[0],...data,version:data.version+1};return {note:{...notes[0]}};
    }
    if(options.method==='DELETE'){assert.equal(data.version,notes[0].version);notes=[];return {ok:true}}
    throw Error('Unexpected '+path);
  });
  env.controller.connect({user:{id:1,name:'Student'},api:env.api});
  assert.equal(requests.length,0,'Notes load on demand and unsupported push makes no request');
  await env.trigger.onclick();const dialog=env.body.children[0],ui=dialog.parts;
  let exported='';env.ctx.window.open=()=>({document:{write:html=>exported=html,close(){}}});
  ui.title.value='</title><script>bad()</script><h1>';ui.content.value='ગુજરાતી &lt; <img onerror=bad()>';
  ui.exportpdf.onclick();assert.ok(exported.includes('&lt;/title&gt;&lt;script&gt;'));assert.ok(!exported.includes('<script>bad()'));assert.ok(!exported.includes('<img onerror'));assert.ok(exported.includes('ગુજરાતી &amp;lt;'));
  assert.equal((exported.match(/<script>/g)||[]).length,1,'Only the fixed print handler may be executable');ui.title.value='';ui.content.value='';
  const edit=(node,value)=>{node.value=value;node.events.input()};
  const submit=()=>ui.form.events.submit({preventDefault(){}});
  edit(ui.content,'ગુજરાતી <img onerror=bad()>');await submit();
  assert.equal(ui.content.value,'ગુજરાતી <img onerror=bad()>');assert.match(ui.status.textContent,/Connection interrupted/);
  edit(ui.content,'Latest draft after failed response');await submit();
  assert.equal(ui.content.value,'Latest draft after failed response','Retry must retain edits newer than a recovered save');
  assert.equal(ui.discard.hidden,false);
  await submit();assert.equal(notes[0].content,'Latest draft after failed response');assert.equal(notes[0].version,2);assert.equal(ui.discard.hidden,true);
  edit(ui.content,'Unsaved conflict');failConflict=true;await submit();
  ui.new.onclick();assert.equal(ui.content.value,'Unsaved conflict','Switching cannot erase an unsaved draft');
  assert.equal(await env.controller.prepareLogout(),false);assert.equal(dialog.open,true);
  let prevented=false;env.events.beforeunload({preventDefault(){prevented=true}});assert.ok(prevented);
  ui.discard.onclick();failConflict=false;
  let resolveRefresh;pendingRefresh=new Promise(resolve=>resolveRefresh=resolve);
  const refreshing=ui.reload.onclick();edit(ui.content,'Typed while refreshing');resolveRefresh({notes:notes.map(n=>({...n}))});await refreshing;pendingRefresh=null;
  assert.equal(ui.content.value,'Typed while refreshing','Late refresh cannot overwrite ongoing typing');
  ui.discard.onclick();const beforeDelete=requests.length;await ui.delete.onclick();assert.equal(requests.length,beforeDelete,'Deletion needs its second confirmation');
  await ui.delete.onclick();assert.equal(notes.length,0);assert.equal(ui.content.value,'');assert.equal(await env.controller.prepareLogout(),true);
  const avatar=new Element();env.controller.renderAvatar(avatar,{name:'Jeel',avatar_url:'https://evil.test/photo'});assert.equal(avatar.textContent,'J');assert.equal(avatar.children.length,0);
  env.controller.renderAvatar(avatar,{name:'Jeel',avatar_url:'https://lh3.googleusercontent.com/photo'});assert.equal(avatar.children[0].referrerPolicy,'no-referrer');avatar.children[0].events.error();assert.equal(avatar.textContent,'J');

  // Permission is requested from the click, before service-worker/network awaits.
  const order=[],closed=[],endpoint='https://fcm.googleapis.com/fcm/send/local-browser';let currentSub=null;
  const reg={pushManager:{getSubscription:async()=>currentSub,subscribe:async options=>{order.push('subscribe');assert.equal(options.userVisibleOnly,true);currentSub={endpoint,toJSON:()=>({endpoint,keys:{}}),unsubscribe:async()=>{order.push('unsubscribe');currentSub=null;return true}};return currentSub}},getNotifications:async()=>[{close:()=>closed.push(true)}]};
  const alertEnv=workspaceEnvironment(async(path,options={})=>{order.push(path);if(path==='/api/push/config')return {enabled:true,public_key:'BAAA',subscriptions:[]};if(options.method==='POST')return {id:7};return {ok:true}});
  Object.assign(alertEnv.ctx.window,{isSecureContext:true,PushManager:function(){},Notification:{permission:'default',requestPermission(){order.push('permission');this.permission='granted';return Promise.resolve('granted')}}});
  alertEnv.ctx.Notification=alertEnv.ctx.window.Notification;
  alertEnv.ctx.navigator.serviceWorker={register:async()=>{order.push('register');return reg},ready:Promise.resolve(reg),getRegistration:async()=>reg};
  alertEnv.controller.connect({user:{id:1},api:alertEnv.api});await tick();order.length=0;
  const enabling=alertEnv.pushButton.onclick();assert.equal(order[0],'permission');await enabling;
  assert.equal(alertEnv.controller.pushActive(),true);assert.equal(alertEnv.pushButton.textContent,'Disable on this device');
  await alertEnv.controller.prepareLogout();assert.equal(alertEnv.controller.pushActive(),false);assert.ok(order.includes('/api/push/subscriptions/7'));assert.equal(currentSub,null);assert.equal(closed.length,1);

  // Appearance follows OS until an explicit preference, and works with blocked storage.
  const appearanceButton=new Element();appearanceButton.attrs['data-theme-label']='';let osChange,storageChange,ready,click;
  const media={matches:true,addEventListener:(name,fn)=>osChange=fn},root={dataset:{},style:{}};
  const themeCtx={window:{matchMedia:()=>media,addEventListener:(name,fn)=>storageChange=fn},localStorage:{getItem(){throw Error('blocked')},setItem(){throw Error('blocked')}},document:{documentElement:root,querySelector:()=>null,querySelectorAll:()=>[appearanceButton],addEventListener:(name,fn)=>ready=fn}};
  vm.createContext(themeCtx);vm.runInContext(fs.readFileSync('theme.js','utf8'),themeCtx);
  assert.equal(root.dataset.theme,'dark');media.matches=false;osChange();assert.equal(root.dataset.theme,'light');
  ready();appearanceButton.events.click();assert.equal(root.dataset.theme,'dark');media.matches=false;osChange();assert.equal(root.dataset.theme,'dark');
  assert.equal(appearanceButton.attrs['aria-label'],'Switch to light mode');storageChange({key:'saathi-theme',newValue:'light'});assert.equal(root.dataset.theme,'light');

  // Push payloads cannot inject private content or redirect the click off-site.
  const handlers={},notified=[],opened=[];let focused=0;let windows=[{url:'https://saathi.test/chat',focus(){throw Error('Must preserve unsaved chat')}}];
  const worker={location:{origin:'https://saathi.test'},addEventListener:(name,fn)=>handlers[name]=fn,registration:{showNotification:async(title,options)=>notified.push({title,options})},clients:{matchAll:async()=>windows,openWindow:async url=>opened.push(url)}};
  const workerCtx={self:worker,URL};vm.createContext(workerCtx);vm.runInContext(fs.readFileSync('service-worker.js','utf8'),workerCtx);
  let work;handlers.push({data:{json:()=>({title:'Private title',body:'Private note',url:'https://evil.test',tag:'bad'})},waitUntil:p=>work=p});await work;
  assert.equal(notified[0].title,'Saathi reminder');assert.ok(!JSON.stringify(notified).includes('Private'));assert.equal(notified[0].options.data.url,'/dashboard#reminders');
  const notification={data:{url:'https://evil.test'},close(){}};handlers.notificationclick({notification,waitUntil:p=>work=p});await work;assert.deepEqual(opened,['/dashboard#reminders']);
  windows=[{url:'https://saathi.test/dashboard#reminders',focus:async()=>focused++}];handlers.notificationclick({notification,waitUntil:p=>work=p});await work;assert.equal(focused,1);assert.equal(opened.length,1);
  // Reload restores unsaved note text and its original conflict version.
  class Storage{getItem(k){return this[k]??null}setItem(k,v){this[k]=String(v)}removeItem(k){delete this[k]}}
  const storage=new Storage();let recoveredVersion;
  const noteApi=async(path,options={})=>{if(options.method==='PATCH'){recoveredVersion=JSON.parse(options.body).version;throw Error('Note changed on another device')}return {notes:[{id:8,client_id:webcrypto.randomUUID(),version:2,title:'Saved',content:'Server content',updated_at:new Date().toISOString()}]}};
  const beforeReload=workspaceEnvironment(noteApi,storage);beforeReload.controller.connect({user:{id:1},api:noteApi});await beforeReload.controller.openNote(8);
  const noteUi=beforeReload.body.children[0].parts;noteUi.content.value='My unsaved edit';noteUi.content.events.input();
  const raw=JSON.parse(storage.getItem('saathi-draft-v1:1:note:8'));raw.version=1;storage.setItem('saathi-draft-v1:1:note:8',JSON.stringify(raw));
  const afterReload=workspaceEnvironment(noteApi,storage);afterReload.controller.connect({user:{id:1},api:noteApi});await afterReload.controller.openNote(8);
  const restored=afterReload.body.children[0].parts;assert.equal(restored.content.value,'My unsaved edit');await restored.form.events.submit({preventDefault(){}});assert.equal(recoveredVersion,1);assert.equal(restored.content.value,'My unsaved edit');
  restored.discard.onclick();assert.equal(restored.content.value,'Server content');assert.equal(storage.getItem('saathi-draft-v1:1:note:8'),null);
  console.log('PASS: note reload recovery, conflict/draft retention, deletion, avatars, opt-in push/logout, theme preferences, private push display and safe click routing');
})().catch(error=>{console.error(error);process.exitCode=1});
