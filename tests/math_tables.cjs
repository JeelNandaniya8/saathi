const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const source=fs.readFileSync('message-format.js','utf8'),ctx={};vm.createContext(ctx);
vm.runInContext(source.slice(source.indexOf('function tableCells('),source.indexOf('function renderMarkdown(')),ctx);
for(const [line,expected] of [
 ['| Conditional | $P(A|B)=P(A\\cap B)/P(B)$ |',['Conditional','$P(A|B)=P(A\\cap B)/P(B)$']],
 ['| Given | \\(P(A|B)\\) |',['Given','\\(P(A|B)\\)']],
 ['Code | `left|right`',['Code','`left|right`']],
 ['| Literal | a\\|b |',['Literal','a\\|b']],
 ['| Plain | P(A|B) |',['Plain','P(A|B)']],
 ['| Absolute | $$|x|$$ |',['Absolute','$$|x|$$']],
])assert.deepEqual(Array.from(ctx.tableCells(line)),expected);
console.log('PASS math/code/literal bars stay within Markdown table cells');
