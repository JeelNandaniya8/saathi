const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict'),path=require('node:path');
const source=fs.readFileSync(path.join(__dirname,'../workspace.js'),'utf8');
function setup(){
 const pending=[],messages=[],drafts=new Map();
 const state={notes:[{id:1,title:'Old',content:'old',version:1}],selected:{id:1,version:1},dirty:true,clientId:'client',confirmDelete:true};
 const ui=Object.fromEntries(['reload','save','delete','title','content','discard'].map(k=>[k,{disabled:false,value:k==='title'?'New':'new'}]));
 const c={state,ui,window:{SaathiRecovery:{removeDraft:(k,id)=>drafts.delete(id),saveDraft:(k,id,d)=>drafts.set(id,d)}},status:m=>messages.push(m),renderList(){},canSwitch:()=>true,selectNote:n=>{state.selected=n},noteDraftKey:()=>state.selected?.id||'new',saveNoteDraft(){},};
 state.api=()=>new Promise((resolve,reject)=>pending.push({resolve,reject}));
 vm.createContext(c);vm.runInContext('let notesRequest=null,notesRevision=0;'+source.slice(source.indexOf('  function invalidateNotesLoad'),source.indexOf('  async function openNotes'))+source.slice(source.indexOf('  async function saveNote'),source.indexOf('  function exportCurrentNotePdf')),c);
 return {c,state,ui,pending,messages};
}
(async()=>{
 // Concurrent opens share one request.
 let t=setup(),p=t.c.loadNotes(),again=t.c.loadNotes();assert.equal(p,again);assert.equal(t.pending.length,1);t.pending[0].resolve({notes:[]});await p;assert.equal(t.ui.reload.disabled,false);
 // A refresh started before a save cannot replace the saved note with old content.
 t=setup();p=t.c.loadNotes();let save=t.c.saveNote({preventDefault(){}});t.pending[1].resolve({note:{id:1,title:'New',content:'new',version:2}});await save;t.pending[0].resolve({notes:[{id:1,title:'Old',version:1}]});await p;assert.equal(t.state.notes[0].version,2);
 // A stale refresh error cannot overwrite successful save feedback.
 t=setup();p=t.c.loadNotes();save=t.c.saveNote({preventDefault(){}});t.pending[1].resolve({note:{id:1,title:'New',content:'new',version:2}});await save;t.pending[0].reject(Error('stale failure'));await p;assert.ok(!t.messages.includes('stale failure'));
 // Delete disables editing while pending; a stale read cannot resurrect the note.
 t=setup();p=t.c.loadNotes();let deletion=t.c.deleteNote();assert.equal(t.ui.content.disabled,true);t.pending[1].resolve({});await deletion;t.pending[0].resolve({notes:[{id:1}]});await p;assert.equal(t.state.notes.length,0);assert.equal(t.ui.content.disabled,false);
 // Failed deletion retains the note and restores editing.
 t=setup();deletion=t.c.deleteNote();t.pending[0].reject(Error('offline'));await deletion;assert.equal(t.state.notes.length,1);assert.equal(t.ui.title.disabled,false);
 // Failed refresh permits a fresh request.
 t=setup();p=t.c.loadNotes();t.pending[0].reject(Error('offline'));await p;p=t.c.loadNotes();assert.equal(t.pending.length,2);t.pending[1].resolve({notes:[]});await p;
 // Discard cannot erase draft recovery while a mutation is in flight.
 t=setup();const discard=source.match(/ui\.discard\.onclick=\(\)=>\{(.*?)\};/)[1];vm.runInContext('function discard(){'+discard+'}',t.c);t.state.busy=true;t.c.discard();assert.equal(t.state.dirty,true);
 console.log('Notes loading and mutation race tests passed');
})().catch(e=>{console.error(e);process.exitCode=1});
