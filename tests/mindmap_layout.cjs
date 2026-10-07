const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const source=fs.readFileSync('dashboard-mindmaps.js','utf8'),ctx={};vm.createContext(ctx);
vm.runInContext(source.slice(source.indexOf('function mindmapLayout('),source.indexOf('function renderMindmapTree('))+source.slice(source.indexOf('function wrapMindmapText('),source.indexOf('function exportMindmapPng(')),ctx);
const root={id:'root',children:Array.from({length:4},(_,i)=>({id:'p'+i,children:Array.from({length:5},(_,j)=>({id:'s'+i+j,children:[]}))}))};
const layout=ctx.mindmapLayout(root);assert.equal(layout.nodes.length,25);assert.equal(layout.edges.length,24);
for(const n of layout.nodes){assert.ok(n.x-160>=0&&n.x+160<=layout.width);assert.ok(n.y-n.height/2>=0&&n.y+n.height/2<=layout.height)}
for(const a of layout.nodes)for(const b of layout.nodes)if(a!==b&&a.depth===b.depth)assert.ok(Math.abs(a.y-b.y)>=(a.height+b.height)/2,'nodes must not overlap');
assert.equal(ctx.mindmapLayout(root,new Set(['p0'])).nodes.length,20);
assert.equal(ctx.mindmapLayout(root,new Set(['root'])).nodes.length,1);
const measure={measureText:s=>({width:[...s].length*10})};const value='ગુજરાતી શબ્દો '+('x'.repeat(100));const lines=ctx.wrapMindmapText(measure,value,80);assert.ok(lines.every(x=>measure.measureText(x).width<=80));assert.equal(lines.join('').replace(/\s/g,''),value.replace(/\s/g,''));
console.log('PASS: full mindmap bounds, non-overlap, collapse and wrapping');
