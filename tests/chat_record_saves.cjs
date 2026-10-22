// Execute the shipped dialog handlers against lost-response and read-back fixtures.
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict'),{test}=require('node:test');
const html=fs.readFileSync('chat.html','utf8');
function setup(kind,zone='Asia/Kolkata'){
 const elements={},pending=[],notices=[],state={},closed=[];
 const element=id=>elements[id]??={value:'',disabled:false,close(){closed.push(id)},showModal(){},select(){}};
 element(kind+'Title').value='Revision ગુજરાતીમાં हिन्दी';
 element(kind==='task'?'taskDue':'reminderTime').value='2026-11-01T18:30';
 element(kind==='task'?'taskPriority':'reminderRepeat').value=kind==='task'?'medium':'once';
 const ctx={state,window:{},Intl,el:{taskDialog:element('taskDialog'),reminderDialog:element('reminderDialog')},
  document:{getElementById:element,documentElement:{lang:'en'}},crypto:require('node:crypto').webcrypto,
  api:(url,options)=>new Promise((resolve,reject)=>pending.push({url,options,resolve,reject})),
  showToast:(...args)=>notices.push(args),chatText:x=>x,setTimeout:fn=>fn(),Date};
 vm.createContext(ctx);vm.runInContext(fs.readFileSync('account-clock.js','utf8'),ctx);ctx.SaathiClock=ctx.window.SaathiClock;ctx.SaathiClock.setZone(zone);vm.runInContext(html.slice(html.indexOf('function suggestedActionTitle('),html.indexOf('function scrollToLatest(')),ctx);
 const button={disabled:false},submit=()=>ctx[kind==='task'?'saveTask':'saveReminder']({preventDefault(){},submitter:button});
 return {ctx,state,element,pending,notices,closed,button,submit};
}
for(const kind of ['task','reminder']){
 test(kind+': account-local time is saved as the exact instant, independent of browser timezone',async()=>{
  const s=setup(kind),work=s.submit(),payload=JSON.parse(s.pending[0].options.body);
  assert.equal(payload[kind==='task'?'due_at':'next_run_at'],'2026-11-01T13:00:00.000Z');
  s.pending[0].reject(Error('Offline'));await work;
 });
 test(kind+': an ambiguous daylight-saving time preserves the draft without sending',async()=>{
  const s=setup(kind,'America/New_York');s.element(kind==='task'?'taskDue':'reminderTime').value='2026-11-01T01:30';
  await s.submit();assert.equal(s.pending.length,0);assert.equal(s.closed.length,0);assert.equal(s.button.disabled,false);
  assert.match(s.notices[0][0],/ambiguous/);
 });
 test(kind+': lost POST response retains one request identity and exact draft',async()=>{
  const s=setup(kind);let work=s.submit();const body=JSON.parse(s.pending[0].options.body);
  assert.match(body.client_id||'',/^[0-9a-f-]{36}$/,'A saved record needs a stable retry identity');
  s.pending[0].reject(Error('Response lost after commit'));await work;
  assert.equal(s.closed.length,0);assert.equal(s.element(kind+'Title').value,'Revision ગુજરાતીમાં हिन्दी');
  work=s.submit();assert.deepEqual(JSON.parse(s.pending[1].options.body),body);
  s.pending[1].reject(Error('Still offline'));await work;
  s.element(kind+'Title').value='A different request';work=s.submit();
  assert.notEqual(JSON.parse(s.pending[2].options.body).client_id,body.client_id);
  s.pending[2].reject(Error('Offline'));await work;
 });
 test(kind+': double submit sends once and success waits for exact owned read-back',async()=>{
  const s=setup(kind),work=s.submit(),second=s.submit();assert.equal(s.pending.length,1);await second;
  const payload=JSON.parse(s.pending[0].options.body),record={...payload,id:91};
  s.pending[0].resolve({[kind]:record});await new Promise(setImmediate);
  assert.equal(s.closed.length,0,'A POST response alone cannot close the dialog as saved');
  assert.equal(s.pending[1].url,'/api/'+(kind==='task'?'tasks':'reminders')+'/91');
  s.pending[1].resolve({[kind]:record});await work;
  assert.equal(s.closed.length,1);assert.equal(s.button.disabled,false);
  assert.ok(s.notices.some(args=>args.includes('/dashboard?'+kind+'=91#'+(kind==='task'?'tasks':'reminders'))));
 });
 test(kind+': failed read-back is not success and retries the same committed object',async()=>{
  const s=setup(kind),work=s.submit(),payload=JSON.parse(s.pending[0].options.body);
  s.pending[0].resolve({[kind]:{...payload,id:91}});await new Promise(setImmediate);
  assert.equal(s.pending.length,2,'Read the owned saved object independently');
  s.pending[1].resolve({[kind]:{...payload,id:92}});await work;
  assert.equal(s.closed.length,0);assert.equal(s.button.disabled,false);
  const again=s.submit();assert.deepEqual(JSON.parse(s.pending[2].options.body),payload);
  s.pending[2].reject(Error('Offline'));await again;
 });
 test(kind+': text edited during a save is kept after the earlier record is verified',async()=>{
  const s=setup(kind),work=s.submit(),payload=JSON.parse(s.pending[0].options.body);
  s.element(kind+'Title').value='New unsaved thought';
  s.pending[0].resolve({[kind]:{...payload,id:91}});await new Promise(setImmediate);
  s.pending[1].resolve({[kind]:{...payload,id:91}});await work;
  assert.equal(s.closed.length,0);assert.equal(s.element(kind+'Title').value,'New unsaved thought');
 });
 for(const changed of ['title','time'])test(kind+': changed '+changed+' fails exact read-back',async()=>{
  const s=setup(kind),work=s.submit(),payload=JSON.parse(s.pending[0].options.body),record={...payload,id:91};
  s.pending[0].resolve({[kind]:record});await new Promise(setImmediate);
  const difference=changed==='title'?{title:'Another object'}:{[kind==='task'?'due_at':'next_run_at']:'2026-12-31T00:00:00Z'};
  s.pending[1].resolve({[kind]:{...record,...difference}});await work;
  assert.equal(s.closed.length,0);assert.equal(s.notices.some(args=>args[1]==='success'),false);
 });
}
