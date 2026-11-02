/* Keep the existing composer above a soft keyboard without disabling zoom. */
(()=>{
 const root=document.documentElement,viewport=window.visualViewport;
 let frame=0;
 function update(){
  frame=0;
  if(viewport&&Math.abs((viewport.scale||1)-1)>.01)return;
  const height=viewport?.height||window.innerHeight;
  if(!Number.isFinite(height)||height<1)return;
  root.style.setProperty('--chat-viewport-height',Math.floor(height)+'px');
  root.classList.toggle('chat-keyboard-open',window.innerHeight-height>100);
 }
 function queue(){if(!frame)frame=requestAnimationFrame(update)}
 viewport?.addEventListener('resize',queue);
 window.addEventListener('resize',queue);
 window.addEventListener('pageshow',queue);
 update();
})();
