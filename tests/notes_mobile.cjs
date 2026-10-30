// Real signed-in page/controllers, synthetic account data only; never sends AI.
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
module.exports=async(page,width,base,baseline=false)=>{
 const overrides=[];
 if(baseline){for(const file of ['workspace.js','workspace.css','study-desk.css']){
  const body=require('node:child_process').execFileSync('git',['show','HEAD^1:'+file]);
  const pattern='**/'+file+'*';const handler=route=>route.fulfill({contentType:file.endsWith('.js')?'application/javascript':'text/css',body});
  await page.route(pattern,handler);overrides.push([pattern,handler]);
 }}
 const folder=process.env.SAATHI_UI_ARTIFACTS;if(folder)fs.mkdirSync(folder,{recursive:true});
 await page.goto(base+'/dashboard');
 await page.locator('#todayTasks .hub-task-title').waitFor();
 await page.emulateMedia({reducedMotion:'reduce'});
 for(const language of ['en','gu','hi']){
  await page.evaluate(lang=>SaathiI18n.setLanguage(lang),language);
  for(const theme of ['light','dark']){
   await page.evaluate(value=>SaathiTheme.apply(value),theme);
   await page.setViewportSize({width,height:width<=390?520:900});
   await page.evaluate(()=>SaathiWorkspace.openNote(3));
   const notes=page.locator('.quick-notes-dialog[open]');
   await page.waitForFunction(()=>!document.querySelector('[data-qn="title"]').disabled);
   const draft='Probability revision\nગુજરાતી નોંધ\nहिन्दी नोट\n'+('One calm study step.\n'.repeat(30));
   await notes.locator('[data-qn="content"]').fill(draft);
   if(folder&&[360,1280].includes(width))await page.screenshot({path:path.join(folder,`${baseline?"before":"after"}-${width}-${language}-${theme}-notes-edit.png`),animations:'disabled'});
   const footer=await notes.locator('[data-qn="save"]').boundingBox();
   if(!baseline){
    assert.ok(footer.y>=0&&footer.y+footer.height<=(width<=390?520:900),`Save stays visible while editing at ${width}px/${language}/${theme}: ${JSON.stringify(footer)}`);
    assert.ok(footer.height>=44,'Save retains a full touch target');
    await notes.locator('[data-qn="title"]').fill('A longer synthetic revision title');
    await notes.locator('[data-qn="title"]').press('Tab');
    assert.equal(await page.evaluate(()=>document.activeElement.dataset.qn),'content');
    await notes.locator('[data-qn="content"]').press('Tab');
    assert.equal(await page.evaluate(()=>document.activeElement.dataset.qn),'save','Keyboard can reach Save directly from the note');
    assert.equal(await notes.locator('[data-qn="content"]').inputValue(),draft,'Scrolling/focus retains exact draft');
    const failSave=route=>route.request().method()==='PATCH'?route.fulfill({status:503,contentType:'application/json',body:JSON.stringify({error:'Fixture network failure'})}):route.fallback();
    await page.route('**/api/quick-notes/3',failSave);
    await notes.locator('[data-qn="save"]').click();
    await notes.locator('.qn-status.error').waitFor();
    assert.equal(await notes.locator('[data-qn="content"]').inputValue(),draft,'Failed save keeps exact draft');
    assert.ok(await notes.locator('[data-qn="save"]').isEnabled(),'Failed save offers a usable retry');
    await page.unroute('**/api/quick-notes/3',failSave);
    await notes.locator('[data-qn="save"]').click();
    await page.waitForFunction(()=>document.querySelector('[data-qn="status"]').textContent===SaathiI18n.t('Saved to your account.'));
    assert.ok(await notes.locator('[data-qn="status"]').isVisible(),'Save feedback remains in view');
   }
   if(baseline&&await notes.locator('[data-qn="discard"]').isVisible())await notes.locator('[data-qn="discard"]').click();
   await page.keyboard.press('Escape');
  }
 }
 for(const [pattern,handler] of overrides)await page.unroute(pattern,handler);
 await page.setViewportSize({width,height:900});
 console.log(`PASS ${baseline?"baseline capture":"verified"} notes edit/save, short height, keyboard, EN/GU/HI, light/dark ${width}px`);
};
