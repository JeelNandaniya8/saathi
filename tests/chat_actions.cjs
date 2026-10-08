const assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs');
const window={};vm.runInNewContext(fs.readFileSync('chat-actions.js','utf8'),{window});
for(const text of ['Hello<SAATHI_ACTION>{"kind":"task"}</SAATHI_ACTION>','Hello<SAATHI_ACTION>{"kind"','Hello<SAATHI_ACT'])assert.equal(window.SaathiChatActions.clean(text),'Hello');
assert.equal(window.SaathiChatActions.clean('Hello <strong>world</strong>'),'Hello <strong>world</strong>');
console.log('PASS: action JSON stays out of completed and partial streamed replies');
