// Visual regressions use the same isolated API fixtures as the core browser suite.
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
module.exports=async function reviewUI(page,width,base){
 const views=['overview','tasks','reminders','habits','journal','checkins','memory','family','study','healer','mocktests','mindmaps','account'];
 const artifacts=process.env.SAATHI_UI_ARTIFACTS;
 if(artifacts)fs.mkdirSync(artifacts,{recursive:true});
 await page.emulateMedia({reducedMotion:'reduce'});
 async function capture(name){if(artifacts&&[1280,360].includes(width))await page.screenshot({path:path.join(artifacts,`${width}-${name}.png`),fullPage:true,animations:'disabled'})}
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
 assert.equal(await page.locator('#todayFocusTitle').textContent(),'Search','Focus uses the actual returned task');
 await page.locator('#todayFocusStart').click();
 const focusDialog=page.locator('.hub-dialog[open]');
 await focusDialog.locator('select').first().waitFor();
 await page.waitForFunction(()=>document.querySelector('.hub-dialog select')?.value==='1');
 await page.keyboard.press('Escape');
 await focusDialog.waitFor({state:'detached'});
 for(const theme of ['light','dark']){
  await page.evaluate(theme=>SaathiTheme.apply(theme),theme);
  for(const view of views){
   await page.evaluate(view=>openView(view),view);
   await page.waitForFunction(()=>!state.sectionRequests?.size&&!state.failedTool);
   await fits(`${theme}/${view}`);
   if(view==='overview')assert.ok(await contrast('#todayFocusStart')>=4.5,`${theme} focus action remains readable`);
   if(view==='tasks'){
    await page.locator('.planning-head button').click();
    assert.equal(await page.evaluate(()=>document.activeElement.id),'taskTitle','Add task focuses the actual planner form');
    if(width<=780)assert.equal(await page.locator('.workspace-bottom-nav [data-open="tasks"]').getAttribute('aria-current'),'page','Mobile navigation follows the active planner');
   }
   if(view==='healer')for(const control of ['#healerConsultBtn','#zenToggleBtn'])assert.ok(await contrast(control)>=4.5,`${theme} Care action text remains readable`);
   if(theme==='light')await capture(view);
  }
  await page.evaluate(()=>SaathiWorkspace.openNote(3));
  const notes=page.locator('.quick-notes-dialog[open]');
  await page.waitForFunction(()=>!document.querySelector('[data-qn="title"]').disabled);
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
   const controls=await page.evaluate(()=>{
    const selector=document.querySelector('#chatMode'),context=document.querySelector('.composer-toolbar>.message-tool');
    const style=getComputedStyle(selector),r=selector.getBoundingClientRect(),c=context.getBoundingClientRect();
    return {modeWidth:r.width,modeHeight:r.height,font:parseFloat(style.fontSize),contextHeight:c.height,contextVisible:getComputedStyle(context).fontSize!=='0px',overlap:r.left<c.right&&c.left<r.right&&r.top<c.bottom&&c.top<r.bottom};
   });
   assert.ok(controls.font>=14&&controls.modeWidth>=120,`${language} mode name has room to read: ${JSON.stringify(controls)}`);
   assert.ok(controls.modeHeight>=44&&controls.contextHeight>=44&&controls.contextVisible&&!controls.overlap,'Mode and context are named, separate touch targets');
   await capture(`${language}-${theme}-chat`);
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
