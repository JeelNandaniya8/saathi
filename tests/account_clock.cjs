const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const ctx={window:{},Intl,Date,document:{documentElement:{lang:'en'}}};vm.createContext(ctx);vm.runInContext(fs.readFileSync('account-clock.js','utf8'),ctx);const clock=ctx.window.SaathiClock;
clock.setZone('Asia/Kolkata');assert.equal(clock.date('2026-10-13T20:00:00Z'),'2026-10-14');assert.equal(clock.hour('2026-10-13T20:00:00Z'),1);assert.equal(clock.period('2026-10-13T20:00:00Z'),'night');assert.equal(clock.period('2026-10-14T01:30:00Z'),'morning');assert.equal(clock.fromInput('2026-10-15T19:00'),'2026-10-15T13:30:00.000Z');
clock.setZone('America/New_York');assert.throws(()=>clock.fromInput('2026-03-08T02:30'));assert.throws(()=>clock.fromInput('2026-11-01T01:30'));
console.log('PASS account timezone, India midnight and ambiguous daylight-saving times');
