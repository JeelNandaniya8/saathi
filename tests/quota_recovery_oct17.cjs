const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const source=fs.readFileSync('study-jobs.js','utf8');
(async()=>{for(const lang of ['en','gu','hi']){
 const events={},pending=[],changes=[],box={isConnected:true,textContent:'',setAttribute(){},append(){}};
 const window={addEventListener:(key,fn)=>events[key]=fn,removeEventListener(){}};
 const ctx={window,document:{documentElement:{lang},createElement:()=>({})},Event,crypto:require('node:crypto').webcrypto,setTimeout,clearTimeout};vm.createContext(ctx);vm.runInContext(source,ctx);
 const api=()=>new Promise((resolve,reject)=>pending.push({resolve,reject}));window.SaathiJobs.showAllowance(box,'map',api,a=>changes.push(a));
 assert.equal(changes[0],null,'Generation must disable while allowance is unresolved');
 pending[0].resolve({allowance:{remaining:0,reset_local:'2030-01-02 05:30 IST'}});await new Promise(setImmediate);assert.equal(changes.at(-1).remaining,0);
 events['saathi-study-job']();events['saathi-study-job']();assert.equal(changes.at(-1),null);
 pending[2].resolve({allowance:{remaining:0,reset_local:'new reset'}});await new Promise(setImmediate);
 pending[1].resolve({allowance:{remaining:2,reset_local:'stale reset'}});await new Promise(setImmediate);
 assert.equal(changes.at(-1).remaining,0,'A stale allowance cannot enable generation');assert.match(box.textContent,/new reset/);
 events['saathi-study-job']();pending[3].reject(Error('offline'));await new Promise(setImmediate);assert.equal(changes.at(-1),null,'An allowance failure must stay disabled');
 if(lang!=='en')assert.ok(!box.textContent.includes('Checking allowance'),'Critical quota labels use the selected language');
}console.log('PASS pending/exhausted/stale/failed allowance in EN/GU/HI')})().catch(e=>{console.error(e);process.exitCode=1});

// A response can be lost after the atomic resource/job commit. Recover the
// exact owned job before checking exhausted quota or submitting another POST.
(async()=>{
 const drafts=new Map(),events=[],window={dispatchEvent:e=>events.push(e.type),SaathiRecovery:{getDraft:()=>drafts.get('job'),saveDraft:(_kind,_id,value)=>drafts.set('job',value),removeDraft:()=>drafts.delete('job')}};
 const ctx={window,document:{documentElement:{lang:'en'}},crypto:require('node:crypto').webcrypto,Event,setTimeout:()=>0,clearTimeout:()=>{}};vm.createContext(ctx);vm.runInContext(source,ctx);
 let posts=0,allowances=0,savedJob;
 async function api(url,options){
  if(url.startsWith('/api/study-jobs'))return {jobs:savedJob?[savedJob]:[]};
  if(url.startsWith('/api/study-allowance')){allowances++;return {allowance:{remaining:1,reset_local:'fixture reset'}}}
  if(options?.method==='POST'){posts++;const request=JSON.parse(options.body);savedJob={id:request.job_id,status:'ready',result_id:42};throw Error('Fixture response lost after commit')}
  if(url==='/api/mock-tests/42')return {test:{id:42}};
  throw Error('Unexpected fixture URL '+url);
 }
 const first=await window.SaathiJobs.create('mock',{topic:'Same exact topic'},api);assert.equal(first.test.id,42);assert.equal(posts,1);assert.equal(drafts.size,0);
 drafts.set('job',{request:{topic:'Same exact topic',job_id:savedJob.id}});
 const again=await window.SaathiJobs.create('mock',{topic:'Same exact topic'},api);assert.equal(again.test.id,42);assert.equal(posts,1);assert.equal(allowances,1,'Saved retries must remain accessible at zero quota');
 console.log('PASS lost-response recovery preserves one job and one result');
})().catch(e=>{console.error(e);process.exitCode=1});

// Finishing a fast job must not leave a delayed refresh that disables the next
// tool during its click. This reproduced intermittently on 360px Chromium.
(async()=>{
 const listeners=new Set(),changes=[],window={addEventListener:(_type,fn)=>listeners.add(fn),removeEventListener:(_type,fn)=>listeners.delete(fn),dispatchEvent:()=>{for(const fn of listeners)fn()}};
 const box={isConnected:true,textContent:'',setAttribute(){},append(){}};
 const ctx={window,document:{documentElement:{lang:'en'},createElement:()=>({})},crypto:require('node:crypto').webcrypto,Event,setTimeout,clearTimeout};vm.createContext(ctx);vm.runInContext(source,ctx);
 const api=async url=>url.startsWith('/api/study-allowance')?{allowance:{remaining:2,reset_local:'fixture reset'}}:{test:{id:42}};
 window.SaathiJobs.showAllowance(box,'map',api,a=>changes.push(a));await new Promise(setImmediate);
 await window.SaathiJobs.create('mock',{topic:'Fast completion'},api);await new Promise(setImmediate);changes.length=0;
 await new Promise(resolve=>setTimeout(resolve,550));
 assert.equal(changes.length,0,'A completed job cannot later disable another tool');
 console.log('PASS completed job has no delayed quota flash in another tool');
})().catch(e=>{console.error(e);process.exitCode=1});
