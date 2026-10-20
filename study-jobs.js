(function(){'use strict';
const words={en:['Creating','Ready','Failed','Open result','Retry','Checking study jobs…'],gu:['તૈયાર થાય છે','તૈયાર','નિષ્ફળ','પરિણામ ખોલો','ફરી પ્રયત્ન','અભ્યાસની સ્થિતિ તપાસે છે…'],hi:['बन रहा है','तैयार','असफल','परिणाम खोलें','फिर कोशिश','अध्ययन की स्थिति जाँची जा रही है…']};
function el(tag,text){const n=document.createElement(tag);if(text)n.textContent=text;return n}
async function result(api,kind,id){return api((kind==='mock'?'/api/mock-tests/':'/api/mindmaps/')+id)}
async function readAllowance(kind,api){const data=await api('/api/study-allowance?kind='+kind),a=data.allowance;if(!a||!Number.isInteger(a.remaining)||typeof a.reset_local!=='string')throw Error('Allowance could not be checked. Retry.');return a}
async function allowance(kind,api){const a=await readAllowance(kind,api);if(a.remaining<=0){const c={gu:['બાકી નથી. ફરી ઉપલબ્ધ: ','સાચવેલા પરિણામો ખોલી શકો છો.'],hi:['बाकी नहीं। फिर उपलब्ध: ','सहेजे परिणाम खोल सकते हैं।']}[document.documentElement.lang];throw Error(c?'0 '+(kind==='map'?(document.documentElement.lang==='gu'?'માઇન્ડમેપ ':'माइंडमैप '):(document.documentElement.lang==='gu'?'મોક ટેસ્ટ ':'मॉक टेस्ट '))+c[0]+a.reset_local+'. '+c[1]:'0 '+kind+' generations remaining. Resets '+a.reset_local+'. Existing results remain available.')}return a}
const allowanceWatches=new WeakMap(),pendingCreates=new Map(),activeCreates=new WeakMap();
function showAllowance(box,kind,api,onChange=()=>{}){
 if(!box)return;allowanceWatches.get(box)?.();let sequence=0,disposed=false;
 const lang=document.documentElement.lang,copy=({gu:['મર્યાદા તપાસાય છે…','બાકી','ફરી ઉપલબ્ધ','ફરી તપાસો','માઇન્ડમેપ','મોક ટેસ્ટ'],hi:['सीमा जाँची जा रही है…','बाकी','फिर उपलब्ध','फिर जाँचें','माइंडमैप','मॉक टेस्ट']}[lang])||['Checking allowance…','remaining','Resets','Retry allowance check','mindmap','mock test'];
 box.setAttribute('role','status');
 async function refresh(){const turn=++sequence;onChange(null);box.textContent=copy[0];try{const a=await readAllowance(kind,api);if(disposed||turn!==sequence||!box.isConnected)return;const noun=copy[kind==='map'?4:5]+(lang==='en'&&a.remaining!==1?'s':'');box.textContent=a.remaining+' '+noun+' '+copy[1]+' · '+copy[2]+' '+a.reset_local;onChange(a)}catch(error){if(disposed||turn!==sequence||!box.isConnected)return;onChange(null);box.textContent=window.SaathiI18n?.t(error.message)||error.message;const retry=el('button',copy[3]);retry.type='button';retry.className='secondary';retry.onclick=()=>{retry.disabled=true;refresh()};box.append(retry)}}
 const stop=()=>{disposed=true;window.removeEventListener('saathi-study-job',refresh)};allowanceWatches.set(box,stop);window.addEventListener('saathi-study-job',refresh);refresh();return stop
}
function samePayload(a,b){return JSON.stringify(Object.entries(a).filter(([key])=>key!=='job_id').sort())===JSON.stringify(Object.entries(b).sort())}
function create(kind,payload,api,onStart=()=>{}){
 let active=activeCreates.get(api);if(!active){active=new Map();activeCreates.set(api,active)}
 const snapshot=JSON.parse(JSON.stringify(payload)),key=kind+JSON.stringify(Object.entries(snapshot).sort());
 if(active.has(key)){onStart('waiting');return active.get(key)}
 const work=runCreate(kind,snapshot,api,onStart);active.set(key,work);
 const release=()=>{if(active.get(key)===work)active.delete(key)};work.then(release,release);
 return work;
}
async function runCreate(kind,payload,api,onStart){
 const key=kind+JSON.stringify(Object.entries(payload).sort()),recovery=window.SaathiRecovery,stored=recovery?.getDraft('study-job',kind)?.request;
 let refreshTimer,request=pendingCreates.get(key)||(stored&&samePayload(stored,payload)?stored:null);
 const changed=()=>window.dispatchEvent(new Event('saathi-study-job'));
 const forget=()=>{pendingCreates.delete(key);recovery?.removeDraft('study-job',kind)};
 const lookup=async()=>{const data=await api('/api/study-jobs?kind='+kind+'&job_id='+encodeURIComponent(request.job_id));return data.jobs.find(job=>job.id===request.job_id)};
 const completed=async job=>{if(job?.status==='ready'){const saved=await result(api,kind,job.result_id);forget();return saved}if(job?.status==='failed'){forget();throw Error(job.error||'Creation failed. Retry when ready.')}return null};
 try{
  let job=request?await lookup():null;
  if(job?.status==='ready')return await completed(job);
  if(job?.status==='failed'){forget();request=null;job=null}
  if(!job){await allowance(kind,api);request=request||{...payload,job_id:crypto.randomUUID()};pendingCreates.set(key,request);recovery?.saveDraft('study-job',kind,{request});onStart('generating');refreshTimer=setTimeout(changed,500);const response=await api(kind==='mock'?'/api/mock-tests/generate':'/api/mindmaps/generate',{method:'POST',body:JSON.stringify(request)});if(!response.job){forget();return response}job=response.job}else onStart('waiting');
  for(let n=0;n<150;n++){const saved=await completed(job);if(saved)return saved;await new Promise(resolve=>setTimeout(resolve,2000));job=await lookup()}
  throw Error('Creation is still pending. Reopen this tool to check its status.')
 }catch(error){if(request){try{const job=await lookup();if(job?.status==='ready')return await completed(job);if(job?.status==='failed')forget()}catch(_){}}throw error}
 finally{clearTimeout(refreshTimer);changed()}
}

function render(box,{kind,api,open,retry,visible=()=>true}){const c=words[document.documentElement.lang]||words.en;box.setAttribute('aria-live','polite');box.textContent=c[5];let timer;
async function refresh(){if(!box.isConnected){window.removeEventListener('saathi-study-job',changed);clearTimeout(timer);return;}try{const data=await api('/api/study-jobs?kind='+kind);if(!box.isConnected)return;box.replaceChildren();for(const job of data.jobs.filter(visible)){const card=el('article');card.className='item';card.append(el('strong',job.request.topic),el('p',c[{creating:0,ready:1,failed:2}[job.status]]));if(job.error)card.append(el('p',window.SaathiI18n?.t(job.error)||job.error));if(job.status!=='creating'){const b=el('button',c[job.status==='ready'?3:4]);b.type='button';b.className='secondary';b.onclick=async()=>{b.disabled=true;try{if(job.status==='ready')await open(await result(api,kind,job.result_id),job);else await retry(job.request)}catch(error){card.append(el('p',error.message))}finally{b.disabled=false}};card.append(b)}box.append(card)}if(data.jobs.some(job=>job.status==='creating'))timer=setTimeout(refresh,2000)}catch(error){box.textContent=error.message;const b=el('button',c[4]);b.type='button';b.onclick=refresh;box.append(b)}}
function changed(){clearTimeout(timer);refresh()}window.addEventListener('saathi-study-job',changed);refresh();return ()=>{clearTimeout(timer);window.removeEventListener('saathi-study-job',changed)}}
window.SaathiJobs={create,render,allowance,showAllowance};
})();
