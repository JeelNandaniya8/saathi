// Exercise the real pages in Chromium with owned, local fixture responses only.
const {chromium}=require('playwright');
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const root=path.resolve('.'),base='http://localhost:8765';
const original={id:1,role:'user',content:'Search',created_at:'2026-09-19T08:00:00Z',attachments:[],ai_mode:'normal'};
const answer={id:2,role:'assistant',content:'Search <script>not executable</script> ગુજરાતી',created_at:original.created_at,source_pages:[],memory_labels:['Requested classroom for this reply','Search']};
const task={id:1,title:'Search',details:'Saved user writing',priority:'high',completed:false,due_at:null};
(async()=>{
 const browser=await chromium.launch({headless:true,...(process.env.CHROMIUM_EXECUTABLE?{executablePath:process.env.CHROMIUM_EXECUTABLE,args:['--no-sandbox','--disable-dev-shm-usage']}: {})});
 try{
  for(const width of [1280,768,390,360,320]){
   const context=await browser.newContext({viewport:{width,height:900},hasTouch:width<=390,isMobile:width<=390,serviceWorkers:'block'}),page=await context.newPage(),errors=[],requests=[];
   let chatProfilePending=false,historyWhileProfilePending=false,profileFields=[],planSaves=0,replanSaves=0,classroomAdds=0,classroomConnected=true,careSaves=[],careEdits=[],foodSaves=0,foodPreview=null,sharedStatus="pending",classroomExplains=0,classroomSchedules=0,ocrReads=0;
   let inlineSaved=null,inlineJobs=[],cardCorrections=0,conversationCreateGate=null;
   let fixtureNote={id:3,title:'Search',content:'Search',updated_at:original.created_at,version:1};
   let chatPlanSaves=0,actionSaves=0,inlineGenerations=0,inlineSubmits=0,contextPrefs={tasks:false,reminders:false,classroom:false};
   let language='en',focus=null,failMindmaps=!process.env.SAATHI_UI_REVIEW,searches=0,fixtureTasks=[{...task}],failClassroomExplain=false,classroomSyncs=0,classroomSelections=0,failClassroomSync=false,classroomError=null,classroomConnects=0;
   const chatPlan={kind:'plan',title:'DNA recall',text:'Two sessions',items:[{kind:'task',title:'DNA Day 1',text:'Recall\nDuration: 15 minutes',duration_minutes:15,at:'2026-10-17T12:30:00Z'},{kind:'task',title:'DNA Day 2',text:'Practice\nDuration: 15 minutes',duration_minutes:15,at:'2026-10-18T12:30:00Z'}]};
   const user=()=>({id:1,name:'Search',username:'fixture',email:'fixture@example.test',plan:'free',timezone:'Asia/Kolkata',language});
   page.on('pageerror',error=>errors.push(error.message));
   await page.route('**/*',async route=>{
    const url=new URL(route.request().url());if(url.origin!==base)return route.abort();
    const pathname=url.pathname;requests.push(pathname);
    if(pathname==='/dashboard-mindmaps.js'&&failMindmaps){failMindmaps=false;return route.abort()}
    if(pathname.startsWith('/api/')){
     let data={},status=200;const method=route.request().method(),body=()=>route.request().postDataJSON();if(pathname==='/api/conversations'&&method==='POST')assert.ok(route.request().headers()['x-csrf-token'],'New chat waits for session readiness');
     if(pathname==='/api/me'&&new URL(page.url()).pathname==='/chat'){chatProfilePending=true;await new Promise(resolve=>setTimeout(resolve,350));chatProfilePending=false}
     if(pathname==='/api/conversations/7/messages'){if(chatProfilePending)historyWhileProfilePending=true;await new Promise(resolve=>setTimeout(resolve,850))}
     if(pathname==='/api/mock-tests/generate'){inlineGenerations++;if(inlineGenerations===1){status=503;data={error:'Fixture creation failed'}}else data={test:{id:53,topic:body().topic,expires_at:new Date(Date.now()+900000).toISOString(),questions:Array.from({length:body().question_count},(_,i)=>({id:i+1,question:'Fixture question '+(i+1),options:Object.fromEntries(['A','B','C','D'].map(letter=>[letter,'Choice '+letter+' '+(i+1)]))}))}};assert.ok(body().job_id);const {job_id,...input}=body();inlineJobs.unshift({id:job_id,kind:'mock',request:input,status:status===503?'failed':'ready',result_id:status===503?null:53,error:status===503?'Fixture creation failed':null});if(data.test)inlineSaved=data.test}
     else if(/^\/api\/conversations\/\d+\/cancel$/.test(pathname)){assert.ok(body().request_id);data={cancelled:true}}
     else if(pathname==='/api/study-allowance')data={allowance:{kind:url.searchParams.get('kind'),remaining:2,reset_local:'2026-10-15, 05:30 AM · Asia/Kolkata'}};
     else if(pathname==='/api/study-jobs')data={jobs:inlineJobs.filter(job=>job.kind===url.searchParams.get('kind'))};
     else if(pathname==='/api/mock-tests/53')data={test:inlineSaved,...(inlineSubmits?{result:{attempt:{score:1,total_questions:5},review:[]}}:{})};
     else if(pathname==='/api/mock-tests/53/submit'){inlineSubmits++;assert.equal(body().answers['1'],'A');data={attempt:{score:1,total_questions:5},review:[{id:1,question:'Fixture question 1',user_answer:'A',correct_answer:'A',explanation:'Literal <script>unsafe</script> explanation'}]}}
     else if(pathname==='/api/mindmaps/generate')data={mindmap:{id:62,topic:body().topic,data:{summary:'Saved map summary',root:{label:'Chat map root',desc:'Topic-specific explanation',children:[{label:'Chat map branch',desc:'Actual detail <script>unsafe</script>',children:[]}]}}}};
     else if(pathname==='/api/chat-context'){if(method==='PATCH')contextPrefs=body();data={permissions:contextPrefs}}
     else if(pathname==='/api/chat-actions/992'){if(method==='POST'){assert.equal(body().automatic,undefined);assert.equal(body().confirmed,true);chatPlanSaves++}data=chatPlanSaves?{saved:true,receipt:{kind:'plan',resource_id:10,resource_ids:[10,11]},resource:{count:2,items:chatPlan.items.map((item,index)=>({id:10+index,title:item.title,due_at:item.at,completed:false}))},content:'Study plan saved to Planner.\n<SAATHI_ACTION>'+JSON.stringify(chatPlan)+'</SAATHI_ACTION>'}:{saved:false,action:chatPlan}}
     else if(pathname==='/api/chat-actions/999'){if(method==='POST'){assert.equal(body().confirmed,true);assert.equal(body().action.title,'Edited chat task');actionSaves++;data={saved:true,receipt:{kind:'task',resource_id:9}}}else data=actionSaves?{saved:true,receipt:{kind:'task',resource_id:9}}:{saved:false,action:{kind:'task',title:'Chat task',text:'User requested details',at:null,priority:'medium',recurrence:'once'}}}
     else if(pathname==='/api/me')data={user:user(),csrf_token:'fixture',chat_modes:[{id:'normal',label:'Normal',description:'A balanced everyday reply'},{id:'quiz',label:'Quiz',description:'Practice questions'}],chat_attachments:{enabled:true,per_message:3,max_bytes:8388608,total_max_bytes:8388608,remaining_today:5}};
     else if(pathname==='/api/preferences'){language=body().language;data={user:user()}}
     else if(pathname==='/api/workspace/preferences')data={preferences:{onboarding_done:true,timezone:'Asia/Kolkata',language,notification_mode:'immediate',quiet_enabled:false,celebrations:false}};
     else if(pathname==='/api/workspace/today')data={tasks:fixtureTasks.filter(item=>!item.completed),revision_due:2,recent_chat:{id:7,title:'Search'},next_exam:{id:4,title:'Owned upcoming exam',days_left:2}};
     else if(pathname==='/api/overview')data={pending_tasks:1,conversations:1,active_reminders:0,active_memories:0};
     else if(pathname==='/api/memories')data={memories:[]};
     else if(pathname==='/api/journal')data={entries:[]};
     else if(pathname==='/api/trusted-contacts')data={sent:[],incoming:[]};
     else if(pathname==='/api/tasks')data={tasks:fixtureTasks};
     else if(pathname==='/api/tasks/1'){fixtureTasks[0]={...fixtureTasks[0],...body()};data={task:fixtureTasks[0]}}
     else if(pathname==='/api/check-ins')data={check_ins:[{id:1,created_at:'2026-10-08T09:00:00Z',mood:3,energy:4,note:'Private summary fixture'}]};
     else if(pathname==='/api/reminders')data={reminders:[]};
     else if(pathname==='/api/care/food-plans/preview'){assert.equal(body().confirmed,true);foodPreview={items:[{day:1,slot:0,name:body().options[0].name,estimated_cost:'20'}],unscheduled:2,blocked_options:[],needs_clinical_review:false,inputs:{currency:'INR'},preview_token:'fixture-preview'};data={plan:foodPreview}}
     else if(pathname==='/api/care/food-plans'){if(method==='POST'){assert.equal(body().save_confirmed,true);assert.equal(body().preview_token,'fixture-preview');foodSaves++;data={id:1}}else data={plans:foodSaves?[{id:1,preview:foodPreview}]:[]}}
     else if(pathname==='/api/care/shares')data={enabled:false,user_id:2,contacts:[],shares:[{id:1,owner_id:1,recipient_id:2,owner_name:'Owner',recipient_name:'Receiver',fields:['status'],status:sharedStatus,version:1,expires_at:'2026-11-01T00:00:00Z'}]};
     else if(pathname==='/api/care/shares/1/respond'){assert.equal(body().confirmed,true);assert.equal(body().action,'revoke');assert.equal(body().version,1);sharedStatus='revoked';data={ok:true}}
     else if(pathname==='/api/care/prescription-draft'){assert.match(route.request().headers()['content-type'],/^multipart\/form-data; boundary=/);assert.match(route.request().postData(),/ai_confirmed/);ocrReads++;data={draft:'Original prescription [unclear] <script>unsafe</script>',verified:false,saved:false}}
     else if(pathname==='/api/care/routines/status')data={enabled:true,delivery_configured:false};
     else if(pathname==='/api/care/routines'){
      if(method==='POST'){careSaves.push(body());if(careSaves.length===1){status=503;data={error:'Temporary save failure'}}else data={id:1}}
      else data={routines:careSaves.length>=2?[{id:1,title:'Existing schedule',note:careEdits.length?'Reviewed instruction':'User confirmed clinician instructions',active:true,recurrence:'daily',care_schedule:{timezone:'UTC',version:careEdits.length+1},next_run_at:'2026-10-09T08:00:00Z',current_scheduled_for:'2026-10-09T08:00:00Z'}]:[],occurrences:[],deliveries:[]};
     }
     else if(pathname==='/api/care/routines/1'){assert.equal(body().action,'edit_instructions');assert.equal(body().version,1);assert.equal(body().confirmed,true);careEdits.push(body());data={ok:true}}
     else if(pathname==='/api/habits')data={habits:[]};
     else if(pathname==='/api/push/config')data={enabled:false};
     else if(pathname==='/api/referrals')data={referral_code:'fixture',referral_url:base,invited:0,qualified:0,bonus_days:0};
     else if(pathname==='/api/mock-tests/history')data={tests:[]};
     else if(pathname==='/api/mindmaps/history')data={mindmaps:[]};
     else if(pathname==='/api/mindmaps/62')data={mindmap:{id:62,topic:'Exact linked map',data:{summary:'Persisted map, outside history',root:{id:'linked-root',label:'Exact linked root',desc:'Stored content',children:[{id:'readable-branch',label:'Probability',desc:'A saved branch stays readable',children:[]}]}}}};
     else if(pathname==='/api/quick-notes/3'){
      if(method==='PATCH'){assert.equal(body().version,fixtureNote.version);fixtureNote={...fixtureNote,...body(),version:fixtureNote.version+1}}
      data={note:fixtureNote};
     }
     else if(pathname==='/api/quick-notes')data={notes:[fixtureNote]};
     else if(pathname==='/api/workspace/search'){searches++;data={items:[{kind:'task',id:1,title:'Search',excerpt:'<img src=x onerror=alert(1)>'}]}}
     else if(pathname==='/api/focus'){
      if(method==='POST')focus={id:1,status:'running',version:1,task_id:body().task_id,duration_seconds:body().minutes*60,remaining_seconds:body().minutes*60};
      data={session:focus};
     }else if(pathname==='/api/focus/1'){
      const action=body().action;focus={...focus,status:action==='pause'?'paused':action==='resume'?'running':'cancelled',version:focus.version+1};data={session:focus};
     }else if(pathname==='/api/messages/991/flashcards/0'){assert.equal(method,'PATCH');assert.equal(body().expected_back,'5′→3′');assert.equal(body().back,'3′→5′');cardCorrections++;data={content:'[FLASHCARDS]\nFront: Template reading?\nBack: 3′→5′\n[/FLASHCARDS]',study_progress:{kind:'flashcards',progress:{corrected_indices:[0],review_indices:[0],known_indices:[]}}}}
     else if(pathname==='/api/conversations'&&method==='POST'){if(conversationCreateGate)await conversationCreateGate;else await new Promise(resolve=>setTimeout(resolve,350));data={conversation:{id:8,title:'New conversation',updated_at:original.created_at}};}
     else if(pathname==='/api/conversations')data={conversations:[{id:7,title:'Search',preview:'Search',updated_at:original.created_at,is_archived:false}]};
     else if(pathname==='/api/conversations/7/messages')data={messages:[original,answer],has_more:false,conversation:{id:7,title:'Search'}};
     else if(pathname==='/api/response-timings')data={summary:{attempts:0,completed:0,errors:0,cancelled:0},recent:[]};
     else if(pathname==='/api/subject-spaces')data={spaces:[]};
     else if(pathname==='/api/revision')data={items:[],due:0,upcoming:0};
     else if(pathname==='/api/classroom/status')data={configured:true,scheduler_ready:true,connected:classroomConnected,connection:{last_sync:null,last_error:classroomError,version:1,auto_sync_enabled:!!classroomSchedules}};
     else if(pathname==='/api/classroom/connect'){assert.deepEqual(body(),{confirmed:true,reconnect:true,version:1});classroomConnects++;data={url:'https://not-google.example/blocked'}}
     else if(pathname==='/api/classroom/courses')data={courses:[{id:'course1',name:'English'}],selected:['course1'],version:1};
     else if(pathname==='/api/classroom/select'){assert.equal(body().confirmed,true);assert.deepEqual(body().courses,['course1']);assert.equal(body().version,1);classroomSelections++;data={ok:true}}
     else if(pathname==='/api/classroom/sync'){assert.equal(body().confirmed,true);classroomSyncs++;if(failClassroomSync){failClassroomSync=false;classroomError='reconnect_required';status=503;data={error:'Classroom could not complete this action. Your imported work is retained.',error_code:'reconnect_required'}}else{classroomError=null;data={ok:true}}}
     else if(pathname==='/api/classroom/assignments')data={assignments:[{id:1,course_id:'course1',submission_state:'NEW',title:'Essay',instructions:'Original teacher instructions <script>unsafe</script>',original_url:'https://classroom.google.com/c/1',due_at:null,available:true,task_id:classroomAdds?9:null}]};
     else if(pathname==='/api/classroom/assignments/1/planner'){assert.equal(body().confirmed,true);classroomAdds++;data={task_id:9}}
     else if(pathname==='/api/classroom/schedule'){assert.equal(body().confirmed,true);assert.equal(body().enabled,true);assert.equal(body().version,1);classroomSchedules++;data={ok:true}}
     else if(pathname==='/api/classroom/assignments/1/explain'){assert.deepEqual(Object.keys(body()).sort(),['ai_confirmed','confirmed','language']);assert.equal(body().ai_confirmed,true);assert.equal(body().language,await page.locator('html').getAttribute('lang'));classroomExplains++;if(failClassroomExplain){failClassroomExplain=false;status=503;data={error:'Raw provider detail must not appear',code:'AI_BUSY'}}else data={explanation:'Useful steps <script>unsafe</script>',saved:false,verified:false}}
     else if(pathname==='/api/classroom/disconnect'){assert.equal(body().confirmed,true);assert.equal(body().remove_imports,true);classroomConnected=false;data={ok:true,revoked:true}}
     else if(pathname==='/api/personal-context')data={fields:profileFields};
     else if(pathname==='/api/personal-context/care/conditions'){
      if(method==='PUT')profileFields=[{...body(),category:'care',field:'conditions',source:'user_reported',version:1,reviewed_at:new Date().toISOString()}];
      else profileFields=[];data={ok:true};
     }
     else if(pathname==='/api/personal-context/revoke'){profileFields=profileFields.map(x=>({...x,use_in_ai:false,version:x.version+1}));data={ok:true}}
     else if(pathname==='/api/exam-plans/preview')data={plan:{...body(),preview_token:'fixture-plan',coverage_limited:false,rest_date:'2026-12-31',items:[{date:'2026-12-20',phase:'recall',topic:'Algebra',minutes:25}]}};
     else if(pathname==='/api/exam-plans'){if(method==='POST'){planSaves++;assert.equal(body().preview_token,'fixture-plan');data={id:1,created:1}}else data={plans:planSaves?[{id:1,title:'Semester exam',exam_date:'2027-01-01',timezone:'UTC'}]:[]}}

     else if(pathname==='/api/exam-plans/1/replan/preview'){assert.equal(body().confirmed,true);data={plan:{items:[{id:1,title:'Recall: Algebra',from:'2026-10-01T18:00:00Z',due_at:'2026-10-10T18:00:00Z'}],unscheduled:0,preserved:[],exam_date:body().exam_date,rest_date:'2026-10-19',date_changed:true,outside_window:0,preview_token:'replan-fixture'}}}
     else if(pathname==='/api/exam-plans/1/replan/apply'){assert.equal(body().preview_token,'replan-fixture');assert.equal(body().confirmed,true);assert.equal(body().exam_date,'2026-10-20');replanSaves++;data={ok:true,moved:1}}
     else {status=404;data={error:'Unmocked fixture endpoint: '+pathname}}
     return route.fulfill({status,contentType:'application/json',body:JSON.stringify(data)});
    }
    const filename=pathname==='/'?'saathi.html':pathname==='/dashboard'?'dashboard.html':pathname==='/chat'?'chat.html':pathname.slice(1),local=path.resolve(root,filename);
    if(!local.startsWith(root+path.sep)||!fs.existsSync(local)||!fs.statSync(local).isFile())return route.fulfill({status:404,body:''});
    const types={'.html':'text/html','.js':'application/javascript','.css':'text/css','.svg':'image/svg+xml','.json':'application/json'};
    return route.fulfill({contentType:types[path.extname(local)]||'application/octet-stream',body:fs.readFileSync(local)});
   });
   if(process.env.SAATHI_UI_REVIEW){await require('./workspace_ui.cjs')(page,width,base);await context.close();assert.deepEqual(errors,[],'No uncaught errors during UI review');continue}
   await page.goto(base+'/dashboard');
   await page.locator('#todayTasks .hub-task-title').waitFor();
   await page.waitForFunction(()=>document.querySelector('#workspaceStatus').hidden);
   assert.equal(await page.evaluate(()=>scrollY),0,'Greeting stays visible on startup');
   // Account text styles must never override the avatar's centering or typography.
   for(const [name,initial] of [['Nihar Chocha','N'],['Jeel Nandaniya','J']]){
    const avatar=await page.evaluate(name=>{
     const node=document.querySelector('#sideAvatar');SaathiWorkspace.renderAvatar(node,{name});
     const css=getComputedStyle(node),box=node.getBoundingClientRect(),range=document.createRange();range.selectNodeContents(node);const letter=range.getBoundingClientRect();
     return {text:node.textContent,display:css.display,align:css.alignItems,justify:css.justifyItems,font:css.fontSize,margin:css.marginTop,offset:Math.abs((letter.left+letter.right-box.left-box.right)/2)};
    },name);
    assert.equal(avatar.text,initial);assert.equal(avatar.display,'grid');assert.equal(avatar.align,'center');assert.equal(avatar.justify,'center');assert.equal(avatar.font,'14px');assert.equal(avatar.margin,'0px');assert.ok(avatar.offset<1,'Initial stays horizontally centered');
   }
   await page.evaluate(()=>SaathiWorkspace.renderAvatar(document.querySelector('#sideAvatar'),{name:'Search'}));

   assert.equal(await page.locator('.nav > button[data-view]').count(),2,'Today and Planner are directly reachable');
   assert.equal(await page.locator('.nav > button[data-view="tasks"]').count(),1);
   assert.equal(await page.locator('.nav > [data-quick-notes]').count(),1);
   assert.equal(await page.locator('.nav > a[href="/chat"]').count(),1);
   assert.equal(await page.locator('#moreNavigation [data-view="study"],#moreNavigation [data-view="healer"]').count(),2,'Study and Care remain reachable');
   assert.equal(await page.locator('.nav-group').count(),3,'Secondary tools are grouped instead of one long list');
   await page.getByText('Owned upcoming exam · 2 days left',{exact:true}).waitFor();
   assert.ok(await page.locator('.hero-panel').evaluate(node=>node.getBoundingClientRect().height<190),'Today greeting leaves the next action in view');
   assert.ok(await page.evaluate(()=>{const before=document.documentElement.dataset.theme;document.documentElement.dataset.theme='light';const light=getComputedStyle(document.body).getPropertyValue('--paper').trim();document.documentElement.dataset.theme='dark';const dark=getComputedStyle(document.body).getPropertyValue('--paper').trim();if(before)document.documentElement.dataset.theme=before;else delete document.documentElement.dataset.theme;return Boolean(light&&dark&&light!==dark)}),'Light and dark workspace surfaces are distinct');
   assert.ok(!requests.some(url=>/dashboard-(study|care|mindmaps)\.js/.test(url)),'Heavy tools must not load on Today');
   assert.ok(!requests.includes('/locale-gu.js'),'English must not download Gujarati catalog');
   assert.equal(await page.locator('#account .referral-banner').count(),1);
   await page.evaluate(()=>openView('account'));
   assert.equal(await page.evaluate(()=>{const active=document.querySelector('.nav button.active');return active.closest('.nav-group').open&&active.closest('.nav-more').open}),true,'Deep navigation reveals both parent groups');
   await page.locator('[data-large-text]').click();
   assert.equal(await page.locator('html').getAttribute('data-text-size'),'large');
   assert.equal(await page.locator('[data-large-text]').getAttribute('aria-pressed'),'true');
   assert.equal(await page.locator('#dailyPreferenceSummary').evaluate(el=>getComputedStyle(el).fontSize),'18px');
   assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),'Large text fits the workspace');
   assert.equal(await page.evaluate(()=>localStorage.getItem('saathi-large-text')),'on');
   await page.locator('[data-large-text]').click();
   await page.locator('#languageSelect').selectOption('gu');
   await page.waitForFunction(()=>document.querySelector('[data-care-routines]').textContent==='દવાની નોંધ ખોલો');
   await page.waitForFunction(()=>document.querySelector('[data-focus-session]').textContent.includes('ધ્યાન'));
   assert.equal(await page.locator('#profileDisplayName').textContent(),'Search','User names must remain unchanged');
   await page.evaluate(()=>openView('overview'));
   assert.equal(await page.locator('#todayTasks .hub-task-title').textContent(),'Search','User task names must remain unchanged');
   await page.locator('[data-focus-session]').click();
   const focusDialog=page.locator('dialog[open]');await focusDialog.getByRole('button',{name:'ધ્યાનથી કામ શરૂ કરો',exact:true}).waitFor();
   assert.notEqual(await focusDialog.locator('button.primary').evaluate(el=>getComputedStyle(el).backgroundColor),'rgba(0, 0, 0, 0)');
   await focusDialog.getByRole('button',{name:'ધ્યાનથી કામ શરૂ કરો',exact:true}).click();
   await focusDialog.getByRole('button',{name:'વિરામ આપો',exact:true}).click();
   await focusDialog.getByRole('button',{name:'ફરી ચાલુ કરો',exact:true}).waitFor();
   await focusDialog.getByRole('button',{name:'બંધ કરો',exact:true}).click();
   await page.locator('[data-focus-session]').click();
   await page.locator('dialog[open]').getByRole('button',{name:'ફરી ચાલુ કરો',exact:true}).waitFor();
   await page.keyboard.press('Escape');await page.locator('dialog[open]').waitFor({state:'detached'});
   await page.evaluate(()=>SaathiHub.search());
   await page.locator('dialog[open] input').fill('Search');
   await page.locator('.hub-result').waitFor();assert.equal(await page.locator('.hub-result img').count(),0);
   assert.equal(searches,1);await page.keyboard.press('Escape');await page.locator('dialog[open]').waitFor({state:'detached'});
   await page.evaluate(()=>openView('mindmaps'));
   await page.waitForFunction(()=>document.querySelector('#workspaceStatusText').textContent.includes('લોડ થયું નથી'));
   await page.locator('#retryWorkspace').click();
   await page.waitForFunction(()=>document.querySelector('#workspaceStatus').hidden);
   assert.equal(requests.filter(url=>url==='/dashboard-mindmaps.js').length,2,'A failed lazy load must be retryable');
   await page.evaluate(()=>openView('mocktests'));
   await page.waitForFunction(()=>document.querySelector('#workspaceStatus').hidden);
   await page.waitForFunction(()=>state.loadedSections?.has('mocktests'));assert.ok(requests.includes('/dashboard-study.js'));
   await page.evaluate(()=>openView('healer'));
   await page.waitForFunction(()=>typeof window.stopCare==='function');
   await page.evaluate(()=>openView('account'));
   await page.locator('#languageSelect').selectOption('hi');
   await page.waitForFunction(()=>document.querySelector('[data-care-routines]').textContent==='दवा का रिकॉर्ड खोलें');
   await page.waitForFunction(()=>SaathiI18n.t('Please log in first.')==='पहले लॉग इन करें।');
   assert.ok(requests.includes('/locale-hi.js'));
   await page.locator('#languageSelect').selectOption('en');
   await page.waitForFunction(()=>document.querySelector('[data-care-routines]').textContent==='Open medication log');
   await page.waitForFunction(()=>document.querySelector('.focus-shortcut b').textContent==='Make a little room to focus');
   await page.evaluate(()=>openView('checkins'));
   const [summaryFile]=await Promise.all([page.waitForEvent('download'),page.locator('#downloadCheckinSummary').click()]);
   const summaryText=fs.readFileSync(await summaryFile.path(),'utf8');
   assert.ok(summaryText.includes('Mood: 3/5'));assert.ok(!summaryText.includes('Private summary fixture'));
   await page.locator('#checkinIncludeNotes').check();
   const [withNotes]=await Promise.all([page.waitForEvent('download'),page.locator('#downloadCheckinSummary').click()]);
   assert.ok(fs.readFileSync(await withNotes.path(),'utf8').includes('Private summary fixture'));
   await page.locator('#checkinIncludeNotes').uncheck();
   await page.locator('#checkins [data-schedule-checkin]').click();
   assert.equal(await page.locator('#reminderTitle').inputValue(),'How are you feeling today?');
   assert.equal(await page.locator('#reminderTime').inputValue(),'','No timing is inferred');
   assert.equal(await page.locator('#reminderRecurrence').inputValue(),'once');
   await page.locator('#reminderTitle').fill('Keep my draft');
   await page.evaluate(()=>openView('healer'));
   await page.locator('#healer [data-schedule-checkin]').click();
   assert.equal(await page.locator('#reminderTitle').inputValue(),'Keep my draft');
   await page.evaluate(()=>{cancelReminderEdit();openView('account')});
   // Actual forms: off-by-default health consent, revoke and preview-before-save.
   await page.locator('#account [data-personal-context]').click();
   let profile=page.locator('dialog[open]').last();
   await profile.getByRole('button',{name:'Review',exact:true}).first().click();
   let editor=page.locator('dialog[open]').last();
   await editor.getByLabel('Conditions you report',{exact:true}).fill('User-provided detail');
   assert.equal(await editor.getByLabel('Allow this field in relevant AI replies').isChecked(),false);
   await editor.getByLabel('Allow this field in relevant AI replies').check();
   await editor.getByLabel('I confirm this information and agree to store it in my account.').check();
   await editor.getByRole('button',{name:'Save',exact:true}).click();
   await page.locator('dialog[open]').getByText('User-provided detail',{exact:true}).waitFor();
   assert.equal(profileFields[0].use_in_ai,true);
   await page.locator('dialog[open]').getByRole('button',{name:'Stop all profile use in AI',exact:true}).click();
   await page.locator('dialog[open]').getByText(/Stored privately; excluded from AI/).waitFor();
   assert.equal(profileFields[0].use_in_ai,false);
   await page.keyboard.press('Escape');
   await page.evaluate(()=>openView('study'));
   await page.locator('[data-exam-plans]').click();
   const exam=page.locator('dialog[open]');
   await exam.getByLabel('Exam name',{exact:true}).fill('Semester exam');
   await exam.getByLabel('Confirmed exam date',{exact:true}).fill('2027-01-01');
   await exam.getByLabel('Topics, one per line',{exact:true}).fill('Algebra');
   await exam.getByLabel('I confirm the exam date and topics. These are not assignment deadlines.').check();
   assert.equal(planSaves,0);
   await exam.getByRole('button',{name:'Preview plan',exact:true}).click();
   await exam.getByText('2026-12-20 · Recall: Algebra · 25 min',{exact:true}).waitFor();
   assert.ok(await exam.evaluate(el=>el.getBoundingClientRect().width<=innerWidth),'New dialogs fit mobile');
   await exam.getByRole('button',{name:'Add this plan to Planner',exact:true}).click();
   await page.waitForFunction(()=>state.currentView==='tasks');assert.equal(planSaves,1);
   await page.evaluate(()=>openView('study'));await page.locator('[data-exam-plans]').click();
   await page.getByRole('button',{name:'Reschedule missed blocks',exact:true}).click();
   const replan=page.getByRole('dialog',{name:'Reschedule missed blocks',exact:true});
   await replan.getByLabel('I have reviewed completed work in Planner.',{exact:true}).check();
   await replan.getByLabel('Confirmed exam date',{exact:true}).fill('2026-10-20');
   await replan.getByRole('button',{name:'Preview plan',exact:true}).click();
   await replan.getByRole('button',{name:'Confirm new dates',exact:true}).waitFor();
   assert.equal(replanSaves,0);
   await replan.getByRole('button',{name:'Confirm new dates',exact:true}).click();
   await replan.waitFor({state:'detached'});assert.equal(replanSaves,1);
   await page.locator('dialog[open]').getByRole('button',{name:'Close',exact:true}).click();
   await page.locator('[data-classroom]').click();
   const classroom=page.getByRole('dialog',{name:'Google Classroom',exact:true});
   await classroom.getByText('No confirmed deadline',{exact:true}).waitFor();
   await classroom.getByText('Not submitted',{exact:true}).waitFor();
   await classroom.getByRole('article').getByText('English',{exact:true}).waitFor();
   assert.equal(await classroom.locator('script').count(),0);
   await classroom.getByRole('button',{name:'Explain requirements and steps',exact:true}).click();assert.equal(classroomExplains,0);
   await classroom.getByLabel('Send only this assignment to the AI provider for an explanation. No profile, memory or other assignments.',{exact:true}).check();
   await classroom.getByRole('button',{name:'Explain requirements and steps',exact:true}).click();
   await classroom.getByText('Useful steps <script>unsafe</script>',{exact:true}).waitFor();assert.equal(classroomExplains,1);assert.equal(await classroom.locator('script').count(),0);
   await classroom.getByLabel('Refresh my selected courses about every six hours. Updates can be delayed. Changing courses turns this off.',{exact:true}).check();
   await classroom.getByRole('button',{name:'Save sync preference',exact:true}).click();
   await page.waitForFunction(()=>!document.querySelector('dialog[open]').dataset.saving);assert.equal(classroomSchedules,1);
   const addAssignment=classroom.getByRole('button',{name:'Add to Planner',exact:true});
   await addAssignment.click();assert.equal(classroomAdds,0);
   await classroom.getByRole('button',{name:'Confirm: Add to Planner',exact:true}).click();
   await classroom.getByText('Already in Planner',{exact:true}).waitFor();assert.equal(classroomAdds,1);
   await classroom.getByRole('button',{name:'Close',exact:true}).click();
   // Connected provider fixtures exercise the actual dialog in all supported
   // languages, including busy -> retry with selected-assignment consent kept.
   for(const labels of [
    {lang:'en',close:'Close',pending:'Not submitted',due:'No confirmed deadline',save:'Save selection',sync:'Sync selected courses',added:'Already in Planner',consent:'Send only this assignment to the AI provider for an explanation. No profile, memory or other assignments.',explain:'Explain requirements and steps',busy:'AI is busy. Your request is kept. Retry shortly.'},
    {lang:'gu',close:'બંધ કરો',pending:'Submit કરેલું નથી',due:'નક્કી કરેલી છેલ્લી તારીખ નથી',save:'પસંદગી સેવ કરો',sync:'પસંદ કરેલા courses sync કરો',added:'Plannerમાં ઉમેરેલું છે',consent:'સમજાવવા માટે ફક્ત આ અસાઇનમેન્ટ AIને મોકલો. Profile, memory કે બીજી અસાઇનમેન્ટ નહીં.',explain:'જરૂરિયાત અને પગલાં સમજાવો',busy:'AI વ્યસ્ત છે. તમારી વિનંતી રાખી છે. થોડી વારમાં ફરી પ્રયત્ન કરો.'},
    {lang:'hi',close:'बंद करें',pending:'Submit नहीं किया',due:'पक्की समयसीमा नहीं',save:'चयन सेव करें',sync:'चुने पाठ्यक्रम सिंक करें',added:'Planner में पहले से है',consent:'समझाने के लिए केवल यह असाइनमेंट AI को भेजें। Profile, memory या अन्य असाइनमेंट नहीं।',explain:'आवश्यकताएँ और चरण समझाएँ',busy:'AI व्यस्त है। आपका अनुरोध रखा है। थोड़ी देर में फिर कोशिश करें।'}
   ]){
    const recovery={en:['Reconnect Classroom','I agree to connect and store selected assignment information.','Google authorization needs renewal. Reconnect Classroom below; your selected courses and imports stay. Previous imports are retained; they are not a current pending list.'],gu:['Classroom ફરી જોડો','પસંદ કરેલી અસાઇનમેન્ટ માહિતી જોડવા અને સંગ્રહની મંજૂરી આપું છું.','Googleની મંજૂરી ફરી લેવી જરૂરી છે. નીચે Classroom ફરી જોડો; પસંદ કરેલા courses અને imports રહેશે. અગાઉનાં imports રાખ્યાં છે; તે હાલનાં બાકી કામની યાદી નથી.'],hi:['Classroom फिर जोड़ें','चुने असाइनमेंट की जानकारी जोड़ने और रखने की अनुमति देता/देती हूँ।','Google की अनुमति फिर चाहिए। नीचे Classroom फिर जोड़ें; चुने पाठ्यक्रम और imports रहेंगे। पिछले imports रखे गए हैं; वे अभी के बाकी काम की सूची नहीं हैं।']}[labels.lang];
    await page.evaluate(lang=>SaathiI18n.setLanguage(lang),labels.lang);
    await page.locator('[data-classroom]').click();
    await classroom.getByText(labels.pending,{exact:true}).waitFor();
    await classroom.getByText(labels.due,{exact:true}).waitFor();
    assert.equal(await classroom.getByLabel('English',{exact:true}).isChecked(),true);
    const connectsBefore=classroomConnects;failClassroomSync=true;
    await classroom.getByRole('button',{name:labels.sync,exact:true}).click();
    await classroom.getByText(recovery[2],{exact:true}).waitFor();
    await classroom.getByRole('button',{name:recovery[0],exact:true}).click();
    await classroom.getByRole('alert').filter({hasText:recovery[1]}).waitFor();
    assert.equal(classroomConnects,connectsBefore,'Reauthorization cannot start without explicit consent');
    await classroom.getByLabel(recovery[1],{exact:true}).check();
    await classroom.getByRole('button',{name:recovery[0],exact:true}).click();
    const invalidLink={en:'The connection link could not be verified. Try again.',gu:'જોડાણની link ચકાસી શકાઈ નથી. ફરી પ્રયત્ન કરો.',hi:'कनेक्शन की लिंक जाँची नहीं जा सकी। फिर कोशिश करें।'}[labels.lang];
    await classroom.getByText(invalidLink,{exact:true}).waitFor();assert.equal(classroomConnects,connectsBefore+1);
    assert.equal(new URL(page.url()).origin,base,'A bad authorization URL cannot navigate away');
    assert.equal(await classroom.getByLabel('English',{exact:true}).isChecked(),true);
    assert.equal(await classroom.getByText('Original teacher instructions <script>unsafe</script>',{exact:true}).count(),1);
    const selectionsBefore=classroomSelections,syncsBefore=classroomSyncs;
    await classroom.getByRole('button',{name:labels.save,exact:true}).click();
    await page.waitForFunction(()=>!document.querySelector('dialog[open]').dataset.saving);
    assert.equal(classroomSelections,selectionsBefore+1);
    await classroom.getByRole('button',{name:labels.sync,exact:true}).click();
    await page.waitForFunction(()=>!document.querySelector('dialog[open]').dataset.saving);
    assert.equal(classroomSyncs,syncsBefore+1);
    await classroom.getByText(labels.added,{exact:true}).waitFor();assert.equal(classroomAdds,1,'Reopen/sync cannot duplicate the Planner task');
    assert.equal(await classroom.getByRole('article').getByText('Essay',{exact:true}).count(),1);
    assert.equal(await classroom.getByText('Original teacher instructions <script>unsafe</script>',{exact:true}).count(),1);
    const attemptsBefore=classroomExplains;
    await classroom.getByRole('button',{name:labels.explain,exact:true}).click();
    await classroom.getByRole('alert').filter({hasText:labels.consent}).waitFor();assert.equal(classroomExplains,attemptsBefore);
    await classroom.getByLabel(labels.consent,{exact:true}).check();failClassroomExplain=true;
    await classroom.getByRole('button',{name:labels.explain,exact:true}).click();
    await classroom.getByRole('alert').filter({hasText:labels.busy}).waitFor();
    assert.equal(await classroom.getByLabel(labels.consent,{exact:true}).isChecked(),true);
    assert.equal(await classroom.getByText('Raw provider detail must not appear',{exact:true}).count(),0);
    await classroom.getByRole('button',{name:labels.explain,exact:true}).click();
    await classroom.getByText('Useful steps <script>unsafe</script>',{exact:true}).waitFor();
    assert.equal(classroomExplains,attemptsBefore+2);assert.equal(classroomAdds,1);assert.equal(await classroom.locator('script').count(),0);
    await classroom.getByRole('button',{name:labels.close,exact:true}).click();
   }
   await page.evaluate(()=>SaathiI18n.setLanguage('en'));
   await page.locator('[data-classroom]').click();await classroom.getByText('Already in Planner',{exact:true}).waitFor();
   await classroom.getByLabel('Also remove imported assignments. Planner tasks stay.',{exact:true}).check();
   await classroom.getByRole('button',{name:'Disconnect',exact:true}).click();
   await classroom.getByRole('button',{name:'Confirm: Disconnect',exact:true}).click();
   await classroom.getByRole('button',{name:'Connect Classroom',exact:true}).waitFor();
   await classroom.getByRole('button',{name:'Close',exact:true}).click();
   // Explicit health consent, retained input and stable retry IDs on both viewports.
   await page.evaluate(()=>openView('reminders'));
   await page.locator('[data-care-routines]').click();
   const medication=page.locator('dialog[open]');
   await medication.getByText('In-app only: server delivery is not configured.',{exact:true}).waitFor();
   await medication.locator('summary').filter({hasText:'Read prescription text'}).click();
   await medication.getByLabel('Prescription image or PDF',{exact:true}).setInputFiles({name:'fixture.png',mimeType:'image/png',buffer:Buffer.from('local transcription fixture')});
   await medication.getByRole('button',{name:'Read prescription text',exact:true}).click();assert.equal(ocrReads,0);
   await medication.getByLabel('I permit this file to be sent to the configured AI provider for unverified transcription. No schedule will be saved.',{exact:true}).check();
   await medication.getByRole('button',{name:'Read prescription text',exact:true}).click();
   await medication.getByText(/Original prescription \[unclear\]/).waitFor();assert.equal(ocrReads,1);assert.equal(careSaves.length,0);assert.equal(await medication.locator('script').count(),0);
   await medication.locator('summary').filter({hasText:'Add confirmed schedule'}).click();
   await medication.getByLabel('Medicine / schedule name',{exact:true}).fill('Existing schedule');
   await medication.getByLabel('Exact clinician-provided instructions',{exact:true}).fill('User confirmed clinician instructions');
   await medication.getByLabel('First date and time',{exact:true}).fill('2026-10-09T08:00');
   await medication.getByRole('button',{name:'Add another confirmed time',exact:true}).click();
   await medication.getByLabel('First date and time',{exact:true}).nth(1).fill('2026-10-09T20:00');
   await medication.locator('form').filter({has:page.getByLabel('Medicine / schedule name',{exact:true})}).locator('button[type=submit]').click();assert.equal(careSaves.length,0);
   await medication.getByLabel('I confirm these existing instructions and schedule, and consent to save this private health information.',{exact:true}).check();
   await medication.locator('form').filter({has:page.getByLabel('Medicine / schedule name',{exact:true})}).locator('button[type=submit]').click();
   await medication.getByText('Temporary save failure',{exact:true}).waitFor();
   assert.equal(await medication.getByLabel('Medicine / schedule name',{exact:true}).inputValue(),'Existing schedule');
   await medication.locator('form').filter({has:page.getByLabel('Medicine / schedule name',{exact:true})}).locator('button[type=submit]').click();
   await medication.getByText('Temporary save failure',{exact:true}).waitFor({state:'hidden'});
   await page.waitForFunction(()=>!document.querySelector('dialog[open]').dataset.saving);
   assert.equal(careSaves.length,2);assert.equal(careSaves[0].client_id,careSaves[1].client_id);
   assert.equal(careSaves[1].confirmed,true);assert.equal(careSaves[1].starts_at.length,2);
   const editInstructions=medication.locator('details').filter({hasText:'Review instructions'});
   await editInstructions.locator('summary').click();
   await editInstructions.getByLabel('Exact clinician-provided instructions',{exact:true}).fill('Reviewed instruction');
   await editInstructions.locator('button[type=submit]').click();assert.equal(careEdits.length,0);
   await editInstructions.getByLabel('I confirm these existing instructions and schedule, and consent to save this private health information.',{exact:true}).check();
   await editInstructions.locator('button[type=submit]').click();
   await medication.getByText('Reviewed instruction',{exact:true}).first().waitFor();assert.equal(careEdits.length,1);
   assert.ok(await medication.evaluate(el=>el.getBoundingClientRect().width<=innerWidth));
   await medication.getByRole('button',{name:'Close',exact:true}).click();
   await page.evaluate(()=>openView('healer'));assert.equal(await page.locator('#healer .care-more').evaluate(e=>e.open),false);assert.equal(await page.locator('#healer > .dw-care > *').count(),3);await page.locator('#healer .care-more > summary').click();await page.locator('[data-food-plan]').click();
   const food=page.getByRole('dialog',{name:'Food choices',exact:true});
   await food.getByLabel('Meal name',{exact:true}).fill('My choice <script>unsafe</script>');await food.getByLabel('Known ingredients (one per line)',{exact:true}).fill('rice');await food.getByLabel('Estimated cost (optional)',{exact:true}).fill('20');
   await food.getByLabel('I checked the entered options and ingredients',{exact:true}).check();
   await food.getByRole('button',{name:'Preview',exact:true}).click();
   await food.getByRole('button',{name:'Save plan',exact:true}).click();assert.equal(foodSaves,0);
   await food.getByLabel('Store this plan including any health restrictions I entered',{exact:true}).check();
   await food.getByRole('button',{name:'Save plan',exact:true}).click();
   await food.getByRole('button',{name:'Delete',exact:true}).waitFor();assert.equal(foodSaves,1);assert.equal(await food.locator('script').count(),0);
   assert.ok(await food.evaluate(el=>el.getBoundingClientRect().width<=innerWidth));
   await food.getByRole('button',{name:'Close',exact:true}).click();await page.locator('[data-care-share]').click();
   const share=page.getByRole('dialog',{name:'Care sharing',exact:true});await share.getByText('Clinical beta is off. Existing access can still be revoked.',{exact:true}).waitFor();
   await share.getByRole('button',{name:'Revoke access',exact:true}).click();assert.equal(sharedStatus,'pending');
   await share.getByRole('button',{name:'Confirm: Revoke access',exact:true}).click();await share.getByText(/Revoked/).waitFor();assert.equal(sharedStatus,'revoked');
   await share.getByRole('button',{name:'Close',exact:true}).click();
   // Full hierarchy, keyboard/collapse and PNG export use real DOM/canvas.
   await page.evaluate(()=>{openView('mindmaps');const root={id:'root',label:'Root',desc:String.raw`Overview \(\frac{1}{2}\)`,children:Array.from({length:4},(_,i)=>({id:'p'+i,label:'Branch '+i,desc:'Description',children:Array.from({length:5},(_,j)=>({id:'s'+i+j,label:'Detail '+j,desc:'ગુજરાતી example'}))}))};state.activeMindmap={topic:'Fixture',data:{root}};displayMindmap(state.activeMindmap)});
   assert.equal(await page.locator('.mm-node').count(),25);
   const mapFit=await page.evaluate(()=>({scale:state.mmZoom,w:state.mmLayout.width*state.mmZoom,h:state.mmLayout.height*state.mmZoom,vw:document.querySelector('#mmViewport').clientWidth,vh:document.querySelector('#mmViewport').clientHeight}));assert.ok(mapFit.scale>=12/14&&mapFit.scale<=1,'Opening a map preserves readable labels');const pan=await page.evaluate(()=>{const vp=document.querySelector('#mmViewport');vp.scrollLeft=1e6;vp.scrollTop=1e6;return {x:vp.scrollLeft,y:vp.scrollTop,w:vp.scrollWidth,h:vp.scrollHeight}});assert.ok(pan.x>0&&pan.y>0,'All map regions remain reachable by scrolling');
   assert.equal(await page.locator('.mm-desc mfrac').count(),1);
   await page.getByRole('button',{name:'Collapse Branch 0',exact:true}).click();assert.equal(await page.locator('.mm-node').count(),20);
   await page.getByRole('button',{name:'Expand Branch 0',exact:true}).click();assert.equal(await page.locator('.mm-node').count(),25);
   const download=page.waitForEvent('download');await page.evaluate(()=>exportMindmapPng());const png=await download;
   const bytes=fs.readFileSync(await png.path());assert.equal(bytes.toString('ascii',1,4),'PNG');assert.ok(bytes.readUInt32BE(16)>1000&&bytes.readUInt32BE(20)>1000);

   await page.evaluate(()=>openView('overview'));
   assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),'Dashboard must fit mobile width');
   await page.evaluate(()=>openView('tasks'));await page.waitForFunction(()=>state.loadedSections?.has('tasks'));
   await page.evaluate(()=>openView('overview'));
   await page.locator('#todayTasks').getByRole('button',{name:'Complete',exact:true}).click();
   await page.locator('#todayTasks .hub-task').waitFor({state:'detached'});
   assert.equal(await page.locator('#todayFocusTitle').textContent(),'A little space to begin.','Completing the focused task removes the stale focus title');
   await page.locator('#todayFocusStart').click();
   assert.ok(await page.locator('#tasks').isVisible(),'Empty focus leads to the working planner');
   await page.evaluate(()=>openView('tasks'));
   await page.locator('#tasks').getByRole('button',{name:'Completed',exact:true}).click();
   await page.locator('#tasks .item.done').waitFor();
   await page.addInitScript(()=>addEventListener('DOMContentLoaded',()=>document.getElementById('newChat')?.click()));
   await page.goto(base+'/chat?conversation=7');
   await page.waitForFunction(()=>!document.querySelector('#chatInput').disabled);await page.locator('#chatInput').fill('Draft typed while history loads');assert.equal(await page.locator('#sendButton').isDisabled(),true,'Send waits for consistent saved history');
   await page.locator('.message.user').waitFor();assert.equal(await page.locator('#chatInput').inputValue(),'Draft typed while history loads');await page.locator('#chatInput').fill('');
   assert.equal(historyWhileProfilePending,true,'History should load concurrently with the profile');
   const math=await page.evaluate(()=>{const box=document.createElement('div');document.body.append(box);SaathiMarkup.render(box,"## Study\n- First\n- Second\n\n\\(P(E)=\\frac{1}{\\sqrt{4}}\\)\n\\[\\frac{a+b}{c}\\]\nBare: \\frac{x}{y}\n`\\frac{x}{y}`\n<img src=x onerror=alert(1)>\n\\(\\href{javascript:alert(1)}{x}\\)\n\n```js\nconst x = 1;\n```");const result={fractionFont:parseFloat(getComputedStyle(box.querySelector('mfrac').closest('.math-inline')).fontSize),fractions:box.querySelectorAll('mfrac').length,roots:box.querySelectorAll('msqrt').length,heading:box.querySelector('h2')?.textContent,list:box.querySelectorAll('li').length,code:box.querySelector('pre code')?.textContent,unsafe:box.querySelectorAll('img,script,a[href^="javascript:"]').length};box.remove();return result});
   const formatting=await page.evaluate(()=>{const box=document.createElement('div');SaathiMarkup.render(box,'#### Recall\n\n---\n###### Details');return{head:box.querySelector('h4')?.textContent,detail:box.querySelector('h6')?.textContent,rules:box.querySelectorAll('hr').length,front:parseFlashcards('[FLASHCARDS]\nFront: DNA question?\n---\nBack: Answer\n[/FLASHCARDS]').cards[0].front}});assert.deepEqual(formatting,{head:'Recall',detail:'Details',rules:1,front:'DNA question?'});
   const table=await page.evaluate(()=>{const box=document.createElement('div');SaathiMarkup.render(box,'| Formula | Meaning |\n| --- | --- |\n| $P(A|B)=\\frac{P(A\\cap B)}{P(B)}$ | Conditional |\n| \\(P(A|B)\\) | `a|b` |');return{columns:[...box.querySelectorAll('tbody tr')].map(row=>row.children.length),formulas:box.querySelectorAll('math').length,raw:box.textContent.includes('$'),errors:box.querySelectorAll('.math-error').length}});assert.deepEqual(table,{columns:[2,2],formulas:2,raw:false,errors:0});
   const nestedMath=await page.evaluate(()=>{
    const box=document.createElement('div');box.className='message-content';document.body.append(box);
    SaathiMarkup.render(box,['**Sample space ($S$):**','*Probability: $\\frac{3}{6}=\\frac{1}{2}$*','__Given \\(A\\)__ and _\\(B\\)_','**Literal `$S$` and \\$5**','**<img src=x onerror=alert(1)>**'].join('\n\n'));
    const fraction=box.querySelector('mfrac').closest('.math-inline');
    const result={strongMath:box.querySelectorAll('strong math').length,emMath:box.querySelectorAll('em math').length,code:box.querySelector('code')?.textContent,codeMath:box.querySelectorAll('code math').length,literal:box.querySelectorAll('strong')[2].textContent,unsafe:box.querySelectorAll('img,script,a[href^="javascript:"]').length,errors:box.querySelectorAll('.math-error').length,verticalOverflow:fraction.scrollHeight>fraction.clientHeight+1};
    const geometry={client:[fraction.clientWidth,fraction.clientHeight],scroll:[fraction.scrollWidth,fraction.scrollHeight],mathHeight:fraction.querySelector('math').getBoundingClientRect().height};
    box.remove();return{result,geometry};
   });
   assert.deepEqual(nestedMath.result,{strongMath:2,emMath:2,code:'$S$',codeMath:0,literal:'Literal $S$ and $5',unsafe:0,errors:0,verticalOverflow:false},'Fraction geometry: '+JSON.stringify(nestedMath.geometry));
   const failedCard=await page.evaluate(()=>visibleMessage({failed:true,content:'[FLASHCARDS]\nFront: Wrong?\nBack: Wrong.\n[/FLASHCARDS]'}));assert.ok(!failedCard.flash,'A failed generation must not look like saved cards');
   await page.evaluate(()=>{state.messages.push({id:991,role:'assistant',content:'[FLASHCARDS]\nFront: Template reading?\nBack: 5′→3′\n[/FLASHCARDS]',study_progress:{kind:'flashcards',progress:{known_indices:[0]}}});renderMessages()});
   await page.getByRole('button',{name:'Correct card',exact:true}).click();await page.getByLabel('Back',{exact:true}).fill('3′→5′');await page.getByRole('button',{name:'Save correction',exact:true}).click();await page.getByText('Corrected by you',{exact:false}).waitFor();assert.equal(cardCorrections,1);
   await page.getByRole('button',{name:'Reveal flashcard answer',exact:true}).click();assert.match(await page.locator('.flashcard-text').textContent(),/3′→5′/);
   await page.evaluate(()=>{state.messages=state.messages.filter(message=>message.id!==991);renderMessages()});
   assert.ok(math.fractionFont>=20,'Inline fractions stay readable within dense text');assert.equal(math.fractions,3);assert.equal(math.roots,1);assert.equal(math.heading,'Study');assert.equal(math.list,2);assert.equal(math.code,'const x = 1;');assert.equal(math.unsafe,0);
   await page.evaluate(()=>{const host=document.createElement('div');host.id='audit-note-link';document.body.append(host);SaathiChatActions.attach(host,{id:996,role:'assistant',content:'Saved to Notes. <SAATHI_ACTION>{"kind":"note","title":"Search","text":"Search"}</SAATHI_ACTION>',action_receipt:{kind:'note',resource_id:3},action_resource:{id:3}})});
   await page.locator('#audit-note-link a').click();await page.waitForFunction(()=>document.querySelector('[data-qn="content"]')?.value==='Search');assert.equal(await page.locator('[data-qn="content"]').inputValue(),'Search');assert.equal(new URL(page.url()).pathname,'/chat','Exact note opens without navigating to Today');await page.locator('[data-qn="close"]').click();await page.locator('#audit-note-link').evaluate(node=>node.remove());

   assert.equal(await page.locator('#chatMode').evaluate(node=>Boolean(node.closest('.composer-actions'))),true,'Mode shares the compact composer action row');
   const layout=await page.evaluate(()=>{const composer=document.querySelector('#composer').getBoundingClientRect(),toolbar=document.querySelector('.composer-toolbar').getBoundingClientRect(),send=document.querySelector('#sendButton').getBoundingClientRect();return {height:composer.height,bottom:composer.bottom,toolbarBottom:toolbar.bottom,sendBottom:send.bottom,overflow:document.documentElement.scrollWidth>innerWidth+1}});
   assert.ok(layout.height<165,'Empty composer leaves room for the conversation: '+JSON.stringify(layout));assert.ok(layout.toolbarBottom<=layout.bottom&&layout.sendBottom<=layout.bottom,'Mode and Send remain inside the compact composer');assert.equal(layout.overflow,false,'Chat fits every screen width');
   await page.locator('.quick-actions summary').click();assert.equal(await page.locator('.quick-action').first().isVisible(),true,'Learning actions remain reachable');await page.locator('.quick-actions summary').click();

   assert.equal(requests.filter(p=>p==='/api/conversations/7/messages').length,1,'Startup history must not be fetched twice');
   assert.equal(await page.locator('#voiceOpenBtn').evaluate(el=>Boolean(el.closest('#composer'))),true,'Voice belongs in composer');
   if(width>900){const sidebar=await page.locator('#sidebar').boundingBox(),main=await page.locator('.main').boundingBox();assert.ok(sidebar.x+sidebar.width<=main.x+1,'Desktop sidebar sits beside the conversation without overlapping it');await page.locator('#closeSidebar').click();assert.equal(await page.locator('#sidebar').isVisible(),false);await page.locator('#openSidebar').click()}

   await page.locator('#chatInput').fill('Keep my draft');
   await page.route('**/api/conversations/7/messages?limit=100',route=>route.fulfill({status:503,contentType:'application/json',body:JSON.stringify({error:'Temporary fixture failure'})}));
   await page.evaluate(()=>selectConversation(7));
   await page.getByRole('button',{name:'Retry loading conversation',exact:true}).waitFor();
   assert.equal(await page.locator('#chatInput').isDisabled(),false,'Typing remains usable after a history failure');
   assert.equal(await page.locator('#sendButton').isDisabled(),true);
   await page.unroute('**/api/conversations/7/messages?limit=100');
   await page.getByRole('button',{name:'Retry loading conversation',exact:true}).click();
   await page.locator('.message.user').waitFor();
   assert.equal(await page.locator('#chatInput').inputValue(),'Keep my draft');
   await page.reload();await page.locator('.message.user').waitFor();
   assert.equal(await page.locator('#chatInput').inputValue(),'Keep my draft','Draft survives browser reload');
   await page.locator('#chatInput').fill('');
   assert.equal(await page.locator('.message.user .message-content').textContent(),'Search');
   assert.equal(await page.locator('.memory-used summary').textContent(),'Sources read when this reply was created: 2');
   for(const [locale,read,requested,preparing,pageLabel] of [
    ['gu','આ જવાબ બનાવતી વખતે વાંચેલા સ્ત્રોત','આ જવાબ માટે માંગેલી Classroom માહિતી','તમારી ફાઇલ તૈયાર થઈ રહી છે…','પાનું'],
    ['hi','यह जवाब बनाते समय पढ़े गए स्रोत','इस जवाब के लिए माँगी गई Classroom जानकारी','आपकी फ़ाइल तैयार हो रही है…','पृष्ठ']
   ]){
    await page.evaluate(locale=>SaathiI18n.setLanguage(locale),locale);
    await page.evaluate(()=>{renderMessages();showRequestProgress('Preparing your upload…')});
    assert.equal(await page.locator('.memory-used summary').textContent(),read+': 2');
    assert.deepEqual(await page.locator('.memory-used li').allTextContents(),[requested,'Search'],'Only the fixed Classroom metadata is translated');
    assert.equal(await page.locator('#uploadCopy').textContent(),preparing);
    assert.equal(await page.locator('.message.user .message-content').textContent(),'Search');
    await page.evaluate(()=>{const n=state.messages.length;state.messages.push({role:'user',attachments:[{id:31,name:'Search.pdf',mime_type:'application/pdf',page_count:2}]});const body=document.createElement('div');body.id='localized-citation-fixture';addDisclosures(body,{source_pages:[{name:'Search.pdf',page:2},{name:'Search.pdf',page:99}]},n+1);state.messages.pop();document.body.append(body)});
    assert.equal(await page.locator('#localized-citation-fixture a').count(),1,'Only a valid page of the owned file becomes a link');
    assert.equal(await page.locator('#localized-citation-fixture a').textContent(),'Search.pdf · '+pageLabel+' 2');
    assert.equal(await page.locator('#localized-citation-fixture a').getAttribute('href'),'/api/attachments/31/view#page=2');
    await page.locator('#localized-citation-fixture').evaluate(node=>node.remove());
    const native=locale==='gu'?{welcome:'આજે સાથી કેવી રીતે મદદ કરી શકે?',prompt:'આ અઠવાડિયા માટે ધ્યાનથી અનુસરી શકાય તેવી અભ્યાસ યોજના બનાવવામાં મદદ કરો.',today:'આજ',remove:'Search.pdf દૂર કરો',pages:'શોધી શકાય એવાં 2 પાનાં'}:{welcome:'आज साथी कैसे मदद कर सकता है?',prompt:'इस सप्ताह के लिए ध्यान से पढ़ने की योजना बनाने में मदद करें।',today:'आज',remove:'Search.pdf हटाएँ',pages:'2 खोजने योग्य पृष्ठ'};
    await page.evaluate(()=>{document.body.append(emptyView());renderConversations();state.selectedFiles=[{file:new File(['fixture'],'Search.pdf',{type:'application/pdf'})}];renderSelectedFiles();const fixture=messageElement({id:800,role:'user',content:'Search',attachments:[{id:31,name:'Search.pdf',mime_type:'application/pdf',size_bytes:7,extracted_page_count:2,url:'/api/attachments/31'}]},0);fixture.id='native-file-fixture';document.body.append(fixture)});
    await page.waitForFunction(text=>document.querySelector('.empty h2')?.textContent===text,native.welcome);
    assert.equal(await page.locator('.empty .prompt small').nth(1).textContent(),native.prompt);
    await page.locator('.empty .prompt').nth(1).click();assert.equal(await page.locator('#chatInput').inputValue(),native.prompt,'The selected prompt is sent in the saved language');
    assert.equal(await page.evaluate(()=>formatDateGroup(new Date().toISOString())),native.today);
    assert.equal(await page.locator('.selected-file button').getAttribute('aria-label'),native.remove);
    assert.ok((await page.locator('#native-file-fixture .attachment-copy small').textContent()).includes(native.pages));
    assert.equal(await page.locator('#native-file-fixture .attachment-copy b').textContent(),'Search.pdf','Literal filenames stay untouched');
    assert.equal(await page.locator('#native-file-fixture .message-name').textContent(),locale==='gu'?'તમે':'आप');
    assert.notEqual(await page.locator('#closeSidebar').getAttribute('aria-label'),'Collapse sidebar');
    assert.notEqual(await page.locator('.conversation-menu').first().getAttribute('aria-label'),'Options for Search');
    await page.evaluate(()=>{document.querySelector('.empty').remove();document.querySelector('#native-file-fixture').remove();clearSelectedFiles();el.input.value='';updateComposer()});

   }
   await page.evaluate(()=>{setBusy(false);return SaathiI18n.setLanguage('en')});
   await page.evaluate(()=>SaathiI18n.setLanguage('gu'));
   await page.waitForFunction(()=>Array.from(document.querySelectorAll('.message-tool')).some(el=>el.textContent==='બદલીને ફરી મોકલો'));
   assert.equal(await page.locator('.message.user .message-content').textContent(),'Search');
   assert.ok((await page.locator('.message.assistant .message-content').textContent()).includes('not executable'));
   await page.getByRole('button',{name:'બદલીને ફરી મોકલો',exact:true}).click();
   await page.locator('#editMessageText').fill('Revised question');await page.locator('#cancelMessageEdit').click();
   assert.equal(await page.locator('.message.user').count(),1);
   assert.equal(await page.locator('.message-more').count(),1);
   assert.equal(await page.locator('.message-more[open]').count(),0);
   assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),'Chat must fit mobile width');
   let releaseCreate;conversationCreateGate=new Promise(resolve=>{releaseCreate=resolve});
   const creatingRequest=page.waitForRequest(request=>new URL(request.url()).pathname==='/api/conversations'&&request.method()==='POST');
   const creating=page.evaluate(()=>createConversation());await creatingRequest;
   try{
    assert.equal(await page.locator('#attachButton').isDisabled(),true,'A file cannot be selected while the new chat would discard it');
    assert.equal(await page.locator('#fileInput').isDisabled(),true,'The native file input follows the same readiness guard');
   }finally{releaseCreate();await creating;conversationCreateGate=null}
   assert.equal(await page.locator('#attachButton').isDisabled(),false,'Attachment selection resumes after the conversation exists');
   await page.waitForFunction(()=>document.querySelector('#archiveLabel').textContent==='આર્કાઇવ કરેલી વાતચીતો');
   assert.equal(await page.locator('.message').count(),0);
   assert.ok(!requests.includes('/api/conversations/8/messages'),'A newly created empty chat needs no extra history request');
   await page.locator('#chatInput').fill('Hello');
   let releaseReply;
   const replyGate=new Promise(resolve=>{releaseReply=resolve});
   await page.route('**/api/conversations/8/messages/stream',async route=>{
    await replyGate;
    await route.fulfill({contentType:'application/x-ndjson',body:JSON.stringify({type:'error',error:'Fixture finished'})+'\n'});
   });
   await page.locator('#sendButton').click();
   await page.locator('.request-stage').waitFor();assert.equal(await page.locator('.request-stage').textContent(),'Checking…','No AI-wait claim before the server identifies the work');assert.equal(await page.locator('.thinking-dots').count(),0);
   await page.evaluate(()=>setRequestStage('classroom'));
   assert.equal(await page.locator('.request-stage').textContent(),'Checking Google Classroom…');
   assert.equal(await page.locator('#sendButton').isDisabled(),false,'Stop stays available while Classroom is checked');
   assert.equal(await page.locator('#uploadStatus').isVisible(),false,'Text replies must not show upload status');
   assert.equal(await page.locator('.upload-progress').isVisible(),false,'No stray progress line');
   await page.screenshot({path:'/tmp/saathi-chat-'+width+'.png'});
   await page.locator('#chatInput').fill('Draft while waiting');await page.locator('#sendButton').click();
   await page.locator('.message.failed').waitFor();assert.equal(await page.locator('#chatInput').inputValue(),'Draft while waiting','Stop preserves a newer draft');releaseReply();
   await page.evaluate(()=>SaathiI18n.setLanguage('en'));
   await page.getByRole('button',{name:'Tools',exact:true}).click();
   let toolsDialog=page.getByRole('dialog',{name:'Tools',exact:true});
   await toolsDialog.getByText('Open workspace · keeps chat open',{exact:true}).click();
   assert.equal(await toolsDialog.getByRole('link',{name:'Study & Classroom',exact:true}).getAttribute('href'),'/dashboard#study');
   assert.equal(await toolsDialog.getByRole('link',{name:'Mock tests',exact:true}).getAttribute('target'),'_blank');
   assert.equal(await toolsDialog.getByRole('button',{name:'Deep study',exact:true}).isDisabled(),true);
   await toolsDialog.getByRole('button',{name:'Quiz',exact:true}).click();
   assert.equal(await page.locator('#chatMode').inputValue(),'quiz');
   await page.locator('#chatInput').fill('Keep this draft');
   await page.getByRole('button',{name:'Tools',exact:true}).click();
   await page.getByRole('dialog',{name:'Tools',exact:true}).getByText('Save with a preview',{exact:true}).click();
   await page.getByRole('dialog',{name:'Tools',exact:true}).getByRole('button',{name:'Add a task',exact:true}).click();
   assert.equal(await page.locator('#chatInput').inputValue(),'Keep this draft');
   await page.locator('#chatInput').fill('');
   await page.getByRole('button',{name:'Tools',exact:true}).click();
   await page.getByRole('dialog',{name:'Tools',exact:true}).getByText('Save with a preview',{exact:true}).click();
   await page.getByRole('dialog',{name:'Tools',exact:true}).getByRole('button',{name:'Add a task',exact:true}).click();
   assert.match(await page.locator('#chatInput').inputValue(),/Help me add a Planner task/);
   assert.equal(await page.locator('#chatMode').inputValue(),'normal');
   await page.locator('#chatInput').fill('');
   assert.equal(requests.filter(p=>p==='/chat-study.js').length,0,'Study generation loads only when requested');
   await page.getByRole('button',{name:'Tools',exact:true}).click();
   await page.getByRole('dialog',{name:'Tools',exact:true}).getByRole('button',{name:'Mock Test',exact:true}).click();
   const inlineTest=page.getByRole('dialog',{name:'Mock Test',exact:true});
   await inlineTest.getByLabel('Topic',{exact:true}).fill('Fractions');
   assert.equal(inlineGenerations,0,'Opening a tool never spends an AI call');
   await inlineTest.getByText('2 mock tests remaining · Resets 2026-10-15, 05:30 AM · Asia/Kolkata',{exact:true}).waitFor();
   await inlineTest.getByRole('button',{name:'Generate and save',exact:true}).click();
   await inlineTest.getByText('Fixture creation failed',{exact:true}).first().waitFor();
   assert.equal(await inlineTest.getByLabel('Topic',{exact:true}).inputValue(),'Fractions');
   await inlineTest.getByRole('button',{name:'Generate and save',exact:true}).click();
   await inlineTest.getByRole('radio',{name:'A. Choice A 1',exact:true}).check();
   await inlineTest.getByRole('button',{name:'Submit answers',exact:true}).click();
   await inlineTest.getByRole('heading',{name:'Score: 1 / 5',exact:true}).waitFor();
   assert.equal(inlineGenerations,2);assert.equal(inlineSubmits,1);
   assert.equal(await inlineTest.locator('script').count(),0);
   assert.equal(new URL(page.url()).pathname,'/chat');
   await inlineTest.getByRole('button',{name:'Close',exact:true}).click();
   await page.getByRole('button',{name:'Tools',exact:true}).click();
   await page.getByRole('dialog',{name:'Tools',exact:true}).getByRole('button',{name:'Mock Test',exact:true}).click();
   const reopenedTest=page.getByRole('dialog',{name:'Mock Test',exact:true});
   await reopenedTest.getByText('Ready',{exact:true}).waitFor();
   await reopenedTest.getByRole('button',{name:'Open result',exact:true}).click();
   await reopenedTest.getByRole('heading',{name:'Score: 1 / 5',exact:true}).waitFor();
   assert.equal(inlineGenerations,2,'Reopening a saved job does not regenerate');
   await reopenedTest.getByRole('button',{name:'Close',exact:true}).click();
   await page.getByRole('button',{name:'Tools',exact:true}).click();
   await page.getByRole('dialog',{name:'Tools',exact:true}).getByRole('button',{name:'Mindmap',exact:true}).click();
   const inlineMap=page.getByRole('dialog',{name:'Mindmap',exact:true});
   await inlineMap.getByLabel('Topic',{exact:true}).fill('Newton laws');
   await inlineMap.getByRole('button',{name:'Generate and save',exact:true}).click();
   await inlineMap.getByText('Chat map branch',{exact:true}).waitFor({timeout:5000}).catch(async error=>{
    console.error('INLINE_MAP_FAILURE',JSON.stringify({width,errors,dialogs:await page.locator('dialog[open]').allTextContents(),requests:requests.slice(-20)}));
    throw error;
   });
   assert.equal(await inlineMap.locator('script').count(),0);
   assert.equal(requests.filter(p=>p==='/chat-study.js').length,1,'Both tools reuse one lazy module');
   await inlineMap.getByRole('button',{name:'Close',exact:true}).click();
   const composerDraft=await page.locator('#chatInput').inputValue();
   await page.locator('#chatInput').fill('Search');
   for(const [lang,tools,map,topic,close,inputLabel,sendLabel] of [['gu','સાધનો','માઇન્ડમેપ','વિષય','બંધ કરો','Saathiને સંદેશ લખો','સંદેશ મોકલો'],['hi','साधन','माइंडमैप','विषय','बंद करें','साथी को संदेश भेजें','संदेश भेजें']]){
    await page.evaluate(lang=>SaathiI18n.setLanguage(lang),lang);
    assert.equal(await page.locator('#chatInput').getAttribute('aria-label'),inputLabel);
    assert.equal(await page.locator('#chatInput').inputValue(),'Search','Language changes cannot translate the student draft');
    await page.evaluate(()=>updateComposer());
    assert.equal(await page.locator('#sendButton').getAttribute('aria-label'),sendLabel,'Typing must keep the localized accessible name');
    await page.getByRole('button',{name:tools,exact:true}).click();
    await page.getByRole('dialog',{name:tools,exact:true}).getByRole('button',{name:map,exact:true}).click();
    await page.getByRole('dialog',{name:map,exact:true}).getByLabel(topic,{exact:true}).waitFor();
    await page.getByRole('dialog',{name:map,exact:true}).getByRole('button',{name:close,exact:true}).click();
   }
   await page.evaluate(()=>SaathiI18n.setLanguage('en'));
   await page.locator('#chatInput').fill(composerDraft);
   const personalLoads=requests.filter(p=>p==='/personal-context.js').length;
   await page.getByRole('button',{name:'Tools',exact:true}).click();
   await page.getByRole('dialog',{name:'Tools',exact:true}).getByRole('button',{name:'Plan for an exam',exact:true}).click();
   const inlineExam=page.getByRole('dialog',{name:'Plan for an exam',exact:true});
   await inlineExam.getByLabel('Confirmed exam date',{exact:true}).waitFor();
   assert.equal(new URL(page.url()).pathname,'/chat','Exam planning keeps the conversation open');
   assert.equal(requests.filter(p=>p==='/personal-context.js').length,personalLoads+1);
   await inlineExam.getByRole('button',{name:'Close',exact:true}).click();
   await page.getByRole('button',{name:'Tools',exact:true}).click();
   await page.getByRole('dialog',{name:'Tools',exact:true}).getByRole('button',{name:'Plan for an exam',exact:true}).click();
   await page.getByRole('dialog',{name:'Plan for an exam',exact:true}).getByLabel('Confirmed exam date',{exact:true}).waitFor();
   assert.equal(requests.filter(p=>p==='/personal-context.js').length,personalLoads+1,'Planner assets are reused');
   await page.getByRole('dialog',{name:'Plan for an exam',exact:true}).getByRole('button',{name:'Close',exact:true}).click();
   await page.getByRole('button',{name:'Chat context',exact:true}).click();
   let chatContext=page.getByRole('dialog',{name:'Chat context',exact:true});
   assert.equal(await chatContext.getByLabel('Planner tasks',{exact:true}).isChecked(),false);
   assert.equal(await chatContext.getByLabel('Saved notes',{exact:true}).count(),0);
   await chatContext.getByLabel('Planner tasks',{exact:true}).check();await chatContext.getByRole('button',{name:'Save',exact:true}).click();
   await chatContext.getByText('Saved to your account',{exact:true}).waitFor();assert.equal(contextPrefs.tasks,true);assert.equal(contextPrefs.notes,undefined);assert.equal(contextPrefs.classroom,false);
   await chatContext.getByRole('button',{name:'Close',exact:true}).click();
   await page.evaluate(()=>{const box=document.createElement('div');document.querySelector('#messageList').append(box);SaathiChatActions.attach(box,{id:999,content:'Review this <SAATHI_ACTION>{"kind":"task"}</SAATHI_ACTION>'})});
   await page.getByRole('button',{name:'Review save preview',exact:true}).click();
   let actionDialog=page.getByRole('dialog',{name:'Review before saving',exact:true});
   await actionDialog.getByLabel('Title',{exact:true}).fill('Edited chat task');assert.equal(actionSaves,0);
   await actionDialog.getByRole('button',{name:'Save',exact:true}).click();await actionDialog.getByText('Saved to your account',{exact:true}).waitFor();assert.equal(actionSaves,1);
   assert.ok(await actionDialog.evaluate(e=>e.getBoundingClientRect().width<=innerWidth));await actionDialog.getByRole('button',{name:'Close',exact:true}).click();
   await page.evaluate(()=>{const box=document.createElement('div');box.id='confirmed-chat-map';document.querySelector('#messageList').append(box);SaathiChatActions.attach(box,{id:994,content:'Mindmap created and saved.',action_receipt:{kind:'mindmap',resource_id:62},action_resource:{summary:'Saved study map',root:{label:String.raw`\(P(E)\)`,desc:String.raw`## Chance
- Formula: \(\frac{1}{2}\)
<img src=x onerror=alert(1)>`,children:[]}}})});
   assert.equal(await page.locator('#confirmed-chat-map mfrac').count(),1);
   assert.equal(await page.locator('#confirmed-chat-map li').count(),1);
   assert.equal(await page.locator('#confirmed-chat-map img').count(),0);
   await page.evaluate(()=>{const box=document.createElement('div');box.id='failed-markerless-action';document.querySelector('#messageList').append(box);SaathiChatActions.attach(box,{id:993,content:'Failed: Nothing was saved.\nRetry when ready.',action_error:'Nothing was saved.'})});
   assert.equal(await page.locator('#failed-markerless-action').getByRole('button',{name:'Retry',exact:true}).count(),1);
   assert.equal(await page.locator('#failed-markerless-action').getByRole('button',{name:'Review save preview',exact:true}).count(),0);
   const actionWrites=actionSaves;
   await page.evaluate(()=>{const box=document.createElement('div');box.id='confirmed-chat-memory';document.querySelector('#messageList').append(box);SaathiChatActions.attach(box,{id:998,auto_action:true,action_receipt:{kind:'memory',resource_id:12},content:'Details prepared. <SAATHI_ACTION>{"kind":"memory","title":"Home city","text":"Ahmedabad <script>window.injected=true</script>"}</SAATHI_ACTION>'})});
   await page.locator('#confirmed-chat-memory').getByText('Saved · Memory',{exact:true}).waitFor();
   await page.locator('#confirmed-chat-memory summary').click();
   assert.ok((await page.locator('#confirmed-chat-memory').innerText()).includes('Ahmedabad <script>'));
   assert.equal(await page.evaluate(()=>window.injected),undefined);
   assert.equal(actionSaves,actionWrites,'Server-confirmed actions must not be executed again by the browser');
   assert.equal(await page.locator('#confirmed-chat-memory a').getAttribute('href'),'/dashboard?memory=12#memory');
   const reminderStatus=await page.evaluate(()=>{const box=document.createElement('div');document.body.append(box);const past=new Date(Date.now()-86400000).toISOString(),future=new Date(Date.now()+86400000).toISOString(),message={id:990,content:'Reminder saved. <SAATHI_ACTION>'+JSON.stringify({kind:'reminder',title:'Revision',at:past})+'</SAATHI_ACTION>',action_receipt:{kind:'reminder',resource_id:90},action_resource:{title:'Revision',active:true,at:past}};SaathiChatActions.attach(box,message);const overdue=box.textContent;box.replaceChildren();message.action_resource.at=future;SaathiChatActions.attach(box,message);const rescheduled=box.textContent;box.remove();return{overdue,rescheduled}});assert.ok(reminderStatus.overdue.includes('Overdue'));assert.ok(reminderStatus.rescheduled.includes('Scheduled')&&!reminderStatus.rescheduled.includes('Overdue'),'Receipt status uses the current saved schedule');
   await page.evaluate(plan=>{state.messages.push({id:992,role:'assistant',created_at:new Date().toISOString(),auto_action:true,action_error:'Automatic save was not authorised.',content:'Failed: Automatic save was not authorised.\nRetry when ready.\n<SAATHI_ACTION>'+JSON.stringify(plan)+'</SAATHI_ACTION>'});renderMessages()},chatPlan);
   assert.equal(chatPlanSaves,0,'An unsaved preview must wait for user confirmation');
   const planMessage=page.locator('.message[data-message-id="992"]');
   await planMessage.getByRole('button',{name:'Review save preview',exact:true}).click();
   actionDialog=page.getByRole('dialog',{name:'Review before saving',exact:true});
   await actionDialog.getByLabel('Title',{exact:true}).waitFor();
   const planPreview=await actionDialog.innerText();assert.ok(planPreview.includes('Asia/Kolkata')&&planPreview.includes('17')&&planPreview.includes('18'));assert.equal((planPreview.match(/15 minutes/g)||[]).length,2);
   await actionDialog.getByRole('button',{name:'Save',exact:true}).click();await actionDialog.getByText('Saved to your account',{exact:true}).waitFor();
   assert.equal(chatPlanSaves,1);assert.ok(!(await planMessage.innerText()).includes('Failed'));assert.ok(!(await planMessage.innerText()).includes('Not saved'));assert.equal(await planMessage.getByRole('button',{name:'Retry',exact:true}).count(),0);
   assert.equal(await page.evaluate(()=>state.messages.find(message=>message.id===992).action_error),undefined);
   await actionDialog.getByRole('button',{name:'Close',exact:true}).click();
   await page.evaluate(()=>{state.conversations[0].preview='Ready to review <SAATHI_ACTION>{\"kind\":\"task\"}</SAATHI_ACTION>';renderConversations()});
   assert.ok(!(await page.locator('#history').textContent()).includes('SAATHI_ACTION'),'Sidebar previews must hide action metadata');
   const beforeCreate=requests.filter(p=>p==='/api/conversations').length;
   if(!await page.locator('#newChat').isVisible())await page.locator('#openSidebar').click();
   await page.locator('#newChat').click();
   assert.equal(await page.locator('#chatInput').isDisabled(),true);assert.equal(await page.locator('#sendButton').isDisabled(),true);
   await page.evaluate(()=>document.querySelector('#newChat').click());
   await page.waitForFunction(()=>state.creatingConversation===false&&state.activeId===8);
   assert.equal(requests.filter(p=>p==='/api/conversations').length-beforeCreate,1,'Double-click must create only one conversation');
   await page.goto(base+'/dashboard#mocktests');await page.waitForFunction(()=>typeof renderTestResults==='function');
   await page.evaluate(()=>renderTestResults({attempt:{score:1,total_questions:1,accuracy_percentage:100,time_spent_seconds:20,excluded_questions:1,created_at:new Date().toISOString()},review:[{id:1,question:'Dice probability',options:{B:'\\frac{5}{108}',C:'10/216'},user_answer:'C',correct_answer:'B',accepted_answers:['B','C'],graded:true,is_correct:true,answer_verified:true,explanation:'10 equally likely favourable outcomes out of 216.'},{id:2,question:'Unresolved key',options:{A:'First',B:'Second'},user_answer:'B',correct_answer:null,graded:false,is_correct:null,quality_note:'The key and explanation disagree.'}]}));
   assert.equal(await page.locator('#reviewQuestionsList .review-status-pill.wrong').count(),0);assert.equal(await page.locator('#reviewQuestionsList .review-status-pill.correct').count(),1);assert.match(await page.locator('#reviewQuestionsList').textContent(),/Not scored/);assert.ok(await page.locator('#reviewQuestionsList mfrac').count()>0);assert.equal(await page.locator('#resHeroTitle').textContent(),'Practice review');assert.equal(await page.locator('[onclick="downloadScorecardPng()"]').count(),1);
   await page.goto(base+'/dashboard?task=1#tasks');await page.waitForFunction(()=>state.linkedResourceHandled?.has('task'));assert.equal(await page.locator('[data-record-kind="task"][data-record-id="1"]').count(),1);assert.equal(await page.evaluate(()=>state.currentView),'tasks');
   const mapGenerations=requests.filter(url=>url==='/api/mindmaps/generate').length;
   await page.goto(base+'/dashboard?mindmap=62#mindmaps');
   await page.locator('#mindmapViewerWrap').waitFor({state:'visible'});
   assert.equal(await page.locator('#mindmapActiveTitle').textContent(),'Exact linked map');
   assert.ok((await page.locator('#mmNodes').textContent()).includes('Exact linked root'));
   assert.equal(requests.filter(url=>url==='/api/mindmaps/62').length,1,'A cold receipt link loads the exact record once');
   assert.equal(requests.filter(url=>url==='/api/mindmaps/generate').length,mapGenerations,'Reopening never regenerates or charges quota');
   await page.goto(base+'/');
   await page.locator('#heroCta').waitFor();
   for(const screen of [320,360,390,768,1280]){
    await page.setViewportSize({width:screen,height:900});
    const fit=await page.evaluate(()=>({width:innerWidth,scroll:document.documentElement.scrollWidth,overflow:[...document.querySelectorAll('body *')].map(el=>({tag:el.tagName,cls:el.className,rect:el.getBoundingClientRect()})).filter(x=>x.rect.width&&x.rect.height&&(x.rect.right>innerWidth+1||x.rect.left< -1)).slice(0,12).map(x=>({tag:x.tag,cls:x.cls,left:x.rect.left,right:x.rect.right}))}));
    assert.ok(fit.scroll<=fit.width+1,'Landing must fit '+screen+'px: '+JSON.stringify(fit));
    assert.ok(await page.locator('#heroCta').isVisible(),'Primary action remains visible');
    assert.ok(await page.locator('#heroLogin').isVisible(),'Login is available without opening the mobile menu');
    assert.equal(await page.locator('#heroLogin').getAttribute('href'),'/account?tab=login');
   }
   await page.locator('[data-lang="gu"]').click();
   await page.waitForFunction(()=>document.getElementById('navCta').textContent==='Saathi ખોલો →');
   assert.equal(await page.locator('#how h2').textContent(),'પહેલી મિનિટથી ઉપયોગી.');assert.equal(await page.locator('#pricing .section-head h2').textContent(),'મફતમાં શરૂ કરો. વધારાનાં સાધનો ઉપલબ્ધ થાય ત્યારે upgrade કરો.');
   assert.ok((await page.locator('#heroLogin').textContent()).includes('લૉગ'));
   assert.match(await page.locator('#heroH1').textContent(),/થોડી સ્પષ્ટતા/);assert.equal(await page.locator('.hero-stage').getAttribute('aria-label'),'Saathiનું ડેશબોર્ડ અને reminderનું પૂર્વાવલોકન');assert.match(await page.locator('[data-theme-toggle]').first().getAttribute('aria-label'),/દેખાવ/);
   await page.locator('[data-lang="hi"]').click();
   assert.equal(await page.locator('#navCta').textContent(),'Saathi खोलें →');
   assert.equal(await page.locator('#how h2').textContent(),'पहले मिनट से उपयोगी।');
   assert.ok((await page.locator('#heroLogin').textContent()).includes('लॉग'));
   assert.match(await page.locator('#heroH1').textContent(),/थोड़ी स्पष्टता/);assert.equal(await page.locator('.hero-stage').getAttribute('aria-label'),'Saathi डैशबोर्ड और रिमाइंडर का पूर्वावलोकन');
   await page.emulateMedia({reducedMotion:'reduce'});
   assert.equal(await page.locator('.reveal').first().evaluate(el=>getComputedStyle(el).opacity),'1','Reduced motion keeps marketing content visible');
   assert.deepEqual(errors,[],'No uncaught errors in real pages');
   console.log('PASS: real Chromium '+width+'px, deferred tools/retry, English/Gujarati, private user text, focus reopen, search escaping and chat edit cancellation');
   await context.close();
  }
 }finally{await browser.close()}
})().catch(error=>{console.error(error);process.exitCode=1});
