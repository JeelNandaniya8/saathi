// Run the production browser voice controller without microphone or provider access.
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const source=fs.readFileSync('chat.html','utf8'),nodes=new Map(),events={},spoken=[],calls=[];
class Element{
 constructor(){this.children=[];this.attrs={};this.hidden=true;this.textContent='';this.classList={add(){},remove(){},toggle(){}};this.handlers={}}
 set innerHTML(value){throw Error('Voice transcript must never be parsed as HTML')}
 setAttribute(k,v){this.attrs[k]=v}append(...nodes){this.children.push(...nodes)}replaceChildren(){this.children=[]}focus(){}addEventListener(k,fn){this.handlers[k]=fn}
}
const get=id=>{if(!nodes.has(id))nodes.set(id,new Element());return nodes.get(id)};
const document={getElementById:get,createElement:()=>new Element(),createTextNode:text=>({textContent:text})};
let recognition,starts=0,aborts=0,cancelled=0;
class Recognition{constructor(){recognition=this}start(){starts++;this.onstart?.()}stop(){this.onend?.()}abort(){this.onend?.()}}
const window={SpeechRecognition:Recognition,speechSynthesis:{speak:u=>spoken.push(u),cancel:()=>cancelled++},addEventListener:(name,fn)=>events[name]=fn};
const state={user:{language:'gu'},activeId:42,sending:false,selectedFiles:[],activeRequest:{abort:()=>aborts++}},el={input:{value:''}};
const ctx={window,document,state,el,SpeechSynthesisUtterance:class{constructor(text){this.text=text}},showToast(){},sendContent:async(...args)=>{calls.push(args);return {assistant_message:{content:'<img src=x onerror=alert(1)> **ગુજરાતી**'}}}};
vm.createContext(ctx);vm.runInContext(source.slice(source.indexOf('// Browser voice uses'),source.lastIndexOf('</script>')),ctx);
const tick=()=>new Promise(resolve=>setImmediate(resolve));
(async()=>{
 events['saathi:ready']();assert.equal(get('voiceOpenBtn').hidden,false);
 el.input.value='Keep my draft';window.openVoiceCall();assert.equal(get('voiceCallOverlay').hidden,true);assert.equal(el.input.value,'Keep my draft');
 el.input.value='';window.openVoiceCall();assert.equal(get('voiceCallOverlay').hidden,false);assert.equal(recognition.lang,'gu-IN');assert.equal(starts,0,'Microphone requires a tap');
 window.vcToggleListen();assert.equal(starts,1);
 recognition.onresult({results:[[{transcript:'<b>hello</b>'}]]});await tick();
 assert.deepEqual(calls[0].map(arg=>Array.isArray(arg)?Array.from(arg):arg),['<b>hello</b>',[],null,'care',false]);
 assert.equal(get('voiceCallHistory').children[0].children[1].textContent,'<b>hello</b>');
 assert.equal(get('voiceCallHistory').children[1].children[1].textContent,'<img src=x onerror=alert(1)> **ગુજરાતી**');
 assert.equal(spoken.length,1);assert.equal(spoken[0].lang,'gu-IN');
 window.closeVoiceCall();spoken[0].onend();assert.equal(starts,1,'Closing must not restart the microphone');
 let release;ctx.sendContent=()=>new Promise(resolve=>{release=resolve});window.openVoiceCall();recognition.onresult({results:[[{transcript:'Another question'}]]});
 window.closeVoiceCall();assert.equal(aborts,1);release({assistant_message:{content:'Late reply'}});await tick();assert.equal(spoken.length,1,'Late replies after close must not speak');
 ctx.sendContent=async()=>undefined;window.openVoiceCall();recognition.onresult({results:[[{transcript:'Failed request'}]]});await tick();assert.equal(spoken.length,1,'Failures must not invent or speak an answer');
 const before=starts;recognition.onerror({error:'not-allowed'});assert.equal(starts,before,'Permission errors must not loop');window.closeVoiceCall();
 console.log('PASS: voice uses saved chat, language, draft retention, safe transcript, close cancellation and no fake fallback');
})().catch(error=>{console.error(error);process.exitCode=1});
