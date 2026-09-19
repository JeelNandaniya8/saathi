const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const source=fs.readFileSync('chat.html','utf8'),drafts=new Map();
const recovery={getDraft:(_,id)=>drafts.get(id),saveDraft:(_,id,data)=>drafts.set(id,data),removeDraft:(_,id)=>drafts.delete(id)};
let sent;
const ctx={window:{SaathiRecovery:recovery},Date,FormData,requestId:()=> 'new-request',
  state:{activeId:1,sending:false,messages:[],selectedFiles:[],chatModes:[{id:'normal'}],conversations:[{id:1,title:'Existing'}]},
  el:{input:{value:'',focus(){}},mode:{value:'normal'},fileOnly:{checked:false},chatTitle:{},uploadStatus:{}},
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
  console.log('PASS: chat draft restore, unchanged retry IDs, edited request IDs, no duplicate saved exchange and failed-send recovery');
})().catch(error=>{console.error(error);process.exitCode=1});
