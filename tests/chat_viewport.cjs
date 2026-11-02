const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
function run(withViewport=true){
 const callbacks={},properties={},classes=new Set(),frames=[];
 const viewport={height:900,scale:1,addEventListener(name,fn){callbacks['visual:'+name]=fn}};
 const window={innerHeight:900,visualViewport:withViewport?viewport:null,addEventListener(name,fn){callbacks[name]=fn}};
 const root={style:{setProperty(k,v){properties[k]=v}},classList:{toggle(k,on){if(on)classes.add(k);else classes.delete(k)}}};
 vm.runInNewContext(fs.readFileSync('chat-viewport.js','utf8'),{window,document:{documentElement:root},requestAnimationFrame:fn=>(frames.push(fn),frames.length),Number,Math});
 const flush=()=>{while(frames.length)frames.shift()()};
 assert.equal(properties['--chat-viewport-height'],'900px');
 if(withViewport){
  viewport.height=400;callbacks['visual:resize']();callbacks['visual:resize']();assert.equal(frames.length,1);flush();
  assert.equal(properties['--chat-viewport-height'],'400px');assert.ok(classes.has('chat-keyboard-open'));
  viewport.height=200;viewport.scale=2;callbacks['visual:resize']();flush();assert.equal(properties['--chat-viewport-height'],'400px','Pinch zoom must not shrink the layout');
  viewport.scale=1;viewport.height=900;callbacks['visual:resize']();flush();
 }else{window.innerHeight=400;callbacks.resize();flush();assert.equal(properties['--chat-viewport-height'],'400px');window.innerHeight=900;callbacks.resize();flush();}
 assert.equal(properties['--chat-viewport-height'],'900px');assert.ok(!classes.has('chat-keyboard-open'));
 callbacks.pageshow();flush();
}
run();run(false);console.log('PASS visual viewport, keyboard resize, zoom, orientation fallback and page restore');
