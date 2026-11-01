// Exercise the handlers registered by the actual page, without AI or saved data.
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const source=fs.readFileSync('chat.html','utf8');
const inputHandler=source.split("el.input.addEventListener('keydown',")[1].split(');\nel.search')[0];
const shortcut=source.slice(source.indexOf("document.addEventListener('keydown',event=>"),source.indexOf("\nwindow.addEventListener('pagehide',()=>{clearInterval"));
let failures=0;
function test(name,check){try{check();console.log('PASS '+name)}catch(error){failures++;console.error('FAIL '+name+': '+error.message)}}
for(const event of [{key:'Enter',isComposing:true},{key:'Enter',keyCode:229},{key:'Enter',shiftKey:true}]){
 test('No send during composition or Shift+Enter '+JSON.stringify(event),()=>{
  let submits=0;const el={composer:{requestSubmit(){submits++}}};
  vm.runInNewContext('('+inputHandler+')', {el,state:{sending:false}})({...event,preventDefault(){}});
  assert.equal(submits,0);
 });
}
test('Ordinary Enter submits once',()=>{
 let submits=0;vm.runInNewContext('('+inputHandler+')',{el:{composer:{requestSubmit(){submits++}}},state:{sending:false}})({key:'Enter',preventDefault(){}});
 assert.equal(submits,1);
});
test('Search shortcut opens History before focusing its hidden input',()=>{
 let handler,hidden=true,focused=false;
 const document={addEventListener(type,fn){handler=fn},querySelector(){return null}};
 const el={search:{focus(){if(!hidden)focused=true}}};
 vm.runInNewContext(shortcut,{document,window:{},el,openSide(){hidden=false},closeSide(){},createConversation(){}});
 handler({key:'k',ctrlKey:true,preventDefault(){}});
 assert.equal(hidden,false);assert.equal(focused,true);
});
if(failures)process.exitCode=1;
