const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
class Element{constructor(tag){this.tag=tag;this.children=[];this.dataset={};this.style={}}append(...nodes){this.children.push(...nodes)}prepend(...nodes){this.children.unshift(...nodes)}replaceChildren(...nodes){this.children=nodes}setAttribute(){}focus(){this.focused=true}scrollIntoView(){}all(){return [this,...this.children.flatMap(n=>n.all())]}}
const ui={window:{},document:{documentElement:{lang:'en'},createElement:tag=>new Element(tag)}};vm.createContext(ui);vm.runInContext(fs.readFileSync('chat-actions.js','utf8'),ui);
for(const lang of ['en','gu','hi'])for(const [kind,view] of Object.entries({note:'notes',task:'tasks',memory:'memory',reminder:'reminders',mindmap:'mindmaps',habit:'habits',journal:'journal',checkin:'checkins'})){
 ui.document.documentElement.lang=lang;const box=new Element('div');ui.window.SaathiChatActions.attach(box,{id:kind+lang,content:'',action_receipt:{kind,resource_id:41},action_resource:{title:'Owned record',at:'2030-01-01T00:00:00Z'}});
 const links=box.all().filter(node=>node.tag==='a');assert.equal(links[0].href,kind==='note'?'/chat?note=41':'/dashboard?'+kind+'=41#'+view,'Saved receipt must link to its exact record');
}
(async()=>{
 const source=fs.readFileSync('dashboard.html','utf8');
 for(const [kind,collection] of [['habit','habits'],['journal','entries'],['checkin','check_ins']]){
  const calls=[],opened=[],list=new Element('div'),record={id:42,title:'Exact owned record'};
  const ctx={URLSearchParams,location:{search:'?'+kind+'=42'},state:{},api:async url=>{calls.push(url);return {[collection]:[record]}},toast:()=>assert.fail('Owned ID should resolve'),editHabit:r=>opened.push(r.id),editJournal:r=>opened.push(r.id),checkinItem:r=>{opened.push(r.id);return new Element('article')},document:{querySelector:()=>null},$:()=>list,requestAnimationFrame:fn=>fn()};vm.createContext(ctx);vm.runInContext(source.slice(source.indexOf('async function openLinkedRecord('),source.indexOf('function openView(')),ctx);
  await ctx.openLinkedRecord(kind,[{id:7,title:'Another record'}]);assert.deepEqual(opened,[42]);assert.ok(calls[0].endsWith('?id=42'),'A truncated or filtered list cannot redirect the link to another record');
 }
 console.log('PASS exact receipt destinations in EN/GU/HI and owned ID recovery beyond loaded lists');
})().catch(e=>{console.error(e);process.exitCode=1});
