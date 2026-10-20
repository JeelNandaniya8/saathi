// Synthetic provider/allowance responses only; never calls the production app.
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
function fixture(){
 const drafts=new Map(),window={dispatchEvent(){},SaathiRecovery:{getDraft:(_kind,id)=>drafts.get(id),saveDraft:(_kind,id,data)=>drafts.set(id,data),removeDraft:(_kind,id)=>drafts.delete(id)}};
 const ctx={window,document:{documentElement:{lang:'en'}},crypto:require('node:crypto').webcrypto,Event,setTimeout,clearTimeout};
 vm.createContext(ctx);vm.runInContext(fs.readFileSync('study-jobs.js','utf8'),ctx);
 return window.SaathiJobs;
}
(async()=>{
 for(const kind of ['map','mock']){
  const jobs=fixture(),gates=[],posted=[],stages=[];
  async function api(url,options){
   if(url.startsWith('/api/study-allowance'))return new Promise(resolve=>gates.push(resolve));
   if(options?.method==='POST'){posted.push(JSON.parse(options.body));return {id:posted.length}}
   throw Error('Unexpected fixture URL '+url);
  }
  const payload={topic:'Recall ગુજરાતી',language:'gu'};
  const first=jobs.create(kind,payload,api,stage=>stages.push(stage));
  const second=jobs.create(kind,{...payload},api);
  await new Promise(setImmediate);
  for(const release of gates)release({allowance:{remaining:2,reset_local:'fixture reset'}});
  const results=await Promise.all([first,second]);
  assert.equal(posted.length,1,'Concurrent identical generation must create one job, not two saved objects');
  assert.equal(results[0].id,results[1].id,'Both callers receive the same result');
  assert.equal(payload.job_id,undefined,'The original selection is not mutated');
  assert.deepEqual(stages,['generating']);
  const fresh=jobs.create(kind,payload,api);await new Promise(setImmediate);
  gates.at(-1)({allowance:{remaining:1,reset_local:'fixture reset'}});await fresh;
  assert.equal(posted.length,2,'A later deliberate generation is not cached as the earlier result');
  assert.notEqual(posted[0].job_id,posted[1].job_id);
 }
 const jobs=fixture(),posted=[];let fail=true;
 async function api(url,options){
  if(url.startsWith('/api/study-allowance'))return {allowance:{remaining:2,reset_local:'fixture reset'}};
  if(url.startsWith('/api/study-jobs'))return {jobs:[]};
  if(options?.method==='POST'){posted.push(JSON.parse(options.body));if(fail)throw Error('Fixture connection lost');return {id:42}}
  throw Error('Unexpected fixture URL '+url);
 }
 await assert.rejects(jobs.create('map',{topic:'Retained request'},api),/Fixture connection lost/);
 fail=false;
 const retried=await Promise.all([jobs.create('map',{topic:'Retained request'},api),jobs.create('map',{topic:'Retained request'},api)]);
 assert.equal(posted.length,2,'An uncertain failure permits one shared retry');
 assert.equal(posted[0].job_id,posted[1].job_id,'The retry preserves the exact original request ID');
 assert.equal(retried[0].id,retried[1].id);
 const changed=await Promise.all([jobs.create('map',{topic:'First topic'},api),jobs.create('map',{topic:'Second topic'},api)]);
 assert.equal(posted.length,4,'Different topics remain separate requests');
 assert.notEqual(posted[2].job_id,posted[3].job_id);
 assert.equal(changed.length,2);
 console.log('PASS identical concurrent mock/map requests create one job and return one result');
})().catch(error=>{console.error(error);process.exitCode=1});
