// Exercise the real pages in Chromium with owned, local fixture responses only.
const {chromium}=require('playwright');
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const root=path.resolve('.'),base='http://localhost:8765';
const original={id:1,role:'user',content:'Search',created_at:'2026-09-19T08:00:00Z',attachments:[],ai_mode:'normal'};
const answer={id:2,role:'assistant',content:'Search <script>not executable</script> ગુજરાતી',created_at:original.created_at,source_pages:[]};
const task={id:1,title:'Search',details:'Saved user writing',priority:'high',completed:false,due_at:null};
(async()=>{
 const browser=await chromium.launch({headless:true,...(process.env.CHROMIUM_EXECUTABLE?{executablePath:process.env.CHROMIUM_EXECUTABLE,args:['--no-sandbox','--disable-dev-shm-usage']}: {})});
 try{
  for(const width of [1280,768,390,360,320]){
   const context=await browser.newContext({viewport:{width,height:900},serviceWorkers:'block'}),page=await context.newPage(),errors=[],requests=[];
   let chatProfilePending=false,historyWhileProfilePending=false,profileFields=[],planSaves=0,replanSaves=0,classroomAdds=0,classroomConnected=true,careSaves=[],careEdits=[],foodSaves=0,foodPreview=null,sharedStatus="pending",classroomExplains=0,classroomSchedules=0,ocrReads=0;
   let actionSaves=0,contextPrefs={tasks:false,reminders:false,classroom:false};
   let language='en',focus=null,failMindmaps=true,searches=0,fixtureTasks=[{...task}];
   const user=()=>({id:1,name:'Search',username:'fixture',email:'fixture@example.test',plan:'free',language});
   page.on('pageerror',error=>errors.push(error.message));
   await page.route('**/*',async route=>{
    const url=new URL(route.request().url());if(url.origin!==base)return route.abort();
    const pathname=url.pathname;requests.push(pathname);
    if(pathname==='/dashboard-mindmaps.js'&&failMindmaps){failMindmaps=false;return route.abort()}
    if(pathname.startsWith('/api/')){
     let data={},status=200;const method=route.request().method(),body=()=>route.request().postDataJSON();
     if(pathname==='/api/me'&&new URL(page.url()).pathname==='/chat'){chatProfilePending=true;await new Promise(resolve=>setTimeout(resolve,350));chatProfilePending=false}
     if(pathname==='/api/conversations/7/messages'&&chatProfilePending)historyWhileProfilePending=true;
     if(pathname==='/api/chat-context'){if(method==='PATCH')contextPrefs=body();data={permissions:contextPrefs}}
     else if(pathname==='/api/chat-actions/999'){if(method==='POST'){assert.equal(body().confirmed,true);assert.equal(body().action.title,'Edited chat task');actionSaves++;data={saved:true,receipt:{kind:'task',resource_id:9}}}else data=actionSaves?{saved:true,receipt:{kind:'task',resource_id:9}}:{saved:false,action:{kind:'task',title:'Chat task',text:'User requested details',at:null,priority:'medium',recurrence:'once'}}}
     else if(pathname==='/api/me')data={user:user(),csrf_token:'fixture',chat_modes:[{id:'normal',label:'Normal',description:'A balanced everyday reply'}],chat_attachments:{enabled:true,per_message:3,max_bytes:8388608,total_max_bytes:8388608,remaining_today:5}};
     else if(pathname==='/api/preferences'){language=body().language;data={user:user()}}
     else if(pathname==='/api/workspace/preferences')data={preferences:{onboarding_done:true,timezone:'Asia/Kolkata',language,notification_mode:'immediate',quiet_enabled:false,celebrations:false}};
     else if(pathname==='/api/workspace/today')data={tasks:fixtureTasks.filter(item=>!item.completed),revision_due:2,recent_chat:{id:7,title:'Search'}};
     else if(pathname==='/api/overview')data={pending_tasks:1,conversations:1,active_reminders:0,active_memories:0};
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
     else if(pathname==='/api/quick-notes')data={notes:[{id:3,title:'Search',content:'Search',updated_at:original.created_at,version:1}]};
     else if(pathname==='/api/workspace/search'){searches++;data={items:[{kind:'task',id:1,title:'Search',excerpt:'<img src=x onerror=alert(1)>'}]}}
     else if(pathname==='/api/focus'){
      if(method==='POST')focus={id:1,status:'running',version:1,task_id:body().task_id,duration_seconds:body().minutes*60,remaining_seconds:body().minutes*60};
      data={session:focus};
     }else if(pathname==='/api/focus/1'){
      const action=body().action;focus={...focus,status:action==='pause'?'paused':action==='resume'?'running':'cancelled',version:focus.version+1};data={session:focus};
     }else if(pathname==='/api/conversations'&&method==='POST'){await new Promise(resolve=>setTimeout(resolve,350));data={conversation:{id:8,title:'New conversation',updated_at:original.created_at}};}
     else if(pathname==='/api/conversations')data={conversations:[{id:7,title:'Search',preview:'Search',updated_at:original.created_at,is_archived:false}]};
     else if(pathname==='/api/conversations/7/messages')data={messages:[original,answer],has_more:false,conversation:{id:7,title:'Search'}};
     else if(pathname==='/api/response-timings')data={summary:{attempts:0,completed:0,errors:0,cancelled:0},recent:[]};
     else if(pathname==='/api/subject-spaces')data={spaces:[]};
     else if(pathname==='/api/revision')data={items:[],due:0,upcoming:0};
     else if(pathname==='/api/classroom/status')data={configured:true,scheduler_ready:true,connected:classroomConnected,connection:{last_sync:null,last_error:null,version:1,auto_sync_enabled:!!classroomSchedules}};
     else if(pathname==='/api/classroom/courses')data={courses:[{id:'course1',name:'English'}],selected:['course1'],version:1};
     else if(pathname==='/api/classroom/assignments')data={assignments:[{id:1,title:'Essay',instructions:'Original teacher instructions <script>unsafe</script>',original_url:'https://classroom.google.com/c/1',due_at:null,available:true,task_id:classroomAdds?9:null}]};
     else if(pathname==='/api/classroom/assignments/1/planner'){assert.equal(body().confirmed,true);classroomAdds++;data={task_id:9}}
     else if(pathname==='/api/classroom/schedule'){assert.equal(body().confirmed,true);assert.equal(body().enabled,true);assert.equal(body().version,1);classroomSchedules++;data={ok:true}}
     else if(pathname==='/api/classroom/assignments/1/explain'){assert.equal(body().ai_confirmed,true);classroomExplains++;data={explanation:'Useful steps <script>unsafe</script>',saved:false,verified:false}}
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

   assert.equal(await page.locator('.nav > button[data-view]').count(),1,'Today is the only top-level workspace view');
   assert.equal(await page.locator('.nav > [data-quick-notes]').count(),1);
   assert.equal(await page.locator('.nav > a[href="/chat"]').count(),1);
   assert.equal(await page.locator('#moreNavigation [data-view="study"],#moreNavigation [data-view="healer"]').count(),2,'Study and Care remain reachable');
   assert.equal(await page.locator('.nav-group').count(),3,'Secondary tools are grouped instead of one long list');
   assert.ok(await page.locator('.hero-panel').evaluate(node=>node.getBoundingClientRect().height<190),'Today greeting leaves the next action in view');
   assert.equal(await page.evaluate(()=>{const before=document.documentElement.dataset.theme;document.documentElement.dataset.theme='dark';const paper=getComputedStyle(document.body).getPropertyValue('--paper').trim();if(before)document.documentElement.dataset.theme=before;else delete document.documentElement.dataset.theme;return paper}), '#20251d','Dark workspace uses the shared surface palette');
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
   await page.waitForFunction(()=>document.querySelector('[data-focus-session]').textContent==='Focus session');
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
   await page.evaluate(()=>{openView('mindmaps');const root={id:'root',label:'Root',desc:'Overview',children:Array.from({length:4},(_,i)=>({id:'p'+i,label:'Branch '+i,desc:'Description',children:Array.from({length:5},(_,j)=>({id:'s'+i+j,label:'Detail '+j,desc:'ગુજરાતી example'}))}))};state.activeMindmap={topic:'Fixture',data:{root}};displayMindmap(state.activeMindmap)});
   assert.equal(await page.locator('.mm-node').count(),25);
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
   await page.evaluate(()=>openView('tasks'));
   await page.locator('#tasks').getByRole('button',{name:'Completed',exact:true}).click();
   await page.locator('#tasks .item.done').waitFor();
   await page.goto(base+'/chat?conversation=7');
   await page.locator('.message.user').waitFor();
   assert.equal(historyWhileProfilePending,true,'History should load concurrently with the profile');
   assert.equal(await page.locator('#chatMode').evaluate(node=>Boolean(node.closest('.composer-actions'))),true,'Mode shares the compact composer action row');
   const layout=await page.evaluate(()=>{const composer=document.querySelector('#composer').getBoundingClientRect(),toolbar=document.querySelector('.composer-toolbar').getBoundingClientRect(),send=document.querySelector('#sendButton').getBoundingClientRect();return {height:composer.height,toolbarBottom:toolbar.bottom,sendBottom:send.bottom,overflow:document.documentElement.scrollWidth>innerWidth+1}});
   assert.ok(layout.height<165,'Empty composer leaves room for the conversation');assert.ok(Math.abs(layout.toolbarBottom-layout.sendBottom)<8,'Mode and Send share one row');assert.equal(layout.overflow,false,'Chat fits every screen width');
   await page.locator('.quick-actions summary').click();assert.equal(await page.locator('.quick-action').first().isVisible(),true,'Learning actions remain reachable');await page.locator('.quick-actions summary').click();

   assert.equal(requests.filter(p=>p==='/api/conversations/7/messages').length,1,'Startup history must not be fetched twice');
   assert.equal(await page.locator('#voiceOpenBtn').evaluate(el=>Boolean(el.closest('#composer'))),true,'Voice belongs in composer');
   if(width>900){assert.ok((await page.locator('#sidebar').boundingBox()).x>width/2);await page.locator('#closeSidebar').click();assert.equal(await page.locator('#sidebar').isVisible(),false);await page.locator('#openSidebar').click()}

   await page.locator('#chatInput').fill('Keep my draft');
   await page.route('**/api/conversations/7/messages?limit=100',route=>route.fulfill({status:503,contentType:'application/json',body:JSON.stringify({error:'Temporary fixture failure'})}));
   await page.evaluate(()=>selectConversation(7));
   await page.getByRole('button',{name:'Retry loading conversation',exact:true}).waitFor();
   assert.equal(await page.locator('#chatInput').isDisabled(),true);
   assert.equal(await page.locator('#sendButton').isDisabled(),true);
   await page.unroute('**/api/conversations/7/messages?limit=100');
   await page.getByRole('button',{name:'Retry loading conversation',exact:true}).click();
   await page.locator('.message.user').waitFor();
   assert.equal(await page.locator('#chatInput').inputValue(),'Keep my draft');
   await page.reload();await page.locator('.message.user').waitFor();
   assert.equal(await page.locator('#chatInput').inputValue(),'Keep my draft','Draft survives browser reload');
   await page.locator('#chatInput').fill('');
   assert.equal(await page.locator('.message.user .message-content').textContent(),'Search');
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
   await page.evaluate(()=>createConversation());
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
   await page.locator('.thinking-dots').waitFor();
   assert.equal(await page.locator('#uploadStatus').isVisible(),false,'Text replies must not show upload status');
   assert.equal(await page.locator('.upload-progress').isVisible(),false,'No stray progress line');
   await page.screenshot({path:'/tmp/saathi-chat-'+width+'.png'});
   releaseReply();
   await page.locator('.message.failed').waitFor();
   await page.evaluate(()=>SaathiI18n.setLanguage('en'));
   await page.getByRole('button',{name:'Chat context',exact:true}).click();
   let chatContext=page.getByRole('dialog',{name:'Chat context',exact:true});
   assert.equal(await chatContext.getByLabel('Planner tasks',{exact:true}).isChecked(),false);
   await chatContext.getByLabel('Planner tasks',{exact:true}).check();await chatContext.getByRole('button',{name:'Save',exact:true}).click();
   await chatContext.getByText('Saved to your account',{exact:true}).waitFor();assert.equal(contextPrefs.tasks,true);assert.equal(contextPrefs.classroom,false);
   await chatContext.getByRole('button',{name:'Close',exact:true}).click();
   await page.evaluate(()=>{const box=document.createElement('div');document.querySelector('#messageList').append(box);SaathiChatActions.attach(box,{id:999,content:'Review this <SAATHI_ACTION>{"kind":"task"}</SAATHI_ACTION>'})});
   await page.getByRole('button',{name:'Review save preview',exact:true}).click();
   let actionDialog=page.getByRole('dialog',{name:'Review before saving',exact:true});
   await actionDialog.getByLabel('Title',{exact:true}).fill('Edited chat task');assert.equal(actionSaves,0);
   await actionDialog.getByRole('button',{name:'Save',exact:true}).click();await actionDialog.getByText('Saved to your account',{exact:true}).waitFor();assert.equal(actionSaves,1);
   assert.ok(await actionDialog.evaluate(e=>e.getBoundingClientRect().width<=innerWidth));await actionDialog.getByRole('button',{name:'Close',exact:true}).click();
   await page.evaluate(()=>{state.conversations[0].preview='Ready to review <SAATHI_ACTION>{\"kind\":\"task\"}</SAATHI_ACTION>';renderConversations()});
   assert.ok(!(await page.locator('#history').textContent()).includes('SAATHI_ACTION'),'Sidebar previews must hide action metadata');
   const beforeCreate=requests.filter(p=>p==='/api/conversations').length;
   if(!await page.locator('#newChat').isVisible())await page.locator('#openSidebar').click();
   await page.locator('#newChat').click();
   assert.equal(await page.locator('#chatInput').isDisabled(),true);assert.equal(await page.locator('#sendButton').isDisabled(),true);
   await page.evaluate(()=>document.querySelector('#newChat').click());
   await page.waitForFunction(()=>state.creatingConversation===false&&state.activeId===8);
   assert.equal(requests.filter(p=>p==='/api/conversations').length-beforeCreate,1,'Double-click must create only one conversation');
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
   assert.equal(await page.locator('#how h2').textContent(),'પહેલી મિનિટથી ઉપયોગી.');assert.equal(await page.locator('#pricing .section-head h2').textContent(),'મફતમાં શરૂ કરો. વધારાનાં સાધનો ઉપલબ્ધ થાય ત્યારે upgrade કરો.');
   assert.ok((await page.locator('#heroLogin').textContent()).includes('લૉગ'));
   await page.locator('[data-lang="hi"]').click();
   assert.equal(await page.locator('#how h2').textContent(),'पहले मिनट से उपयोगी।');
   assert.ok((await page.locator('#heroLogin').textContent()).includes('लॉग'));
   await page.emulateMedia({reducedMotion:'reduce'});
   assert.equal(await page.locator('.reveal').first().evaluate(el=>getComputedStyle(el).opacity),'1','Reduced motion keeps marketing content visible');
   assert.deepEqual(errors,[],'No uncaught errors in real pages');
   console.log('PASS: real Chromium '+width+'px, deferred tools/retry, English/Gujarati, private user text, focus reopen, search escaping and chat edit cancellation');
   await context.close();
  }
 }finally{await browser.close()}
})().catch(error=>{console.error(error);process.exitCode=1});
