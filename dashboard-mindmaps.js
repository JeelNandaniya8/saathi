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
  if(!mindmap||!mindmap.data)return;
  $('mindmapCreatorPanel').style.display='none';
  $('mindmapViewerWrap').style.display='block';
  $('mindmapActiveTopicBadge').textContent='Mindmap';
  $('mindmapActiveTitle').textContent=mindmap.topic||mindmap.data.topic;
  $('mindmapActiveSummary').textContent=mindmap.data.summary||'';
  renderMindmapTree(mindmap.data);
  state.mmZoom=1;
  applyMindmapZoom();
  scrollTo({top:$('mindmapViewerWrap').offsetTop-80,behavior:'smooth'});
}

function newMindmapPrompt(){
  $('mindmapViewerWrap').style.display='none';
  $('mindmapCreatorPanel').style.display='block';
  $('mindmapTopicInput').value='';
  $('mindmapTopicInput').focus();
  scrollTo({top:$('mindmapCreatorPanel').offsetTop-80,behavior:'smooth'});
}

function renderMindmapTree(data){
  const svg=$('mmSvg');
  const nodesLayer=$('mmNodes');
  svg.innerHTML='';
  nodesLayer.innerHTML='';
  if(!data||!data.root)return;

  const root=data.root;
  const stageW=1400;
  const stageH=900;
  const centerX=stageW/2;
  const centerY=stageH/2;

  // Place Root Node
  createNodeEl(nodesLayer,root.label,root.desc,centerX,centerY,'root',root.color||'#4f46e5');

  const children=root.children||[];
  if(!children.length)return;

  const leftChildren=[];
  const rightChildren=[];
  children.forEach((c,idx)=>{
    if(idx%2===0)rightChildren.push(c);
    else leftChildren.push(c);
  });

  function layoutBranch(items,isRight){
    const count=items.length;
    const xPillar=isRight?(centerX+320):(centerX-320);
    const xSub=isRight?(centerX+580):(centerX-580);
    const startY=count===1?centerY:(centerY-(count-1)*110);

    items.forEach((item,i)=>{
      const pillarY=count===1?centerY:(startY+i*220);
      const col=item.color||(isRight?'#0ea5e9':'#10b981');

      drawBezierCurve(svg,centerX,centerY,xPillar,pillarY,col);
      createNodeEl(nodesLayer,item.label,item.desc,xPillar,pillarY,'pillar',col);

      const subItems=item.children||[];
      const subCount=subItems.length;
      if(subCount>0){
        const subStartY=subCount===1?pillarY:(pillarY-(subCount-1)*45);
        subItems.forEach((sub,si)=>{
          const subY=subCount===1?pillarY:(subStartY+si*90);
          const subCol=sub.color||col;
          drawBezierCurve(svg,xPillar,pillarY,xSub,subY,subCol);
          createNodeEl(nodesLayer,sub.label,sub.desc,xSub,subY,'sub',subCol);
        });
      }
    });
  }

  if(rightChildren.length)layoutBranch(rightChildren,true);
  if(leftChildren.length)layoutBranch(leftChildren,false);

  const vp=$('mmViewport');
  setTimeout(()=>{
    vp.scrollLeft=(stageW-vp.clientWidth)/2;
    vp.scrollTop=(stageH-vp.clientHeight)/2;
  },50);
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

  const icon=type==='root'?'🌱':(type==='pillar'?'🔹':'💡');
  const titleEl=document.createElement('div');
  titleEl.className='mm-title';
  if(type==='pillar')titleEl.style.color=color;
  titleEl.textContent=`${icon} ${label}`;

  el.appendChild(titleEl);
  if(desc){
    const descEl=document.createElement('div');
    descEl.className='mm-desc';
    descEl.textContent=desc;
    el.appendChild(descEl);
  }

  container.appendChild(el);
}

function zoomMindmap(delta){
  state.mmZoom=Math.min(2.0,Math.max(0.5,+(state.mmZoom+delta).toFixed(2)));
  applyMindmapZoom();
}

function resetMindmapZoom(){
  state.mmZoom=1.0;
  applyMindmapZoom();
  const vp=$('mmViewport');
  vp.scrollLeft=(1400-vp.clientWidth)/2;
  vp.scrollTop=(900-vp.clientHeight)/2;
}

function applyMindmapZoom(){
  const stage=$('mmStage');
  if(stage)stage.style.transform=`scale(${state.mmZoom})`;
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

function exportMindmapPng(){
  const data=state.activeMindmap?.data;
  if(!data||!data.root)return;
  const canvas=document.createElement('canvas');
  canvas.width=1600;
  canvas.height=1000;
  const ctx=canvas.getContext('2d');

  const bgGrad=ctx.createLinearGradient(0,0,1600,1000);
  bgGrad.addColorStop(0,'#0f172a');
  bgGrad.addColorStop(0.5,'#1e293b');
  bgGrad.addColorStop(1,'#090d16');
  ctx.fillStyle=bgGrad;
  ctx.fillRect(0,0,1600,1000);

  ctx.fillStyle='#f1d97f';
  ctx.font='800 24px Inter, sans-serif';
  ctx.fillText('SAATHI AI · VISUAL CONCEPT MAP',80,70);

  ctx.fillStyle='#ffffff';
  ctx.font='800 48px Inter, sans-serif';
  ctx.fillText(data.topic||data.root.label,80,130);

  ctx.fillStyle='#94a3b8';
  ctx.font='500 22px Inter, sans-serif';
  ctx.fillText(data.summary||'Hierarchical Study Guide',80,175);

  const root=data.root;
  const cx=800,cy=560;

  ctx.fillStyle='#1e1b4b';
  ctx.strokeStyle='#6366f1';
  ctx.lineWidth=3;
  ctx.beginPath();
  ctx.roundRect(cx-150,cy-50,300,100,20);
  ctx.fill();
  ctx.stroke();

  ctx.fillStyle='#ffffff';
  ctx.font='800 24px Inter, sans-serif';
  ctx.textAlign='center';
  ctx.fillText(root.label,cx,cy+8);

  const pillars=root.children||[];
  pillars.forEach((p,idx)=>{
    const angle=(Math.PI*2/pillars.length)*idx;
    const px=cx+Math.cos(angle)*440;
    const py=cy+Math.sin(angle)*260;

    ctx.strokeStyle=p.color||'#38bdf8';
    ctx.lineWidth=2.5;
    ctx.beginPath();
    ctx.moveTo(cx,cy);
    ctx.quadraticCurveTo((cx+px)/2,(cy+py)/2-30,px,py);
    ctx.stroke();

    ctx.fillStyle='#1e293b';
    ctx.strokeStyle=p.color||'#38bdf8';
    ctx.lineWidth=2;
    ctx.beginPath();
    ctx.roundRect(px-140,py-40,280,80,16);
    ctx.fill();
    ctx.stroke();

    ctx.fillStyle=p.color||'#38bdf8';
    ctx.font='700 20px Inter, sans-serif';
    ctx.fillText(p.label,px,py-4);

    ctx.fillStyle='#cbd5e1';
    ctx.font='500 13px Inter, sans-serif';
    const shortDesc=(p.desc||'').slice(0,36)+(p.desc&&p.desc.length>36?'…':'');
    ctx.fillText(shortDesc,px,py+22);
  });

  ctx.textAlign='left';
  ctx.fillStyle='rgba(255,255,255,0.4)';
  ctx.font='500 18px Inter, sans-serif';
  ctx.fillText('Saathi study mindmap · '+location.host,80,950,1240);

  const link=document.createElement('a');
  const safeTopic=(data.topic||'mindmap').toLowerCase().replace(/[^a-z0-9]+/g,'-');
  link.download=`saathi-mindmap-${safeTopic}.png`;
  link.href=canvas.toDataURL('image/png');
  link.click();
  toast('Mindmap PNG poster downloaded! 🌟','success');
}

