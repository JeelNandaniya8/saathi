const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const {webcrypto}=require('node:crypto');
class Storage{getItem(k){return this[k]??null}setItem(k,v){this[k]=String(v)}removeItem(k){delete this[k]}}
const storage=new Storage(),events={},records=[];let now=Date.now(),clock=0;
class TestDate extends Date{static now(){return now}}
const window={crypto:webcrypto,performance:{now:()=>clock},addEventListener:(name,fn)=>events[name]=fn,speechSynthesis:{getVoices:()=>[{lang:'en-US'},{lang:'gu-IN'}]}};
const ctx={window,document:{querySelectorAll:()=>[]},localStorage:storage,Date:TestDate,Uint8Array};
vm.createContext(ctx);vm.runInContext(fs.readFileSync('recovery.js','utf8'),ctx);
const r=window.SaathiRecovery,api=async(path,options)=>records.push(JSON.parse(options.body));
(async()=>{
  r.connect({user:{id:1},api});r.saveDraft('chat',4,{content:'ગુજરાતી draft'});
  assert.equal(r.getDraft('chat',4).content,'ગુજરાતી draft');
  r.connect({user:{id:2},api});assert.equal(r.getDraft('chat',4),null);
  r.saveDraft('chat',4,{content:'Other account'});r.clearDrafts();
  r.connect({user:{id:1},api});assert.equal(r.getDraft('chat',4).content,'ગુજરાતી draft');
  now+=86400001;assert.equal(r.getDraft('chat',4),null);
  for(let i=0;i<15;i++){now++;r.saveDraft('note',i,{content:'note'})}
  assert.equal(Object.keys(storage).length,12);assert.equal(r.getDraft('note',0),null);
  const sample=r.measureStart('/api/conversations/4/messages/stream');clock=125;r.measureDelta(sample);clock=700;r.measureDelta(sample);r.measureEnd(sample,'error',{code:'AI_QUOTA',message:'private text'});
  await Promise.resolve();assert.equal(records.length,1);assert.equal(records[0].first_text_ms,125);assert.equal(records[0].total_ms,700);assert.equal(records[0].error_code,'AI_QUOTA');assert.ok(!JSON.stringify(records).includes('private text'));
  const next=r.measureStart('/api/conversations/4/regenerate');r.forgetAccount();r.measureEnd(next,'cancelled');await Promise.resolve();
  assert.equal(records.length,1);assert.equal(r.saveDraft('chat',4,{content:'after logout'}),false);
  assert.equal(Object.keys(storage).filter(k=>k.startsWith('saathi-draft-v1:1:')).length,0);
  r.connect({user:{id:1},api});events.storage({key:'saathi-draft-logout',newValue:JSON.stringify({user:1})});assert.equal(r.saveDraft('chat',4,{content:'other tab'}),false);
  assert.equal(r.voiceFor('gu').lang,'gu-IN');assert.equal(r.voiceFor('fr'),null);
  console.log('PASS: account-scoped drafts, expiry, bounded copies, logout across tabs, timing privacy and language voice selection');
})().catch(error=>{console.error(error);process.exitCode=1});
