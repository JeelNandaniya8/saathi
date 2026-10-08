const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const source=fs.readFileSync('chat.html','utf8');
let now=0,scheduled=null,renders=[],scrolls=0;
const node={isConnected:true,classList:{add(){}}},message={id:'stream',content:'First'};
const context={window:{SaathiChatActions:{clean:text=>text.replace(/<SAATHI_ACTION>[\s\S]*$/,'')}},performance:{now:()=>now},el:{list:{querySelector:()=>node},messages:{scrollHeight:500,scrollTop:200,clientHeight:300}},renderMarkdown:(_,text)=>renders.push(text),scrollToLatest:()=>scrolls++,setTimeout:fn=>(scheduled=fn,1),clearTimeout:()=>scheduled=null};
vm.createContext(context);vm.runInContext(source.slice(source.indexOf('function createStreamPainter('),source.indexOf('function progressiveReveal(')),context);
const painter=context.createStreamPainter(message);
painter.update();assert.deepEqual(renders,['First'],'first chunk paints immediately');
for(let i=0;i<200;i++){message.content+='x';painter.update()}
assert.equal(renders.length,1,'burst does not repeatedly parse Markdown');
now=80;scheduled();assert.equal(renders.length,2);assert.equal(renders[1],message.content);
context.el.messages.scrollTop=0;message.content+='tail';painter.update();now=160;scheduled();assert.equal(scrolls,2,'reading older content does not jump to bottom');
message.content+='pending';painter.update();painter.cancel();assert.equal(scheduled,null);painter.update();assert.equal(renders.length,3);
assert.ok(source.includes('el.input.disabled=Boolean(state.loadingConversation||state.historyError)'));
assert.ok(source.includes("if(!el.input.value.trim())window.SaathiRecovery?.removeDraft"));
message.content='Visible<SAATHI_ACTION>{partial';now=300;const actionPainter=context.createStreamPainter(message);actionPainter.update();assert.equal(renders.at(-1),'Visible','Streaming previews never expose action JSON');actionPainter.cancel();
console.log('PASS immediate first chunk, coalesced burst, scroll intent, cancellation and draft guards');
