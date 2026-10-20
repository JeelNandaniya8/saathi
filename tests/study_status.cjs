const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
(async()=>{
 for(const lang of ['en','gu','hi']){
  let catalog={};if(lang!=='en')vm.runInNewContext(fs.readFileSync('locale-'+lang+'.js','utf8'),{window:{SaathiI18n:{register:copy=>catalog=copy}}});
  for(const kind of ['map','mock'])for(const phase of ['waiting','generating']){
   const nodes=new Map(),get=id=>{if(!nodes.has(id))nodes.set(id,{value:'Fixture topic',textContent:'Generate',style:{}});return nodes.get(id)};
   let reject;
   const jobs={create(_kind,_payload,_api,onStart){onStart(phase);return new Promise((_resolve,fail)=>reject=fail)}};
   const ctx={window:{SaathiJobs:jobs,SaathiI18n:{t:text=>catalog[text]||text}},SaathiJobs:jobs,$:get,state:{user:{language:lang},mapRemaining:2,mockRemaining:1},api(){},toast(){},renderMindmapsHistory(){}};
   const text=fs.readFileSync(kind==='map'?'dashboard-mindmaps.js':'dashboard-study.js','utf8');
   const start=text.indexOf(kind==='map'?'async function handleMindmapSubmit':'async function generateMockTest');
   const end=text.indexOf(kind==='map'?'\nfunction displayMindmap':'\nfunction startTestTimer',start);
   vm.createContext(ctx);vm.runInContext(text.slice(start,end),ctx);
   const work=kind==='map'?ctx.handleMindmapSubmit({preventDefault(){}}):ctx.generateMockTest({preventDefault(){}});
   const key=phase==='waiting'?'Waiting for result…':kind==='map'?'Generating mindmap…':'Generating exam with AI…';
   if(lang!=='en')assert.ok(catalog[key]&&catalog[key]!==key,lang+' has native generation/waiting copy');
   assert.equal(get(kind==='map'?'mindmapSubmitBtn':'testSubmitBtn').textContent,catalog[key]||key,lang+' '+kind+' reflects the actual '+phase+' stage');
   reject(Error('Fixture stopped'));await work;
  }
 }
 console.log('PASS mock/map waiting and generating labels in EN/GU/HI');
})().catch(error=>{console.error(error);process.exitCode=1});
