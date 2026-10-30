(()=>{'use strict';
 const exhibit=document.querySelector('#exhibit'),workspace=document.querySelector('.ss-workspace'),steps=[...document.querySelectorAll('[data-ss-open]')],feedback=document.querySelector('.ss-state-copy');
 const order=['import','payroll','offers','history'];let frame=0,lastPanel=null,focusAfter='';
 const text=(selector,value)=>{const element=exhibit.querySelector(selector);if(element&&element.textContent!==value)element.textContent=value};
 function sync(){
  frame=0;const native=exhibit.querySelector('[data-salary-tab][aria-selected=true]'),panel=exhibit.querySelector('#salary-panel');if(!native||!panel)return;const current=native.dataset.salaryTab;
  workspace.dataset.stage=current;steps.forEach(step=>{const active=step.dataset.ssOpen===current;step.setAttribute('aria-selected',String(active));step.tabIndex=active?0:-1});panel.setAttribute('aria-labelledby','ss-step-'+current);
  text('.box-bar strong','Comp·Pass / 从材料到可核对的流水');text('.box-bar .tiny-label','虚构材料与预置结果 · 未调用 OCR 或 AI 识别服务');
  text('.import-intro h2','先看材料，再核对每一笔。');
  let message='查看虚构截图或录屏，展开已整理的预置结果，再人工核对。';
  if(current==='import'&&exhibit.querySelector('#import-review-status'))message=exhibit.querySelector('#review-import')?.checked?'复核已勾选；确认写入后，流水与比较区间会在本页同步更新。':'请核对收入所属月、实际到账日、金额，以及本次写入的月份口径。';
  if(current==='payroll')message='当前所选区间合计：'+(exhibit.querySelector('#payroll-sum')?.textContent||'待校对')+'。可修改月份与金额，并随时对照原件。';
  if(current==='offers')message=exhibit.querySelector('#compare-result')?.textContent||'修改两版方案的月薪和发薪月数，按相同年度口径比较。';
  if(current==='history')message='本次演示的修改与版本记录保留在这里；刷新或重置后清空。';
  if(feedback.textContent!==message)feedback.textContent=message;
  if(current==='offers'){
   const totalA=exhibit.querySelector('#total-a')?.textContent||'待补充',totalB=exhibit.querySelector('#total-b')?.textContent||'待补充',signature=totalA+'|'+totalB;
   let chart=exhibit.querySelector('.ss-comparison-chart');if(!chart){chart=document.createElement('div');chart.className='ss-comparison-chart';chart.setAttribute('aria-label','两版方案税前年现金图示');exhibit.querySelector('.offer-grid')?.after(chart)}
   if(chart.dataset.signature!==signature){chart.dataset.signature=signature;chart.innerHTML='<p class="ss-chart-title">当前输入对应的税前年现金 · 同一年度口径</p><div class="ss-chart-row"><span>方案 A</span><div class="ss-chart-track"><span data-ss-bar="a"></span></div><strong data-ss-total="a"></strong></div><div class="ss-chart-row"><span>方案 B</span><div class="ss-chart-track"><span data-ss-bar="b"></span></div><strong data-ss-total="b"></strong></div>';const a=Number(totalA.replace(/[^0-9.-]/g,'')),b=Number(totalB.replace(/[^0-9.-]/g,'')),max=Math.max(a,b,1);for(const [key,total,value]of[['a',totalA,a],['b',totalB,b]]){chart.querySelector('[data-ss-total="'+key+'"]').textContent=total;chart.querySelector('[data-ss-bar="'+key+'"]').style.width=Number.isFinite(value)&&/\d/.test(total)?Math.max(0,value/max)*100+'%':'0%'}}
  }
  if(panel!==lastPanel){lastPanel=panel;if(!matchMedia('(prefers-reduced-motion: reduce)').matches)panel.classList.add('ss-panel-enter');if(focusAfter){let target;if(focusAfter==='review')target=panel.querySelector('.import-result-title h3');else if(focusAfter==='payroll')target=panel.querySelector('h2');else target=exhibit.querySelector('#'+focusAfter);if(target){if(!target.matches('button,input,select,a'))target.tabIndex=-1;target.focus({preventScroll:true})}focusAfter=''}}
 }
 function schedule(){if(!frame)frame=requestAnimationFrame(sync)}
 steps.forEach(step=>step.addEventListener('click',()=>{const native=exhibit.querySelector('[data-salary-tab="'+step.dataset.ssOpen+'"]');native?.click();schedule()}));
 document.querySelector('.ss-workflow').addEventListener('keydown',event=>{const button=event.target.closest('[data-ss-open]');if(!button||!['ArrowLeft','ArrowRight','Home','End'].includes(event.key))return;event.preventDefault();let index=order.indexOf(button.dataset.ssOpen);index=event.key==='Home'?0:event.key==='End'?order.length-1:(index+(event.key==='ArrowRight'?1:-1)+order.length)%order.length;steps[index].click();steps[index].focus({preventScroll:true})});
 exhibit.addEventListener('click',event=>{if(event.target.closest('#load-import-example'))focusAfter='review';else if(event.target.closest('#apply-import'))focusAfter='payroll';else if(event.target.closest('#reset-salary'))focusAfter='reset-salary';else if(event.target.closest('#save-version'))focusAfter='save-version'},true);
 new MutationObserver(schedule).observe(exhibit,{childList:true,subtree:true,characterData:true});document.querySelector('#tour')?.classList.add('ss-short-tour');document.querySelector('#material-dialog')?.classList.add('ss-material-dialog');sync();
})();
