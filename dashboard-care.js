/* ── Wellbeing space Logic ────────────────────────── */
function scrollHealerTo(id){
  const el=$(id);
  if(el)el.scrollIntoView({behavior:'smooth',block:'start'});
}

function quickSelectSymptom(text){
  $('healerSymptomInput').value=text;
  runHealerConsultation();
}

async function runHealerConsultation(){
  const symptomText=($('healerSymptomInput').value||'').trim();
  if(!symptomText){
    toast('Please describe your symptoms or select a quick topic above.','warning');
    $('healerSymptomInput').focus();
    return;
  }

  const lang=$('healerLanguageSelect').value||'en';
  const btn=$('healerConsultBtn');
  btn.disabled=true;
  btn.textContent='Preparing your guide…';

  try{
    const res=await api('/api/healer/consult',{
      method:'POST',
      body:JSON.stringify({symptoms:symptomText,language:lang})
    });

    if(res.ok&&res.report){
      renderHealerReport(res.report);
      toast('Your preparation guide is ready','success');
    }else{
      toast('Could not prepare your guide. Please try again.','error');
    }
  }catch(err){
    toast(err.message||'Could not connect. Please retry.','error');
  }finally{
    btn.disabled=false;
    btn.textContent='Prepare my next steps';
  }
}

function renderHealerReport(report){
  const out=$('healerResultOutput');out.style.display='block';out.replaceChildren();
  const card=document.createElement('article');card.className='panel wellbeing-result';
  const title=document.createElement('h2');title.textContent=report.comfort_title;
  const intro=document.createElement('p');intro.textContent=report.comfort_message;
  const explanation=document.createElement('p');explanation.textContent=report.body_explanation;
  card.append(title,intro,explanation);
  for(const item of report.home_remedies||[]){
    const section=document.createElement('section'),heading=document.createElement('h3'),text=document.createElement('p');
    heading.textContent=item.title;text.textContent=item.tip;section.append(heading,text);card.append(section);
  }
  for(const text of report.red_flags||[]){const note=document.createElement('p');note.className='consent-note';note.textContent=text;card.append(note)}
  const disclaimer=document.createElement('p');disclaimer.className='helper';disclaimer.textContent=report.doctor_disclaimer;card.append(disclaimer);
  out.append(card);out.scrollIntoView({behavior:'smooth',block:'start'});
}
let breathTimer=null;
let breathState='idle';
let breathPhase='inhale';
let breathCount=4;

function toggleBreathingExercise(){
  const orb=$('zenOrb');
  const phaseLabel=$('zenPhase');
  const counter=$('zenCounter');
  const btn=$('zenToggleBtn');

  if(breathState==='running'){
    clearInterval(breathTimer);
    breathState='idle';
    orb.className='zen-orb';
    phaseLabel.textContent='Paused';
    counter.textContent='—';
    btn.textContent='▶ Resume Breathing';
    return;
  }

  breathState='running';
  btn.textContent='⏸ Pause Breathing';
  runBreathPhase('inhale',4);
}

function runBreathPhase(phase,seconds){
  if(breathState!=='running')return;
  breathPhase=phase;
  breathCount=seconds;

  const orb=$('zenOrb');
  const phaseLabel=$('zenPhase');
  const counter=$('zenCounter');

  if(phase==='inhale'){
    orb.className='zen-orb expand';
    phaseLabel.textContent='Inhale 🌸';
  }else if(phase==='hold'){
    orb.className='zen-orb hold';
    phaseLabel.textContent='Hold 🧘';
  }else if(phase==='exhale'){
    orb.className='zen-orb contract';
    phaseLabel.textContent='Exhale 🍃';
  }

  counter.textContent=breathCount;

  clearInterval(breathTimer);
  breathTimer=setInterval(()=>{
    breathCount--;
    if(breathCount>0){
      counter.textContent=breathCount;
    }else{
      clearInterval(breathTimer);
      if(breathPhase==='inhale'){
        runBreathPhase('exhale',6);
      }else if(breathPhase==='hold'){
        runBreathPhase('exhale',6);
      }else{
        runBreathPhase('inhale',4);
      }
    }
  },1000);
}

/* Synthesized Ambient Audio Generator (Web Audio API) */
let audioCtx=null;
let activeAmbientSound=null;
let activeAmbientNodes=[];

function getAudioContext(){
  if(!audioCtx){
    const AudioContext=window.AudioContext||window.webkitAudioContext;
    audioCtx=new AudioContext();
  }
  if(audioCtx.state==='suspended')audioCtx.resume();
  return audioCtx;
}

function stopAmbientSound(){
  activeAmbientNodes.forEach(node=>{
    try{if(node.stop)node.stop();if(node.disconnect)node.disconnect()}catch(e){}
  });
  activeAmbientNodes=[];
  activeAmbientSound=null;
  document.querySelectorAll('.sound-btn').forEach(b=>b.classList.remove('playing'));
}

function toggleAmbientSound(type){
  if(activeAmbientSound===type){
    stopAmbientSound();
    toast('Ambient sound paused ⏸','info');
    return;
  }

  stopAmbientSound();
  const ctx=getAudioContext();
  activeAmbientSound=type;

  if(type==='om'){
    // Optional soft background tone
    const osc1=ctx.createOscillator();
    const osc2=ctx.createOscillator();
    const gain=ctx.createGain();

    osc1.type='sine';
    osc1.frequency.setValueAtTime(432,ctx.currentTime); // base tone
    osc2.type='sine';
    osc2.frequency.setValueAtTime(216,ctx.currentTime); // lower tone

    gain.gain.setValueAtTime(0.08,ctx.currentTime);

    osc1.connect(gain);
    osc2.connect(gain);
    gain.connect(ctx.destination);

    osc1.start();
    osc2.start();
    activeAmbientNodes=[osc1,osc2,gain];
    $('sndDrone').classList.add('playing');
    toast('Playing Soft tone 🕉️','success');
  }else if(type==='rain'||type==='ocean'){
    // Pink noise synthesis with bandpass filter
    const bufferSize=2*ctx.sampleRate;
    const noiseBuffer=ctx.createBuffer(1,bufferSize,ctx.sampleRate);
    const output=noiseBuffer.getChannelData(0);
    let b0=0,b1=0,b2=0,b3=0,b4=0,b5=0,b6=0;

    for(let i=0;i<bufferSize;i++){
      const white=Math.random()*2-1;
      b0=0.99886*b0+white*0.0555179;
      b1=0.99332*b1+white*0.0750759;
      b2=0.96900*b2+white*0.1538520;
      b3=0.86650*b3+white*0.3104856;
      b4=0.55000*b4+white*0.5329522;
      b5=-0.7616*b5-white*0.0168980;
      output[i]=(b0+b1+b2+b3+b4+b5+b6+white*0.5362)*0.08;
      b6=white*0.115926;
    }

    const whiteNoise=ctx.createBufferSource();
    whiteNoise.buffer=noiseBuffer;
    whiteNoise.loop=true;

    const filter=ctx.createBiquadFilter();
    filter.type=type==='rain'?'lowpass':'bandpass';
    filter.frequency.setValueAtTime(type==='rain'?850:400,ctx.currentTime);

    const gain=ctx.createGain();
    gain.gain.setValueAtTime(0.09,ctx.currentTime);

    whiteNoise.connect(filter);
    filter.connect(gain);
    gain.connect(ctx.destination);

    whiteNoise.start();
    activeAmbientNodes=[whiteNoise,filter,gain];

    if(type==='rain'){
      $('sndRain').classList.add('playing');
      toast('Gentle soothing rain playing 🌧️','success');
    }else{
      $('sndWaves').classList.add('playing');
      toast('Ocean waves playing 🌊','success');
    }
  }
}


window.stopCare=()=>{clearInterval(breathTimer);stopAmbientSound();audioCtx?.close().catch(()=>{})};
