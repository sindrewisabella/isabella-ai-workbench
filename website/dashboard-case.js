/* Guided viewing of the original historical snapshot; source data and calculations stay in the embedded page. */
(()=>{'use strict';
 const $=selector=>document.querySelector(selector),canvas=$('#exhibit'),frame=$('#dashboard-frame'),guide=$('#dashboard-guide-content'),announcement=$('#dashboard-announcement'),reduce=matchMedia('(prefers-reduced-motion: reduce)');
 if(!canvas||!frame||!guide)return;
 const escape=value=>String(value??'').replace(/[&<>"']/g,char=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
 const source='fullstack-dashboard/index.html?start=2026-07-01&end=2026-09-21';
 const zones={
  funnel:{anchor:'fullstack-funnel',name:'招聘漏斗',number:'01',title:'从总体到个人，看清每一轮的推进。',purpose:'定位需要复核的流失或积压，再回到具体记录。',problem:'飞书记录分散，笔试又占用了面试轮次，直接照搬系统阶段不容易看懂真实招聘流程。',feature:'把简历入库、评估、各轮技术面、HR 面和入职放进一个视图；点击阶段，展开进入时间、来源与当前状态。Offer 沟通和待入职在 HR 明细中查看。',steps:['先在看板顶部选择统计周期。','点击一个漏斗阶段，查看该周期的阶段人选。','在阶段明细中对照进入时间、来源与当前状态。'],note:'相邻阶段数字可用于观察转化，但不同阶段按各自时间窗口统计，不必然属于同一批人，不能直接当作严格同批转化率。'},
  trend:{anchor:'fullstack-trend',name:'渠道趋势',number:'02',title:'推荐得多，还要看能否进入下一步。',purpose:'让渠道投入和后续推进放在一起看，为调整寻访方式提供线索。',problem:'只有总推荐量，分不清是寻访量不够，还是推荐材料与岗位要求不匹配。',feature:'在同一周期里对照 HR 寻访、猎头等渠道进入评估与评估通过的数量，并可切换周、双周、月和自定义日期。',steps:['先把统计周期固定在同一范围。','对照不同渠道进入评估与评估通过的数量。','结合岗位、材料质量与时间范围复核差异。'],note:'数量差异只是分析起点，仍需结合岗位难度、材料质量与时间范围复核。'},
  goals:{anchor:'fullstack-goals-section',name:'目标完成度',number:'03',title:'把“最近很忙”，变成目标与实际的对照。',purpose:'区分需要补的是数量还是匹配度，帮助安排下一周期的招聘动作。',problem:'只说每天处理了很多简历，不能回答推荐量是否足够、质量是否达标、距离目标还差多少。',feature:'左边放既定推荐量与通过率目标，右边放所选周期的实际完成、完成率和差距。',steps:['先看左侧已经配置的业务目标。','对照右侧所选周期的推荐量与实际通过率。','把完成率和差距放在一起看，区分数量与匹配度。'],note:'目标来自这个看板的业务配置，不是通用招聘标准，也不是 AI 自动做出的经营判断。'},
  interview:{anchor:'fullstack-interview-section',name:'面试官分析',number:'04',title:'把面试轮次、面评结果和反馈缺口连起来。',purpose:'看到哪些记录尚未提交结论、哪些环节值得复核，再推动具体反馈。',problem:'当时的系统页面难以直接按面试官汇总多轮进展，笔试占用轮次后，仅看轮次名更容易误判。',feature:'按约定的面试官与轮次规则整理记录，筛选面试官和结果，对照各轮评分、通过／不通过／待定及当前阶段，并展开完整明细。',steps:['使用“面试官”筛选，定位需要查看的范围。','结合面评结果、轮次和当前阶段一起看。','展开完整明细，核对尚未提交或需要复核的结论。'],note:'通过率差异可以提示问题，不足以单独判定面试官质量；待面试或未提交结论也不等于“不通过”。'}
 };
 let current='funnel',guideMode='steps',ready=false,loadTimer,expanded=false,boundDocument=null;const inertBefore=new Map();
 function speak(message){$('#dashboard-zone-status').textContent=message;announcement.textContent=message}
 function renderGuide(){
  const z=zones[current];
  guide.innerHTML=`<div class="dashboard-guide-top"><span>GUIDED VIEW / 当前模块</span><strong>${z.number}</strong></div><h3>${escape(z.title)}</h3><p class="dashboard-guide-purpose">${escape(z.purpose)}</p><div class="dashboard-guide-tabs" role="tablist" aria-label="${escape(z.name)}说明"><button type="button" role="tab" id="dashboard-guide-steps" data-guide-mode="steps" aria-selected="${guideMode==='steps'}" aria-controls="dashboard-guide-body" tabindex="${guideMode==='steps'?0:-1}">操作指引</button><button type="button" role="tab" id="dashboard-guide-scope" data-guide-mode="scope" aria-selected="${guideMode==='scope'}" aria-controls="dashboard-guide-body" tabindex="${guideMode==='scope'?0:-1}">设计与口径</button></div><div id="dashboard-guide-body" class="dashboard-guide-body" role="tabpanel" aria-labelledby="dashboard-guide-${guideMode}">${guideMode==='steps'?`<ol>${z.steps.map(step=>`<li>${escape(step)}</li>`).join('')}</ol>`:`<p>${escape(z.problem)}</p><p>${escape(z.feature)}</p><p class="dashboard-guide-note">${escape(z.note)}</p>`}</div><button type="button" class="dashboard-locate" id="locate-zone">在画布中定位${escape(z.name)} <span aria-hidden="true">↖</span></button>`;
 }
 function clearHighlights(doc){doc.querySelectorAll('.dashboard-studio-focus').forEach(element=>element.classList.remove('dashboard-studio-focus'))}
 function locate({focus=false}={}){
  if(!ready){speak('原版看板正在载入，完成后可定位到'+zones[current].name+'。');return}
  try{
   const doc=frame.contentDocument,z=zones[current],target=doc.getElementById(z.anchor);
   if(!target||target.hidden||!target.getClientRects().length){speak('当前岗位视图未展示这个区域，可在原版看板切回全栈岗位后再定位。');return}
   clearHighlights(doc);target.classList.add('dashboard-studio-focus');frame.contentWindow.scrollTo({top:target.getBoundingClientRect().top+frame.contentWindow.scrollY-19,behavior:reduce.matches?'instant':'smooth'});
   if(focus){target.tabIndex=-1;target.focus({preventScroll:true})}
   speak('已定位到'+z.name+'。可以在原版画布中继续筛选或展开记录。');
  }catch{speak('暂时无法定位，可单独打开原版看板继续浏览。')}
 }
 function show(key,{locateCanvas=true,focusTab=false}={}){
  if(!zones[key])return;current=key;guideMode='steps';document.querySelectorAll('[data-zone]').forEach(button=>{const active=button.dataset.zone===key;button.setAttribute('aria-selected',String(active));button.tabIndex=active?0:-1;if(active&&focusTab)button.focus({preventScroll:true})});$('#dashboard-zone').setAttribute('aria-labelledby','tab-'+key);renderGuide();if(locateCanvas)locate();
 }
 function visibleControls(scope){return [...scope.querySelectorAll('a[href],button:not([disabled]),input:not([disabled]),select:not([disabled]),iframe,[tabindex]')].filter(element=>element.tabIndex>=0&&!element.closest('[hidden],[inert]')&&element.getClientRects().length)}
 function setBackgroundInert(active){
  if(!active){inertBefore.forEach((wasInert,element)=>{element.inert=wasInert});inertBefore.clear();return}
  let branch=canvas;while(branch.parentElement){const parentElement=branch.parentElement;[...parentElement.children].forEach(element=>{if(element!==branch&&element instanceof HTMLElement&&!['SCRIPT','STYLE','LINK'].includes(element.tagName)){inertBefore.set(element,element.inert);element.inert=true}});if(parentElement===document.body)break;branch=parentElement}
 }
 function setExpanded(force){expanded=typeof force==='boolean'?force:!expanded;canvas.classList.toggle('expanded',expanded);document.body.classList.toggle('demo-expanded',expanded);$('#expand-dashboard').textContent=expanded?'收起画布 ↙':'放大画布 ⤢';$('#expand-dashboard').setAttribute('aria-expanded',String(expanded));setBackgroundInert(expanded);if(expanded){canvas.setAttribute('role','dialog');canvas.setAttribute('aria-modal','true')}else{canvas.removeAttribute('role');canvas.removeAttribute('aria-modal');$('#expand-dashboard').focus({preventScroll:true})}}
 function setLoadState(failed=false){ready=false;const state=$('#dashboard-frame-state');state.hidden=false;state.classList.toggle('is-error',failed);state.querySelector('p').textContent=failed?'原版看板暂未载入。可以重新打开，或使用“单独打开”入口。':'正在打开原版看板…';$('#retry-dashboard').hidden=!failed;$('#dashboard-load-label').textContent=failed?'快照暂未载入':'正在载入历史快照…'}
 function frameReady(){
  clearTimeout(loadTimer);
  try{
   const doc=frame.contentDocument;if(!doc?.getElementById('fullstack-funnel')){setLoadState(true);return}
   ready=true;$('#dashboard-frame-state').hidden=true;$('#dashboard-load-label').textContent='2026.09.21 历史脱敏快照';
   if(!doc.getElementById('dashboard-studio-guide-style')){const style=doc.createElement('style');style.id='dashboard-studio-guide-style';style.textContent='.dashboard-studio-focus{outline:3px solid #90a67a;outline-offset:7px;border-radius:13px;animation:dashboardStudioLocate 1.1s ease-out}@keyframes dashboardStudioLocate{from{outline-color:#b99867;outline-offset:12px}to{outline-color:#90a67a;outline-offset:7px}}@media(prefers-reduced-motion:reduce){.dashboard-studio-focus{animation:none}}';doc.head.append(style)}
   if(boundDocument!==doc){boundDocument=doc;doc.addEventListener('keydown',event=>{
    if(!expanded)return;
    if(event.key==='Escape'){event.preventDefault();event.stopImmediatePropagation();setExpanded(false);return}
    if(event.key==='Tab'){const controls=visibleControls(doc),outer=visibleControls(canvas),frameIndex=outer.indexOf(frame);if(event.shiftKey&&doc.activeElement===controls[0]){event.preventDefault();(outer[frameIndex-1]||outer[outer.length-1]).focus({preventScroll:true})}else if(!event.shiftKey&&doc.activeElement===controls[controls.length-1]){event.preventDefault();(outer[frameIndex+1]||outer[0]).focus({preventScroll:true})}}
   },true);}
   speak('原版看板已打开。可直接浏览，或选择一个模块查看指引。');
  }catch{setLoadState(true)}
 }
 function reloadFrame(){setLoadState(false);frame.src=source;clearTimeout(loadTimer);loadTimer=setTimeout(()=>{if(!ready)setLoadState(true)},10000);speak('正在恢复初始日期范围和筛选状态。')}
 $('.dashboard-tabs').addEventListener('click',event=>{const button=event.target.closest('[data-zone]');if(button)show(button.dataset.zone)});
 $('.dashboard-tabs').addEventListener('keydown',event=>{const button=event.target.closest('[data-zone]');if(!button||!['ArrowLeft','ArrowRight','Home','End'].includes(event.key))return;event.preventDefault();event.stopPropagation();const keys=Object.keys(zones),i=keys.indexOf(current),next=event.key==='Home'?0:event.key==='End'?keys.length-1:(i+(event.key==='ArrowLeft'?-1:1)+keys.length)%keys.length;show(keys[next],{focusTab:true})});
 guide.addEventListener('click',event=>{const mode=event.target.closest('[data-guide-mode]');if(mode){guideMode=mode.dataset.guideMode;renderGuide();guide.querySelector('[data-guide-mode="'+guideMode+'"]').focus({preventScroll:true});return}if(event.target.closest('#locate-zone'))locate({focus:true})});
 guide.addEventListener('keydown',event=>{const mode=event.target.closest('[data-guide-mode]');if(!mode||!['ArrowLeft','ArrowRight','Home','End'].includes(event.key))return;event.preventDefault();event.stopPropagation();guideMode=event.key==='Home'?'steps':event.key==='End'?'scope':guideMode==='steps'?'scope':'steps';renderGuide();guide.querySelector('[data-guide-mode="'+guideMode+'"]').focus({preventScroll:true})});
 $('#overview-dashboard').addEventListener('click',()=>{if(!ready)return;speak('已回到看板顶部，可调整日期和岗位视图。');clearHighlights(frame.contentDocument);frame.contentWindow.scrollTo({top:0,behavior:reduce.matches?'instant':'smooth'})});
 $('#reset-dashboard').addEventListener('click',reloadFrame);$('#retry-dashboard').addEventListener('click',reloadFrame);$('#expand-dashboard').addEventListener('click',()=>setExpanded());
 document.addEventListener('keydown',event=>{if(!expanded)return;if(event.key==='Escape'){event.preventDefault();setExpanded(false);return}if(event.key==='Tab'){const controls=visibleControls(canvas),first=controls[0],last=controls[controls.length-1];if(event.shiftKey&&document.activeElement===first){event.preventDefault();last.focus({preventScroll:true})}else if(!event.shiftKey&&document.activeElement===last){event.preventDefault();first.focus({preventScroll:true})}}});
 frame.addEventListener('load',frameReady);show('funnel',{locateCanvas:false});
 try{if(frame.contentDocument?.readyState==='complete'&&frame.contentDocument.getElementById('fullstack-funnel'))frameReady();else loadTimer=setTimeout(()=>{if(!ready)setLoadState(true)},10000)}catch{setLoadState(true)}
})();
