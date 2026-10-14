const assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs');
const window={};vm.runInNewContext(fs.readFileSync('chat-actions.js','utf8'),{window});
for(const text of ['Hello<SAATHI_ACTION>{"kind":"task"}</SAATHI_ACTION>','Hello<SAATHI_ACTION>{"kind"','Hello<SAATHI_ACT'])assert.equal(window.SaathiChatActions.clean(text),'Hello');
assert.equal(window.SaathiChatActions.clean('Hello <strong>world</strong>'),'Hello <strong>world</strong>');
for(const text of ['Remember that I prefer physics','My birthday is 1 January','Add a task titled Revision','Save a note. Title: Revision; Content: Private checklist','Confirm reminder','Snooze my revision reminder 30 minutes'])assert.equal(window.SaathiChatActions.stageFor(text),'saving');
assert.equal(window.SaathiChatActions.stageFor('Remind me tomorrow at 7 PM to revise'),'checking');
for(const text of ['Explain probability','> Remember my birthday','Make flashcards about chemistry'])assert.equal(window.SaathiChatActions.stageFor(text),'waiting');
console.log('PASS: action JSON stays out of completed and partial streamed replies');
