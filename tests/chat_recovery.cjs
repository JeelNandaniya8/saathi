const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const source=fs.readFileSync('chat.html','utf8'),drafts=new Map();
const recovery={getDraft:(_,id)=>drafts.get(id),saveDraft:(_,id,data)=>drafts.set(id,data),removeDraft:(_,id)=>drafts.delete(id)};
let sent;
const ctx={window:{SaathiRecovery:recovery},Date,FormData,URL:{createObjectURL:()=> 'blob:recovered-image'},requestId:()=> 'new-request',
  state:{activeId:1,sending:false,messages:[],selectedFiles:[],chatModes:[{id:'normal'}],conversations:[{id:1,title:'Existing'}]},
  el:{input:{value:'',focus(){}},mode:{value:'normal'},fileOnly:{checked:false},chatTitle:{},uploadStatus:{}},
  createStreamPainter:()=>({update(){},cancel(){}}),
  updateComposer(){},updateModeDescription(){},showToast(){},renderMessages(){},renderSelectedFiles(){},renderConversations(){},sortConversations(){},showRequestProgress(){},scrollToLatest(){},releaseLocalPreviews(){},
  normaliseMessageDisplay:v=>v,normaliseConversationDisplay:v=>v,decodeLegacyText:v=>v,
  currentConversation:()=>ctx.state.conversations[0],setBusy:busy=>ctx.state.sending=busy,
  streamChatRequest:async(path,body)=>{sent=JSON.parse(body);return {user_message:{id:10,role:'user',content:'Draft'},assistant_message:{id:11,role:'assistant',content:'Saved answer'},conversation:{id:1,title:'Existing'}}}};
vm.createContext(ctx);
vm.runInContext(source.slice(source.indexOf('function saveChatDraft('),source.indexOf('\nfunction renderChatModes')),ctx);
vm.runInContext(source.slice(source.indexOf('async function sendContent('),source.indexOf('\nlet editingMessage=')),ctx);
(async()=>{
  ctx.el.input.value='Draft';ctx.saveChatDraft();ctx.el.input.value='';ctx.restoreChatDraft();assert.equal(ctx.el.input.value,'Draft');
  drafts.set(1,{content:'Draft',mode:'normal',request_id:'same-request'});ctx.restoreChatDraft();
  ctx.state.messages=[{id:10,role:'user',content:'Draft'},{id:11,role:'assistant',content:'Saved answer'}];
  await ctx.sendContent('Draft');assert.equal(sent.request_id,'same-request');assert.equal(ctx.state.messages.length,2,'A recovered completed retry must not duplicate the visible exchange');assert.equal(drafts.has(1),false);
  drafts.set(1,{content:'Draft',mode:'normal',request_id:'old-request'});ctx.restoreChatDraft();await ctx.sendContent('Changed draft');assert.equal(sent.request_id,'new-request');
  ctx.streamChatRequest=async()=>{throw Error('Offline')};await ctx.sendContent('Keep this');ctx.saveChatDraft();assert.equal(drafts.get(1).content,'Keep this');assert.equal(ctx.state.sending,false);
  // Composer resend must reconcile the failed local exchange just like Retry.
  ctx.state.messages=[];ctx.el.input.value='';
  ctx.streamChatRequest=async()=>{throw Object.assign(Error('Busy'),{code:'AI_BUSY'})};
  await ctx.sendContent('Original question');
  const failedKey=ctx.state.messages[0].request_id;
  ctx.streamChatRequest=async(path,body)=>{sent=JSON.parse(body);return {user_message:{id:20,role:'user',content:'Original question'},assistant_message:{id:21,role:'assistant',content:'Verified answer'},conversation:{id:1,title:'Existing'}}};
  await ctx.sendContent(ctx.el.input.value);
  assert.equal(sent.request_id,failedKey);
  assert.equal(ctx.state.messages.length,2,'Resending the recovered composer must replace its failed exchange');
  assert.ok(ctx.state.messages.every(m=>Number.isInteger(m.id)),'No stale failed or temporary records after receipt');
  for(const mime of ['image/png','application/pdf'])for(const code of ['AI_BUSY','AI_TIMEOUT']){
    const {File}=require('node:buffer');
    const file=new File(['INDIGO-471'],mime==='image/png'?'Search.png':'Search.pdf',{type:mime});
    const text='  મૂળ વિનંતી 😊 · मूल अनुरोध  ';
    ctx.state.messages=[];ctx.state.selectedFiles=[{file,previewUrl:mime==='image/png'?'blob:selection':null}];ctx.el.fileOnly.checked=true;ctx.el.input.value=text;ctx.state.draftRequestId=null;
    const attempts=[];
    ctx.streamChatRequest=async(path,body)=>{attempts.push(body);throw Object.assign(Error(code),{code})};
    await ctx.sendContent(text);await ctx.sendContent(ctx.el.input.value);
    assert.equal(ctx.state.messages.length,2,'Repeated failures keep one visible attempt');
    assert.equal(ctx.el.fileOnly.checked,true);assert.equal(ctx.state.selectedFiles[0].file,file);
    ctx.streamChatRequest=async(path,body)=>{attempts.push(body);return {user_message:{id:30,role:'user',content:text.trim()},assistant_message:{id:31,role:'assistant',content:'Verified file reply'},conversation:{id:1,title:'Existing'}}};
    await ctx.sendContent(ctx.el.input.value);
    const keys=attempts.map(body=>body.get('request_id'));assert.equal(new Set(keys).size,1);
    for(const body of attempts){assert.equal(body.get('content'),text.trim());assert.equal(body.get('mode'),'normal');assert.equal(body.get('file_only'),'true');assert.equal(await body.get('attachments').text(),'INDIGO-471');assert.equal(body.get('attachments').name,file.name)}
    assert.equal(ctx.state.messages.length,2);assert.equal(drafts.has(1),false);
  }
  const {File}=require('node:buffer'),png=new File(['INDIGO-471'],'same.png',{type:'image/png'});
  ctx.el.input.value='';ctx.state.selectedFiles=[];ctx.state.messages=[];
  ctx.streamChatRequest=async()=>{throw Object.assign(Error('Timeout'),{code:'AI_TIMEOUT'})};
  await ctx.sendContent('Keep the image preview',[png],'original-request','normal',true);
  assert.equal(ctx.state.selectedFiles[0].file,png);
  assert.equal(ctx.state.selectedFiles[0].previewUrl,'blob:recovered-image','A recovered PNG must keep its image preview instead of a PDF badge');
  assert.equal(ctx.el.fileOnly.checked,true);
  console.log('PASS: chat draft restore, unchanged retry IDs, edited request IDs, no duplicate saved exchange and failed-send recovery');
})().catch(error=>{console.error(error);process.exitCode=1});
