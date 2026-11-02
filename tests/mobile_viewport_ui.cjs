// Browser-rendered keyboard occlusion regression; not a physical-device claim.
const assert=require('node:assert/strict'),path=require('node:path');
module.exports=async(page,width,base)=>{
 if(width>390)return;
 await page.setViewportSize({width,height:900});
 await page.addInitScript(()=>{
  const viewport=new EventTarget();viewport.height=900;viewport.scale=1;
  Object.defineProperty(window,'visualViewport',{configurable:true,value:viewport});
 });
 const stub=route=>route.fulfill({contentType:'application/javascript',body:''});
 for(const baseline of [true,false]){
  if(baseline)await page.route('**/chat-viewport.js*',stub);
  for(const language of ['en','gu','hi']){
   await page.goto(base+'/chat?conversation=7');
   await page.waitForFunction(()=>state.ready&&!state.loadingConversation);
   await page.evaluate(lang=>SaathiI18n.setLanguage(lang),language);
   for(const empty of [true,false]){
    await page.evaluate(empty=>{state.messages=empty?[]:[{id:1,role:'assistant',content:'Synthetic study answer',created_at:new Date().toISOString()}];renderMessages()},empty);
    const draft={en:'Keep this unfinished question',gu:'આ અધૂરો પ્રશ્ન સાચવો',hi:'यह अधूरा सवाल रखें'}[language];
    await page.locator('#chatInput').fill(draft);
    if(!baseline&&!empty){
     await page.locator('#fileInput').setInputFiles({name:'keyboard-fixture.png',mimeType:'image/png',buffer:Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRZkAAAAASUVORK5CYII=','base64')});
     assert.equal(await page.evaluate(()=>state.selectedFiles[0]?.file.name),'keyboard-fixture.png');
    }
    await page.evaluate(()=>{visualViewport.height=400;visualViewport.dispatchEvent(new Event('resize'))});
    await page.waitForTimeout(60);
    const box=await page.locator('#sendButton').boundingBox();
    if(baseline)assert.ok(box.y+box.height>400,'Baseline Send is below the synthetic visible viewport');
    else{
     assert.ok(box.y>=0&&box.y+box.height<=401,'Send stays above the synthetic keyboard: '+JSON.stringify(box));
     assert.equal(await page.locator('#chatInput').inputValue(),draft);
     const beforeZoom=await page.locator('.main').evaluate(n=>n.getBoundingClientRect().height);
     await page.evaluate(()=>{visualViewport.scale=2;visualViewport.height=200;visualViewport.dispatchEvent(new Event('resize'))});
     await page.waitForTimeout(40);
     assert.equal(await page.locator('.main').evaluate(n=>n.getBoundingClientRect().height),beforeZoom,'Pinch zoom keeps the reading layout');
     await page.evaluate(()=>{visualViewport.scale=1;visualViewport.height=400;visualViewport.dispatchEvent(new Event('resize'))});
    }
    if(process.env.SAATHI_UI_ARTIFACTS&&width===360)await page.screenshot({path:path.join(process.env.SAATHI_UI_ARTIFACTS,`${baseline?'before':'after'}-360-${language}-${empty?'empty':'active'}-visual-keyboard.png`),clip:{x:0,y:0,width,height:400},animations:'disabled'});
    await page.evaluate(()=>{visualViewport.height=900;visualViewport.dispatchEvent(new Event('resize'))});
    await page.waitForTimeout(40);
    assert.equal(await page.locator('#chatInput').inputValue(),draft,'Closing keyboard keeps exact writing');
    if(!baseline&&!empty){
     assert.equal(await page.evaluate(()=>state.selectedFiles[0]?.file.name),'keyboard-fixture.png','Keyboard changes retain the selected upload');
     await page.evaluate(()=>{clearSelectedFiles();renderSelectedFiles();updateComposer()});
    }
    await page.locator('#chatInput').fill('');
   }
  }
  if(baseline)await page.unroute('**/chat-viewport.js*',stub);
 }
 console.log(`PASS simulated keyboard viewport: before/after, empty/active, EN/GU/HI and zoom ${width}px`);
};
