/* Interactive, prewritten Skill examples. No model or business service is invoked. */
(()=>{'use strict';
 const escape=value=>String(value??'').replace(/[&<>"']/g,char=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
 const mounts=new WeakMap();
 const icons={
  'feishu-candidate-recommendation-card':'<rect x="6" y="5" width="28" height="30" rx="5"/><circle cx="15" cy="15" r="4"/><path d="M10 27c1-7 10-7 11 0m4-14h5m-5 6h5m-5 6h3"/>',
  'meeting-analyzer':'<path d="M5 6h30v22H21l-9 7v-7H5z"/><path d="M12 14h16m-16 6h10"/>',
  'hire-eval-builder':'<rect x="7" y="4" width="27" height="32" rx="4"/><path d="m12 14 3 3 5-7m5 5h4m-17 12 3 3 5-7m5 5h4"/>'
 };
 const icon=id=>`<svg viewBox="0 0 40 40" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${icons[id]||icons['hire-eval-builder']}</svg>`;
 const excerpt=(value,max=65)=>{const text=String(value||'');return text.length>max?text.slice(0,max)+'…':text};
 function mount({root,methods=[],skillHref=id=>'skill.html?id='+encodeURIComponent(id)}){
  if(!root)return;
  mounts.get(root)?.();
  const controller=new AbortController(),signal=controller.signal;
  root.classList.add('methods-motion-grid');
  root.innerHTML=methods.map((method,index)=>{
   const input=String(method.input||'').split('\n').filter(Boolean).slice(0,3),output=String(method.output||'').split('\n').filter(Boolean),prefix='methods-motion-'+method.id;
   return `<article class="methods-motion-card" data-methods-motion-card="${escape(method.id)}"><div class="methods-motion-heading"><span class="methods-motion-icon">${icon(method.id)}</span><span class="methods-motion-number">0${index+1}</span></div><h3>${escape(method.name)}</h3><p class="methods-motion-description">${escape(method.short||method.what||'')}</p><div class="methods-motion-tabs" role="tablist" aria-label="${escape(method.name)}预置示例"><button type="button" role="tab" id="${prefix}-input" data-methods-motion-tab="input" aria-selected="true" aria-controls="${prefix}-panel">输入材料</button><button type="button" role="tab" id="${prefix}-output" data-methods-motion-tab="output" aria-selected="false" aria-controls="${prefix}-panel" tabindex="-1">输出示例</button><span>预置示例</span></div><div class="methods-motion-stage" data-state="input" role="tabpanel" id="${prefix}-panel" aria-labelledby="${prefix}-input" tabindex="0"><div class="methods-motion-stage-caption"><span data-methods-motion-caption>先把材料放在一起</span><i aria-hidden="true"></i></div><div class="methods-motion-sources" aria-hidden="false">${input.map((line,i)=>`<div class="methods-motion-source methods-motion-source-${i}"><span class="methods-motion-source-number">0${i+1}</span><p>${escape(excerpt(line))}</p><span class="methods-motion-source-corner" aria-hidden="true">↘</span></div>`).join('')}</div><div class="methods-motion-trace" aria-hidden="true"><svg viewBox="0 0 260 200" fill="none"><path d="M45 57c58 0 32 61 85 61s32-61 85-61m-170 53c58 0 32 8 85 8s32-8 85-8m-85 8v40"/></svg></div><div class="methods-motion-output" aria-hidden="true"><div class="methods-motion-output-top"><span class="methods-motion-page-icon" aria-hidden="true">▤</span><strong>${escape(output[0]||'输出示例')}</strong><span class="methods-motion-output-mark" aria-hidden="true">✳</span></div><div class="methods-motion-output-lines">${output.slice(1,5).map((line,i)=>`<p style="--mm-line:${i}">${escape(excerpt(line,85))}</p>`).join('')}</div></div></div><div class="methods-motion-bottom-caption"><span data-methods-motion-stage-label>示例输入 · 材料节选</span><span>完整内容见详情</span></div><div class="methods-motion-actions"><a href="${escape(skillHref(method.id))}">完整示例 <span aria-hidden="true">↗</span></a><button type="button" data-preview="skill:${escape(method.id)}" aria-haspopup="dialog" aria-label="快速预览${escape(method.name)}的完整输入与输出"><span>展开</span><i aria-hidden="true">＋</i></button></div></article>`;
  }).join('');
  function activate(card,mode,focus=false){
   const stage=card.querySelector('.methods-motion-stage'),tabs=[...card.querySelectorAll('[data-methods-motion-tab]')];
   stage.dataset.state=mode;stage.setAttribute('aria-labelledby',tabs.find(tab=>tab.dataset.methodsMotionTab===mode).id);
   tabs.forEach(tab=>{const selected=tab.dataset.methodsMotionTab===mode;tab.setAttribute('aria-selected',String(selected));tab.tabIndex=selected?0:-1;if(selected&&focus)tab.focus({preventScroll:true})});
   card.querySelector('.methods-motion-sources').setAttribute('aria-hidden',String(mode!=='input'));
   card.querySelector('.methods-motion-output').setAttribute('aria-hidden',String(mode!=='output'));
   card.querySelector('[data-methods-motion-caption]').textContent=mode==='input'?'先把材料放在一起':'把依据整理成清楚的产物';
   card.querySelector('[data-methods-motion-stage-label]').textContent=mode==='input'?'示例输入 · 材料节选':'示例输出 · 预置内容';
  }
  root.addEventListener('click',event=>{const tab=event.target.closest('[data-methods-motion-tab]');if(tab)activate(tab.closest('[data-methods-motion-card]'),tab.dataset.methodsMotionTab)},{signal});
  root.addEventListener('keydown',event=>{const tab=event.target.closest('[data-methods-motion-tab]');if(!tab||!['ArrowLeft','ArrowRight','Home','End'].includes(event.key))return;event.preventDefault();const mode=event.key==='Home'?'input':event.key==='End'?'output':tab.dataset.methodsMotionTab==='input'?'output':'input';activate(tab.closest('[data-methods-motion-card]'),mode,true)},{signal});
  mounts.set(root,()=>controller.abort());
 }
 window.IsabellaMethods={mount};
})();
