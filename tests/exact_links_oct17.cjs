const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
class Element{constructor(tag){this.tag=tag;this.children=[];this.dataset={};this.style={}}append(...nodes){this.children.push(...nodes)}prepend(...nodes){this.children.unshift(...nodes)}replaceChildren(...nodes){this.children=nodes}setAttribute(key,value){this.attrs??={};this.attrs[key]=value}focus(){this.focused=true}scrollIntoView(){}all(){return [this,...this.children.flatMap(n=>n.all())]}}
const ui={window:{},document:{documentElement:{lang:'en'},createElement:tag=>new Element(tag)}};vm.createContext(ui);vm.runInContext(fs.readFileSync('chat-actions.js','utf8'),ui);
// Actual live history returned its own "Failed:" prefix. Reopening must
// render one localized label, keep the exact error detail and never imply a save.
for(const [lang,label,detail,retry] of [
 ['en','Failed','Nothing was saved: no valid action was returned.','Retry'],
 ['gu','નિષ્ફળ','કંઈ સાચવાયું નથી: માન્ય કાર્યવાહી મળી નથી.','ફરી પ્રયત્ન કરો'],
 ['hi','असफल','कुछ सेव नहीं हुआ: मान्य कार्रवाई नहीं मिली।','फिर कोशिश करें']
])for(const prefix of ['','Failed: ','Failed: Failed: ']){
 ui.document.documentElement.lang=lang;const box=new Element('div');
 ui.window.SaathiChatActions.attach(box,{id:lang+prefix,content:'Failed: Nothing was saved: no valid action was returned.\nRetry when ready.',action_error:prefix+'Nothing was saved: no valid action was returned.'});
 const all=box.all(),status=all.find(n=>n.tag==='p');
 assert.equal(status.textContent,label+': '+detail,'Historical failures must use one native label');
 assert.deepEqual(all.filter(n=>n.tag==='button').map(n=>n.textContent),[retry]);
 assert.equal(all.filter(n=>n.tag==='a').length,0,'A failed action cannot offer a saved receipt link');
}
console.log('PASS reloaded failure copy and retry without false save in EN/GU/HI');
for(const lang of ['en','gu','hi'])for(const [kind,view] of Object.entries({note:'notes',task:'tasks',memory:'memory',reminder:'reminders',mindmap:'mindmaps',habit:'habits',journal:'journal',checkin:'checkins'})){
 ui.document.documentElement.lang=lang;const box=new Element('div');ui.window.SaathiChatActions.attach(box,{id:kind+lang,content:'',action_receipt:{kind,resource_id:41},action_resource:{title:'Owned record',at:'2030-01-01T00:00:00Z'}});
 const links=box.all().filter(node=>node.tag==='a');assert.equal(links[0].href,kind==='note'?'/chat?note=41':'/dashboard?'+kind+'=41#'+view,'Saved receipt must link to its exact record');
}
(async()=>{
 const source=fs.readFileSync('dashboard.html','utf8');
 const mapReads=[];
 const linkedMap={URLSearchParams,location:{search:'?mindmap=62'},state:{},loadSavedMindmap:async id=>mapReads.push(id)};
 vm.createContext(linkedMap);vm.runInContext(source.slice(source.indexOf('async function openLinkedRecord('),source.indexOf('function openView(')),linkedMap);
 await linkedMap.openLinkedRecord('mindmap');await linkedMap.openLinkedRecord('mindmap');
 assert.deepEqual(mapReads,[62],'A receipt must reopen its exact persisted map once, without generation');
 const sectionContext={api:()=>{},SaathiHub:{},state:{},renderMindmapsHistory:()=>{},openLinkedRecord:linkedMap.openLinkedRecord,$:()=>({addEventListener(){}})};
 vm.createContext(sectionContext);vm.runInContext(source.slice(source.indexOf('const workspaceSections=['),source.indexOf("$('mockTestForm').addEventListener('submit',generateMockTest);"))+';this.mapSection=workspaceSections.find(section=>section.key===\'mindmaps\');',sectionContext);
 linkedMap.state.linkedResourceHandled.clear();await sectionContext.mapSection.apply({mindmaps:[]});
 assert.deepEqual(mapReads,[62,62],'Cold startup must resolve the ID even when the history list omits it');
 for(const [kind,collection] of [['habit','habits'],['journal','entries'],['checkin','check_ins']]){
  const calls=[],opened=[],list=new Element('div'),record={id:42,title:'Exact owned record'};
  const ctx={URLSearchParams,location:{search:'?'+kind+'=42'},state:{},api:async url=>{calls.push(url);return {[collection]:[record]}},toast:()=>assert.fail('Owned ID should resolve'),editHabit:r=>opened.push(r.id),editJournal:r=>opened.push(r.id),checkinItem:r=>{opened.push(r.id);return new Element('article')},document:{querySelector:()=>null},$:()=>list,requestAnimationFrame:fn=>fn()};vm.createContext(ctx);vm.runInContext(source.slice(source.indexOf('async function openLinkedRecord('),source.indexOf('function openView(')),ctx);
  await ctx.openLinkedRecord(kind,[{id:7,title:'Another record'}]);assert.deepEqual(opened,[42]);assert.ok(calls[0].endsWith('?id=42'),'A truncated or filtered list cannot redirect the link to another record');
 }
 console.log('PASS exact receipt destinations in EN/GU/HI and owned ID recovery beyond loaded lists');
})().catch(e=>{console.error(e);process.exitCode=1});

// Error codes and persisted provider errors use native critical UI copy.
(async()=>{const ctx={window:{},NodeFilter:{SHOW_TEXT:4},document:{body:{querySelectorAll:()=>[]},documentElement:{},createTreeWalker:()=>({nextNode:()=>false})}};vm.createContext(ctx);vm.runInContext(fs.readFileSync('i18n.js','utf8'),ctx);for(const lang of ['gu','hi']){vm.runInContext(fs.readFileSync('locale-'+lang+'.js','utf8'),ctx);await ctx.window.SaathiI18n.setLanguage(lang);for(const code of ['AI_BUSY','AI_TIMEOUT','AI_QUOTA','AI_ACCESS','AI_CONNECTION','AI_FORMAT','AI_LENGTH','AI_ACCURACY','AI_STOPPED'])assert.ok(new RegExp(lang==='gu'?'[\\u0a80-\\u0aff]':'[\\u0900-\\u097f]').test(ctx.window.SaathiI18n.error(code,'Raw provider detail')));assert.notEqual(ctx.window.SaathiI18n.t('The AI service is temporarily busy. Please retry in a moment; your message is kept here.'),'The AI service is temporarily busy. Please retry in a moment; your message is kept here.')}console.log('PASS critical AI codes and persisted provider errors in GU/HI')})().catch(e=>{console.error(e);process.exitCode=1});

// Language changes must update the actual accessible name, even when the
// toolbar's own observer runs after the generic catalog translator.
const toolbar=new Element('nav'),languageUpdates=[];const toolbarCtx={window:{},document:{documentElement:{lang:'gu'},createElement:tag=>new Element(tag),querySelector:selector=>selector==='.top-actions'?toolbar:null,getElementById:()=>null},MutationObserver:class{constructor(fn){languageUpdates.push(fn)}observe(){}}};vm.createContext(toolbarCtx);vm.runInContext(fs.readFileSync('chat-actions.js','utf8'),toolbarCtx);toolbarCtx.window.SaathiChatActions.connect({});assert.equal(toolbar.children[0].attrs['aria-label'],'અભ્યાસ સાધનો');toolbarCtx.document.documentElement.lang='hi';languageUpdates.forEach(fn=>fn());assert.equal(toolbar.children[0].attrs['aria-label'],'पढ़ाई के साधन');console.log('PASS native toolbar accessible name after language observer updates');
