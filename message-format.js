/* Shared safe Markdown and native MathML; all rendering assets are self-hosted. */
(function(){'use strict';
function math(target,tex,block=false){
  target.style.maxWidth='100%';target.style.overflowX='auto';target.style.display=block?'block':'inline-block';target.style.verticalAlign='middle';target.style.fontSize=/\\(?:dfrac|tfrac|frac|binom)\b/.test(tex)?'max(1.3em, 21px)':'max(1.15em, 18px)';target.style.lineHeight='1.65';target.style.paddingBlock='3px';
  target.setAttribute('aria-label',tex);target.dataset.math=tex;target.dataset.display=String(block);
  if(!window.katex){target.textContent=tex;return}
  try{
    window.katex.render(!block&&/\\(?:dfrac|tfrac|frac|binom)\b/.test(tex)?'\\displaystyle '+tex:tex,target,{output:'mathml',displayMode:block,throwOnError:true,trust:false,maxExpand:200,maxSize:15});
    // Keep native fraction descenders inside the inline wrapper's scroll area.
    if(!block)target.querySelector('math')?.style.setProperty('display','block')
  }
  catch(error){target.replaceChildren(document.createTextNode(tex));target.title='Formula could not be rendered';target.classList.add('math-error')}
}
function appendInline(target,text){
  const source=String(text||''),pattern=/(`[^`\n]+`|\\(?:frac|sqrt)\{(?:[^{}]|\{[^{}]*\})*\}(?:\{(?:[^{}]|\{[^{}]*\})*\})?|\\\[[\s\S]*?\\\]|\\\([\s\S]*?\\\)|\$\$[\s\S]*?\$\$|\$[^$\n]+\$|\\[\\`*_{}\[\]()<>#|$]|\*\*[^*\n]+\*\*|__[^_\n]+__|\*[^*\n]+\*|_[^_\n]+_|\[[^\]\n]+\]\(https?:\/\/[^\s)]+\)|\[▶\s*Play[^\]\n]+\]|\[🫁\s*[^\]\n]+\])/gi;let last=0;
  source.replace(pattern,(match,token,offset)=>{if(offset>last)target.append(document.createTextNode(source.slice(last,offset)));let node;
    const link=token.match(/^\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)$/);
    if(link){node=document.createElement('a');node.textContent=link[1];node.href=link[2];node.target='_blank';node.rel='noopener noreferrer'}
    else if(/^\[▶\s*Play\s*432Hz/i.test(token)){node=document.createElement('button');node.type='button';node.className='action-chip-btn';node.innerHTML='<span>🕉️</span> Play soft tone';node.onclick=()=>window.toggleChatAmbient?.('om')}
    else if(/^\[▶\s*Play\s*(Gentle\s*)?Rain/i.test(token)){node=document.createElement('button');node.type='button';node.className='action-chip-btn';node.innerHTML='<span>🌧️</span> Play Rain';node.onclick=()=>window.toggleChatAmbient?.('rain')}
    else if(/^\[▶\s*Play\s*Ocean/i.test(token)){node=document.createElement('button');node.type='button';node.className='action-chip-btn';node.innerHTML='<span>🌊</span> Play Ocean';node.onclick=()=>window.toggleChatAmbient?.('ocean')}
    else if(/^\[🫁/i.test(token)){node=document.createElement('button');node.type='button';node.className='action-chip-btn';node.innerHTML='<span>🫁</span> Gentle breathing';node.onclick=()=>window.openChatBreathing?.()}
    else if(token.startsWith('$')||token.startsWith('\\(')||token.startsWith('\\[')||/^\\(?:frac|sqrt)/.test(token)){node=document.createElement('span');const block=token.startsWith('$$')||token.startsWith('\\['),size=token.startsWith('$$')||token.startsWith('\\')?2:1;node.className='math-inline'+(block?' math-display':'');math(node,/^\\(?:frac|sqrt)/.test(token)?token:token.slice(size,-size),block)}
    else if(token.startsWith('\\')&&token.length===2){node=document.createTextNode(token[1])}
    else if(token.startsWith('`')){node=document.createElement('code');node.textContent=token.slice(1,-1)}
    else if(token.startsWith('**')||token.startsWith('__')){node=document.createElement('strong');appendInline(node,token.slice(2,-2))}
    else{node=document.createElement('em');appendInline(node,token.slice(1,-1))}
    target.append(node);last=offset+match.length;return match
  });if(last<source.length)target.append(document.createTextNode(source.slice(last)))
}
function markdownBlockStart(lines,index){
  const line=lines[index]||'',next=lines[index+1]||'';
  return !line.trim()||/^\s*```/.test(line)||/^#{1,6}\s+/.test(line)||/^\s*[-*+]\s+/.test(line)||/^\s*\d+[.)]\s+/.test(line)||/^\s*>\s?/.test(line)||/^\s*(?:-{3,}|\*{3,}|_{3,})\s*$/.test(line)||(line.includes('|')&&/^\s*\|?\s*:?-{3,}/.test(next));
}
function tableCells(line){
  // Markdown separators belong outside math, code and escaped literal bars.
  const tokens=[],protectedLine=line.replace(/`[^`\n]+`|\\\[[^\n]*?\\\]|\\\([^\n]*?\\\)|\$\$[^\n]*?\$\$|\$[^$\n]+\$|\\\||\bP\([^\n)]*\|[^\n)]*\)/g,value=>'\u0000'+(tokens.push(value)-1)+'\u0000');
  return protectedLine.trim().replace(/^\||\|$/g,'').split('|').map(cell=>cell.trim().replace(/\u0000(\d+)\u0000/g,(_,index)=>tokens[Number(index)]))
}
function renderMarkdown(target,text){
  target.replaceChildren();const lines=String(text||'').replace(/\r\n?/g,'\n').split('\n');let index=0;
  while(index<lines.length){const line=lines[index];if(!line.trim()){index++;continue}
    const fence=line.match(/^\s*```\s*([^\s`]*)/);if(fence){const code=[];index++;while(index<lines.length&&!/^\s*```/.test(lines[index]))code.push(lines[index++]);if(index<lines.length)index++;const shell=document.createElement('div');shell.className='code-block';const head=document.createElement('div');head.className='code-head';const language=document.createElement('span');language.textContent=fence[1]||'Code';const copy=document.createElement('button');copy.type='button';copy.className='code-copy';copy.textContent='Copy';copy.addEventListener('click',()=>navigator.clipboard?.writeText(code.join('\n')).catch(()=>{}));head.append(language,copy);const pre=document.createElement('pre'),codeNode=document.createElement('code');codeNode.textContent=code.join('\n');pre.append(codeNode);shell.append(head,pre);target.append(shell);continue}
    if(/^\s*(?:-{3,}|\*{3,}|_{3,})\s*$/.test(line)){target.append(document.createElement('hr'));index++;continue}
    const heading=line.match(/^(#{1,6})\s+(.+)/);if(heading){
      const node=document.createElement('h'+heading[1].length);appendInline(node,heading[2]);target.append(node);index++;continue
    }
    const listMatch=line.match(/^\s*([-*+]|\d+[.)])\s+(.+)/);if(listMatch){const ordered=/\d/.test(listMatch[1]),list=document.createElement(ordered?'ol':'ul');while(index<lines.length){const item=lines[index].match(ordered?/^\s*\d+[.)]\s+(.+)/:/^\s*[-*+]\s+(.+)/);if(!item)break;const li=document.createElement('li');appendInline(li,item[1]);list.append(li);index++}target.append(list);continue}
    if(/^\s*>\s?/.test(line)){const quote=document.createElement('blockquote'),parts=[];while(index<lines.length&&/^\s*>\s?/.test(lines[index]))parts.push(lines[index++].replace(/^\s*>\s?/,''));appendInline(quote,parts.join('\n'));target.append(quote);continue}
    if(line.includes('|')&&index+1<lines.length&&/^\s*\|?\s*:?-{3,}/.test(lines[index+1])){const headers=tableCells(line);index+=2;const wrap=document.createElement('div');wrap.className='table-wrap';const table=document.createElement('table'),thead=document.createElement('thead'),headRow=document.createElement('tr');headers.forEach(value=>{const th=document.createElement('th');appendInline(th,value);headRow.append(th)});thead.append(headRow);table.append(thead);const tbody=document.createElement('tbody');while(index<lines.length&&lines[index].includes('|')&&lines[index].trim()){const tr=document.createElement('tr');tableCells(lines[index++]).forEach(value=>{const td=document.createElement('td');appendInline(td,value);tr.append(td)});tbody.append(tr)}table.append(tbody);wrap.append(table);target.append(wrap);continue}
    const paragraph=[];while(index<lines.length){if(paragraph.length&&markdownBlockStart(lines,index))break;paragraph.push(lines[index++]);if(index>=lines.length||!lines[index].trim())break}const p=document.createElement('p');appendInline(p,paragraph.join('\n'));target.append(p)
  }
}
document.addEventListener('DOMContentLoaded',()=>{for(const target of document.querySelectorAll('[data-math]'))math(target,target.dataset.math,target.dataset.display==='true')});
window.SaathiMarkup={render:renderMarkdown,inline:appendInline,math};
})();
