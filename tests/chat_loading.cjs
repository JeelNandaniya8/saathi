const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const source=fs.readFileSync('chat.html','utf8'),pending=[];
const node=()=>({setAttribute(){},addEventListener(event,handler){this.click=handler}});
const ctx={state:{activeId:1,messages:[],selectedFiles:[],conversations:[{id:1},{id:2}]},el:{input:{disabled:false,focus(){}},send:{},chatTitle:{},list:{replaceChildren(){},append(...items){this.items=items}}},document:{createElement:node},
 saveChatDraft(){},restoreChatDraft(){},updateComposer(){},currentConversation:()=>({title:'Saved'}),renderConversations(){},closeConversationMenu(){},closeSide(){},renderChatLoading(){},renderMessages(){},scrollToLatest(){},releaseLocalPreviews(){},showToast(){},normaliseMessageDisplay:v=>v,decodeLegacyText:v=>v,
 api:()=>new Promise((resolve,reject)=>pending.push({resolve,reject}))};
vm.createContext(ctx);vm.runInContext(source.slice(source.indexOf('let startupMessages='),source.indexOf('\nfunction emptyView')),ctx);
const result=(id,content)=>({conversation:{id,title:'Saved'},messages:[{content}]});
(async()=>{
 const first=ctx.selectConversation(1),second=ctx.selectConversation(2),latest=ctx.selectConversation(1);
 pending[0].resolve(result(1,'Old response'));await first;
 assert.equal(ctx.state.messages.length,0);assert.equal(ctx.el.input.disabled,true,'Old response cannot unlock a newer load');
 pending[1].reject(Error('Old failure'));await second;assert.equal(ctx.state.historyError,false);
 pending[2].resolve(result(1,'Latest response'));await latest;assert.equal(ctx.state.messages[0].content,'Latest response');assert.equal(ctx.el.input.disabled,false);
 const failing=ctx.selectConversation(2);pending[3].reject(Error('Offline'));await failing;
 assert.equal(ctx.state.historyError,true);assert.equal(ctx.el.input.disabled,true);assert.equal(ctx.el.list.items[1].textContent,'Retry loading conversation');
 const retry=ctx.el.list.items[1].click();pending[4].resolve(result(2,'Recovered'));await retry;
 assert.equal(ctx.state.historyError,false);assert.equal(ctx.state.messages[0].content,'Recovered');assert.equal(ctx.el.input.disabled,false);
 console.log('PASS: out-of-order chat loads, stale errors, blocked failed history and retry recovery');
})().catch(error=>{console.error(error);process.exitCode=1});
