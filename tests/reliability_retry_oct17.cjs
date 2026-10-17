const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const source=fs.readFileSync('chat.html','utf8'),drafts=new Map();
const ctx={state:{activeId:7,draftRequestId:'same',selectedFiles:[{file:{name:'page.png',size:12}}],chatModes:[{id:'normal'}]},el:{input:{value:'Read this file'},mode:{value:'normal'},fileOnly:{checked:true}},window:{SaathiRecovery:{saveDraft:(_,id,value)=>drafts.set(id,value),getDraft:(_,id)=>drafts.get(id)}},updateComposer(){},updateModeDescription(){},showToast(){}};
vm.createContext(ctx);vm.runInContext(source.slice(source.indexOf('function saveChatDraft('),source.indexOf('\nfunction renderChatModes')),ctx);
ctx.saveChatDraft();assert.equal(drafts.get(7).file_only,true,'A retry must retain the original file-only restriction');assert.equal(drafts.get(7).had_attachments,true,'Draft must disclose that its files need reattaching');
ctx.el.fileOnly.checked=false;ctx.restoreChatDraft();assert.equal(ctx.el.fileOnly.checked,true,'Reload must restore file-only selection');
console.log('PASS exact file-only retry draft');
