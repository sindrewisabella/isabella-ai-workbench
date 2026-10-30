/* Bespoke record-based exhibit scenes. The art is illustrative; evidence labels stay explicit. */
(() => {
  'use strict';
  const registry = window.IsabellaExhibitScenes ||= {};
  const escape = value => String(value ?? '').replace(/[&<>"']/g,char=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
  registry.cli = ({work,exhibit,index,esc=escape}) => `<div class="exhibit-scene scene-cli">
    <div class="sr-scene-grain" aria-hidden="true"></div>
    <header class="sr-cli-heading"><span class="sr-scene-kicker">招聘操作 / BOSS 实录</span><h4>BOSS 招聘操作<br>招呼与简历回收</h4><p>打招呼、求简历、接收附件，<br>逐段查看操作与核验回执。</p></header>
    <div class="sr-cli-terminal"><div class="sr-terminal-top"><span><i></i> AI / 操作步骤示意</span><em>2026.10.21</em></div><div class="sr-terminal-body"><div class="sr-log-line"><span>01</span><div><small>SCOPE</small><strong>确认岗位与处理范围</strong><p>留下条件、话术与历史联系记录</p></div><i aria-hidden="true">✓</i></div><div class="sr-log-line"><span>02</span><div><small>ACTION</small><strong>执行已经确认的操作</strong><p>检查重复，再进行下一步</p></div><i aria-hidden="true">✓</i></div><div class="sr-log-line"><span>03</span><div><small>READ BACK</small><strong>回到同一会话核对结果</strong><p>请求、到达、接收分别留证据</p></div><i aria-hidden="true">↳</i></div></div><div class="sr-terminal-bottom"><span class="sr-terminal-cursor" aria-hidden="true"></span>把重复工作，变成可回查的过程。</div></div>
    <div class="sr-receipt sr-receipt-one"><span>01 / 打招呼实录</span><strong>操作后，核对界面</strong><small>累计核验数 ≠ 新增招呼数</small><b aria-hidden="true">↗</b></div>
    <div class="sr-receipt sr-receipt-two"><span>02 / 求简历实录</span><strong>查看平台请求回执</strong><small>请求发出 ≠ 附件已到</small><b aria-hidden="true">✓</b></div>
    <div class="sr-cli-film"><img src="assets/boss-accept-explained-poster.png" alt="BOSS 接收附件脱敏实录的小幅预览" width="280" height="170"><span aria-hidden="true">▶</span><small>03 / 接收附件另段呈现</small></div>
    <footer class="sr-cli-footer"><span><i></i>${esc(exhibit?.scope || '历史实录 · 人选信息已模糊')}</span><small>不同会话片段，不作为同批转化漏斗。</small></footer>
  </div>`;
  registry.evaluation = ({work,exhibit,index,esc=escape}) => `<div class="exhibit-scene scene-evaluation">
    <div class="sr-scene-grain" aria-hidden="true"></div>
    <header class="sr-eval-heading"><span class="sr-scene-kicker">简历初筛 / 历史批次</span><h4>批量简历初筛<br>结果回写与核验</h4><p>查看历史批次的初筛结果，<br>核对写回记录与判断分歧。</p></header>
    <div class="sr-eval-back-sheet" aria-hidden="true"><span>REVIEW NOTES / 依据与分歧</span></div>
    <div class="sr-eval-sheet"><div class="sr-sheet-heading"><span>历史批次 / 运维外包</span><i>2026.09.14</i></div><div class="sr-batch-equation"><div><strong>9</strong><span>扫描</span></div><b>=</b><div><strong>4</strong><span>已有记录</span></div><b>+</b><div><strong>5</strong><span>新增评估</span></div></div><div class="sr-batch-cells" aria-label="9 位扫描人选中，4 位已有记录、5 位新增评估">${Array.from({length:9},(_,i)=>`<i class="${i<4?'sr-batch-existing':'sr-batch-new'}" style="--sr-step:${i}"><span aria-hidden="true">${i<4?'—':'✓'}</span></i>`).join('')}</div><div class="sr-batch-legend"><span><i></i>已有记录，分开处理</span><span><i></i>新增评估，留下结果</span></div><div class="sr-eval-rule"><span>岗位规则</span><i></i><span>初筛结果</span><i></i><span>目标台账</span></div></div>
    <div class="sr-readback-stamp"><div class="sr-stamp-circle"><strong>5<span>/ 5</span></strong><span>回读核验</span></div><small>写回之后，再看一遍</small><i aria-hidden="true">↶</i></div>
    <div class="sr-eval-side-note"><span aria-hidden="true">✳</span><p>AI 先整理，<br>判断分歧继续校准。</p></div>
    <footer class="sr-eval-footer"><span>真实匿名汇总 · 历史作业展示</span><small>批次人数不代表并发数；系统任务另批核对。</small></footer>
  </div>`;
  registry.dashboard = ({work,exhibit,index,esc=escape}) => `<div class="exhibit-scene scene-dashboard">
    <div class="sr-scene-grain" aria-hidden="true"></div>
    <header class="sr-dash-heading"><span class="sr-scene-kicker">招聘数据 / 全栈岗位</span><h4>全栈招聘看板<br>漏斗、渠道与面试</h4></header>
    <svg class="sr-dash-links" viewBox="0 0 974 520" aria-hidden="true"><path d="M291 292C415 292 361 145 535 145S755 193 755 287M423 320C568 320 578 382 690 382"/><circle class="sr-dash-link-dot" cx="535" cy="145" r="4"/></svg>
    <div class="sr-dash-funnel"><span class="sr-dash-window-label">01 / 阶段导航</span><h5>招聘阶段漏斗</h5><div class="sr-funnel-shape"><div>简历记录</div><div>评估阶段</div><div>面试进展</div><div>后续跟进</div></div><span class="sr-funnel-caption">按阶段展开明细 ↗</span></div>
    <div class="sr-dash-trend"><div><span class="sr-dash-window-label">02 / 渠道趋势</span><i>选择日期范围</i></div><svg viewBox="0 0 310 114" aria-hidden="true"><path class="sr-chart-grid" d="M10 25H300M10 57H300M10 89H300M55 10V102M115 10V102M175 10V102M235 10V102"/><path class="sr-chart-area" d="M10 84C39 84 42 62 70 65S109 85 139 54S178 69 207 43S253 61 300 24V104H10Z"/><path class="sr-chart-line" d="M10 84C39 84 42 62 70 65S109 85 139 54S178 69 207 43S253 61 300 24"/><circle cx="207" cy="43" r="4"/></svg><small>趋势图结构示意 · 非业务统计值</small></div>
    <div class="sr-dash-interviews"><span class="sr-dash-window-label">03 / 面试进展</span><div class="sr-interview-avatars" aria-hidden="true"><i></i><i></i><i></i></div><strong>回到具体记录</strong><span class="sr-interview-row"><i></i>看面试官</span><span class="sr-interview-row"><i></i>查待跟进</span><span class="sr-interview-row"><i></i>展开明细</span></div>
    <div class="sr-dash-original"><img src="${esc(work?.image || 'assets/portfolio-fullstack.png')}" alt="全栈招聘数据看板原版历史界面的小幅预览" width="320" height="180"><span>原版界面局部 ↗</span></div>
    <footer class="sr-dash-footer"><span><i></i>2026.09.21 历史脱敏快照</span><small>非实时数据 · 图形用于说明板块与浏览路径</small></footer>
  </div>`;
})();
