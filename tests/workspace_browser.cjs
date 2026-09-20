// Exercise the real pages in Chromium with owned, local fixture responses only.
const {chromium}=require('playwright');
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const root=path.resolve('.'),base='http://localhost:8765';
const original={id:1,role:'user',content:'Search',created_at:'2026-09-19T08:00:00Z',attachments:[],ai_mode:'normal'};
const answer={id:2,role:'assistant',content:'Search <script>not executable</script> ગુજરાતી',created_at:original.created_at,source_pages:[]};
const task={id:1,title:'Search',details:'Saved user writing',priority:'high',completed:false,due_at:null};
(async()=>{
 const browser=await chromium.launch({headless:true});
 try{
  for(const width of [1280,390]){
   const context=await browser.newContext({viewport:{width,height:900},serviceWorkers:'block'}),page=await context.newPage(),errors=[],requests=[];
   let language='en',focus=null,failMindmaps=true,searches=0,fixtureTasks=[{...task}];
   const user=()=>({id:1,name:'Search',username:'fixture',email:'fixture@example.test',plan:'free',language});
   page.on('pageerror',error=>errors.push(error.message));
   await page.route('**/*',async route=>{
    const url=new URL(route.request().url());if(url.origin!==base)return route.abort();
    const pathname=url.pathname;requests.push(pathname);
    if(pathname==='/dashboard-mindmaps.js'&&failMindmaps){failMindmaps=false;return route.abort()}
    if(pathname.startsWith('/api/')){
     let data={},status=200;const method=route.request().method(),body=()=>route.request().postDataJSON();
     if(pathname==='/api/me')data={user:user(),csrf_token:'fixture',chat_modes:[{id:'normal',label:'Normal',description:'A balanced everyday reply'}],chat_attachments:{enabled:true,per_message:3,max_bytes:8388608,total_max_bytes:8388608,remaining_today:5}};
     else if(pathname==='/api/preferences'){language=body().language;data={user:user()}}
     else if(pathname==='/api/workspace/preferences')data={preferences:{onboarding_done:true,timezone:'Asia/Kolkata',language,notification_mode:'immediate',quiet_enabled:false,celebrations:false}};
     else if(pathname==='/api/workspace/today')data={tasks:fixtureTasks.filter(item=>!item.completed),revision_due:2,recent_chat:{id:7,title:'Search'}};
     else if(pathname==='/api/overview')data={pending_tasks:1,conversations:1,active_reminders:0,active_memories:0};
     else if(pathname==='/api/tasks')data={tasks:fixtureTasks};
     else if(pathname==='/api/tasks/1'){fixtureTasks[0]={...fixtureTasks[0],...body()};data={task:fixtureTasks[0]}}
     else if(pathname==='/api/reminders')data={reminders:[]};
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
     }else if(pathname==='/api/conversations')data={conversations:[{id:7,title:'Search',preview:'Search',updated_at:original.created_at,is_archived:false}]};
     else if(pathname==='/api/conversations/7/messages')data={messages:[original,answer],has_more:false,conversation:{id:7,title:'Search'}};
     else if(pathname==='/api/response-timings')data={summary:{attempts:0,completed:0,errors:0,cancelled:0},recent:[]};
     else if(pathname==='/api/subject-spaces')data={spaces:[]};
     else if(pathname==='/api/revision')data={items:[],due:0,upcoming:0};
     else {status=404;data={error:'Unmocked fixture endpoint: '+pathname}}
     return route.fulfill({status,contentType:'application/json',body:JSON.stringify(data)});
    }
    const filename=pathname==='/dashboard'?'dashboard.html':pathname==='/chat'?'chat.html':pathname.slice(1),local=path.resolve(root,filename);
    if(!local.startsWith(root+path.sep)||!fs.existsSync(local)||!fs.statSync(local).isFile())return route.fulfill({status:404,body:''});
    const types={'.html':'text/html','.js':'application/javascript','.css':'text/css','.svg':'image/svg+xml','.json':'application/json'};
    return route.fulfill({contentType:types[path.extname(local)]||'application/octet-stream',body:fs.readFileSync(local)});
   });
   await page.goto(base+'/dashboard');
   await page.locator('#todayTasks .hub-task-title').waitFor();
   await page.waitForFunction(()=>document.querySelector('#workspaceStatus').hidden);
   assert.ok(!requests.some(url=>/dashboard-(study|care|mindmaps)\.js/.test(url)),'Heavy tools must not load on Today');
   assert.ok(!requests.includes('/locale-gu.js'),'English must not download Gujarati catalog');
   assert.equal(await page.locator('#account .referral-banner').count(),1);
   await page.evaluate(()=>openView('account'));
   await page.locator('#languageSelect').selectOption('gu');
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
   await page.locator('#languageSelect').selectOption('en');
   await page.waitForFunction(()=>document.querySelector('[data-focus-session]').textContent==='Focus session');
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
   assert.deepEqual(errors,[],'No uncaught errors in real pages');
   console.log('PASS: real Chromium '+width+'px, deferred tools/retry, English/Gujarati, private user text, focus reopen, search escaping and chat edit cancellation');
   await context.close();
  }
 }finally{await browser.close()}
})().catch(error=>{console.error(error);process.exitCode=1});
