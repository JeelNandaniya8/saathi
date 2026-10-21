'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const source=fs.readFileSync('classroom-file-draft.js','utf8');
const ID='11111111-1111-4111-8111-111111111111';
function setup({lang='en',missing=false,remaining=5}={}){
 class El{
  constructor(tag){this.tag=tag;this.children=[];this.events={};this.attributes={};this.textContent=''}
  append(...xs){this.children.push(...xs)}
  before(el){this.previous=el}
  remove(){this.removed=true}
  setAttribute(k,v){this.attributes[k]=v}
  removeAttribute(k){delete this.attributes[k]}
  addEventListener(k,v){this.events[k]=v}
 }
 const state={id:7,text:'Keep my exact draft',mode:'normal',fileOnly:false,requestId:'exact-request',missing,files:[],ready:true,busy:false,allowance:{enabled:true,remaining_today:remaining},manifest:[]};
 const host=new El('form'),calls={attached:[],notified:[],fetch:[],urls:[]};
 const root={document:{documentElement:{lang},createElement:t=>new El(t)},location:{href:'https://example.test/chat?classroom_file='+ID},
  history:{state:null,replaceState:(s,t,url)=>calls.urls.push(url)}};
 root.fetch=async(...args)=>{calls.fetch.push(args);return new Response(new Blob(['%PDF-1.4\nSynthetic'],{type:'application/pdf'}),{headers:{
  'Content-Type':'application/pdf','X-Saathi-File-Name':'Practice.pdf','X-Saathi-File-Modified':'1000'}})};
 const sandbox={window:root,document:root.document,URL,File,Blob,AbortController,Response,console};
 vm.runInNewContext(source,sandbox);
 root.SaathiClassroomFile.connect({host,snapshot:()=>({...state}),attach:(f,p)=>{calls.attached.push([f,p]);return true},notify:m=>calls.notified.push(m)});
 const panel=host.previous,buttons=panel.children.filter(e=>e.tag==='button'),status=panel.children.find(e=>e.attributes.role==='status');
 return{state,root,calls,panel,buttons,status,api:root.SaathiClassroomFile};
}
function deferred(){let resolve;const promise=new Promise(r=>resolve=r);return{promise,resolve}}
(async()=>{
 for(const lang of ['en','gu','hi']){
  const s=setup({lang});await s.buttons[0].events.click();
  assert.equal(s.calls.attached.length,1);assert.equal(s.calls.fetch.length,1);
  assert.equal(s.calls.fetch[0][0],'/api/classroom/files/'+ID+'/download');
  assert.equal(s.calls.fetch[0][1].cache,'no-store');
  assert.equal(s.calls.attached[0][0].name,'Practice.pdf');
  assert.equal(s.calls.attached[0][0].lastModified,1000);
  assert(s.panel.removed);assert.equal(s.calls.urls[0],'/chat');
  assert.equal(s.state.text,'Keep my exact draft');assert.equal(s.state.requestId,'exact-request');
 }
 for(const change of [{busy:true},{ready:false},{files:[{name:'Existing.pdf'}]},{allowance:{enabled:true,remaining_today:0}},{allowance:{enabled:true,remaining_today:null}}]){
  const s=setup();Object.assign(s.state,change);await s.buttons[0].events.click();
  assert.equal(s.calls.fetch.length,0);assert.equal(s.calls.attached.length,0);assert(!s.panel.removed);
 }
 for(const field of ['text','id','mode','fileOnly','requestId']){
  const s=setup(),pending=deferred(),response=await s.root.fetch('fixture');s.calls.fetch=[];
  s.root.fetch=()=>pending.promise;const action=s.buttons[0].events.click();
  s.state[field]=field==='id'?8:field==='fileOnly'?true:'changed';pending.resolve(response);await action;
  assert.equal(s.calls.attached.length,0);assert.match(s.status.textContent,/changed/);
  assert.equal(s.state[field],field==='id'?8:field==='fileOnly'?true:'changed');
 }
 {
  const s=setup({missing:true});s.state.manifest=[{name:'Different.pdf',size:17,type:'application/pdf',lastModified:1000}];
  await s.buttons[0].events.click();assert.equal(s.calls.attached.length,0);assert.match(s.status.textContent,/does not match/);
  assert.equal(s.state.requestId,'exact-request');assert.equal(s.state.fileOnly,false);
 }
 {
  const s=setup({missing:true});s.state.manifest=[{name:'Practice.pdf',size:18,type:'application/pdf',lastModified:1000}];
  // Exact bytes, name, type and modification marker are required for recovery.
  const response=await s.root.fetch('fixture'),blob=await response.blob();s.state.manifest[0].size=blob.size;s.calls.fetch=[];
  await s.buttons[0].events.click();assert.equal(s.calls.attached.length,1);
  assert.equal(s.state.requestId,'exact-request');assert.equal(s.state.fileOnly,false);
 }
 {
  const s=setup(),pending=deferred(),response=await s.root.fetch('fixture');
  s.root.fetch=()=>pending.promise;const action=s.buttons[0].events.click();s.buttons[1].events.click();
  pending.resolve(response);await action;assert.equal(s.calls.attached.length,0);assert(s.panel.removed);
 }
 for(const code of ['file_expired','file_permission','file_changed','file_size','file_type']){
  const s=setup();s.root.fetch=async()=>new Response(JSON.stringify({error_code:code}),{status:409});
  await s.buttons[0].events.click();assert.equal(s.calls.attached.length,0);assert(!s.panel.removed);assert(s.status.textContent);
 }
 const chat=fs.readFileSync('chat.html','utf8'),module=fs.readFileSync('classroom-file-draft.js','utf8');
 assert(chat.includes('chooseFiles([file])'));assert(chat.includes('if(!recovered){el.fileOnly.checked=true;'));
 assert(!module.includes('sendContent('));assert(!module.includes('/api/chat'));
 console.log('Classroom file draft: 3 languages, quota/busy gates, five draft races, exact recovery, cancellation and provider errors passed');
})().catch(error=>{console.error(error);process.exitCode=1});
