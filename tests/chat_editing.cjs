const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const source=fs.readFileSync('chat.html','utf8'),els=new Map();
class Element{
 constructor(){this.value='';this.textContent='';this.disabled=false;this.open=false;this.handlers={};this.children=[]}
 addEventListener(name,fn){this.handlers[name]=fn}focus(){}showModal(){this.open=true}close(){this.open=false;this.handlers.close?.()}append(...nodes){this.children.push(...nodes)}
}
const $=id=>{if(!els.has(id))els.set(id,new Element());return els.get(id)};
let sends=[],notices=[],fetcher;
const ctx={document:{getElementById:$,createElement:()=>new Element(),createTextNode:text=>({textContent:text})},
 state:{activeId:7,sending:false,selectedFiles:[],messages:[]},el:{input:{value:''}},AbortController,File,Error,Promise,
 showToast:message=>notices.push(message),sendContent:async(...args)=>sends.push(args),fetch:(...args)=>fetcher(...args)};
vm.createContext(ctx);vm.runInContext(source.slice(source.indexOf('let editingMessage='),source.indexOf('\nasync function retryFailed')),ctx);
(async()=>{
 const message={id:1,role:'user',content:'Original',attachments:[{id:5,name:'lesson.pdf',mime_type:'application/pdf'}],ai_mode:'explain',file_only:true};
 ctx.state.messages=[message,{id:2,role:'assistant',content:'Saved answer'}];
 ctx.el.input.value='Private draft';ctx.editMessage(message);assert.equal($('editMessageDialog').open,false);assert.equal(ctx.el.input.value,'Private draft');assert.ok(notices.length);
 ctx.el.input.value='';ctx.editMessage(message);$('editMessageText').value='Edited';let release;
 fetcher=async()=>{await new Promise(resolve=>release=resolve);return {ok:true,blob:async()=>new Blob(['PDF'])}};
 const cancelled=$('sendMessageEdit').onclick();$('cancelMessageEdit').onclick();release();await cancelled;assert.equal(sends.length,0,'Closing the editor while files load must cancel sending');
 ctx.editMessage(message);$('editMessageText').value='Keep edited text';fetcher=async()=>({ok:false});await $('sendMessageEdit').onclick();assert.equal($('editMessageDialog').open,true);assert.equal($('editMessageText').value,'Keep edited text');assert.ok($('editMessageNotice').textContent.includes('kept here'));
 fetcher=async()=>({ok:true,blob:async()=>new Blob(['PDF'])});await $('sendMessageEdit').onclick();assert.equal(sends.length,1);assert.equal(sends[0][0],'Keep edited text');assert.equal(sends[0][1][0].name,'lesson.pdf');assert.equal(sends[0][3],'explain');assert.equal(sends[0][4],true);assert.equal(ctx.state.messages.length,2,'Earlier messages must remain saved');
 ctx.messageSource=()=>({hasPdf:true,names:['lesson.pdf']});ctx.state.messages=[{attachments:[{id:5,name:'lesson.pdf',mime_type:'application/pdf',page_count:3}]}];
 vm.runInContext(source.slice(source.indexOf('function addDisclosures('),source.indexOf('async function setMessageFeedback')),ctx);
 const body=new Element();ctx.addDisclosures(body,{source_pages:[{name:'lesson.pdf',page:2},{name:'lesson.pdf',page:99},{name:'missing.pdf',page:1}]},1);
 const links=body.children[0].children[0].children.filter(child=>child.href);assert.equal(links.length,1);assert.equal(links[0].href,'/api/attachments/5/view#page=2');assert.equal(links[0].rel,'noopener noreferrer');
 ctx.state.messages[0].attachments.push({...ctx.state.messages[0].attachments[0],id:6});const ambiguous=new Element();ctx.addDisclosures(ambiguous,{source_pages:[{name:'lesson.pdf',page:2}]},1);assert.ok(!ambiguous.children[0].children[0].children.some(child=>child.href),'Duplicate file names must not point at a guessed PDF');
 console.log('PASS: edit draft protection, attachment failure recovery, cancellation, retained history and verified PDF page links');
})().catch(error=>{console.error(error);process.exitCode=1});
