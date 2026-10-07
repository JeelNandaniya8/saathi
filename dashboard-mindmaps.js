/* ── Visual Mindmap Studio Engine ───────────────────────────── */
async function handleMindmapSubmit(event){
  event.preventDefault();
  const input=$('mindmapTopicInput');
  const topic=input.value.trim();
  if(!topic)return;
  const depth=$('mindmapDepth')?.value||'standard';
  const btn=$('mindmapSubmitBtn');
  btn.disabled=true;
  btn.textContent='Generating mindmap…';
  try{
    const res=await api('/api/mindmaps/generate',{
      method:'POST',
      body:JSON.stringify({topic,language:state.user?.language||'en'})
    });
    state.activeMindmap=res.mindmap;
    if(!state.mindmaps)state.mindmaps=[];
    state.mindmaps.unshift(res.mindmap);
    renderMindmapsHistory();
    displayMindmap(res.mindmap);
    toast('Mindmap generated successfully! ✨','success');
  }catch(err){
    if(err.message&&err.message.includes('Upgrade to Saathi Plus')){
      openUpgradeModal();
    }
    toast(err.message||'Could not generate mindmap','error');
  }finally{
    btn.disabled=false;
    btn.textContent='Generate visual mindmap';
  }
}

function displayMindmap(mindmap){
  state.mmCollapsed=new Set();
  if(!mindmap||!mindmap.data)return;
  $('mindmapCreatorPanel').style.display='none';
  $('mindmapViewerWrap').style.display='block';
  $('mindmapActiveTopicBadge').textContent='Mindmap';
  $('mindmapActiveTitle').textContent=mindmap.topic||mindmap.data.topic;
  $('mindmapActiveSummary').textContent=mindmap.data.summary||'';
  renderMindmapTree(mindmap.data);
  state.mmZoom=1;
  resetMindmapZoom();
  scrollTo({top:$('mindmapViewerWrap').offsetTop-80,behavior:'smooth'});
}

function newMindmapPrompt(){
  $('mindmapViewerWrap').style.display='none';
  $('mindmapCreatorPanel').style.display='block';
  $('mindmapTopicInput').value='';
  $('mindmapTopicInput').focus();
  scrollTo({top:$('mindmapCreatorPanel').offsetTop-80,behavior:'smooth'});
}

function mindmapLayout(root,collapsed=new Set(),heightFor=()=>300){
  const nodes=[],edges=[];let depthMax=0;
  function measure(node,depth){
    const children=collapsed.has(node.id)?[]:(node.children||[]).map(child=>measure(child,depth+1));
    const height=heightFor(node),span=Math.max(height,children.reduce((sum,c)=>sum+c.span,0)+Math.max(0,children.length-1)*32);
    depthMax=Math.max(depthMax,depth);return {node,depth,height,span,children};
  }
  function place(item,top,parent){
    const entry={...item,x:200+item.depth*400,y:top+item.span/2};nodes.push(entry);if(parent)edges.push([parent,entry]);
    let childTop=top+(item.span-item.children.reduce((sum,c)=>sum+c.span,0)-Math.max(0,item.children.length-1)*32)/2;
    for(const child of item.children){place(child,childTop,entry);childTop+=child.span+32}
  }
  const tree=measure(root,0);place(tree,80,null);return {nodes,edges,width:400*(depthMax+1),height:tree.span+160};
}
function renderMindmapTree(data){
  const svg=$('mmSvg'),nodesLayer=$('mmNodes');svg.replaceChildren();nodesLayer.replaceChildren();if(!data?.root)return;
  state.mmCollapsed??=new Set();const layout=mindmapLayout(data.root,state.mmCollapsed);state.mmLayout=layout;
  const stage=$('mmStage');stage.style.minWidth='0';stage.style.minHeight='0';stage.style.width=layout.width+'px';stage.style.height=layout.height+'px';svg.setAttribute('viewBox',`0 0 ${layout.width} ${layout.height}`);
  for(const [parent,child] of layout.edges)drawBezierCurve(svg,parent.x,parent.y,child.x,child.y,child.node.color||'#4263eb');
  const language=state.user?.language||'en',labels={en:['Expand','Collapse'],gu:['ખોલો','સંકેલો'],hi:['खोलें','समेटें']}[language]||['Expand','Collapse'];
  for(const item of layout.nodes){
    const n=createNodeEl(nodesLayer,item.node.label,item.node.desc,item.x,item.y,item.depth===0?'root':item.depth===1?'pillar':'sub',item.node.color||'#4263eb');n.style.width='320px';n.style.maxWidth='320px';n.style.overflowWrap='anywhere';
    const desc=n.querySelector('.mm-desc');if(desc){desc.style.maxHeight='100px';desc.style.overflow='auto';desc.tabIndex=0}
    if(item.node.children?.length){const toggle=document.createElement('button');toggle.type='button';toggle.className='mini-button';toggle.style.minHeight='44px';toggle.dataset.nodeId=item.node.id;toggle.textContent=state.mmCollapsed.has(item.node.id)?'+':'−';toggle.setAttribute('aria-label',(state.mmCollapsed.has(item.node.id)?labels[0]:labels[1])+' '+item.node.label);toggle.setAttribute('aria-expanded',String(!state.mmCollapsed.has(item.node.id)));toggle.onclick=()=>{state.mmCollapsed.has(item.node.id)?state.mmCollapsed.delete(item.node.id):state.mmCollapsed.add(item.node.id);renderMindmapTree(data);[...nodesLayer.querySelectorAll('button')].find(b=>b.dataset.nodeId===item.node.id)?.focus({preventScroll:true})};n.append(toggle)}
  }
  const vp=$('mmViewport');vp.tabIndex=0;vp.setAttribute('aria-label',({gu:'માઇન્ડમેપ. સરકાવીને જુઓ; + અને − થી ઝૂમ, 0 થી મૂળ કદ.',hi:'माइंडमैप। स्क्रॉल करके देखें; + और − से ज़ूम, 0 से मूल आकार।'})[language]||'Mindmap. Scroll to pan; plus and minus to zoom, zero to reset.');vp.onkeydown=e=>{if(e.target!==vp)return;if(['+','=','-','0'].includes(e.key)){e.preventDefault();e.key==='0'?resetMindmapZoom():zoomMindmap(e.key==='-'?-.1:.1)}};
  if(!vp.dataset.panBound){vp.dataset.panBound='true';let drag=null;vp.addEventListener('pointerdown',e=>{if(e.pointerType!=='mouse'||e.button!==0||e.target.closest('.mm-node'))return;drag={x:e.clientX,y:e.clientY,left:vp.scrollLeft,top:vp.scrollTop};vp.setPointerCapture(e.pointerId)});vp.addEventListener('pointermove',e=>{if(drag){vp.scrollLeft=drag.left+drag.x-e.clientX;vp.scrollTop=drag.top+drag.y-e.clientY}});for(const name of ['pointerup','pointercancel','lostpointercapture'])vp.addEventListener(name,()=>{drag=null})}
  applyMindmapZoom();
}

function drawBezierCurve(svg,x1,y1,x2,y2,color){
  const path=document.createElementNS('http://www.w3.org/2000/svg','path');
  const dx=(x2-x1)*0.55;
  const d=`M ${x1} ${y1} C ${x1+dx} ${y1}, ${x2-dx} ${y2}, ${x2} ${y2}`;
  path.setAttribute('d',d);
  path.setAttribute('stroke',color);
  path.setAttribute('stroke-width','2.5');
  path.setAttribute('fill','none');
  path.setAttribute('stroke-linecap','round');
  path.setAttribute('opacity','0.65');
  svg.appendChild(path);
}

function createNodeEl(container,label,desc,x,y,type,color){
  const el=document.createElement('div');
  el.className=`mm-node ${type}`;
  el.style.left=`${x}px`;
  el.style.top=`${y}px`;
  if(type!=='root')el.style.borderColor=color;

  const titleEl=document.createElement('div');
  titleEl.className='mm-title';
  if(type==='pillar')titleEl.style.color=color;
  titleEl.textContent=label;

  el.appendChild(titleEl);
  if(desc){
    const descEl=document.createElement('div');
    descEl.className='mm-desc';
    descEl.textContent=desc;
    el.appendChild(descEl);
  }

  container.appendChild(el);return el;
}

function zoomMindmap(delta){
  state.mmZoom=Math.min(2.0,Math.max(0.5,+(state.mmZoom+delta).toFixed(2)));
  applyMindmapZoom();
}

function resetMindmapZoom(){
  state.mmZoom=1.0;
  applyMindmapZoom();
  const vp=$('mmViewport');
  vp.scrollLeft=0;vp.scrollTop=Math.max(0,(state.mmLayout?.height||900)/2-vp.clientHeight/2);
}

function applyMindmapZoom(){
  const stage=$('mmStage');
  if(stage){stage.style.transform=`scale(${state.mmZoom})`;let sizer=$('mmSizer');if(!sizer){sizer=document.createElement('div');sizer.id='mmSizer';sizer.setAttribute('aria-hidden','true');$('mmViewport').append(sizer)}sizer.style.width=(state.mmLayout?.width||1400)*state.mmZoom+'px';sizer.style.height=(state.mmLayout?.height||900)*state.mmZoom+'px'}
  if($('mindmapZoomIndicator'))$('mindmapZoomIndicator').textContent=`${Math.round(state.mmZoom*100)}%`;
}

function renderMindmapsHistory(){
  const box=$('mindmapsHistoryList');
  if(!box)return;
  box.innerHTML='';
  const items=state.mindmaps||[];
  if(!items.length){
    box.innerHTML='<div class="item" style="color:var(--muted);padding:18px">No mindmaps created yet. Enter a topic above to generate your first concept tree!</div>';
    return;
  }
  items.forEach(m=>{
    const d=document.createElement('div');
    d.className='item';
    d.style.display='flex';
    d.style.alignItems='center';
    d.style.justifyContent='space-between';
    d.style.gap='12px';
    d.style.padding='14px 18px';

    const dt=m.created_at?new Date(m.created_at).toLocaleDateString():'Recent';
    d.innerHTML=`
      <div>
        <strong style="font-size:14px;color:var(--ink);display:block">${escapeText(m.topic)}</strong>
        <small style="color:var(--muted);font-size:12px">Created ${dt}</small>
      </div>
      <button type="button" class="secondary" style="min-height:36px;font-size:12.5px" onclick="loadSavedMindmap(${Number(m.id)})">Open Map →</button>
    `;
    box.appendChild(d);
  });
}

async function loadSavedMindmap(id){
  toast('Loading mindmap…','info');
  try{
    const res=await api(`/api/mindmaps/${id}`);
    if(res.mindmap){
      state.activeMindmap=res.mindmap;
      displayMindmap(res.mindmap);
    }
  }catch(err){
    toast(err.message||'Could not load mindmap','error');
  }
}

function shareMindmapWhatsApp(){
  const topic=state.activeMindmap?.topic||'Concept';
  const refCode=state.referrals?.referral_code||'';
  const link=refCode?`${location.origin}/account?ref=${refCode}&google=1`:`${location.origin}/account?google=1`;
  const text=encodeURIComponent(`Check out this visual AI concept mindmap on "${topic}" I created with Saathi!\n\nStudy concept trees and master any topic faster here:\n${link}`);
  window.open(`https://api.whatsapp.com/send?text=${text}`,'_blank');
}

function wrapMindmapText(ctx,text,width){
  const lines=[];for(const paragraph of String(text||'').split('\n')){let line='';for(const word of paragraph.split(/\s+/)){const candidate=line?line+' '+word:word;if(ctx.measureText(candidate).width<=width){line=candidate;continue}if(line)lines.push(line);line='';for(const char of word){if(line&&ctx.measureText(line+char).width>width){lines.push(line);line=''}line+=char}}lines.push(line)}return lines;
}
function exportMindmapPng(){
  const data=state.activeMindmap?.data;if(!data?.root)return;
  const canvas=document.createElement('canvas'),ctx=canvas.getContext('2d');if(!ctx){toast('Image export is unavailable in this browser.','error');return}
  const text=new Map();const layout=mindmapLayout(data.root,new Set(),node=>{ctx.font='600 20px system-ui';const title=wrapMindmapText(ctx,node.label,288);ctx.font='16px system-ui';const desc=wrapMindmapText(ctx,node.desc,288);text.set(node,{title,desc});return 40+title.length*26+desc.length*22});
  const scale=Math.min(2,Math.sqrt(16000000/(layout.width*layout.height)),16000/layout.height);
  canvas.width=Math.ceil(layout.width*scale);canvas.height=Math.ceil(layout.height*scale);ctx.scale(scale,scale);ctx.fillStyle='#faf7f0';ctx.fillRect(0,0,layout.width,layout.height);
  for(const [parent,child] of layout.edges){ctx.strokeStyle='#a79b85';ctx.lineWidth=2;ctx.beginPath();ctx.moveTo(parent.x+160,parent.y);ctx.lineTo(child.x-160,child.y);ctx.stroke()}
  for(const item of layout.nodes){const x=item.x-160,y=item.y-item.height/2;ctx.fillStyle='#fffdf8';ctx.strokeStyle='#d5cebf';ctx.lineWidth=1;ctx.beginPath();ctx.roundRect(x,y,320,item.height,14);ctx.fill();ctx.stroke();let lineY=y+28;ctx.fillStyle='#292b28';ctx.font='600 20px system-ui';for(const line of text.get(item.node).title){ctx.fillText(line,x+16,lineY);lineY+=26}ctx.fillStyle='#51554c';ctx.font='16px system-ui';for(const line of text.get(item.node).desc){ctx.fillText(line,x+16,lineY);lineY+=22}}
  canvas.toBlob(blob=>{if(!blob){toast('Image export failed. Please retry.','error');return}const url=URL.createObjectURL(blob),link=document.createElement('a');link.download='saathi-mindmap.png';link.href=url;link.click();setTimeout(()=>URL.revokeObjectURL(url),30000);toast('Mindmap PNG downloaded.','success')},'image/png');
}
