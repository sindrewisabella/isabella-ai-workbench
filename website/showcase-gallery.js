/* Introduction and a readable interface detail on each rotating exhibit. */
(()=>{'use strict';
 const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const version='20261030-wine2';
 const routes={workbench:'workbench-interactive.html',cli:'cli-case.html',salary:'salary-case.html',evaluation:'evaluation-case.html',dashboard:'dashboard-case.html'};
 const exhibits={
  workbench:{name:'笔试工作台',nav:'笔试管理',purpose:'登记发放与回收，跟进延期、验收和返修。',heading:'一份笔试，\n从发出到验收。',description:'谁交了、谁延期、谁需要返修，放在同一条人选记录里跟进。',features:[['发放登记','记录发放时间与回收期限'],['材料回收','登记提交、延期与补交'],['验收返修','保留材料、意见和下一步']],scope:'虚构人选 · 可操作演示',scene:'材料回收与下一步'},
  cli:{name:'BOSS 招聘操作实录',nav:'BOSS 招聘',purpose:'查看打招呼、请求简历与接收附件的分段录像。',heading:'重复的点击，\n留下可核对的过程。',description:'人确定岗位、条件和范围，AI 执行重复操作，再逐段核对回执。',features:[['打招呼','按已确认岗位与范围执行'],['求简历','查看请求过程与平台回执'],['接收附件','区分请求与同意接收']],scope:'历史实录 · 人选信息已模糊',scene:'BOSS 操作实录局部'},
  salary:{name:'薪酬方案计算器',nav:'薪酬比较',purpose:'复核示例工资流水，比较两版方案的税前年现金。',heading:'每一笔收入，\n先核对，再比较。',description:'从预置工资材料到流水，再把两版方案放到同一年度口径下看。',features:[['月份核对','核对工资月、到账日和金额'],['流水写入','修改后重新核对才能写入'],['方案比较','对照两版税前年现金']],scope:'虚构材料 · 预置提取结果',scene:'材料整理与人工核对'},
  evaluation:{name:'批量简历评估记录',nav:'简历初筛',purpose:'回看历史初筛批次、经理判断对照与评估任务核验。',heading:'看批次结果，\n也看判断分歧。',description:'把处理量、初筛结果与后续评估分开记录，让每一步都能回查。',features:[['批次回放','查看初筛分布与回读结果'],['判断对照','按同一投递与阶段对照'],['任务回执','核对评估任务是否已建立']],scope:'历史运行记录 · 匿名汇总',scene:'历史批次与处理记录'},
  dashboard:{name:'全栈招聘数据看板',nav:'招聘看板',purpose:'按日期浏览历史招聘漏斗、渠道与面试官进展。',heading:'从招聘全局，\n找到要跟进的事。',description:'把分散的招聘记录放在同一个视图，再回到具体阶段和明细。',features:[['漏斗明细','展开各阶段的历史记录'],['渠道趋势','按日期观察来源与推进'],['面试进展','查看面试官与待跟进明细']],scope:'历史脱敏快照 · 非实时数据',scene:'招聘漏斗局部'}
 };
 function mount({root,works=[],initial}){
  if(!root||!works.length)return;
  root._destroyShowcase?.();
  const controller=new AbortController(),signal=controller.signal;
  const reduce=matchMedia('(prefers-reduced-motion:reduce)'),DELAY=7000;
  let saved,userPaused=false;
  try{saved=sessionStorage.getItem('isabella-showcase-work');userPaused=sessionStorage.getItem('isabella-showcase-autoplay')==='paused'}catch{}
  let selected=Math.max(0,works.findIndex(w=>w.id===(initial||saved))),start,suppress=false;
  let timer=0,startedAt=0,remaining=DELAY,visible=false,hovered=false,dragging=false,motionOverride=false,observer,destroyed=false;
  const wrap=i=>(i+works.length)%works.length,href=id=>routes[id]+'?v='+version;
  root.className='showcase-gallery';root.setAttribute('aria-label','旋转作品展台');root.tabIndex=0;
  root.innerHTML=`<header class="showcase-detail" aria-live="off"></header><div class="showcase-stage"><div class="showcase-orbit" aria-hidden="true"><span>FROM EVERYDAY WORK TO SOMETHING USEFUL</span></div><div class="showcase-floor" aria-hidden="true"></div><div class="showcase-cards">${works.map((work,index)=>{
   const exhibit=exhibits[work.id],render=window.IsabellaExhibitScenes?.[work.id];
   const scene=render?render({work,exhibit,index,esc}):`<div class="exhibit-scene scene-fallback"><h4>${esc(work.name)}</h4><p>${esc(exhibit.purpose)}</p><span>进入完整作品展示 ↗</span></div>`;
   return `<a class="showcase-card showcase-card--${work.id}" data-showcase-card="${index}" href="${href(work.id)}" aria-label="进入${esc(work.name)}作品展示">${scene}</a>`;
  }).join('')}</div><button class="showcase-arrow showcase-prev" aria-label="上一件作品" type="button">←</button><button class="showcase-arrow showcase-next" aria-label="下一件作品" type="button">→</button></div><nav class="showcase-index" aria-label="选择一件作品">${works.map((w,i)=>`<button type="button" data-showcase-index="${i}"><i>${String(i+1).padStart(2,'0')}</i><span>${esc(exhibits[w.id].nav)}</span></button>`).join('')}</nav><div class="showcase-bottom"><p class="showcase-help">点击两侧切换，点击中央作品进入完整展示。<span>也可以用键盘 ← → 浏览</span></p><div class="showcase-playback"><button type="button" data-showcase-autoplay aria-pressed="true"><i aria-hidden="true">Ⅱ</i><span>暂停轮播</span></button><span class="showcase-auto-state" aria-live="off">自动浏览</span><span class="showcase-auto-meter" aria-hidden="true"><i></i></span><small>7 秒 / 件</small></div></div>`;
  const cards=[...root.querySelectorAll('[data-showcase-card]')],indices=[...root.querySelectorAll('[data-showcase-index]')];
  const toggle=root.querySelector('[data-showcase-autoplay]'),meter=root.querySelector('.showcase-auto-meter i'),state=root.querySelector('.showcase-auto-state');
  function position(){const mobile=innerWidth<=650;root.querySelector('.showcase-stage').style.height=(Math.max(...cards.map(c=>c.offsetHeight))+(mobile?32:48))+'px';cards.forEach((card,i)=>{let delta=i-selected;if(delta>works.length/2)delta-=works.length;if(delta< -works.length/2)delta+=works.length;const distance=Math.abs(delta);card.style.transform=distance===0?'none':`translateX(${delta*(mobile?73:64)}%) translateZ(${-distance*(mobile?95:145)}px) rotateY(${delta*(mobile?-15:-21)}deg) scale(${distance===1?.9:.78})`;card.style.opacity=distance===0?'1':distance===1?'.57':'.12';card.style.zIndex=String(10-distance);card.dataset.position=delta;card.tabIndex=distance===0?0:-1;card.setAttribute('aria-label',distance===0?'进入'+works[i].name+'的具体作品展示':'切换到'+works[i].name)})}
  function stopClock(){if(timer){remaining=Math.max(0,remaining-(performance.now()-startedAt));clearTimeout(timer);timer=0;startedAt=0}meter.style.transition='none';meter.style.transform=`scaleX(${1-remaining/DELAY})`}
  function pauseReason(){if(userPaused)return '已暂停';if(reduce.matches&&!motionOverride)return '减少动效 · 手动浏览';if(document.hidden)return '后台暂停';if(!visible)return '离开展台暂停';if(dragging)return '操作时暂停';if(hovered)return '悬停暂停';if(root.contains(document.activeElement)&&document.activeElement!==toggle)return '阅读时暂停';return ''}
  function syncClock(){
   if(destroyed)return;
   const reason=pauseReason(),motionStopped=reduce.matches&&!motionOverride;
   toggle.setAttribute('aria-pressed',String(!userPaused&&!motionStopped));toggle.setAttribute('aria-label',userPaused||motionStopped?'开始自动轮播':'暂停自动轮播');toggle.querySelector('span').textContent=userPaused||motionStopped?'继续轮播':'暂停轮播';toggle.querySelector('i').textContent=userPaused||motionStopped?'▶':'Ⅱ';
   root.dataset.rotation=reason?'paused':'playing';root.dataset.inView=String(visible);state.textContent=reason||'自动浏览';
   if(reason){stopClock();return}if(timer)return;
   startedAt=performance.now();timer=setTimeout(()=>{timer=0;startedAt=0;remaining=DELAY;select(selected+1,false,'auto')},Math.max(20,remaining));
   meter.style.transition='none';meter.style.transform=`scaleX(${1-remaining/DELAY})`;
   requestAnimationFrame(()=>{if(timer){meter.style.transition=`transform ${remaining}ms linear`;meter.style.transform='scaleX(1)'}});
  }
  function select(index,focus=false,source='manual'){
   stopClock();remaining=DELAY;meter.style.transform='scaleX(0)';selected=wrap(index);
   const w=works[selected],d=exhibits[w.id],summary=root.querySelector('.showcase-detail');root.dataset.selected=w.id;position();indices.forEach((b,i)=>b.setAttribute('aria-current',String(i===selected)));
   summary.setAttribute('aria-live',source==='auto'?'off':'polite');summary.innerHTML=`<div class="showcase-work-summary"><span class="showcase-evidence">${String(selected+1).padStart(2,'0')} / 05 <i></i> ${esc(d.scope)}</span><h3>${esc(d.name)}</h3><p>${esc(d.purpose)}</p></div><a href="${href(w.id)}" class="showcase-open">查看完整展示 <span aria-hidden="true">↗</span></a>`;
   try{sessionStorage.setItem('isabella-showcase-work',w.id)}catch{}
   if(focus)cards[selected].focus({preventScroll:true});
   if(innerWidth<=800){const nav=root.querySelector('.showcase-index'),button=indices[selected],left=button.getBoundingClientRect().left-nav.getBoundingClientRect().left+nav.scrollLeft-(nav.clientWidth-button.offsetWidth)/2;nav.scrollTo({left,behavior:reduce.matches||source==='auto'?'instant':'smooth'})}
   syncClock();
  }
  root.addEventListener('click',event=>{
   if(event.target.closest('[data-showcase-autoplay]')){if(reduce.matches&&!motionOverride){motionOverride=true;userPaused=false}else userPaused=!userPaused;try{sessionStorage.setItem('isabella-showcase-autoplay',userPaused?'paused':'playing')}catch{}syncClock();return}
   const card=event.target.closest('[data-showcase-card]'),index=event.target.closest('[data-showcase-index]'),arrow=event.target.closest('.showcase-arrow');
   if(card){if(suppress){event.preventDefault();return}const i=Number(card.dataset.showcaseCard);if(i!==selected){event.preventDefault();if(event.detail>0)card.blur();select(i)}}else if(index){if(event.detail>0)index.blur();select(Number(index.dataset.showcaseIndex))}else if(arrow){if(event.detail>0)arrow.blur();select(selected+(arrow.classList.contains('showcase-prev')?-1:1))}
  },{signal});
  root.addEventListener('keydown',event=>{if(!['ArrowLeft','ArrowRight','Home','End'].includes(event.key))return;event.preventDefault();select(event.key==='Home'?0:event.key==='End'?works.length-1:selected+(event.key==='ArrowLeft'?-1:1),true)},{signal});
  root.addEventListener('pointerenter',e=>{if(e.pointerType==='mouse'||e.pointerType==='pen'){hovered=true;syncClock()}},{signal});root.addEventListener('pointerleave',()=>{hovered=false;syncClock()},{signal});
  root.addEventListener('focusin',syncClock,{signal});root.addEventListener('focusout',()=>requestAnimationFrame(syncClock),{signal});
  const stage=root.querySelector('.showcase-stage');stage.addEventListener('pointerdown',e=>{if(e.button===0){start={x:e.clientX,y:e.clientY};dragging=true;syncClock()}},{signal});
  stage.addEventListener('pointerup',e=>{if(!start)return;const dx=e.clientX-start.x,dy=e.clientY-start.y;start=null;dragging=false;if(Math.abs(dx)>55&&Math.abs(dx)>Math.abs(dy)*1.3){suppress=true;select(selected+(dx>0?-1:1));setTimeout(()=>suppress=false,180)}else syncClock()},{signal});
  stage.addEventListener('pointercancel',()=>{start=null;dragging=false;syncClock()},{signal});
  const releasePointer=()=>{if(dragging){dragging=false;start=null;syncClock()}};addEventListener('pointerup',releasePointer,{signal});
  addEventListener('resize',position,{signal});document.addEventListener('visibilitychange',syncClock,{signal});reduce.addEventListener('change',syncClock,{signal});
  if('IntersectionObserver'in window){observer=new IntersectionObserver(entries=>{visible=entries[0].isIntersecting&&entries[0].intersectionRatio>=.15;syncClock()},{threshold:[0,.15]});observer.observe(root)}else{const r=root.getBoundingClientRect();visible=r.top<innerHeight&&r.bottom>0}
  root._destroyShowcase=()=>{destroyed=true;stopClock();observer?.disconnect();controller.abort()};
  select(selected,false,'initial');root.offsetWidth;root.classList.add('showcase-ready');
 }
 window.IsabellaShowcase={mount};
})();
