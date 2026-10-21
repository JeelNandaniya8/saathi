// Visual regressions use the same isolated API fixtures as the core browser suite.
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
module.exports=async function reviewUI(page,width,base){
 const views=['overview','tasks','reminders','habits','journal','checkins','memory','family','study','healer','mocktests','mindmaps','account'];
 const artifacts=process.env.SAATHI_UI_ARTIFACTS;
 if(artifacts)fs.mkdirSync(artifacts,{recursive:true});
 await page.emulateMedia({reducedMotion:'reduce'});
 async function capture(name){if(artifacts&&[1280,360].includes(width)){await page.evaluate(()=>{document.activeElement?.blur();window.scrollTo(0,0)});await page.screenshot({path:path.join(artifacts,`${width}-${name}.png`),fullPage:!name.includes('notes'),animations:'disabled'})}}
 async function fits(name){
  const size=await page.evaluate(()=>({viewport:innerWidth,scroll:document.documentElement.scrollWidth}));
  assert.ok(size.scroll<=size.viewport+1,`${name} fits ${width}px: ${JSON.stringify(size)}`);
 }
 async function contrast(selector){
  return page.locator(selector).first().evaluate(el=>{
   const style=getComputedStyle(el),canvas=document.createElement('canvas');canvas.width=canvas.height=1;
   let surface=el,background=style.backgroundColor;
   while(background==='rgba(0, 0, 0, 0)'&&surface.parentElement){surface=surface.parentElement;background=getComputedStyle(surface).backgroundColor}
   const ctx=canvas.getContext('2d');
   function rgb(color){ctx.clearRect(0,0,1,1);ctx.fillStyle=color;ctx.fillRect(0,0,1,1);return [...ctx.getImageData(0,0,1,1).data].slice(0,3)}
   function light(color){const values=rgb(color).map(c=>{c/=255;return c<=.04045?c/12.92:((c+.055)/1.055)**2.4});return values[0]*.2126+values[1]*.7152+values[2]*.0722}
   const a=light(style.color),b=light(background);return (Math.max(a,b)+.05)/(Math.min(a,b)+.05);
  });
 }
 await page.goto(base+'/dashboard');
 await page.locator('#todayTasks .hub-task-title').waitFor();
 assert.equal(await page.locator('#sidebar .brand img').getAttribute('src'),'/saathi-icon.svg','Dashboard retains the existing Saathi logo');
 assert.equal(await page.locator('#todayFocusTitle').textContent(),'Search','Focus uses the actual returned task');
 if(width>780){
  const focus=await page.locator('.focus-card').boundingBox(),plan=await page.locator('.today-layout').boundingBox();
  assert.ok(Math.abs(focus.width-plan.width)<2&&focus.y+focus.height<=plan.y,'Dashboard focus spans the desk above the returned plan');
 }
 await page.locator('#todayFocusStart').click();
 const focusDialog=page.locator('.hub-dialog[open]');
 await focusDialog.locator('select').first().waitFor();
 await page.waitForFunction(()=>document.querySelector('.hub-dialog select')?.value==='1');
 await page.keyboard.press('Escape');
 await focusDialog.waitFor({state:'detached'});
 let releaseCompletion;
 const completionGate=new Promise(resolve=>releaseCompletion=resolve);
 await page.route('**/api/tasks/1',async route=>{await completionGate;return route.fulfill({status:503,contentType:'application/json',body:JSON.stringify({error:'Temporary fixture save failure'})})});
 const complete=page.locator('.hub-task-complete').first();
 await complete.hover();
 assert.equal(await complete.evaluate(button=>getComputedStyle(button,'::after').content),'none','Hover must not depict an unfinished task as completed');
 await complete.click();
 assert.equal(await complete.getAttribute('aria-busy'),'true','Task completion distinguishes the pending write');
 assert.ok(await complete.isDisabled(),'Pending completion cannot be submitted twice');
 releaseCompletion();
 await page.waitForFunction(()=>{const button=document.querySelector('.hub-task-complete');return button&&!button.disabled&&!button.hasAttribute('aria-busy')});
 assert.equal(await page.locator('#todayFocusTitle').textContent(),'Search','A failed completion keeps the real task visible');
 await page.unroute('**/api/tasks/1');
 await page.waitForFunction(()=>!document.getElementById('toast')?.classList.contains('show'));
 await page.evaluate(()=>openView('tasks'));
 assert.equal(await page.locator('#taskEditor').getAttribute('open'),null,'Saved tasks lead before the editor is requested');
 await page.locator('#tasks .planning-head button').click();
 assert.ok(await page.locator('#taskEditor').evaluate(editor=>editor.open),'Add task expands the actual editor');
 await page.locator('#taskTitle').fill('Unsaved study step');
 await page.locator('#taskEditor>summary').click();
 await page.locator('#tasks .planning-head button').click();
 assert.equal(await page.locator('#taskTitle').inputValue(),'Unsaved study step','Collapsing an editor preserves its exact unsaved draft');
 await page.locator('#taskTitle').fill('');
 for(const theme of ['light','dark']){
  await page.evaluate(theme=>SaathiTheme.apply(theme),theme);
  for(const view of views){
   await page.evaluate(view=>openView(view),view);
   await page.waitForFunction(()=>!state.sectionRequests?.size&&!state.failedTool);
   await fits(`${theme}/${view}`);
   if(view==='overview'){
    assert.ok(await contrast('#todayFocusStart')>=4.5,`${theme} focus action remains readable`);
    const complete=await page.locator('.hub-task-complete').first().boundingBox();
    assert.ok(complete.width>=44&&complete.height>=44,'Completing a task has a distinct full-size touch target');
   }
   if(view==='tasks'){
    await page.locator('#tasks .planning-head button').click();
    assert.equal(await page.evaluate(()=>document.activeElement.id),'taskTitle','Add task focuses the actual planner form');
    if(width<=780)assert.equal(await page.locator('.workspace-bottom-nav [data-open="tasks"]').getAttribute('aria-current'),'page','Mobile navigation follows the active planner');
   }
   if(view==='healer')for(const control of ['#healerConsultBtn','#zenToggleBtn'])assert.ok(await contrast(control)>=4.5,`${theme} Care action text remains readable`);
   if(theme==='light')await capture(view);
  }
  await page.evaluate(()=>SaathiWorkspace.openNote(3));
  const notes=page.locator('.quick-notes-dialog[open]');
  await page.waitForFunction(()=>!document.querySelector('[data-qn="title"]').disabled);
  await notes.locator('.qn-more>summary').click();
  assert.ok(await notes.locator('[data-qn="exportpdf"]').isVisible(),'Occasional note actions remain reachable in their named menu');
  await notes.locator('.qn-more>summary').click();
  await notes.locator('[data-qn="content"]').fill('Electric potential is energy per unit charge. V = U / q.');
  await notes.locator('[data-qn="save"]').click();
  await page.waitForFunction(()=>document.querySelector('[data-qn="status"]').textContent==='Saved to your account.');
  await capture(`${theme}-notes`);
  const bounds=await notes.evaluate(node=>{const r=node.getBoundingClientRect();return {left:r.left,right:r.right,bottom:r.bottom,width:innerWidth,height:innerHeight}});
  assert.ok(bounds.left>=0&&bounds.right<=bounds.width+1&&bounds.bottom<=bounds.height+1,`${theme} notes stays inside the viewport`);
  await page.keyboard.press('Escape');
  await page.evaluate(()=>SaathiWorkspace.openNote(3));
  assert.equal(await notes.locator('[data-qn="content"]').inputValue(),'Electric potential is energy per unit charge. V = U / q.','Notes reopen from the persisted fixture read');
  await page.keyboard.press('Escape');
  await page.goto(base+'/dashboard?mindmap=62#mindmaps');
  await page.locator('.mm-node:not(.root) .mm-title').waitFor();
  const mapContrast=await contrast('.mindmap-toolbar button');
  await capture(`${theme}-saved-map`);
  assert.ok(mapContrast>=4.5,`${theme} mindmap controls have readable contrast: ${mapContrast.toFixed(2)}:1`);
  const titleContrast=await contrast('.mm-node:not(.root) .mm-title');
  assert.ok(titleContrast>=4.5,`${theme} map branch text remains readable: ${titleContrast.toFixed(2)}:1`);
  assert.ok(await contrast('#mindmapViewerWrap button.primary')>=4.5,`${theme} export action remains readable`);
  assert.ok(await page.locator('#mindmapsHistoryList .empty').count(),'Empty map history uses a full-width reading surface');
  if(width===1280)console.log(`Map contrast ${theme}: controls ${mapContrast.toFixed(2)}:1; branch ${titleContrast.toFixed(2)}:1`);
 }
 for(const language of ['en','gu','hi']){
  await page.goto(base+'/dashboard#account');
  await page.locator('#languageSelect').selectOption(language);
  await page.waitForFunction(language=>document.documentElement.lang===language,language);
  await page.goto(base+'/dashboard');
  await page.locator('#todayFocusStart:not([disabled])').waitFor();
  if(language!=='en')assert.notEqual(await page.locator('#focusHeading').textContent(),'Today’s focus','New dashboard labels follow the saved language');
  await page.evaluate(()=>SaathiWorkspace.openNotes());
  assert.notEqual(await page.evaluate(()=>document.activeElement.tagName),'TEXTAREA','Opening Notes does not request a typing keyboard');
  if(language!=='en')assert.notEqual(await page.locator('#quickNotesTitle').textContent(),'Your notes','Notes heading follows the saved language');
  await page.keyboard.press('Escape');
  await page.goto(base+'/chat?conversation=7');
  await page.locator('.message.assistant .message-content').waitFor();
  for(const theme of ['light','dark']){
   await page.evaluate(theme=>SaathiTheme.apply(theme),theme);
   await fits(`${language}/${theme}/chat`);
   assert.ok(await contrast('.message.assistant .message-content')>=4.5,`${language}/${theme} assistant text remains readable on the open conversation surface`);
   const controls=await page.evaluate(()=>{
    const selector=document.querySelector('#chatMode'),context=document.querySelector('.composer-toolbar>.message-tool');
    const style=getComputedStyle(selector),r=selector.getBoundingClientRect(),c=context.getBoundingClientRect();
    return {modeWidth:r.width,modeHeight:r.height,font:parseFloat(style.fontSize),contextHeight:c.height,contextVisible:getComputedStyle(context).fontSize!=='0px',overlap:r.left<c.right&&c.left<r.right&&r.top<c.bottom&&c.top<r.bottom};
   });
   assert.ok(controls.font>=14&&controls.modeWidth>=120,`${language} mode name has room to read: ${JSON.stringify(controls)}`);
   assert.ok(controls.modeHeight>=44&&controls.contextHeight>=44&&controls.contextVisible&&!controls.overlap,'Mode and context are named, separate touch targets');
   await capture(`${language}-${theme}-chat`);
  }
  await page.evaluate(()=>{state.attachmentLimits.remaining_today=0;attachmentMeta()});
  assert.ok(await page.locator('#uploadLimitsDetails').evaluate(details=>details.open),'Exhausted upload quota reveals its limits instead of hiding the explanation');
  assert.ok(await page.locator('#attachButton').isDisabled(),'Exhausted uploads remain disabled');
  await page.locator('#chatInput').fill('A text-only question');
  assert.ok(await page.locator('#sendButton').isEnabled(),'Upload exhaustion still permits an ordinary text draft');
  await page.locator('#chatInput').fill('');
  await page.evaluate(()=>{state.attachmentLimits.remaining_today=5;attachmentMeta();document.getElementById('uploadLimitsDetails').open=false});
  for(const theme of ['light','dark']){
   await page.evaluate(theme=>SaathiTheme.apply(theme),theme);
   const savedMessages=await page.evaluate(()=>state.messages);
   await page.evaluate(()=>renderChatLoading());
   await page.waitForFunction(()=>document.querySelector('.chat-placeholder p').textContent===SaathiI18n.t('Loading conversation…'));
   assert.ok(await page.locator('.chat-placeholder').isVisible(),'Loading state includes a visible native label');
   await page.evaluate(()=>{state.messages=[];renderMessages()});
   await fits(`${language}/empty-chat`);
   assert.equal(await page.locator('.prompts>.prompt').count(),3);
   assert.equal(await page.locator('.prompt-secondary>.prompt:visible').count(),2,'Secondary starting points remain reachable on mobile');
   if(language!=='en')assert.equal(await page.locator('.empty h2').evaluate(heading=>getComputedStyle(heading).letterSpacing),'normal','Native headings retain script shaping rather than Latin tracking');
   const welcome=await page.evaluate(()=>{
    const composer=document.querySelector('#composer').getBoundingClientRect(),prompts=document.querySelector('.prompts').getBoundingClientRect(),last=document.querySelector('.prompt-secondary').getBoundingClientRect();
    return {forms:document.querySelectorAll('#composer').length,composerBottom:composer.bottom,promptsTop:prompts.top,lastBottom:last.bottom,height:innerHeight};
   });
   assert.equal(welcome.forms,1,'Empty chat retains one actual composer');
   assert.ok(welcome.composerBottom<=welcome.promptsTop&&welcome.lastBottom<=welcome.height,`Composer precedes reachable starting points: ${JSON.stringify(welcome)}`);
   await capture(`${language}-${theme}-empty-chat`);
   await page.locator('.prompts>.prompt').first().click();
   const starter=await page.locator('#chatInput').inputValue();
   assert.ok(starter.length>0,'Starting point prepares a draft without sending it');
   const mode=await page.locator('#chatMode').inputValue();
   const recovered=await page.evaluate(()=>SaathiRecovery.getDraft('chat',state.activeId));
   assert.equal(recovered.content,starter,'A prepared starting point is persisted before leaving the page');
   assert.equal(recovered.mode,mode,'Starting-point recovery retains the selected mode');
   assert.equal(recovered.request_id,null,'A new starting point cannot reuse an earlier failed request ID');
   await page.locator('[data-start-prompt="Talk it through"]').click();
   assert.equal(await page.locator('#chatInput').inputValue(),starter,'Another starting point cannot overwrite an existing draft');
   assert.equal(await page.locator('#chatMode').inputValue(),mode,'A protected draft also retains its mode');
   await page.locator('#chatInput').fill('');
   await page.locator('[data-start-prompt="Talk it through"]').click();
   assert.ok(await page.locator('#chatMode').inputValue(),'Starting points cannot select a mode missing from the account');
   for(const prompt of await page.locator('[data-start-prompt]').all()){
    await page.locator('#chatInput').fill('');
    await prompt.click();
    assert.ok((await page.locator('#chatInput').inputValue()).trim(),'Every starting point prepares a usable draft');
   }
   await page.locator('#chatInput').fill('');
   await page.evaluate(messages=>{state.messages=messages;renderMessages()},savedMessages);
  }
 }
 if(width<=390){
  await page.setViewportSize({width,height:520});
  await page.waitForFunction(()=>document.querySelector('#sendButton').getBoundingClientRect().bottom<=innerHeight);
  await fits('Short mobile viewport');
  const visible=await page.evaluate(()=>{const message=document.querySelector('#messages').getBoundingClientRect(),send=document.querySelector('#sendButton').getBoundingClientRect();return {messageHeight:message.height,bottom:send.bottom,height:innerHeight}});
  if(artifacts)await page.screenshot({path:path.join(artifacts,`${width}-short-chat.png`),animations:'disabled'});
  assert.ok(visible.messageHeight>=140&&visible.bottom<=visible.height,'A short mobile viewport keeps the conversation and Send visible: '+JSON.stringify(visible));
  await page.setViewportSize({width,height:900});
 }
 await page.evaluate(()=>{SaathiTheme.apply('light');return SaathiI18n.setLanguage('en')});
 console.log(`PASS: UI ${width}px, 13 workspace views, light/dark map contrast, EN/GU/HI chat, short mobile viewport`);
};
