const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const source=fs.readFileSync('chat.html','utf8');
const tick=()=>new Promise(resolve=>setImmediate(resolve));
function fixture({delayedAbort=false,regenerating=false}={}){
  let resolveCancel,rejectCancel,rejectStream;
  const drafts=new Map(),toasts=[];
  const ctx={window:{SaathiRecovery:{getDraft:(_,id)=>drafts.get(id),saveDraft:(_,id,data)=>drafts.set(id,data),removeDraft:(_,id)=>drafts.delete(id)}},Date,FormData,AbortController,setTimeout,clearTimeout,
    state:{activeId:1,sending:false,messages:regenerating?[{id:10,role:'user',content:'Question'},{id:11,role:'assistant',content:'Original answer',cancelled:true,completed_on_stop:true}]:[],selectedFiles:[],conversations:[{id:1,title:'Existing'}]},
    el:{input:{value:'',focus(){}},mode:{value:'normal'},fileOnly:{checked:false},chatTitle:{},uploadStatus:{}},
    createStreamPainter:()=>({update(){},cancel(){}}),requestId:()=> 'stop-request',currentConversation:()=>ctx.state.conversations[0],
    updateComposer(){},setRequestStage(){},showToast:message=>toasts.push(message),renderMessages(){},renderSelectedFiles(){},renderConversations(){},sortConversations(){},showRequestProgress(){},scrollToLatest(){},releaseLocalPreviews(){},clearSelectedFiles(){},saveChatDraft(){},
    normaliseMessageDisplay:v=>v,normaliseConversationDisplay:v=>v,decodeLegacyText:v=>v,setBusy:busy=>ctx.state.sending=busy,
    api:()=>new Promise((resolve,reject)=>{resolveCancel=resolve;rejectCancel=reject}),
    streamChatRequest:async(_url,_body,onDelta)=>new Promise((_resolve,reject)=>{
      rejectStream=()=>reject(Object.assign(Error('Checking whether anything was already saved.'),{name:'AbortError',code:'AI_STOPPED',stop_unconfirmed:true}));
      ctx.state.activeRequest={abort(){if(!delayedAbort)rejectStream()}};
      if(!regenerating)onDelta('Partial answer');
    })};
  vm.createContext(ctx);
  vm.runInContext(source.slice(source.indexOf('async function sendContent('),source.indexOf('\nlet editingMessage=')),ctx);
  vm.runInContext(source.slice(source.indexOf('async function stopCurrentRequest('),source.indexOf('\nasync function retryFailed(')),ctx);
  vm.runInContext(source.slice(source.indexOf('async function regenerateReply('),source.indexOf('\nfunction openConversationMenu(')),ctx);
  return {ctx,drafts,toasts,resolve:data=>resolveCancel(data),reject:()=>rejectCancel(Error('Offline')),rejectStream:()=>rejectStream()};
}
(async()=>{
  for(const delayedAbort of [false,true]){
    for(const outcome of ['cancelled','completed','unconfirmed']){
      const f=fixture({delayedAbort}),{ctx}=f;
      const sending=ctx.sendContent('Keep my question');await tick();
      const stopping=ctx.stopCurrentRequest();await tick();
      assert.equal(ctx.state.messages.some(m=>m.failed),false,'Do not finalize a receipt before the cancel/save result');
      if(outcome==='unconfirmed')f.reject();
      else if(outcome==='cancelled')f.resolve({cancelled:true});
      else f.resolve({cancelled:false,completed:{user_message:{id:20,role:'user',content:'Keep my question'},assistant_message:{id:21,role:'assistant',content:'Verified saved answer'}}});
      if(delayedAbort){await stopping;f.rejectStream()}
      await Promise.all([sending,stopping]);
      assert.equal(ctx.state.sending,false);assert.equal(ctx.state.cancelling,false);
      const failed=ctx.state.messages.find(m=>m.failed);
      if(outcome==='completed'){
        assert.equal(failed,undefined,'A saved-before-Stop result must not acquire a false failure');
        assert.equal(ctx.state.messages.length,2);assert.equal(ctx.state.messages[1].content,'Verified saved answer');
        assert.equal(f.drafts.has(1),false,'Do not restore a draft that was verified as saved');
      }else{
        assert.equal(ctx.el.input.value,'Keep my question');assert.match(failed.content,/Partial answer/);
        assert.doesNotMatch(failed.content,/Checking whether/,'The check must reach an honest terminal state');
        if(outcome==='cancelled'){
          assert.match(failed.content,/No answer or action was saved/);assert.equal(ctx.state.messages[0].cancelled,true);assert.equal(ctx.state.draftRequestId,null,'Composer resend after a confirmed Stop needs a fresh request ID');assert.equal(f.drafts.get(1).request_id,null,'Reload must not recover the cancelled request ID');
        }else{
          assert.match(failed.content,/Saved state is unconfirmed/);assert.doesNotMatch(failed.content,/No answer or action was saved/);
          assert.notEqual(ctx.state.messages[0].cancelled,true,'An unconfirmed Stop must retry the same request');
        }
      }
    }
  }
  for(const outcome of ['cancelled','completed','unconfirmed']){
    const f=fixture({regenerating:true}),{ctx}=f;
    const work=ctx.regenerateReply();await tick();
    assert.equal(ctx.state.messages[1].cancelled,undefined,'A previous Stop must not decide a later regeneration');
    const stop=ctx.stopCurrentRequest();await tick();
    if(outcome==='unconfirmed')f.reject();
    else if(outcome==='cancelled')f.resolve({cancelled:true});
    else f.resolve({cancelled:false,completed_regeneration:{assistant_message:{id:22,role:'assistant',content:'Verified replacement'}}});
    await Promise.all([work,stop]);
    assert.equal(ctx.state.messages.length,2);
    assert.equal(ctx.state.messages[1].content,outcome==='completed'?'Verified replacement':'Original answer');
    if(outcome==='cancelled')assert.match(f.toasts.at(-1),/original saved answer is kept/);
    if(outcome==='unconfirmed')assert.match(f.toasts.at(-1),/Saved state is unconfirmed/);
  }
  console.log('PASS Stop receipts: both response orders, saved-before-Stop, offline uncertainty, draft retention and regeneration');
})().catch(error=>{console.error(error);process.exitCode=1});
