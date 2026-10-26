(()=>{'use strict';
const stages=['简历初筛','简历评估','笔试','面试'],names={all:'全部岗位',growth:'增长岗位',ops:'运维岗位'};
// Authored public examples only. Each application occurs in exactly one current stage.
const rows=[
['G01','growth',0,1],['G02','growth',0,2],['G03','growth',1,4],['G04','growth',1,2],['G05','growth',2,5],['G06','growth',2,1],['G07','growth',3,3],['G08','growth',3,1],
['O01','ops',0,3],['O02','ops',0,1],['O03','ops',0,2],['O04','ops',1,6],['O05','ops',2,4],['O06','ops',2,2],['O07','ops',3,1],['O08','ops',3,3]
].map(([id,job,stage,days])=>({id,job,stage,days}));
const next=['核对岗位条件，完成初筛','请评估人提交结论','确认笔试提交／验收进度','确认面试安排／反馈'];
let job='all',view='stages',stage=null;
const $=s=>document.querySelector(s);
function render(){
 const list=rows.filter(r=>job==='all'||r.job===job),waiting=list.filter(r=>r.days>=3),counts=stages.map((_,i)=>list.filter(r=>r.stage===i).length);
 $('#dash-title').textContent=names[job];$('#dash-view').value=view;
 document.querySelectorAll('[data-job]').forEach(b=>b.setAttribute('aria-pressed',b.dataset.job===job));
 const kpis=`<div class="dash-kpis"><div><small>当前投递</small><strong>${list.length}<span>条</span></strong></div><div><small>等待 ≥ 3 天</small><strong>${waiting.length}<span>条</span></strong></div><div><small>当前查看岗位</small><strong>${job==='all'?2:1}<span>个</span></strong></div></div>`;
 let content='';
 if(view==='rules')content=`<section class="dash-rules"><h3>先把口径放在数字旁边。</h3><dl><dt>来源与时间</dt><dd>本页自带的 16 条虚构投递，固定快照 2026 年 10 月 26 日；不是公司实际业绩。</dd><dt>当前投递</dt><dd>每个示例投递编号只计一次；按投递统计，不跨岗位按人去重。</dd><dt>阶段人数</dt><dd>一条投递只属于一个当前阶段。各阶段相加等于当前投递数，不表示历史漏斗或转化率。</dd><dt>等待 ≥ 3 天</dt><dd>进入当前阶段满 3 天的投递；是提醒阈值，不直接代表流程超时。</dd><dt>换成真实岗位</dt><dd>从飞书招聘读取记录，由人确认阶段映射、去重方式和时间范围。公开页不连接业务系统。</dd></dl></section>`;
 else {
  const shown=(view==='queue'?waiting:list.filter(r=>stage!==null&&r.stage===stage)).slice().sort((a,b)=>b.days-a.days||a.id.localeCompare(b.id));
  const bars=view==='stages'?`<section aria-labelledby="stage-title"><div class="dash-section-title"><h3 id="stage-title">人选在走哪一步？</h3><small>点击数字，看对应记录</small></div><div class="dash-stages">${stages.map((n,i)=>`<button data-stage="${i}" aria-pressed="${stage===i}"><span>${n}</span><strong>${counts[i]}</strong><div class="dash-track"><i style="width:${counts[i]/list.length*100}%"></i></div></button>`).join('')}</div><p class="dash-footnote">当前阶段分布 · 各阶段合计 ${list.length} 条，不是历史转化率。</p></section>`:'';
  content=bars+`<section class="dash-queue"><div class="dash-section-title"><h3>${view==='queue'?'等待 ≥ 3 天的记录':stage===null?'从上面的阶段开始':'当前筛选：'+stages[stage]}</h3><small>${view==='queue'?shown.length+' 条需关注':stage!==null?shown.length+' 条投递':'按岗位、阶段逐层查看'}</small></div>${shown.length?`<div class="dash-table-wrap"><table><thead><tr><th>示例投递</th><th>岗位</th><th>阶段 / 等待</th><th>下一步</th></tr></thead><tbody>${shown.map(r=>`<tr><td>${r.id}</td><td>${names[r.job]}</td><td>${stages[r.stage]} · ${r.days} 天</td><td>${next[r.stage]}</td></tr>`).join('')}</tbody></table></div>`:'<p class="dash-empty">点击一个阶段，就能看到对应的投递、等待天数和下一步。也可以切到“待跟进清单”。</p>'}</section>`;
 }
 $('#dashboard-result').innerHTML=kpis+content;
}
document.querySelector('.dash-app').addEventListener('click',e=>{const b=e.target.closest('[data-job],[data-stage]');if(!b)return;if(b.hasAttribute('data-job')){job=b.dataset.job;stage=null}else stage=Number(b.dataset.stage);render()});
$('#dash-view').addEventListener('change',e=>{view=e.target.value;stage=null;render()});
document.querySelectorAll('[data-tour]').forEach(b=>b.addEventListener('click',()=>{view=b.dataset.tour;stage=null;render();$('#exhibit').scrollIntoView({behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'instant':'smooth'});$('#dash-view').focus({preventScroll:true})}));
render();})();
