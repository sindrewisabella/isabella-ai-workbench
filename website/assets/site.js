const stageContent={
  cli:{title:'让重复操作，<br>有一个新的做法。',caption:'招聘 CLI · 流程结构示意',rows:[['人','确定岗位和联系范围','我来判断'],['AI','读取资料，分批联系','按要求执行'],['✓','保留结果，检查回执','有据可查']]},
  salary:{title:'从一份材料，<br>到能核对的方案。',caption:'薪酬工具 · 交互结构示意，识别与上线待验收',rows:[['人','提供材料，确认比较口径','我来确定'],['AI','协助识别和整理流水','逐笔核对'],['✓','比较不同方案的构成','再做选择']]},
  workbench:{title:'每一份笔试，<br>知道下一步是什么。',caption:'笔试工作台 · 流程结构示意',rows:[['人','明确流程与验收要求','我来定义'],['AI','协助搭建页面和同步','工具落地'],['✓','人来验收，记录交接','可追踪']]}
};
for(const b of document.querySelectorAll('[data-stage]'))b.addEventListener('click',()=>{
 const s=stageContent[b.dataset.stage];document.getElementById('stage-title').innerHTML=s.title;
 document.getElementById('stage-caption').textContent=s.caption;
 document.getElementById('stage-content').innerHTML=s.rows.map(([symbol,text,note],i)=>`<div><span class="stage-step-icon ${i===1?'ai':i===2?'result':''}">${symbol}</span><span>${text}</span><b>${note}</b></div>`).join('');
 for(const x of document.querySelectorAll('[data-stage]')){x.classList.toggle('active',x===b);x.setAttribute('aria-pressed',String(x===b))}
});
const stage=document.querySelector('.hero-stage');
if(stage&&!matchMedia('(prefers-reduced-motion: reduce)').matches&&matchMedia('(pointer: fine)').matches){
 let raf;stage.addEventListener('pointermove',event=>{cancelAnimationFrame(raf);raf=requestAnimationFrame(()=>{const r=stage.getBoundingClientRect();stage.style.setProperty('--stage-x',((event.clientX-r.left)/r.width-.5)*7+'deg');stage.style.setProperty('--stage-y',-((event.clientY-r.top)/r.height-.5)*5+'deg')})});
 stage.addEventListener('pointerleave',()=>{stage.style.setProperty('--stage-x','0deg');stage.style.setProperty('--stage-y','0deg')});
}
for(const b of document.querySelectorAll('[data-filter]'))b.addEventListener('click',()=>{
 let count=0;for(const card of document.querySelectorAll('[data-category]')){card.hidden=b.dataset.filter!=='all'&&card.dataset.category!==b.dataset.filter;if(!card.hidden)count++}
 for(const x of document.querySelectorAll('[data-filter]')){x.classList.toggle('active',x===b);x.setAttribute('aria-pressed',String(x===b))}
 document.getElementById('work-count').textContent=`${count} 组作品 · 页面图形为结构示意，具体完成范围见案例`;
});
const escapeHtml=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const dialog=document.getElementById('case-dialog');
if(dialog){
 const caseData=fetch('assets/cases.json').then(r=>{if(!r.ok)throw Error('load');return r.json()});
 for(const button of document.querySelectorAll('[data-case]'))button.addEventListener('click',async()=>{
  document.getElementById('dialog-title').textContent=button.dataset.case;const body=document.getElementById('dialog-body');body.textContent='正在读取作品说明…';dialog.showModal();
  try{const data=await caseData,c=data.find(x=>x.name===button.dataset.case);if(!c)throw Error('missing');
   body.innerHTML=[['为什么做',c.why],['解决什么问题',c.problem],['做到什么效果',c.effect],['怎样展示过程',c.evidence]].map(([title,text])=>`<section><h3>${escapeHtml(title)}</h3><p>${escapeHtml(text)}</p></section>`).join('')+(c.name==='简历评估与校准'?'<img src="assets/evaluation-flow.svg" alt="人工确认标准、AI提取原文证据、生成建议、人工复核并校准的工作流程">':'')+'<p class="dialog-note">这是案例内容概览。具体交互、截图和使用结果将按证据逐项补齐。</p>';
  }catch{body.textContent='作品说明暂时没有加载成功，请关闭后刷新页面重试。'}
 });
 document.getElementById('dialog-close').addEventListener('click',()=>dialog.close());
 dialog.addEventListener('click',e=>{if(e.target===dialog){const r=dialog.getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)dialog.close()}});
}
