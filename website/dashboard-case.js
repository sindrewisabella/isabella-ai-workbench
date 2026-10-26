(()=>{'use strict';
const $=s=>document.querySelector(s),frame=$('#exhibit iframe');
const zones={
 funnel:{anchor:'fullstack-funnel',title:'从总体到个人，看清每一轮的推进。',problem:'飞书记录分散，笔试又占用了面试轮次，直接照搬系统阶段不容易看懂真实招聘流程。',feature:'把简历入库、评估、各轮技术面、HR 面和入职放进一个视图；点击阶段，展开进入时间、来源与当前状态。Offer 沟通和待入职在 HR 明细中查看。',value:'定位需要复核的流失或积压，再回到具体记录，而不是只看一个总人数。',note:'相邻阶段数字可用于观察转化，但不同阶段按各自时间窗口统计，不必然属于同一批人，不能直接当作严格同批转化率。'},
 trend:{anchor:'fullstack-trend',title:'推荐得多，还要看能否进入下一步。',problem:'只有总推荐量，分不清是寻访量不够，还是推荐材料与岗位要求不匹配。',feature:'在同一周期里对照 HR 寻访、猎头等渠道进入评估与评估通过的数量，并可切换周、双周、月和自定义日期。',value:'让渠道投入和后续推进放在一起看，为调整寻访方式提供线索。',note:'数量差异只是分析起点，仍需结合岗位难度、材料质量与时间范围复核。'},
 goals:{anchor:'fullstack-goals-section',title:'把“最近很忙”，变成目标与实际的对照。',problem:'只说每天处理了很多简历，不能回答推荐量是否足够、质量是否达标、距离目标还差多少。',feature:'左边放既定推荐量与通过率目标，右边放所选周期的实际完成、完成率和差距。',value:'区分需要补的是数量还是匹配度，帮助安排下一周期的招聘动作。',note:'目标来自这个看板的业务配置，不是通用招聘标准，也不是 AI 自动做出的经营判断。'},
 interview:{anchor:'fullstack-interview-section',title:'把面试轮次、面评结果和反馈缺口连起来。',problem:'当时的系统页面难以直接按面试官汇总多轮进展，笔试占用轮次后，仅看轮次名更容易误判。',feature:'按约定的面试官与轮次规则整理记录，筛选面试官和结果，对照各轮评分、通过／不通过／待定及当前阶段，并展开完整明细。',value:'看到哪些记录尚未提交结论、哪些环节值得复核，再推动具体反馈。',note:'通过率差异可以提示问题，不足以单独判定面试官质量；待面试或未提交结论也不等于“不通过”。'}
};
function show(key){const z=zones[key];document.querySelectorAll('[data-zone]').forEach(b=>{b.setAttribute('aria-selected',b.dataset.zone===key);b.tabIndex=b.dataset.zone===key?0:-1});$('#dashboard-zone').setAttribute('aria-labelledby','tab-'+key);$('#dashboard-zone').innerHTML=`<h3>${z.title}</h3><dl><dt>原来卡在哪</dt><dd>${z.problem}</dd><dt>因此这样设计</dt><dd>${z.feature}</dd><dt>帮助做什么判断</dt><dd>${z.value}</dd></dl><p>${z.note}</p><button id="locate-zone">在原版看板中查看 ↑</button>`;$('#locate-zone').onclick=()=>{frame.contentDocument?.getElementById(z.anchor)?.scrollIntoView({behavior:'instant',block:'start'});$('#exhibit').scrollIntoView({behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'instant':'smooth'})}}
document.querySelector('.dashboard-tabs').addEventListener('click',e=>{const b=e.target.closest('[data-zone]');if(b)show(b.dataset.zone)});
$('#expand-dashboard').onclick=()=>{const expanded=$('#exhibit').classList.toggle('expanded');document.body.classList.toggle('demo-expanded',expanded);$('#expand-dashboard').textContent=expanded?'收起展示 ↙':'放大查看 ↗';$('#expand-dashboard').setAttribute('aria-expanded',expanded)};
document.addEventListener('keydown',e=>{if(e.key==='Escape'&&$('#exhibit').classList.contains('expanded'))$('#expand-dashboard').click()});
show('funnel');})();
