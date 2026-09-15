// Exercise production UI controllers with a small DOM and stubbed account APIs.
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
class Element{
 constructor(tag='div'){this.tag=tag;this.children=[];this.dataset={};this.attrs={};this.events={};this.disabled=false;this.hidden=false;this.value='';this.checked=false;this.open=false;this._text=''}
 set textContent(v){this._text=String(v);this.children=[]}
 get textContent(){return this._text+this.children.map(n=>n.textContent).join('')}
 get firstChild(){return {set textContent(v){},textContent:this._text}}
 append(...ns){for(const n of ns){n.parentNode=this;this.children.push(n)}}
 replaceChildren(...ns){this._text='';this.children=[];this.append(...ns)}
 setAttribute(k,v){this.attrs[k]=v}
 addEventListener(k,fn){this.events[k]=fn}
 querySelectorAll(selector){const all=this.children.flatMap(x=>[x,...x.querySelectorAll('*')]);if(selector==='*')return all;return all.filter(x=>x.tag===selector)}
 querySelector(selector){return this.querySelectorAll(selector)[0]||null}
 get options(){return this.children}
 showModal(){this.open=true}close(){this.open=false;this.events.close?.()}
 remove(){if(this.parentNode)this.parentNode.children=this.parentNode.children.filter(x=>x!==this)}
 focus(){this.focused=true}
}
const tick=()=>new Promise(r=>setImmediate(r));
function setup(api){
 const ids=Object.fromEntries(['subjectSpaces','subjectDetail','newSubject','revisionQueue','revisionCount','refreshRevision','importRevision','careSmallStep','careLightenPlan','dailySettings','dailyPreferenceSummary','personaliseWorkspace'].map(id=>[id,new Element()]));
 const body=new Element('body'),document={body,getElementById:id=>ids[id]||null,createElement:tag=>new Element(tag),querySelector:()=>null};
 const notices=[],opened=[],window={SaathiWorkspace:{openNotes:async()=>opened.push('notes'),openNote:async id=>opened.push(id)},open:()=>{}};
 const ctx={window,document,Intl,Date,Math,location:{hash:''}},options={api,notify:(...args)=>notices.push(args),openView:id=>opened.push(id),confirm:async()=>true,tasks:()=>[],refreshTasks:async()=>{}};
 vm.createContext(ctx);vm.runInContext(fs.readFileSync('daily-workspace.js','utf8'),ctx);
 return {ids,body,controller:window.SaathiDaily,options,notices,opened};
}
const pref={language:'en',goal:'explore',onboarding_done:true,timezone:'Asia/Kolkata',quiet_enabled:false,quiet_start:'22:00',quiet_end:'08:00',notification_mode:'immediate',digest_time:'18:00',celebrations:false};
(async()=>{
 let reviewed=false,fail=true,calls=[],careCalls=0;
 const card={id:8,version:1,topic:'ગુજરાતી',front:'પ્રશ્ન <script>literal</script>',back:'જવાબ',next_review_at:'2026-09-15T00:00:00Z'};
 const api=async(path,options={})=>{
  calls.push([path,options.method||'GET',JSON.parse(options.body||'{}')]);
  if(path==='/api/workspace/preferences')return {preferences:{...pref}};
  if(path==='/api/revision')return {items:reviewed?[]:[card],due:reviewed?0:1,upcoming:reviewed?1:0,next_at:reviewed?'2026-09-16T00:00:00Z':null};
  if(path==='/api/subject-spaces')return {spaces:[]};
  if(path==='/api/revision/8'){assert.equal(JSON.parse(options.body).version,1);if(fail)throw Error('Connection interrupted');reviewed=true;return {ok:true}}
  if(path==='/api/care/plan-preview')return {timezone:'Asia/Kolkata',tasks:[{id:1,title:'Read a page',due_at:'2026-09-15T06:30:00Z',proposed_at:'2026-09-16T06:30:00Z'}]};
  if(path==='/api/care/lighten-plan'){careCalls++;assert.equal(JSON.parse(options.body).items[0].proposed_at,'2026-09-16T06:30:00Z');return {moved:1}}
  throw Error('Unexpected '+path);
 };
 const e=setup(api);assert.equal(e.controller.allowImmediateAlerts(),false,'No browser alerts before preferences load');
 await e.controller.connect(e.options);assert.equal(e.controller.celebrationsEnabled(),false);assert.equal(e.controller.allowImmediateAlerts(),true);
 await e.ids.refreshRevision.onclick();const answer=e.ids.revisionQueue.querySelectorAll('div').find(x=>x.className==='dw-answer'),fieldset=e.ids.revisionQueue.querySelector('fieldset');
 assert.equal(answer.hidden,true);assert.equal(fieldset.hidden,true);
 const reveal=e.ids.revisionQueue.querySelectorAll('button').find(x=>x.textContent==='Reveal answer');
 await reveal.onclick();assert.equal(answer.hidden,false);assert.equal(fieldset.hidden,false);
 const good=fieldset.querySelectorAll('button').find(x=>x.textContent==='Got it');
 await good.onclick();assert.equal(fieldset.disabled,false);assert.equal(answer.hidden,false);assert.equal(reviewed,false,'A failed request must leave the current review intact');
 fail=false;await good.onclick();assert.equal(reviewed,true);assert.match(e.ids.revisionQueue.textContent,/up to date/);
 await e.ids.careLightenPlan.onclick();assert.equal(careCalls,0,'Opening a preview never changes tasks');
 const d=e.body.children.find(x=>x.tag==='dialog'&&x.open),form=d.querySelector('form'),input=form.querySelector('input'),save=form.querySelector('button');
 assert.equal(input.checked,false);assert.equal(save.disabled,true,'No tasks are preselected');
 input.checked=true;input.parentNode.parentNode.onchange();assert.equal(save.disabled,false);
 form.onsubmit({preventDefault(){}});await tick();assert.equal(careCalls,1);assert.equal(d.open,false);
 const quiet={...pref,quiet_enabled:true};
 assert.equal(e.controller.quietAt(quiet,new Date('2026-09-15T16:30:00Z')),true);
 assert.equal(e.controller.quietAt(quiet,new Date('2026-09-16T02:30:00Z')),false);
 const digest=setup(async()=>({preferences:{...pref,notification_mode:'digest'}}));await digest.controller.connect(digest.options);assert.equal(digest.controller.allowImmediateAlerts(),false,'Daily summary mode suppresses individual in-tab notifications');
 let saved=[];
 const o=setup(async(path,options={})=>{if(options.method==='PATCH'){saved.push(JSON.parse(options.body));return {preferences:{...pref,onboarding_done:true}}}return {preferences:{...pref,onboarding_done:false}}});
 await o.controller.connect(o.options);const welcome=o.body.children.find(x=>x.tag==='dialog'),skip=welcome.querySelectorAll('button').find(x=>x.textContent==='Skip for now');await skip.onclick();
 assert.equal(saved.length,1);assert.equal(saved[0].onboarding_done,true);assert.equal(welcome.open,false);
 console.log('PASS: revision reveal/retry, explicit care preview confirmation, timezone boundaries, digest suppression and skippable onboarding');
})().catch(error=>{console.error(error);process.exitCode=1});
