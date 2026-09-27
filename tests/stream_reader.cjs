const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const source=fs.readFileSync('chat.html','utf8');
const fn=source.slice(source.indexOf('async function streamChatRequest('),source.indexOf('\nfunction renderChatModes'));
const ctx={window:{},AbortController,TextDecoder,FormData,setTimeout,clearTimeout,state:{csrf:'test'},el:{uploadStatus:{}},showRequestProgress(){},location:{},fetch:null};
vm.createContext(ctx);vm.runInContext(fn,ctx);
(async()=>{
 let pipe;ctx.fetch=async()=>({ok:true,status:200,body:new ReadableStream({start(c){pipe=c}})});
 const deltas=[];let finished=false;
 const work=ctx.streamChatRequest('/test','{}',s=>deltas.push(s)).then(r=>{finished=true;return r});
 await new Promise(r=>setImmediate(r));
 const bytes=new TextEncoder().encode(JSON.stringify({type:'delta',text:'ગુજરાતી 😊'})+'\n');
 // Split every UTF-8 code point across reads.
 for(const byte of bytes)pipe.enqueue(Uint8Array.of(byte));
 await new Promise(r=>setImmediate(r));
 assert.equal(deltas.join(''),'ગુજરાતી 😊');assert.equal(finished,false,'Text must arrive before EOF');
 pipe.enqueue(new TextEncoder().encode('{"type":"complete","data":{"saved":true}}\n'));pipe.close();
 assert.equal((await work).saved,true);
 let abortSignal;ctx.fetch=async(url,options)=>{abortSignal=options.signal;return {ok:true,status:200,body:new ReadableStream({start(c){options.signal.addEventListener('abort',()=>c.error(new DOMException('Stopped','AbortError')))}})}};
 const cancelled=ctx.streamChatRequest('/test','{}',()=>{});await new Promise(r=>setImmediate(r));ctx.state.activeRequest.abort();
 await assert.rejects(cancelled,{name:'AbortError'});assert.equal(abortSignal.aborted,true);
 const timings=[];ctx.window.SaathiRecovery={measureStart:()=>({}),measureDelta:()=>{},measureEnd:(_,outcome,error)=>timings.push({outcome,code:error?.code})};
 ctx.fetch=async()=>({ok:true,status:200,body:new ReadableStream({start(c){c.enqueue(new TextEncoder().encode('{"type":"error","error":"Usage limit","code":"AI_QUOTA","retry_after":31}\n'));c.close()}})});
 await assert.rejects(ctx.streamChatRequest('/api/conversations/3/messages/stream','{}',()=>{}),error=>error.code==='AI_QUOTA'&&error.retry_after===31);
 assert.equal(timings.length,1);assert.equal(timings[0].outcome,'error');assert.equal(timings[0].code,'AI_QUOTA');
 console.log('PASS: incremental Gujarati/emoji before EOF and Stop cancellation');
})().catch(e=>{console.error(e);process.exitCode=1});
