const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const page=fs.readFileSync('dashboard.html','utf8'),account=fs.readFileSync('account.html','utf8');
const group={open:false},nodes=new Map(),node=()=>({hidden:false,classList:{toggle(){}},setAttribute(){},removeAttribute(){},querySelector(){return null}});
const button={...node(),dataset:{view:'memory'},closest:()=>group,querySelector:()=>({textContent:'Memory'})};
const context={state:{currentView:'overview',workspaceReady:false},workspaceViews:['overview','memory'],history:{pushState(){},replaceState(){}},document:{querySelectorAll:selector=>selector==='.view'?[]:[button],querySelector:()=>button},$:id=>{if(!nodes.has(id))nodes.set(id,node());return nodes.get(id)},setNavigation(){},window:{},scrollTo(){}};
vm.createContext(context);vm.runInContext(page.slice(page.indexOf('function openView('),page.indexOf('function syncWorkspaceHistory(')),context);
context.openView('memory',{focus:false});assert.equal(group.open,true,'direct links reveal their navigation group');assert.equal(context.state.currentView,'memory');
assert.ok(page.includes('<details class="nav-more"><summary>'));
assert.ok(!page.includes('id="metricStreak"'));
const passwords=['signupPassword','loginPassword','resetPassword'].map(id=>({id,type:'password',parentElement:{append(button){this.button=button}}}));
const authContext={document:{querySelectorAll:()=>passwords,createElement:()=>({attributes:{},setAttribute(k,v){this.attributes[k]=v},addEventListener(_,fn){this.click=fn}})}};
vm.createContext(authContext);const start=account.indexOf("document.querySelectorAll('input[type=\"password\"]')");vm.runInContext(account.slice(start,account.indexOf("switchTab(params.get('mode')",start)),authContext);
for(const input of passwords){const b=input.parentElement.button;assert.equal(b.type,'button');b.click();assert.equal(input.type,'text');assert.equal(b.attributes['aria-pressed'],'true');b.click();assert.equal(input.type,'password');assert.equal(b.attributes['aria-pressed'],'false')}
assert.ok(account.includes("if(event.persisted)checkExistingSession()"));
console.log('PASS deep-link navigation, retained tools, password toggle semantics and session-check guard');

// Scheduling a check-in prepares a reviewable draft without a network write.
const reminderNodes=new Map(),notices=[],opened=[];
const checkinCtx={state:{user:{language:'en'},reminderEditingId:null},translations:{en:{checkinReminderTitle:'How are you?',checkinReminderNote:'Optional',checkinDraftKept:'Kept',checkinReview:'Review'}},$:id=>{if(!reminderNodes.has(id))reminderNodes.set(id,{value:'',focus(){this.focused=true}});return reminderNodes.get(id)},openView:id=>opened.push(id),toast:message=>notices.push(message)};
vm.createContext(checkinCtx);const helper=page.slice(page.indexOf('function readReminderDraft()'),page.indexOf("$('reminderForm').addEventListener('submit'",page.indexOf('function readReminderDraft()')));vm.runInContext(helper,checkinCtx);
checkinCtx.prepareCheckinReminder();assert.equal(reminderNodes.get('reminderTitle').value,'How are you?');assert.equal(reminderNodes.get('reminderTime').value,'');assert.equal(reminderNodes.get('reminderRecurrence').value,'once');assert.ok(reminderNodes.get('reminderTime').focused);
reminderNodes.get('reminderTitle').value='My unsaved reminder';checkinCtx.prepareCheckinReminder();assert.equal(reminderNodes.get('reminderTitle').value,'My unsaved reminder');assert.equal(notices.at(-1),'Kept');

// Sensitive free-text stays out of a clinician-shareable file unless opted in.
const summaryCtx={Intl};vm.createContext(summaryCtx);vm.runInContext(page.slice(page.indexOf('function checkinSummaryText('),page.indexOf('async function downloadCheckinSummary(')),summaryCtx);
const records=[{created_at:'2026-10-08T09:00:00Z',mood:3,energy:4,note:'Private health note'}],summaryWords={checkinSummaryTitle:'Summary',checkinSummaryNote:'Self-reported',checkinMood:'Mood',checkinEnergy:'Energy'};
const privateSummary=summaryCtx.checkinSummaryText(records,summaryWords,'Asia/Kolkata',false);assert.ok(privateSummary.includes('Mood: 3/5'));assert.ok(privateSummary.includes('Asia/Kolkata'));assert.ok(!privateSummary.includes('Private health note'));
assert.ok(summaryCtx.checkinSummaryText(records,summaryWords,'UTC',true).includes('Private health note'));
