function renderMockTestHistory(){
  const box=$('mockTestHistoryList');
  if(!box)return;
  box.replaceChildren();
  if(!state.mockTests||!state.mockTests.length){
    box.append(emptyNode('No tests completed yet. Start your first mock test above!'));
    return;
  }
  state.mockTests.forEach(test=>{
    const card=document.createElement('article');
    card.className='item';
    const icon=document.createElement('div');
    icon.className='avatar';
    icon.style.cssText='width:36px;height:36px;border-radius:10px;font-size:16px;background:var(--accent-soft);color:var(--accent)';
    icon.textContent='◈';
    const copy=document.createElement('div');
    copy.className='item-copy';
    const title=document.createElement('b');
    title.textContent=test.topic;
    const diffBadge=document.createElement('span');
    diffBadge.className='priority '+test.difficulty;
    diffBadge.textContent=test.difficulty;
    title.append(diffBadge);
    const sub=document.createElement('p');
    const scoreStr=test.best_score!=null?`Best: ${test.best_score}/${test.question_count} (${test.best_accuracy}%)`:'Not attempted yet';
    sub.textContent=`${test.question_count} Questions · ${test.time_limit_minutes} mins · ${scoreStr}`;
    const date=document.createElement('small');
    date.textContent=`Created ${formatDate(test.created_at)}`;
    copy.append(title,sub,date);
    const actions=document.createElement('div');
    actions.className='item-actions';
    const launchBtn=document.createElement('button');
    launchBtn.className='mini-button';
    launchBtn.type='button';
    launchBtn.textContent='Practice Again';
    launchBtn.onclick=()=>quickStartFromHistory(test);
    actions.append(launchBtn);
    card.append(icon,copy,actions);
    box.append(card);
  });
}

async function quickStartFromHistory(test){
  try{
    const response=await api('/api/mock-tests/'+test.id);
    state.activeTest=response.test;state.activeTestAnswers={};state.activeTestFlags=new Set();state.activeTestIndex=0;
    if(response.result){state.lastAttemptResult=response.result;renderTestResults(response.result);return}
    const remaining=Math.ceil((new Date(response.test.expires_at).getTime()-Date.now())/1000);
    if(remaining<=0){$('testTopic').value=test.topic;toast('This test has ended. Generate a new practice test when ready.');return}
    state.testTotalSeconds=response.test.time_limit_minutes*60;state.testSecondsLeft=remaining;
    $('mockTestCreatorBox').style.display='none';$('mockTestResultsBox').style.display='none';$('mockTestRunnerBox').style.display='block';
    $('runnerTopicTitle').textContent=test.topic;startTestTimer();renderQuestion(0);
  }catch(error){toast(error.message,'error')}
}

async function generateMockTest(event){
  if(event)event.preventDefault();
  const btn=$('testSubmitBtn');
  btn.disabled=true;
  const originalText=btn.textContent;
  btn.textContent='Generating exam with AI... ⏳';
  const payload={
    topic:$('testTopic').value.trim(),
    question_count:parseInt($('testCount').value,10)||10,
    difficulty:$('testDifficulty').value||'medium',
    time_limit_minutes:parseInt($('testTimeLimit').value,10)||10,
    language:$('testLanguage').value||'en'
  };
  try{
    const res=await api('/api/mock-tests/generate',{method:'POST',body:JSON.stringify(payload)});
    state.activeTest=res.test;
    state.activeTest.questions=res.test.questions||[];
    if(!state.activeTest.questions.length)throw new Error('This test has no questions. Please retry.');
    state.activeTestAnswers={};
    state.activeTestFlags=new Set();
    state.activeTestIndex=0;
    state.testTotalSeconds=(res.test.time_limit_minutes||10)*60;
    state.testSecondsLeft=state.testTotalSeconds;
    
    // Switch to runner UI
    $('mockTestCreatorBox').style.display='none';
    $('mockTestResultsBox').style.display='none';
    $('mockTestRunnerBox').style.display='block';
    
    $('runnerTopicTitle').textContent=res.test.topic;
    $('runnerDifficultyBadge').textContent=(res.test.difficulty||'Medium').toUpperCase()+' · '+res.test.question_count+' QUESTIONS';
    
    startTestTimer();
    renderQuestion(0);
    toast('Mock test ready. You can begin.','success');
  }catch(error){
    if(error.message&&error.message.includes('Saathi Plus')){
      openUpgradeModal();
    }
    toast(error.message,'error');
  }finally{
    btn.disabled=false;
    btn.textContent=originalText;
  }
}

function startTestTimer(){
  clearInterval(state.testTimerInterval);
  updateTimerDisplay();
  state.testTimerInterval=setInterval(()=>{
    state.testSecondsLeft=Math.max(0,Math.ceil((new Date(state.activeTest.expires_at).getTime()-Date.now())/1000));
    updateTimerDisplay();
    if(state.testSecondsLeft<=0){
      clearInterval(state.testTimerInterval);
      toast('Time is up! Submitting your exam automatically...','warning');
      submitMockTest(true);
    }
  },1000);
}

function updateTimerDisplay(){
  const mins=Math.floor(state.testSecondsLeft/60);
  const secs=state.testSecondsLeft%60;
  const display=$('runnerTimerDisplay');
  if(!display)return;
  display.textContent=`⏱️ ${String(mins).padStart(2,'0')}:${String(secs).padStart(2,'0')}`;
  if(state.testSecondsLeft<=120){
    display.classList.add('urgent');
  }else{
    display.classList.remove('urgent');
  }
}

function renderQuestion(index){
  const questions=state.activeTest?.questions||[];
  if(!questions.length)return;
  if(index<0)index=0;
  if(index>=questions.length)index=questions.length-1;
  state.activeTestIndex=index;
  const q=questions[index];
  const qId=q.id||(index+1);
  
  $('qNumberDisplay').textContent=`Question ${index+1} of ${questions.length}`;
  $('qTextDisplay').textContent=q.question;
  
  const isFlagged=state.activeTestFlags.has(qId);
  const flagBtn=$('qFlagBtn');
  flagBtn.textContent=isFlagged?'🚩 Flagged for review':'⚐ Mark for review';
  flagBtn.style.color=isFlagged?'var(--gold)':'var(--muted)';
  
  const optionsWrap=$('qOptionsWrap');
  optionsWrap.replaceChildren();
  const letters=['A','B','C','D'];
  const currentAnswer=state.activeTestAnswers[qId];
  
  letters.forEach(letter=>{
    const optText=q.options?.[letter]||'';
    const optBtn=document.createElement('button');
    optBtn.className='option-btn'+(currentAnswer===letter?' selected':'');
    optBtn.type='button';
    const badge=document.createElement('span');
    badge.className='option-badge';
    badge.textContent=letter;
    const textSpan=document.createElement('span');
    textSpan.textContent=optText;
    optBtn.append(badge,textSpan);
    optBtn.onclick=()=>selectOption(qId,letter);
    optionsWrap.append(optBtn);
  });
  
  $('qPrevBtn').disabled=index===0;
  $('qNextBtn').textContent=index===questions.length-1?'Submit Test →':'Next →';
  $('qStatusHelper').textContent=currentAnswer?`Selected option ${currentAnswer}`:'Not answered yet';
  
  renderPalette();
}

function selectOption(qId,letter){
  state.activeTestAnswers[qId]=letter;
  renderQuestion(state.activeTestIndex);
}

function toggleFlagCurrentQuestion(){
  const q=state.activeTest?.questions?.[state.activeTestIndex];
  if(!q)return;
  const qId=q.id||(state.activeTestIndex+1);
  if(state.activeTestFlags.has(qId)){
    state.activeTestFlags.delete(qId);
  }else{
    state.activeTestFlags.add(qId);
  }
  renderQuestion(state.activeTestIndex);
}

function navQuestion(delta){
  const questions=state.activeTest?.questions||[];
  const target=state.activeTestIndex+delta;
  if(target>=questions.length){
    confirmSubmitTest();
  }else{
    renderQuestion(target);
  }
}

function renderPalette(){
  const questions=state.activeTest?.questions||[];
  const grid=$('paletteGrid');
  if(!grid)return;
  grid.replaceChildren();
  
  let answeredCount=0;
  questions.forEach((q,idx)=>{
    const qId=q.id||(idx+1);
    const isAnswered=!!state.activeTestAnswers[qId];
    if(isAnswered)answeredCount++;
    const isCurrent=idx===state.activeTestIndex;
    const isFlagged=state.activeTestFlags.has(qId);
    
    const btn=document.createElement('button');
    btn.className='pal-btn'+(isCurrent?' current':'')+(isAnswered?' answered':'')+(isFlagged?' flagged':'');
    btn.type='button';
    btn.textContent=String(idx+1);
    btn.onclick=()=>renderQuestion(idx);
    grid.append(btn);
  });
  
  if($('paletteAnsweredCount'))$('paletteAnsweredCount').textContent=`${answeredCount}/${questions.length} Answered`;
}

async function confirmSubmitTest(){
  const questions=state.activeTest?.questions||[];
  const total=questions.length;
  const answered=Object.keys(state.activeTestAnswers).length;
  const unanswered=total-answered;
  
  let message=`You have answered ${answered} of ${total} questions.`;
  if(unanswered>0){
    message+=` ${unanswered} question(s) remain unanswered. Are you sure you want to finish and submit now?`;
  }else{
    message+=` Are you ready to finish and submit your exam?`;
  }
  const confirmed=await confirmAction({
    title:'Submit Mock Test?',
    message:message,
    confirmLabel:'Submit Exam',
    tone:unanswered>0?'warning':'danger'
  });
  if(confirmed){
    submitMockTest(false);
  }
}

async function submitMockTest(isTimeout=false){
  clearInterval(state.testTimerInterval);
  const testId=state.activeTest?.id;
  if(!testId)return;
  
  const timeSpent=Math.max(1,state.testTotalSeconds-state.testSecondsLeft);
  const submitBtn=$('runnerSubmitBtn');
  if(submitBtn)submitBtn.disabled=true;
  
  try{
    const res=await api(`/api/mock-tests/${testId}/submit`,{
      method:'POST',
      body:JSON.stringify({
        answers:state.activeTestAnswers,
        time_taken_seconds:timeSpent
      })
    });
    
    state.lastAttemptResult=res;
    renderTestResults(res);
    playChime();
    blastConfetti();
    toast('Test evaluated successfully! 🎉','success');
    
    // Refresh history in background
    api('/api/mock-tests/history').then(data=>{
      state.mockTests=data.tests||[];
      renderMockTestHistory();
    }).catch(()=>{});
  }catch(error){
    toast(error.message,'error');
  }finally{
    if(submitBtn)submitBtn.disabled=false;
  }
}

function renderTestResults(data){
  const attempt=data.attempt;
  const review=data.review||[];
  const test=state.activeTest;
  
  $('mockTestRunnerBox').style.display='none';
  $('mockTestCreatorBox').style.display='none';
  $('mockTestResultsBox').style.display='block';
  
  $('resScoreNum').textContent=`${attempt.score}/${attempt.total_questions}`;
  $('resScorePct').textContent=`${attempt.accuracy_percentage}%`;
  
  const pct=attempt.accuracy_percentage;
  let title='Great Work! 🎉';
  if(pct>=90)title='Outstanding Mastery! 🏆🌟';
  else if(pct>=70)title='Solid Performance! 👏';
  else if(pct<50)title='Keep Practicing! 💪';
  $('resHeroTitle').textContent=title;
  
  const mins=Math.floor(attempt.time_spent_seconds/60);
  const secs=attempt.time_spent_seconds%60;
  const timeStr=`${mins}m ${secs}s`;
  $('resHeroSub').textContent=`You completed the test in ${timeStr} with ${attempt.accuracy_percentage}% accuracy.`;
  
  // Update scorecard preview
  $('previewCandidateName').textContent=$('scorecardIncludeName')?.checked?(state.user?.name||'Student'):'My study session';
  $('previewTopicName').textContent=test?.topic||'Mock Test';
  $('previewScoreNum').textContent=`${attempt.score} / ${attempt.total_questions}`;
  $('previewScorePct').textContent=`(${attempt.accuracy_percentage}% Accuracy)`;
  $('previewMetaRow').innerHTML=`<span>⏱️ Time: ${timeStr}</span><span>📅 ${new Date().toLocaleDateString()}</span><span>⚡ Level: ${escapeText(test?.difficulty||'Medium')}</span>`;
  
  // Render review questions
  const list=$('reviewQuestionsList');
  list.replaceChildren();
  
  review.forEach((item,idx)=>{
    const card=document.createElement('div');
    card.className='review-item';
    
    const head=document.createElement('div');
    head.style.cssText='display:flex;align-items:center;justify-content:space-between;margin-bottom:10px';
    
    const qNum=document.createElement('strong');
    qNum.style.fontSize='13px';
    qNum.textContent=`Question ${idx+1}`;
    
    const pill=document.createElement('span');
    let pillClass='unattempted';
    let pillText='Not Attempted';
    if(item.is_correct){
      pillClass='correct';
      pillText='✓ Correct (+1)';
    }else if(item.user_answer){
      pillClass='wrong';
      pillText='× Incorrect';
    }
    pill.className=`review-status-pill ${pillClass}`;
    pill.textContent=pillText;
    head.append(qNum,pill);
    
    const qPrompt=document.createElement('p');
    qPrompt.style.cssText='font-size:15px;font-weight:600;margin:0 0 14px;color:var(--ink)';
    qPrompt.textContent=item.question;
    
    const answersRow=document.createElement('div');
    answersRow.style.cssText='display:flex;gap:18px;font-size:13px;flex-wrap:wrap;margin-bottom:12px';
    
    const userAns=document.createElement('div');
    userAns.innerHTML=`<span style="color:var(--muted)">Your Answer:</span> <strong style="color:${item.is_correct?'var(--sage)':'var(--danger)'}">${escapeText(item.user_answer||'None')} (${escapeText(item.options?.[item.user_answer]||'Unanswered')})</strong>`;
    
    const correctAns=document.createElement('div');
    correctAns.innerHTML=`<span style="color:var(--muted)">Correct Answer:</span> <strong style="color:var(--sage)">${escapeText(item.correct_answer)} (${escapeText(item.options?.[item.correct_answer]||'')})</strong>`;
    answersRow.append(userAns,correctAns);
    
    const expBox=document.createElement('div');
    expBox.className='review-explanation';
    expBox.innerHTML=`<strong>💡 Detailed Explanation:</strong><p style="margin:6px 0 0">${escapeText(item.explanation||'Review this topic carefully.')}</p>`;
    
    card.append(head,qPrompt,answersRow,expBox);
    list.append(card);
  });
  
  // Render canvas scorecard
  generateScorecardCanvas(data);
}

function generateScorecardCanvas(data){
  const canvas=$('scorecardCanvas');
  if(!canvas)return;
  const ctx=canvas.getContext('2d');
  const width=1080;
  const height=1350;
  
  const attempt=data.attempt;
  const test=state.activeTest;
  const userName=$('scorecardIncludeName')?.checked?(state.user?.name||'Student'):'My study session';
  const topic=test?.topic||'General Subject Exam';
  const mins=Math.floor(attempt.time_spent_seconds/60);
  const secs=attempt.time_spent_seconds%60;
  const timeStr=`${mins}m ${secs}s`;
  
  // 1. Background Gradient
  const bgGrad=ctx.createLinearGradient(0,0,width,height);
  bgGrad.addColorStop(0,'#0e1420');
  bgGrad.addColorStop(0.5,'#182338');
  bgGrad.addColorStop(1,'#2c1f0d');
  ctx.fillStyle=bgGrad;
  ctx.fillRect(0,0,width,height);
  
  // 2. Ambient glows
  const glow1=ctx.createRadialGradient(900,200,50,900,200,600);
  glow1.addColorStop(0,'rgba(218,174,74,0.22)');
  glow1.addColorStop(1,'transparent');
  ctx.fillStyle=glow1;
  ctx.fillRect(0,0,width,height);
  
  const glow2=ctx.createRadialGradient(200,1100,50,200,1100,500);
  glow2.addColorStop(0,'rgba(91,124,250,0.18)');
  glow2.addColorStop(1,'transparent');
  ctx.fillStyle=glow2;
  ctx.fillRect(0,0,width,height);
  
  // 3. Border frame
  ctx.strokeStyle='rgba(255,255,255,0.1)';
  ctx.lineWidth=4;
  ctx.strokeRect(40,40,width-80,height-80);
  
  // 4. Header / Brand
  ctx.fillStyle='#f1d97f';
  ctx.font='800 24px Inter, -apple-system, sans-serif';
  ctx.letterSpacing='4px';
  ctx.fillText('✦ SAATHI AI EXAM SIMULATOR ✦',80,120);
  
  // 5. Candidate Info
  ctx.fillStyle='#ffffff';
  ctx.font='700 48px Inter, -apple-system, sans-serif';
  ctx.fillText(userName,80,195);
  
  ctx.fillStyle='#a6aba3';
  ctx.font='500 28px Inter, -apple-system, sans-serif';
  ctx.fillText('Subject Assessment: '+topic,80,245);
  
  // 6. Central Score Hero Card
  const cardX=80, cardY=310, cardW=width-160, cardH=580;
  ctx.fillStyle='rgba(255,255,255,0.05)';
  ctx.strokeStyle='rgba(229,195,105,0.4)';
  ctx.lineWidth=3;
  ctx.beginPath();
  ctx.roundRect(cardX,cardY,cardW,cardH,36);
  ctx.fill();
  ctx.stroke();
  
  // Big Score Number
  ctx.fillStyle='#f1d97f';
  ctx.font='800 130px Inter, -apple-system, sans-serif';
  ctx.textAlign='center';
  ctx.fillText(`${attempt.score} / ${attempt.total_questions}`,width/2,500);
  
  // Accuracy & Verdict
  ctx.fillStyle='#ffffff';
  ctx.font='800 42px Inter, -apple-system, sans-serif';
  ctx.fillText(`${attempt.accuracy_percentage}% ACCURACY`,width/2,580);
  
  const pct=attempt.accuracy_percentage;
  let verdict='EXCELLENT PERFORMANCE 🌟';
  if(pct>=90)verdict='OUTSTANDING MASTERY 🏆';
  else if(pct<50)verdict='GROWTH IN PROGRESS 💪';
  ctx.fillStyle='#8fb4a0';
  ctx.font='700 28px Inter, -apple-system, sans-serif';
  ctx.fillText(verdict,width/2,640);
  
  // Stats Row inside Card
  ctx.textAlign='left';
  const statBoxY=710, boxW=(cardW-60)/3;
  
  // Stat 1: Time
  ctx.fillStyle='rgba(255,255,255,0.06)';
  ctx.beginPath();
  ctx.roundRect(cardX+20,statBoxY,boxW,130,20);
  ctx.fill();
  ctx.fillStyle='#a6aba3';
  ctx.font='600 20px Inter, sans-serif';
  ctx.fillText('TIME SPENT',cardX+40,statBoxY+45);
  ctx.fillStyle='#ffffff';
  ctx.font='700 32px Inter, sans-serif';
  ctx.fillText(timeStr,cardX+40,statBoxY+95);
  
  // Stat 2: Difficulty
  ctx.fillStyle='rgba(255,255,255,0.06)';
  ctx.beginPath();
  ctx.roundRect(cardX+40+boxW,statBoxY,boxW,130,20);
  ctx.fill();
  ctx.fillStyle='#a6aba3';
  ctx.font='600 20px Inter, sans-serif';
  ctx.fillText('DIFFICULTY',cardX+60+boxW,statBoxY+45);
  ctx.fillStyle='#ffd166';
  ctx.font='700 32px Inter, sans-serif';
  ctx.fillText((test?.difficulty||'Medium').toUpperCase(),cardX+60+boxW,statBoxY+95);
  
  // Stat 3: Total Questions
  ctx.fillStyle='rgba(255,255,255,0.06)';
  ctx.beginPath();
  ctx.roundRect(cardX+60+boxW*2,statBoxY,boxW,130,20);
  ctx.fill();
  ctx.fillStyle='#a6aba3';
  ctx.font='600 20px Inter, sans-serif';
  ctx.fillText('QUESTIONS',cardX+80+boxW*2,statBoxY+45);
  ctx.fillStyle='#ffffff';
  ctx.font='700 32px Inter, sans-serif';
  ctx.fillText(String(attempt.total_questions),cardX+80+boxW*2,statBoxY+95);
  
  // 7. Challenge Callout Box
  ctx.fillStyle='rgba(91,124,250,0.12)';
  ctx.strokeStyle='rgba(91,124,250,0.3)';
  ctx.lineWidth=2;
  ctx.beginPath();
  ctx.roundRect(80,940,width-160,200,26);
  ctx.fill();
  ctx.stroke();
  
  ctx.fillStyle='#ffffff';
  ctx.font='700 34px Inter, sans-serif';
  ctx.fillText('⚡ Think you can beat this score?',120,1015);
  ctx.fillStyle='#bac3ba';
  ctx.font='500 24px Inter, sans-serif';
  ctx.fillText('Practise with Saathi: '+location.host,120,1070,840);
  
  // 8. Footer Watermark
  ctx.fillStyle='rgba(255,255,255,0.4)';
  ctx.font='500 22px Inter, sans-serif';
  ctx.fillText(`Saathi practice result · AI questions may contain errors · ${new Date().toLocaleDateString()}`,80,1230,920);
}

function downloadScorecardPng(){
  const canvas=$('scorecardCanvas');
  if(!canvas)return;
  const link=document.createElement('a');
  const topic=(state.activeTest?.topic||'mock-test').toLowerCase().replace(/[^a-z0-9]+/g,'-');
  link.download=`saathi-scorecard-${topic}.png`;
  link.href=canvas.toDataURL('image/png');
  link.click();
  toast('Scorecard downloaded!','success');
}

function shareOnWhatsApp(){
  const attempt=state.lastAttemptResult?.attempt;
  const topic=state.activeTest?.topic||'Exam';
  const score=attempt?.score||0;
  const total=attempt?.total_questions||10;
  const pct=attempt?.accuracy_percentage||0;
  const text=encodeURIComponent(`I just scored ${score}/${total} (${pct}%) on "${topic}" using Saathi AI Exam Simulator!\n\nCan you beat my score? Challenge me here:\n${location.origin}/dashboard#mocktests`);
  window.open(`https://api.whatsapp.com/send?text=${text}`,'_blank');
}

function retakeOrNewTest(){
  $('mockTestResultsBox').style.display='none';
  $('mockTestRunnerBox').style.display='none';
  $('mockTestCreatorBox').style.display='block';
  scrollTo({top:0,behavior:'smooth'});
}

