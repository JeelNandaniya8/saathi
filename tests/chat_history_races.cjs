const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const path=require('node:path');
const html=fs.readFileSync(path.join(__dirname,'../chat.html'),'utf8');
const history=html.slice(html.indexOf('let historyLoadSequence='),html.indexOf('\nasync function createConversation'));
const older=html.slice(html.indexOf('async function loadOlderMessages(){'),html.indexOf('\nasync function copyMessage'));
function setup(){
 const pending=[],toasts=[];
 const button={disabled:false,isConnected:true};
 const state={activeId:1,showArchived:false,hasMore:true,nextBeforeId:10,messages:[{id:10}]};
 const el={list:{querySelector:()=>button},messages:{scrollHeight:100,scrollTop:20},search:{value:''},history:{replaceChildren(){}}};
 const c={state,el,api:()=>new Promise((resolve,reject)=>pending.push({resolve,reject})),normaliseMessageDisplay:x=>x,normaliseConversationDisplay:x=>x,renderMessages:()=>{el.messages.scrollHeight+=50},renderConversations(){},showToast:x=>toasts.push(x),document:{createElement:()=>({setAttribute(){},append(){},addEventListener(){}})}};
 vm.createContext(c);vm.runInContext('let conversationLoadSequence=0;'+history+'\n'+older,c);
 return {c,pending,toasts,button,state,el,advance:()=>vm.runInContext('conversationLoadSequence++',c)};
}
(async()=>{
 // Repeated clicks make one request; overlapping pages are deduplicated and preserve position.
 let t=setup(),p=t.c.loadOlderMessages();await t.c.loadOlderMessages();assert.equal(t.pending.length,1);assert.equal(t.button.disabled,true);
 t.pending[0].resolve({messages:[{id:9},{id:10}],has_more:true,next_before_id:9});await p;
 assert.deepEqual(Array.from(t.state.messages,x=>x.id),[9,10]);assert.equal(t.el.messages.scrollTop,70);assert.equal(t.button.disabled,false);
 // A -> B -> A does not admit A's obsolete pagination response.
 t=setup();p=t.c.loadOlderMessages();t.state.activeId=2;t.advance();t.state.activeId=1;t.advance();
 t.pending[0].resolve({messages:[{id:2}],has_more:false});await p;assert.deepEqual(Array.from(t.state.messages,x=>x.id),[10]);
 // A stale failure does not show an error in another chat.
 t=setup();p=t.c.loadOlderMessages();t.state.activeId=2;t.advance();t.pending[0].reject(Error('old error'));await p;assert.equal(t.toasts.length,0);
 // Current failure unlocks retry.
 t=setup();p=t.c.loadOlderMessages();t.pending[0].reject(Error('offline'));await p;assert.equal(t.button.disabled,false);assert.equal(t.toasts.length,1);
 p=t.c.loadOlderMessages();assert.equal(t.pending.length,2);t.pending[1].resolve({messages:[],has_more:false});await p;
 // New search results win even if the old request finishes last.
 t=setup();p=t.c.loadConversations('old');let newer=t.c.loadConversations('new');
 t.pending[1].resolve({conversations:[{id:2}]});await newer;t.pending[0].resolve({conversations:[{id:3}]});await p;assert.equal(t.state.conversations[0].id,2);
 // Archived state invalidates results before the next request starts.
 t=setup();p=t.c.loadConversations('old');t.state.showArchived=true;t.pending[0].resolve({conversations:[{id:3}]});await p;assert.equal(t.state.conversations,undefined);
 // Typing during debounce invalidates both stale results and errors.
 t=setup();p=t.c.loadConversations('old');vm.runInContext('historyLoadSequence++',t.c);t.pending[0].reject(Error('stale'));await p;assert.equal(t.toasts.length,0);
 console.log('Chat history race tests passed');
})().catch(error=>{console.error(error);process.exitCode=1});
