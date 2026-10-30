(() => {
  'use strict';
  const exhibit = document.querySelector('#exhibit');
  if (!exhibit) return;
  const esc = value => String(value ?? '').replace(/[&<>"']/g,char=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
  const pct = (a,b) => b ? (100*a/b).toFixed(1) : '0.0';
  const duration = seconds => seconds ? `${Math.floor(seconds/60)} 分 ${Math.round(seconds%60)} 秒` : '未记录';
  let data;
  let scheduled = false;
  const makeFlow = nodes => `<div class="es-batch-flow">${nodes.map(([number,label],index)=>`${index?'<span class="es-flow-arrow" aria-hidden="true">→</span>':''}<div><strong>${esc(number)}</strong><span>${esc(label)}</span></div>`).join('')}</div>`;
  function batchVisual() {
    const index = Number(exhibit.querySelector('#batch-select')?.value ?? 2);
    const batch = data.batches[index];
    if (!batch) return '';
    const flow = batch.scanned ? [[batch.scanned,'扫描人选'],[batch.existing,'已有记录'],[batch.count,'新增评估'],[batch.readback,'回读核验']] : [[batch.count,'单批已评'],[batch.yes,'AI 推荐'],[batch.no,'AI 不推荐'],[batch.readback,'回读核验']];
    return `<div class="es-batch-visual"><section class="es-distribution"><span class="es-visual-kicker">${esc(batch.date)} / ${esc(batch.role)}</span><h3>这一批，留下了什么？</h3><div class="es-distribution-bar" aria-label="${batch.count} 份初筛中，推荐 ${batch.yes} 份，不推荐 ${batch.no} 份"><span style="width:${100*batch.yes/batch.count}%"></span><i style="width:${100*batch.no/batch.count}%"></i></div><div class="es-distribution-labels"><span><i></i>推荐 <b>${batch.yes}</b></span><span><i></i>不推荐 <b>${batch.no}</b></span><small>分母：本批 ${batch.count} 份初筛</small></div><p>批次人数不代表同时并发数；推荐结果与后续业务评估分别核对。</p></section><section class="es-batch-proof">${makeFlow(flow)}<div class="es-time-chip"><span>${batch.elapsedSeconds?'作业完整耗时':'该批完整耗时'}</span><strong>${duration(batch.elapsedSeconds)}</strong><small>${batch.elapsedSeconds?'含初筛、写回及经理结论同步':'没有完整起止记录，不补算提速或耗时'}</small></div></section></div>`;
  }
  function qualityVisual() {
    const role = exhibit.querySelector('[data-role][aria-pressed="true"]')?.dataset.role || 'all';
    const roles = role==='all' ? data.roles : data.roles.filter(item=>item.role===role);
    const paired = roles.reduce((sum,item)=>sum+item.paired,0);
    const agree = roles.reduce((sum,item)=>sum+item.agree,0);
    const disagreement = paired-agree;
    return `<div class="es-quality-visual"><figure class="es-agreement-ring"><svg viewBox="0 0 160 160" role="img" aria-label="${paired} 条配对中，${agree} 条判断相同，${disagreement} 条分歧"><circle class="es-ring-track" cx="80" cy="80" r="63"></circle><circle class="es-ring-value" cx="80" cy="80" r="63" pathLength="100" stroke-dasharray="${pct(agree,paired)} 100"></circle></svg><figcaption><strong>${pct(agree,paired)}<small>%</small></strong><span>判断一致率</span></figcaption></figure><div class="es-quality-copy"><span class="es-visual-kicker">SAME APPLICATION / SAME REVIEW STAGE</span><h3>同一投递，逐条对照。</h3><div class="es-agreement-counts"><div><i></i><span>相同</span><strong>${agree}</strong><small>条</small></div><div><i></i><span>分歧</span><strong>${disagreement}</strong><small>条</small></div><div><span>可配对</span><strong>${paired}</strong><small>条</small></div></div><p>YES 对通过、NO 对不通过计为相同。这里是历史多版本存量对照，<b>不等于当前版本盲测准确率</b>。</p></div><div class="es-role-comparison">${roles.map(item=>`<div><span>${esc(item.role)}</span><i aria-hidden="true"><b style="width:${100*item.agree/item.paired}%"></b></i><strong>${item.agree} / ${item.paired}</strong><small>同判 / 配对</small></div>`).join('')}</div></div>`;
  }
  function assignmentVisual() {
    const assignments=data.assignments;
    const tileRow=(title,count)=>`<section><header><span>${title}</span><strong>${count}<em> / ${assignments.applications}</em></strong></header><div class="es-receipt-tiles" aria-label="${title}，${count} 条已核验任务，${assignments.applications-count} 条未核验">${Array.from({length:assignments.applications},(_,index)=>`<i class="${index<count?'es-tile-verified':'es-tile-pending'}" aria-hidden="true" style="--es-tile-delay:${index*4}ms"></i>`).join('')}</div><small>${count===assignments.applications?'本批对应系统任务均已找到':`${assignments.applications-count} 条尚未完成任务回执核验`}</small></section>`;
    return `<div class="es-assignment-visual"><div class="es-assignment-header"><div><span class="es-visual-kicker">${esc(assignments.date)} / ${esc(assignments.role)} / 独立批次</span><h3>任务回执，一格一条。</h3></div><div class="es-receipt-legend"><span><i></i>已核验任务</span><span><i></i>未完成核验</span></div></div><div class="es-receipt-pair">${tileRow('主评估人',assignments.primaryVerified)}${tileRow('第二评估人',assignments.secondaryVerified)}</div><p>已找到系统评估任务，<b>不代表经理已经提交评估</b>。本批与 51 / 81 份初筛批次分别统计。</p></div>`;
  }
  function enhance() {
    scheduled=false;
    if (!data) return;
    const box=exhibit.querySelector('.case-box');
    const body=exhibit.querySelector('#run-body');
    if (!box || !body) return;
    box.classList.add('es-studio');
    exhibit.querySelector('.run-tabs')?.setAttribute('data-own-keys','true');
    exhibit.querySelector('.run-steps')?.setAttribute('data-own-keys','true');
    const selected=exhibit.querySelector('[data-view][aria-selected="true"]')?.dataset.view || 'runs';
    const signature=[selected,exhibit.querySelector('#batch-select')?.value,exhibit.querySelector('[data-role][aria-pressed="true"]')?.dataset.role].join(':');
    document.querySelectorAll('[data-es-jump]').forEach(button=>button.setAttribute('aria-current',button.dataset.esJump===selected?'true':'false'));
    exhibit.querySelectorAll('[data-view]').forEach(button=>button.tabIndex=button.getAttribute('aria-selected')==='true'?0:-1);
    exhibit.querySelectorAll('[data-phase]').forEach(button=>button.tabIndex=button.getAttribute('aria-selected')==='true'?0:-1);
    const current=body.querySelector('.es-visual');
    if (current?.dataset.signature===signature) return;
    current?.remove();
    const visual=document.createElement('div');visual.className='es-visual';visual.dataset.signature=signature;
    visual.innerHTML=({runs:batchVisual,quality:qualityVisual,assign:assignmentVisual}[selected] || batchVisual)();
    const metrics=body.querySelector('.run-metrics');
    if (metrics) metrics.before(visual); else body.prepend(visual);
  }
  function schedule() { if(!scheduled){scheduled=true;requestAnimationFrame(enhance);} }
  new MutationObserver(schedule).observe(exhibit,{childList:true,subtree:true});
  document.querySelector('.es-overview')?.addEventListener('click',event=>{
    const button=event.target.closest('[data-es-jump]');if(!button)return;
    const target=exhibit.querySelector(`[data-view="${button.dataset.esJump}"]`);
    if(target){target.click();exhibit.scrollIntoView({block:'start',behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'auto':'smooth'});}
  });
  exhibit.addEventListener('keydown',event=>{
    const tab=event.target.closest('[data-view],[data-phase]');
    if(!tab||!['ArrowLeft','ArrowRight','Home','End'].includes(event.key))return;
    event.preventDefault();
    const attribute=tab.hasAttribute('data-view')?'data-view':'data-phase';
    const tabs=[...exhibit.querySelectorAll(`[${attribute}]`)];
    const current=tabs.indexOf(tab),next=event.key==='Home'?0:event.key==='End'?tabs.length-1:(current+(event.key==='ArrowRight'?1:tabs.length-1))%tabs.length;
    const value=tabs[next].getAttribute(attribute);tabs[next].click();exhibit.querySelector(`[${attribute}="${value}"]`)?.focus();
  });
  fetch('evaluation-run-data.json').then(response=>{if(!response.ok)throw Error();return response.json();}).then(result=>{data=result;schedule();}).catch(()=>{});
})();
