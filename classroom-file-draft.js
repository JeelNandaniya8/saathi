/* A Google-selected file becomes an ordinary, reviewable Chat attachment. */
(function(root){
'use strict';
const copy={
 title:['Classroom file','Classroom ફાઇલ','Classroom फ़ाइल'],
 review:['Review the selected file before sending. Nothing has been sent to AI. Your usual upload allowance applies when you send.','મોકલતાં પહેલાં પસંદ કરેલી ફાઇલ તપાસો. AIને કંઈ મોકલ્યું નથી. Send પર તમારી સામાન્ય upload મર્યાદા લાગુ પડે છે.','भेजने से पहले चुनी फ़ाइल देखें। AI को कुछ नहीं भेजा गया है। Send पर आपकी सामान्य अपलोड सीमा लागू होगी।'],
 attach:['Attach selected file','પસંદ કરેલી ફાઇલ જોડો','चुनी फ़ाइल जोड़ें'],
 cancel:['Cancel download','ડાઉનલોડ રદ કરો','डाउनलोड रोकें'],
 close:['Dismiss','બંધ કરો','बंद करें'],
 loading:['Preparing your file…','ફાઇલ તૈયાર થાય છે…','फ़ाइल तैयार हो रही है…'],
 done:['File attached. Review your message, then press Send.','ફાઇલ જોડાઈ. સંદેશ તપાસીને Send દબાવો.','फ़ाइल जुड़ गई। संदेश जाँचकर Send दबाएँ।'],
 changed:['Your draft or chat changed. Nothing was replaced. Review it before attaching again.','Draft અથવા Chat બદલાયું. કંઈ બદલ્યું નથી. ફરી જોડતાં પહેલાં તપાસો.','ड्राफ़्ट या चैट बदली है। कुछ बदला नहीं गया। फिर जोड़ने से पहले जाँचें।'],
 busy:['Finish the current reply or file selection first. Your draft is kept.','પહેલાં હાલનો જવાબ અથવા ફાઇલ પસંદગી પૂરી કરો. Draft રાખ્યો છે.','पहले मौजूदा जवाब या फ़ाइल चयन पूरा करें। ड्राफ़्ट सुरक्षित है।'],
 quota:['Upload allowance is unavailable or exhausted. Check Uploads before attaching.','Upload મર્યાદા ઉપલબ્ધ નથી અથવા પૂરી થઈ. જોડતાં પહેલાં Uploads તપાસો.','अपलोड सीमा उपलब्ध नहीं है या पूरी हो गई। जोड़ने से पहले Uploads देखें।'],
 mismatch:['This file does not match the attachment in your recovered draft. That draft is kept.','આ ફાઇલ recovered draftની ફાઇલ સાથે મળતી નથી. Draft રાખ્યો છે.','यह फ़ाइल बहाल ड्राफ़्ट के अटैचमेंट से मेल नहीं खाती। ड्राफ़्ट सुरक्षित है।'],
 file_expired:['File permission expired. Return to Study → Google Classroom and select the file again.','ફાઇલની મંજૂરી પૂરી થઈ. Study → Google Classroomમાં ફરી ફાઇલ પસંદ કરો.','फ़ाइल की अनुमति समाप्त हुई। Study → Google Classroom में फिर फ़ाइल चुनें।'],
 file_changed:['The file or course selection changed. Your draft is kept; select the file again.','ફાઇલ અથવા courseની પસંદગી બદલાઈ. Draft રાખ્યો છે; ફરી ફાઇલ પસંદ કરો.','फ़ाइल या पाठ्यक्रम चयन बदला। ड्राफ़्ट सुरक्षित है; फिर फ़ाइल चुनें।'],
 file_permission:['Google did not allow this file to be read. Check access in the original assignment.','Googleએ આ ફાઇલ વાંચવાની મંજૂરી આપી નથી. મૂળ અસાઇનમેન્ટમાં access તપાસો.','Google ने यह फ़ाइल पढ़ने की अनुमति नहीं दी। मूल असाइनमेंट में पहुँच जाँचें।'],
 file_type:['Use a PDF, PNG, JPG, WebP, or a Google document exported as PDF.','PDF, PNG, JPG, WebP અથવા PDFમાં બદલેલો Google દસ્તાવેજ વાપરો.','PDF, PNG, JPG, WebP या PDF में बदला Google दस्तावेज़ इस्तेमाल करें।'],
 file_size:['This file exceeds the 5 MB upload limit. Your draft is kept.','આ ફાઇલ 5 MB upload મર્યાદા કરતાં મોટી છે. Draft રાખ્યો છે.','यह फ़ाइल 5 MB अपलोड सीमा से बड़ी है। ड्राफ़्ट सुरक्षित है।'],
 file_empty:['The selected file is empty. Your draft is kept.','પસંદ કરેલી ફાઇલ ખાલી છે. Draft રાખ્યો છે.','चुनी फ़ाइल खाली है। ड्राफ़्ट सुरक्षित है।'],
 failed:['Could not prepare this file. Your draft is kept. Retry here or attach it manually.','ફાઇલ તૈયાર થઈ નથી. Draft રાખ્યો છે. અહીં ફરી પ્રયાસ કરો અથવા જાતે ફાઇલ જોડો.','फ़ाइल तैयार नहीं हुई। ड्राफ़्ट सुरक्षित है। फिर कोशिश करें या फ़ाइल खुद जोड़ें।'],
 prompt:['Explain what I need to do in this assignment. Use only this file and cite its pages.','આ અસાઇનમેન્ટમાં શું કરવાનું છે તે સમજાવો. ફક્ત આ ફાઇલ વાપરો અને તેના પાનાં જણાવો.','इस असाइनमेंट में क्या करना है समझाएँ। केवल इस फ़ाइल का उपयोग करें और उसके पन्ने बताएँ।']
};
function t(key){const lang=root.document?.documentElement.lang,index=lang==='gu'?1:lang==='hi'?2:0;return(copy[key]||copy.failed)[index]}
function fingerprint(value){return JSON.stringify([value.id,value.text,value.mode,value.fileOnly,value.requestId,value.missing,value.files])}
function eligible(value){return value.ready&&value.id&&!value.busy&&!value.files.length&&value.allowance?.enabled===true&&Number.isFinite(value.allowance.remaining_today)&&value.allowance.remaining_today>0}
function matches(file,manifest){return Array.isArray(manifest)&&manifest.length===1&&['name','size','type','lastModified'].every(k=>manifest[0][k]===file[k])}
function connect(adapter){
 const id=new URL(root.location.href).searchParams.get('classroom_file');
 if(!id||!/^[a-f0-9-]{36}$/.test(id))return;
 const panel=document.createElement('section'),title=document.createElement('strong'),detail=document.createElement('p'),status=document.createElement('p'),attach=document.createElement('button'),dismiss=document.createElement('button');
 panel.className='classroom-file-review';panel.setAttribute('aria-label',t('title'));title.textContent=t('title');detail.textContent=t('review');status.setAttribute('role','status');status.setAttribute('aria-live','polite');
 attach.type=dismiss.type='button';attach.className=dismiss.className='message-tool';attach.textContent=t('attach');dismiss.textContent=t('close');
 panel.append(title,detail,status,attach,dismiss);adapter.host.before(panel);
 let controller=null,disposed=false;
 function close(){disposed=true;controller?.abort();panel.remove();const url=new URL(root.location.href);if(url.searchParams.get('classroom_file')===id){url.searchParams.delete('classroom_file');root.history.replaceState(root.history.state,'',url.pathname+url.search+url.hash)}}
 dismiss.addEventListener('click',close);
 attach.addEventListener('click',async()=>{
  if(controller){controller.abort();return}
  const initial=adapter.snapshot();
  if(!eligible(initial)){status.textContent=t(initial.busy||initial.files.length?'busy':'quota');return}
  const before=fingerprint(initial);controller=new AbortController();attach.textContent=t('cancel');panel.setAttribute('aria-busy','true');status.textContent=t('loading');
  try{
   const response=await root.fetch('/api/classroom/files/'+id+'/download',{credentials:'same-origin',cache:'no-store',signal:controller.signal});
   if(!response.ok){let result={};try{result=await response.json()}catch(_){}throw new Error(result.error_code||'failed')}
   const blob=await response.blob(),name=decodeURIComponent(response.headers.get('X-Saathi-File-Name')||''),modified=Number(response.headers.get('X-Saathi-File-Modified'));
   if(!name||!Number.isFinite(modified)||!blob.size||blob.size>5242880)throw new Error('file_size');
   const file=new File([blob],name,{type:blob.type,lastModified:modified}),now=adapter.snapshot();
   if(disposed||controller.signal.aborted)return;
   if(fingerprint(now)!==before||!eligible(now))throw new Error('changed');
   if(now.missing&&!matches(file,now.manifest))throw new Error('mismatch');
   if(!adapter.attach(file,now.missing?t('done'):t('prompt')))throw new Error('failed');
   adapter.notify(t('done'));close();
  }catch(error){if(!disposed)status.textContent=error.name==='AbortError'?'':t(Object.hasOwn(copy,error.message)?error.message:'failed')}
  finally{controller=null;if(!disposed){attach.textContent=t('attach');panel.removeAttribute('aria-busy')}}
 });
}
root.SaathiClassroomFile={connect,fingerprint,eligible,matches};
})(typeof window==='undefined'?globalThis:window);
