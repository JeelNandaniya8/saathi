const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const source=fs.readFileSync('dashboard-study.js','utf8'),drafts=new Map(),pending=[];
const state={activeTest:{id:3,expires_at:new Date(Date.now()+60000).toISOString(),questions:[{id:1},{id:2}]},activeTestAnswers:{1:'A'},activeTestFlags:new Set([2]),activeTestIndex:1,testTotalSeconds:60,testSecondsLeft:50};
const button={disabled:false};let restarted=0;
const c={state,window:{SaathiRecovery:{saveDraft:(kind,id,v)=>drafts.set(id,structuredClone(v)),getDraft:(kind,id)=>drafts.get(id),removeDraft:(kind,id)=>drafts.delete(id)}},Date,clearInterval(){},$:()=>button,api:path=>path.includes('/history')?Promise.resolve({tests:[]}):new Promise((resolve,reject)=>pending.push({resolve,reject})),renderTestResults(){},playChime(){},blastConfetti(){},toast(){},startTestTimer:()=>restarted++,renderMockTestHistory(){}};
vm.createContext(c);vm.runInContext(source.slice(0,source.indexOf('function renderMockTestHistory'))+source.slice(source.indexOf('async function submitMockTest('),source.indexOf('function renderTestResults(')),c);
(async()=>{
 c.saveMockDraft();state.activeTestAnswers={};state.activeTestFlags=new Set();state.activeTestIndex=0;c.restoreMockDraft();assert.equal(state.activeTestAnswers[1],'A');assert.ok(state.activeTestFlags.has(2));assert.equal(state.activeTestIndex,1);
 let p=c.submitMockTest();await c.submitMockTest();assert.equal(pending.length,1);assert.equal(button.disabled,true);pending[0].reject(Error('Offline'));await p;assert.equal(restarted,1);assert.equal(drafts.has(3),true);assert.equal(button.disabled,false);
 p=c.submitMockTest();pending[1].resolve({attempt:{id:1}});await p;assert.equal(drafts.has(3),false);assert.equal(state.testSubmitting,false);
 drafts.set(3,{answers:{1:'Z',999:'A'},flags:[999],index:999});c.restoreMockDraft();assert.equal(Object.keys(state.activeTestAnswers).length,0);assert.equal(state.activeTestFlags.size,0);assert.equal(state.activeTestIndex,1);
 console.log('PASS: mock refresh recovery, submit-once, failed-submit retry and input validation');
})().catch(e=>{console.error(e);process.exitCode=1});
