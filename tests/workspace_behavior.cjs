// Exercise production functions with a small DOM/history model; no network or user data.
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const source=fs.readFileSync('dashboard.html','utf8');
const ids=['overview','tasks','reminders','habits','journal','checkins','memory','family','account'];
let focusTarget=null;
class Element {
 constructor(id){this.id=id;this.hidden=false;this.dataset={};this.textContent=id;this.attrs={};this.children=[];this.value='';this.inert=false;this.classes=new Set();this.classList={toggle:(k,v)=>v?this.classes.add(k):this.classes.delete(k),contains:k=>this.classes.has(k),add:k=>this.classes.add(k),remove:k=>this.classes.delete(k)};}
 setAttribute(k,v){this.attrs[k]=v}removeAttribute(k){delete this.attrs[k]}
 focus(){focusTarget=this.id}
 prepend(node){node.parent=this;this.children.unshift(node)}
 remove(){if(this.parent)this.parent.children=this.parent.children.filter(n=>n!==this)}
 querySelector(selector){if(selector==='h1')return heading.get(this.id);if(selector==='.section-error')return this.children.find(n=>n.className==='section-error')||null;return null}
}
const elements=new Map(),heading=new Map(ids.map(id=>[id,new Element(id+'-heading')]));
const $=id=>{if(!elements.has(id))elements.set(id,new Element(id));return elements.get(id)};
const views=ids.map($),buttons=ids.map(id=>{const el=new Element(id+'-button');el.dataset.view=id;return el});
const main=new Element('main'),body=new Element('body'),events={},media={matches:false,addEventListener(k,fn){this.onchange=fn}};
let entries=['/account','/dashboard'],index=1;
const location={hash:'',replace(url){entries[index]=url;this.hash=url.includes('#')?'#'+url.split('#')[1]:''}};
const history={pushState(data,title,url){entries=entries.slice(0,index+1);entries.push('/dashboard'+url);index++;location.hash=url},replaceState(data,title,url){entries[index]='/dashboard'+url;location.hash=url},back(){index--;location.hash=entries[index].split('#')[1]?'#'+entries[index].split('#')[1]:'';events.popstate()},forward(){index++;location.hash=entries[index].split('#')[1]?'#'+entries[index].split('#')[1]:'';events.popstate()}};
const document={body,title:'',querySelectorAll(sel){if(sel==='.view')return views;if(sel==='.nav button[data-view]')return buttons;throw Error(sel)},querySelector(sel){if(sel==='main')return main;if(sel==='.nav button.active')return buttons.find(b=>b.classes.has('active'));throw Error(sel)},createElement(){return new Element('created')}};
const state={currentView:null,loadingSections:false,loadFailures:[],reminders:[],notified:new Set()};
const ctx={state,document,$,history,location,matchMedia:()=>media,scrollTo(){},window:{addEventListener:(name,fn)=>events[name]=fn},console,Date,Set};vm.createContext(ctx);
vm.runInContext(source.slice(source.indexOf('const workspaceViews='),source.indexOf('function applyTheme(theme)')),ctx);
ctx.syncWorkspaceHistory(false);assert.equal(entries[index],'/dashboard#overview');
for(const id of ['tasks','reminders','memory']){
 $('journalContent').value='Unsaved private draft';
 ctx.openView(id);assert.equal(state.currentView,id);assert.equal(focusTarget,id+'-heading');assert.equal($(id).hidden,false);assert.equal($('overview').hidden,true);
 const count=entries.length;ctx.openView(id);assert.equal(entries.length,count,'Repeated view must not add history');
 history.back();assert.equal(state.currentView,'overview');assert.equal(entries[index],'/dashboard#overview','Back must stay inside dashboard');
 history.forward();assert.equal(state.currentView,id);history.back();assert.equal($('journalContent').value,'Unsaved private draft');
}
location.hash='#memory';ctx.syncWorkspaceHistory(false);assert.equal(state.currentView,'memory','Refresh/deep link must restore section');
location.hash='#unknown';ctx.syncWorkspaceHistory();assert.equal(state.currentView,'overview');assert.equal(location.hash,'#overview');
media.matches=true;ctx.setNavigation(false);assert.equal($('sidebar').inert,true);ctx.setNavigation(true);assert.equal(main.inert,true);assert.equal($('sidebar').inert,false);ctx.openView('tasks');assert.equal(main.inert,false);assert.equal($('sidebar').inert,true);
media.matches=false;media.onchange();assert.equal($('sidebar').inert,false);
vm.runInContext(source.slice(source.indexOf('function checkDueReminders()'),source.indexOf('async function installApp()')),ctx);
assert.doesNotThrow(()=>ctx.checkDueReminders(),'Missing Notification API must not crash dashboard');
ctx.window.Notification=function(){};ctx.Notification={permission:'granted'};state.reminders=[{active:true,id:1,next_run_at:'2020-01-01'}];
assert.doesNotThrow(()=>ctx.checkDueReminders(),'Unsupported constructor must not crash dashboard');
vm.runInContext(source.slice(source.indexOf('const workspaceSections='),source.indexOf('function updateGreeting()')),ctx);
(async()=>{
 let applied=[];ctx.api=async url=>{if(url==='/bad')throw Error('Offline');return {items:[1]}};
 const sections=[{key:'tasks',label:'Planner',url:'/ok',apply:data=>applied.push(data.items[0])},{key:'memory',label:'Memory',url:'/bad',apply:()=>{}}];
 await ctx.loadWorkspaceSections(sections);assert.deepEqual(applied,[1]);assert.equal(state.loadFailures.length,1);assert.equal($('workspaceStatus').hidden,false);assert.equal($('memory').attrs['aria-busy'],'false');assert.ok($('memory').querySelector('.section-error'));
 ctx.api=async()=>({});await ctx.loadWorkspaceSections(state.loadFailures);assert.equal(state.loadFailures.length,0);assert.equal($('workspaceStatus').hidden,true);assert.equal($('memory').querySelector('.section-error'),null);assert.equal($('journalContent').value,'Unsaved private draft');
 // Initial connection failures must leave a usable Retry button.
 const initCtx={state:{user:null},$,applyTheme(){},localStorage:{getItem:()=>null},localDate:()=>'',syncWorkspaceHistory(){},api:async()=>{throw Error('Offline')},toast(){}};
 vm.createContext(initCtx);vm.runInContext(source.slice(source.indexOf('async function init(){'),source.indexOf("$('skipWorkspace').addEventListener")),initCtx);
 $('retryWorkspace').disabled=true;await initCtx.init();assert.equal($('retryWorkspace').disabled,false);assert.equal($('workspaceStatus').hidden,false);
 // Only a real 401 may redirect to login; network/server errors stay in place.
 let redirects=[],scheduled,cleared=0;
 const apiCtx={state:{csrf:'test-csrf'},location:{hash:'#memory',replace:url=>redirects.push(url)},AbortController,TypeError,setTimeout:fn=>{scheduled=fn;return 1},clearTimeout:()=>cleared++};
 vm.createContext(apiCtx);vm.runInContext(source.slice(source.indexOf('async function api('),source.indexOf('function toastTone(')),apiCtx);
 apiCtx.fetch=async()=>({status:500,ok:false,json:async()=>({error:'Temporarily unavailable'})});await assert.rejects(apiCtx.api('/api/memories'),/Temporarily unavailable/);assert.equal(redirects.length,0);
 apiCtx.fetch=async()=>{throw new TypeError('Network unavailable')};await assert.rejects(apiCtx.api('/api/me'),/Check your connection/);assert.equal(redirects.length,0);
 apiCtx.fetch=async()=>({status:200,ok:true,json:async()=>{scheduled();const error=Error('Aborted');error.name='AbortError';throw error}});await assert.rejects(apiCtx.api('/api/me'),/took too long/);assert.equal(redirects.length,0);
 apiCtx.fetch=async()=>({status:401});await assert.rejects(apiCtx.api('/api/me'),/log in/);assert.deepEqual(redirects,['/account?next=%2Fdashboard%23memory']);assert.equal(cleared,4);
 // Run actual login/OTP submit handlers and verify replacement, not addition.
 const account=fs.readFileSync('account.html','utf8');
 const handlers={},authCtx={document:{getElementById:id=>{const el=$(id);el.addEventListener=(event,fn)=>handlers[id]=fn;return el}},post:async()=>({}),hideMessage(){},showMessage(){},destination:'/dashboard#memory',location,pendingEmail:'preview@example.test'};
 vm.createContext(authCtx);
 for(const name of ['loginForm','otpForm']){const line=account.split('\n').find(l=>l.startsWith("document.getElementById('"+name+"').addEventListener('submit'"));assert.ok(line);vm.runInContext(line,authCtx);entries=['/account'];index=0;await handlers[name]({preventDefault(){}});assert.deepEqual(entries,['/dashboard#memory']);}
 console.log('PASS: dashboard Back/Forward, deep links, draft retention, mobile focus, notification fallback, retry recovery, API errors, login/OTP history');
})().catch(error=>{console.error(error);process.exitCode=1});
// Execute the actual next-path expression, including hostile redirect inputs.
const accountSource=fs.readFileSync('account.html','utf8');
const destinationCode=accountSource.slice(accountSource.indexOf('const params='),accountSource.indexOf(';let pendingEmail'));
for(const [next,expected] of [['/dashboard#tasks','/dashboard#tasks'],['/dashboard#memory','/dashboard#memory'],['/chat','/chat'],['https://example.test','/dashboard'],['//example.test','/dashboard'],['/dashboard#unknown','/dashboard'],['/chat?next=evil','/dashboard']]){
 const sandbox={URLSearchParams,location:{search:'?next='+encodeURIComponent(next)}};vm.createContext(sandbox);vm.runInContext(destinationCode,sandbox);assert.equal(vm.runInContext('destination',sandbox),expected);
}
