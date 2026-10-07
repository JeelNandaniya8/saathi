const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict'),path=require('node:path');
const html=fs.readFileSync(path.join(__dirname,'../dashboard.html'),'utf8');
function setup(kind){
 const cap=kind[0].toUpperCase()+kind.slice(1),plural=kind==='task'?'tasks':'reminders';
 const source=html.slice(html.indexOf('function read'+cap+'Draft()'),html.indexOf("$('"+kind+"Cancel').onclick="));
 const elements={},pending=[],state={[kind+'EditingId']:1,[plural]:[{id:1,title:'Original'},{id:2,title:'Other'}],overview:{}};
 const $=id=>elements[id]??=( {value:'draft',disabled:false,setAttribute(){},removeAttribute(){},addEventListener(_,fn){this.submit=fn}} );
 const ctx={state,$,api:(url,options)=>new Promise((resolve,reject)=>pending.push({url,options,resolve,reject})),localInputToIso:x=>x,toast(){},['render'+cap+'s'](){},['cancel'+cap+'Edit'](){state[kind+'EditingId']=null;$(kind+'Title').value=''}};
 vm.createContext(ctx);vm.runInContext(source,ctx);
 return {state,$,pending,submit:()=>$(kind+'Form').submit({preventDefault(){}}),plural};
}
(async()=>{
 for(const kind of ['task','reminder']){
  let t=setup(kind),p=t.submit();await t.submit();assert.equal(t.pending.length,1);
  // A slow save for entry 1 must not replace entry 2 or clear its draft.
  t.state[kind+'EditingId']=2;t.$(kind+'Title').value='Editing other';
  t.pending[0].resolve({[kind]:{id:1,title:'Saved',active:true}});await p;
  assert.equal(t.state[t.plural].find(x=>x.id===2).title,'Other');assert.equal(t.$(kind+'Title').value,'Editing other');
  assert.equal(t.$(kind+'Submit').disabled,false);
  // New text typed in the same entry survives an earlier save.
  t=setup(kind);p=t.submit();t.$(kind+'Title').value='New unsaved edit';t.pending[0].resolve({[kind]:{id:1,title:'Saved'}});await p;assert.equal(t.$(kind+'Title').value,'New unsaved edit');
  // Continue editing a newly created entry instead of creating a duplicate on the next save.
  t=setup(kind);t.state[kind+'EditingId']=null;p=t.submit();t.$(kind+'Title').value='Continued draft';t.pending[0].resolve({[kind]:{id:3,title:'Created'}});await p;
  assert.equal(t.state[kind+'EditingId'],3);p=t.submit();assert.equal(t.pending[1].options.method,'PATCH');assert.ok(t.pending[1].url.endsWith('/3'));t.pending[1].resolve({[kind]:{id:3,title:'Updated'}});await p;
  // Normal success clears only the submitted draft.
  t=setup(kind);p=t.submit();t.pending[0].resolve({[kind]:{id:1,title:'Saved'}});await p;assert.equal(t.state[kind+'EditingId'],null);
  // Failure retains text and allows an explicit retry.
  t=setup(kind);p=t.submit();t.pending[0].reject(Error('offline'));await p;assert.equal(t.$(kind+'Title').value,'draft');assert.equal(t.$(kind+'Submit').disabled,false);
  p=t.submit();assert.equal(t.pending.length,2);t.pending[1].resolve({[kind]:{id:1}});await p;
 }
 console.log('Planner and reminder save race tests passed');
})().catch(e=>{console.error(e);process.exitCode=1});
