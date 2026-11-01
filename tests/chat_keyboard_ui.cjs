// Actual Chromium keyboard/composition behavior, using the existing synthetic workspace.
const assert=require('node:assert/strict'),path=require('node:path');
module.exports=async(page,width,base)=>{
 await page.goto(base+'/chat?conversation=7');
 await page.waitForFunction(()=>state.ready&&!state.loadingMessages);
 if(width<=390)await page.setViewportSize({width,height:520});
 for(const language of ['en','gu','hi']){
  await page.evaluate(lang=>SaathiI18n.setLanguage(lang),language);
  const draft={en:'My unfinished study question',gu:'મારો અધૂરો અભ્યાસ પ્રશ્ન',hi:'मेरा अधूरा पढ़ाई का सवाल'}[language];
  await page.locator('#chatInput').fill(draft);
  const composition=await page.locator('#chatInput').evaluate(input=>{
   let submits=0;const form=input.form,guard=event=>{submits++;event.preventDefault();event.stopImmediatePropagation()};
   form.addEventListener('submit',guard,true);
   input.dispatchEvent(new KeyboardEvent('keydown',{key:'Enter',isComposing:true,bubbles:true,cancelable:true}));
   input.dispatchEvent(new KeyboardEvent('keydown',{key:'Enter',keyCode:229,bubbles:true,cancelable:true}));
   form.removeEventListener('submit',guard,true);return {submits,draft:input.value};
  });
  assert.equal(composition.submits,0,'Accepting an IME candidate must not submit the form');
  assert.equal(composition.draft,draft,'Composition preserves exact writing');
  if(await page.locator('#sidebar').isVisible())await page.locator('#closeSidebar').click();
  await page.keyboard.press('Control+k');
  await page.locator('#searchInput').waitFor({state:'visible'});
  assert.ok(await page.locator('#searchInput').evaluate(node=>document.activeElement===node),'Search gets focus after History opens');
  if(width<=900){
   assert.equal(await page.locator('#sidebar').getAttribute('role'),'dialog');
   assert.equal(await page.locator('#sidebar').getAttribute('aria-modal'),'true');
   assert.ok(await page.locator('.main').evaluate(node=>node.inert));
   const ends=await page.locator('#sidebar').evaluate(side=>{
    const nodes=[...side.querySelectorAll('a[href],button,input,select,textarea,[tabindex]')].filter(node=>!node.disabled&&node.tabIndex>=0&&node.getClientRects().length&&!node.closest('[inert]'));
    nodes[nodes.length-1].focus();return {first:nodes[0].outerHTML,last:nodes[nodes.length-1].outerHTML};
   });
   await page.keyboard.press('Tab');
   assert.equal(await page.evaluate(()=>document.activeElement.outerHTML),ends.first,'Tab wraps within mobile History');
   await page.keyboard.press('Shift+Tab');
   assert.equal(await page.evaluate(()=>document.activeElement.outerHTML),ends.last,'Shift+Tab wraps within mobile History');
   if(process.env.SAATHI_UI_ARTIFACTS&&width===360){
    await page.locator('#searchInput').focus();
    await page.screenshot({path:path.join(process.env.SAATHI_UI_ARTIFACTS,`${width}-${language}-keyboard-history.png`),animations:'disabled'});
   }
   await page.keyboard.press('Escape');
   assert.ok(await page.locator('#sidebar').isHidden());
   assert.equal(await page.locator('.main').evaluate(node=>node.inert),false);
   assert.ok(await page.locator('#openSidebar').evaluate(node=>document.activeElement===node),'Escape restores the History trigger');
   await page.locator('#openSidebar').click();
   assert.ok(await page.locator('#closeSidebar').evaluate(node=>document.activeElement===node),'Opening History moves focus into the drawer');
   await page.locator('#sidebar [data-quick-notes]').click();
   await page.locator('.quick-notes-dialog[open]').waitFor();
   await page.keyboard.press('Escape');
   assert.ok(await page.locator('.quick-notes-dialog').isHidden());
   assert.ok(await page.locator('#sidebar').isVisible(),'Escape closes Notes without dismissing its underlying History');
   await page.locator('#closeSidebar').click();
  }else await page.locator('#closeSidebar').click();
  assert.equal(await page.locator('#chatInput').inputValue(),draft,'History changes keep the exact composer draft');
  await page.locator('#chatInput').fill('');
 }
 console.log(`PASS keyboard/IME, History search/focus, EN/GU/HI ${width}px`);
};
