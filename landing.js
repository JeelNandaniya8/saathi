/* Small illustrative previews: no recordings, requests or tracking. */
(() => {
  const copy = {
    en: {start:'Start free →',demo:'Try Live Chat',join:'Join Waitlist',title:'Join the waitlist',email:'Email',close:'Close',privacy:'We store your email only to let you know when this plan is ready. No payment is taken.',success:'You’re on the list. We’ll email you when the plan is ready.',error:'We couldn’t save your email. Please try again.',busy:'Saving…',limit:'Please try again in an hour.',preview:'Illustrative preview',labels:['Question 2 · 04:59','One topic, clear connections','A gentle breathing break','Your notes stay private','Share by choice','Page → summary → practice','Review · choose · remove']},
    gu: {start:'મફતમાં શરૂ કરો →',demo:'લાઇવ ચેટ અજમાવો',join:'પ્રતીક્ષા યાદીમાં જોડાઓ',title:'પ્રતીક્ષા યાદીમાં જોડાઓ',email:'ઈમેલ',close:'બંધ કરો',privacy:'આ પ્લાન તૈયાર થાય ત્યારે જણાવવા માટે જ તમારો ઈમેલ સાચવીએ છીએ. કોઈ ચુકવણી લેવામાં આવતી નથી.',success:'તમે યાદીમાં જોડાઈ ગયા છો. પ્લાન તૈયાર થશે ત્યારે ઈમેલ કરીશું.',error:'ઈમેલ સાચવી શકાયો નહીં. ફરી પ્રયાસ કરો.',busy:'સાચવી રહ્યા છીએ…',limit:'એક કલાક પછી ફરી પ્રયાસ કરો.',preview:'ઉદાહરણરૂપ ઝલક',labels:['પ્રશ્ન ૨ · ૦૪:૫૯','એક વિષય, સ્પષ્ટ જોડાણો','શાંતિથી શ્વાસ લો','તમારી નોંધો ખાનગી રહે છે','તમારી પસંદગીથી શેર કરો','પાનું → સારાંશ → અભ્યાસ','જુઓ · પસંદ કરો · દૂર કરો']},
    hi: {start:'मुफ़्त शुरू करें →',demo:'लाइव चैट आज़माएं',join:'प्रतीक्षा सूची में जुड़ें',title:'प्रतीक्षा सूची में जुड़ें',email:'ईमेल',close:'बंद करें',privacy:'प्लान तैयार होने पर बताने के लिए ही आपका ईमेल सहेजते हैं। कोई भुगतान नहीं लिया जाता।',success:'आप सूची में जुड़ गए हैं। प्लान तैयार होने पर ईमेल करेंगे।',error:'ईमेल सहेजा नहीं जा सका। फिर कोशिश करें।',busy:'सहेज रहे हैं…',limit:'एक घंटे बाद फिर कोशिश करें।',preview:'उदाहरण की झलक',labels:['प्रश्न २ · ०४:५९','एक विषय, स्पष्ट संबंध','सुकून से सांस लें','आपके नोट्स निजी रहते हैं','अपनी इच्छा से साझा करें','पन्ना → सारांश → अभ्यास','देखें · चुनें · हटाएं']}
  };
  let lang='en',plan='plus',busy=false,metadata={"en":{"title":"Saathi · A calmer way to study","description":"Study with PDFs and photos, practise with AI mock exams, organise notes and build gentle routines. Saathi brings clarity daily in English, Gujarati and Hindi.","locale":"en_IN"},"gu":{"title":"સાથી · શાંતિથી અભ્યાસ કરો","description":"સાથી સાથે PDF અને ફોટામાંથી શીખો, AI મોક પરીક્ષાથી અભ્યાસ કરો, ખાનગી નોંધો સાચવો અને રોજની દિનચર્યા ગોઠવો. અંગ્રેજી, ગુજરાતી અને હિન્દીમાં તમારા અભ્યાસનો સરળ સાથી.","locale":"gu_IN"},"hi":{"title":"साथी · सुकून से पढ़ाई करें","description":"साथी के साथ PDF और फ़ोटो से सीखें, AI मॉक परीक्षा से अभ्यास करें, निजी नोट्स सहेजें और दिनचर्या बनाएं। अंग्रेज़ी, गुजराती और हिन्दी में पढ़ाई का आपका सहज साथी।","locale":"hi_IN"}};
  const dialog=document.getElementById('waitlistDialog'),form=document.getElementById('waitlistForm'),status=document.getElementById('waitlistStatus'),submit=document.getElementById('waitlistSubmit');
  const diagrams=[
    '<b>02 / 10</b><div class="demo-options"><i></i><i></i><i></i></div>',
    '<div class="demo-map"><b>●</b><span>┌────┴────┐</span><div>○　　　○</div></div>',
    '<div class="demo-breath">○</div>',
    '<div class="demo-paper"><i></i><i></i><i></i><b>✓</b></div>',
    '<div class="demo-share">○ <span>→</span> ○</div>',
    '<div class="demo-paper"><b>∑</b><i></i><i></i><i></i></div>',
    '<div class="demo-options"><i></i><i></i><i></i></div>'
  ];
  document.querySelectorAll('.feature').forEach((card,index)=>{
    const visual=document.createElement('figure');visual.className='feature-demo';
    visual.innerHTML='<div class="demo-scene" aria-hidden="true">'+diagrams[index]+'</div><figcaption><span></span><small></small></figcaption>';
    card.querySelector('h3').before(visual);
  });
  const observer=new IntersectionObserver(entries=>entries.forEach(entry=>entry.target.classList.toggle('playing',entry.isIntersecting&&!document.hidden)));
  document.querySelectorAll('.feature-demo').forEach(el=>observer.observe(el));
  document.addEventListener('visibilitychange',()=>{document.querySelectorAll('.feature-demo').forEach(el=>{if(document.hidden)el.classList.remove('playing');else{observer.unobserve(el);observer.observe(el)}})});
  function update(value){
    lang=copy[value]?value:'en';const c=copy[lang];document.documentElement.lang=lang;
    document.getElementById('heroCta').textContent=c.start;
    document.getElementById('heroDemo').textContent=c.demo;
    document.querySelectorAll('[data-waitlist]').forEach(el=>el.textContent=c.join);
    document.getElementById('waitlistTitle').textContent=c.title+' · Saathi '+(plan==='plus'?'Plus':'Family');
    document.getElementById('waitlistLabel').textContent=c.email;
    document.getElementById('waitlistClose').setAttribute('aria-label',c.close);
    document.getElementById('waitlistPrivacy').textContent=c.privacy;
    submit.textContent=busy?c.busy:c.join;
    document.querySelectorAll('.feature-demo').forEach((el,index)=>{el.querySelector('figcaption span').textContent=c.labels[index];el.querySelector('small').textContent=c.preview;});
    const url=new URL(location.href);url.searchParams.set('lang',lang);history.replaceState(null,'',url);
    if(metadata){const m=metadata[lang];document.title=m.title;document.querySelector('meta[name="description"]').content=m.description;for(const key of ['title','description','locale'])document.querySelector(`meta[property="og:${key}"]`).content=m[key];document.querySelector('meta[property="og:url"]').content=url.origin+'/?lang='+lang;document.querySelector('link[rel="canonical"]').href=url.origin+'/?lang='+lang;}
  }
  window.updateLandingLanguage=update;
  update(document.documentElement.lang==='en'?(new URLSearchParams(location.search).get('lang')||localStorage.getItem('saathi-language')||'en'):document.documentElement.lang);

  document.querySelectorAll('[data-waitlist]').forEach(button=>button.addEventListener('click',()=>{if(busy)return;plan=button.dataset.waitlist;form.reset();status.textContent='';update(lang);dialog.showModal();document.getElementById('waitlistEmail').focus();}));
  document.getElementById('waitlistClose').addEventListener('click',()=>dialog.close());
  form.addEventListener('submit',async event=>{
    event.preventDefault();if(busy)return;busy=true;submit.disabled=true;update(lang);status.textContent='';
    const payload={email:form.email.value.trim(),plan,language:lang};
    const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),20000);
    try{
      const sessionResponse=await fetch('/api/me',{signal:controller.signal});
      if(!sessionResponse.ok)throw Error();
      const session=await sessionResponse.json();
      const response=await fetch('/api/waitlist',{method:'POST',signal:controller.signal,headers:{'Content-Type':'application/json','X-CSRF-Token':session.csrf_token||''},body:JSON.stringify(payload)});
      if(!response.ok){status.textContent=response.status===429?copy[lang].limit:copy[lang].error;return;}
      status.textContent=copy[lang].success;form.reset();
    }catch(_){status.textContent=copy[lang].error;}finally{clearTimeout(timer);busy=false;submit.disabled=false;update(lang);}
  });
})();

