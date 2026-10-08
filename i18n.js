/* Translate application labels only. User writing and generated answers stay untouched. */
(function(){
  let language='en',catalogs={gu:{},hi:{}},reverse={},loading={},observer=null;
  const originals=new WeakMap(),attributes=new WeakMap(),staticNodes=[];
  const excluded='script,style,textarea,pre,code,[data-i18n],[data-user-content],.message-content,.message-name,.conversation-copy,.qn-note,.item-copy,.hub-result,.hub-task-title,.dw-space-title,.dw-resource-open,#todayResume,#profileDisplayName,#profileEmail,#sideName,#userName,#greeting,.option-btn,.quiz-option';
  function t(text){const source=reverse[text]||text;return catalogs[language]?.[source]||source}
  const walker=document.createTreeWalker(document.body,NodeFilter.SHOW_TEXT);
  while(walker.nextNode()){const text=walker.currentNode;if(text.nodeValue.trim()&&!text.parentElement?.closest(excluded))staticNodes.push(text)}
  function translateText(text){if(!text.parentElement||text.parentElement.closest(excluded))return;const value=text.nodeValue,prior=originals.get(text);let source=prior&&value===prior.translated?prior.source:value;const core=source.trim(),translated=source.replace(core,t(core));if(translated!==value)text.nodeValue=translated;originals.set(text,{source,translated})}
  const uiSelector='button,summary,option,label,legend,[data-ui-text],.helper,.dw-muted,.dw-error,.dw-dialog h2,.dw-check span,.qn-status,.qn-empty,.qn-header h2,.qn-header p,.qn-meta span,.recovery-dialog h2,.recovery-metric span,.hub-dialog h2,#toastMessage,#toast,#editMessageNotice,#workspaceStatusText,#modeDescription,#composerMeta,#uploadCopy,.history-state,.prompt b';
  function controls(root){
    const targets=[];if(root.nodeType===1)targets.push(root);if(root.querySelectorAll)targets.push(...root.querySelectorAll(uiSelector+',[placeholder],[aria-label],[title]'));
    for(const el of targets){if(el.closest(excluded)||el.matches?.('.conversation-main,.qn-note,.hub-result,.hub-task-title,.dw-resource-open,.option-btn,.quiz-option'))continue;
      for(const attr of ['placeholder','aria-label','title'])if(el.hasAttribute?.(attr)){let map=attributes.get(el);if(!map){map={};attributes.set(el,map)}const value=el.getAttribute(attr),previous=map[attr],source=previous&&previous.translated===value?previous.source:value,translated=t(source);if(translated!==value)el.setAttribute(attr,translated);map[attr]={source,translated}}
      if(el.matches?.(uiSelector))for(const child of el.childNodes)if(child.nodeType===3)translateText(child);
    }
  }
  function apply(){for(const text of staticNodes)if(text.isConnected)translateText(text);controls(document.body)}
  async function setLanguage(value){language=['gu','hi'].includes(value)?value:'en';document.documentElement.lang=language;const requested=language;if(requested!=='en'&&!Object.keys(catalogs[requested]).length){if(!loading[requested])loading[requested]=new Promise((resolve,reject)=>{const script=document.createElement('script');script.src='/locale-'+requested+'.js?v=20261008e';script.onload=()=>resolve();script.onerror=()=>{delete loading[requested];script.remove();reject(Error('Language labels could not load.'))};document.head.append(script)});try{await loading[requested]}catch(_){return}}apply();if(!observer&&typeof MutationObserver!=='undefined'){observer=new MutationObserver(changes=>{for(const change of changes){if(change.type==='characterData'){const parent=change.target.parentElement;if(parent?.matches(uiSelector))translateText(change.target)}else for(const node of change.addedNodes){if(node.nodeType===1)controls(node);else if(node.nodeType===3){const parent=node.parentElement;if(parent?.matches(uiSelector))translateText(node)}}}});observer.observe(document.body,{childList:true,subtree:true,characterData:true})}}
  window.SaathiI18n={setLanguage,t,register:(dict,locale='gu')=>{if(!['gu','hi'].includes(locale))return;catalogs[locale]=dict;reverse=Object.fromEntries(Object.values(catalogs).flatMap(dict=>Object.entries(dict).map(([key,value])=>[value,key])));apply()}};
})();
