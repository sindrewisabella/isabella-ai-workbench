// Browser adapter for the currently inspected Maimai v41 page.
// Called by maimai_hr.py through ego-browser nodejs; REQUEST is injected as JSON.
const task = await taskSpace(REQUEST.space);
const page = task.page(REQUEST.page || 'p1');
const fs = await import('node:fs/promises');
const cardComparison = {compareCards};
function compareListCard(item,actual) {
  if(!actual) return {equivalent:false,reason:'missing_actual'};
  return cardComparison.compareCards(
    {uid:item.uid,name:item.name,contact_button:item.contact_button,text:item.list_text || item.text},
    {uid:actual.uid,name:actual.name,contact_button:actual.contact_button,text:actual.text});
}
function assertMaimai(url) {
  if (new URL(url).hostname !== 'maimai.cn') throw new Error('当前页面不是 maimai.cn，已停止');
}
assertMaimai(await page.url());
function readCards({limit = 20} = {}) {
  const seen = new Set();
  const cards = [];
  for (const el of document.querySelectorAll('[class*="card___"]')) {
    if (!el.getClientRects().length) continue;
    // Normal search results use talentDiscover_discover_list_pc_*; when a
    // keyword has no exact hit v41 renders a recommendation fallback whose
    // cards use talent_search_empty_rec_*.  Both carry the authoritative uid.
    const marker = el.querySelector('[id^="talentDiscover_discover_list_pc_"], [id^="talent_search_empty_rec_"]');
    const nameEl = el.querySelector('[class*="name___"]');
    const uid = marker?.id.match(/^(?:talentDiscover_discover_list_pc_|talent_search_empty_rec_)(\d+)_/m)?.[1];
    if (!uid || !nameEl || seen.has(uid)) continue;
    seen.add(uid);
    const body = el.innerText;
    const links = [...el.querySelectorAll('a[href]')].map(a => a.href).filter(u => u.includes('maimai.cn/profile/'));
    cards.push({uid, marker_id: marker.id, name: nameEl.innerText.trim(), text: body,
      contact_button: el.querySelector('.directChatButtonPanel')?.innerText.trim() || '',
      profile_url: links[0] || null,
      // Keep the actual page URL; never invent a working personal profile URL.
      source_url: location.href,
      skills: [...el.querySelectorAll('[class*="occTag___"]')].map(x=>x.innerText),
      basic: el.querySelector('[class*="uinfoLeft"] p')?.innerText || '',
      expectation: [...el.querySelectorAll('p')].find(x=>x.innerText.startsWith('期望：'))?.innerText || '',
      collected_at: new Date().toISOString()});
    if (cards.length >= limit) break;
  }
  return {url:location.href,query:document.querySelector('input[placeholder^="搜索提示"]')?.value || '',
    job:document.querySelector('[class*="positionNameText"]')?.innerText.trim() || '',
    filters:[...document.querySelectorAll('[class*="header___"]')].map(e=>e.innerText.trim()).filter(Boolean),
    total_display:document.body.innerText.match(/共找到\s*[^\n]*人才/)?.[0] || '',
    loading:document.body.innerText.includes('加载中...'),cards};
}
function dialogState() {
  const ds=[...document.querySelectorAll('[role="dialog"]')].filter(e=>e.getClientRects().length && e.innerText.includes('招聘立即沟通'));
  if(ds.length!==1) return null;
  const d=ds[0], sw=d.querySelector('[role="switch"]');
  const costs=[...document.querySelectorAll('[role="tooltip"],.ant-tooltip')].filter(e=>e.getClientRects().length).map(e=>e.innerText).filter(t=>t.includes('本次将消耗'));
  return {text:d.innerText, candidate_name:d.querySelector('[class*="intro-name"]')?.innerText.trim() || '',
    job_title:d.querySelector('[class*="project-name"]')?.innerText.trim() || '', message:d.querySelector('textarea')?.value || '',
    auto_resume:sw ? sw.getAttribute('aria-checked')==='true' : null,
    cost_text:[...new Set(costs)].join('\n')};
}
async function readyCards() {
  await page.waitForFunction(()=>!document.body.innerText.includes('加载中...') &&
    (document.querySelector('[id^="talentDiscover_discover_list_pc_"]') || document.body.innerText.includes('暂无匹配人才')),
    undefined,{timeout:25000});
}
async function openDialog(item) {
  if(!/^\d+$/.test(item.uid)) throw new Error('候选人编号无效');
  const before=await page.evaluate(readCards,{limit:100});
  const actual=before.cards.find(c=>c.uid===item.uid);
  const cardCheck=compareListCard(item,actual);
  if(!cardCheck.equivalent) throw new Error('候选人资料发生变化或不在当前页，请重新采集并审阅：'+cardCheck.reason);
  if(actual.contact_button!=='立即沟通') throw new Error('当前不是首次立即沟通状态，停止重复联系');
  const u=new URL(before.url);
  if(u.searchParams.get('pid')!==String(REQUEST.job_id)) throw new Error('当前岗位编号与批准岗位不一致');
  await page.snapshot();
  // Ego's long-distance wheel input repeatedly timed out before opening this
  // dialog. Use the observed card DOM for this entry only; the actual send
  // button, quota checks, recipient checks and receipts remain unchanged.
  await page.evaluate(({marker,name,job})=>{
    if(new URL(location.href).searchParams.get('pid')!==String(job))throw new Error('dialog entry job changed');
    if([...document.querySelectorAll('[role="dialog"]')].some(e=>e.getClientRects().length))throw new Error('dialog already open');
    const card=document.getElementById(marker)?.closest('[class*="card___"]');
    const panel=card?.querySelector('.directChatButtonPanel');
    if(card?.querySelector('[class*="name___"]')?.innerText.trim()!==name || panel?.innerText.trim()!=='立即沟通')throw new Error('dialog entry recipient or contact state changed');
    const matches=[...panel.children].filter(e=>e.innerText.trim()==='立即沟通');
    if(matches.length!==1)throw new Error('dialog entry button ambiguous');
    matches[0].click();
  },{marker:actual.marker_id,name:item.name,job:REQUEST.job_id});
  await page.waitForFunction(({name,job})=>[...document.querySelectorAll('[role="dialog"]')].some(e=>e.getClientRects().length &&
    e.querySelector('textarea') && e.querySelector('[class*="intro-name"]')?.innerText.trim()===name &&
    e.querySelector('[class*="project-name"]')?.innerText.trim()===job),{name:item.name,job:REQUEST.job_title},{timeout:20000});
  await page.snapshot();
  await page.hover('loc=role:button[name="发送后留在此页"]');
  const d=await page.evaluate(dialogState);
  if(!d || d.candidate_name!==item.name || d.job_title!==REQUEST.job_title) throw new Error('弹窗人选或关联岗位核验失败');
  d.card_comparison={...cardCheck,observed_text:actual.text};
  return d;
}
if(REQUEST.action==='page') {
  if(!Number.isInteger(REQUEST.number) || REQUEST.number<1) throw new Error('无效页码');
  const before=await page.evaluate(()=>({number:document.querySelector('[class*="pagesItem___"][class*="current___"]')?.innerText,ids:[...document.querySelectorAll('[id^="talentDiscover_discover_list_pc_"]')].map(e=>e.id).join('|')}));
  if(before.number!==String(REQUEST.number)) {
    await page.snapshot({scope:'full_page'});
    await page.click(`css=[class*="paginationCon___"] [class*="pagesItem___"]:text-is("${REQUEST.number}")`);
    await page.waitForFunction(({number,ids})=>document.querySelector('[class*="pagesItem___"][class*="current___"]')?.innerText===String(number) && [...document.querySelectorAll('[id^="talentDiscover_discover_list_pc_"]')].map(e=>e.id).join('|')!==ids && !document.body.innerText.includes('加载中...'),{number:REQUEST.number,ids:before.ids},{timeout:25000});
  }
  REQUEST.action='collect';
}
let result;
if(REQUEST.action==='collect') {
  await readyCards(); result=await page.evaluate(readCards,{limit:REQUEST.limit});
} else if(REQUEST.action==='search') {
  await page.snapshot();
  // Select current site's search tab by semantic text, never a fixed tab index.
  const searchSel='input[placeholder^="搜索提示"]';
  const hasInput=await page.evaluate(()=>!!document.querySelector('input[placeholder^="搜索提示"]'));
  if(!hasInput) {
    await page.click('text="搜索"');
    await page.waitForSelector(searchSel,{state:'visible',timeout:20000});
  }
  const prior=await page.evaluate(()=>[...document.querySelectorAll('[id^="talentDiscover_discover_list_pc_"]')].map(e=>e.id).join('|'));
  await page.fill(searchSel,REQUEST.query);
  // 脉脉 v41 在恢复后的搜索条件页可能忽略 Enter，点击同一条件栏的
  // “搜索”按钮才会真正刷新结果。
  const clicked=await page.evaluate(()=>{
    const input=document.querySelector('input[placeholder^="搜索提示"]');
    // The criteria bar is a stable local container; selecting a global
    // "搜索" label can hit the navigation tab and leave the old results.
    const box=input?.closest('.input-container___TCetX') || input?.parentElement?.parentElement?.parentElement;
    const btn=box?.querySelector('.mui-btn-primary') || [...(box?.querySelectorAll('*')||[])].find(e=>e.innerText?.trim()==='搜索' && e.getClientRects().length);
    if(!btn) return false; btn.click(); return true;
  });
  if(!clicked) throw new Error('未找到搜索条件栏的搜索按钮');
  // Input text alone does not prove results refreshed. Fail closed if unchanged.
  await page.waitForFunction(({prior})=>{
    const ids=[...document.querySelectorAll('[id^="talentDiscover_discover_list_pc_"]')].map(e=>e.id).join('|');
    return ids!==prior && (ids.length>0 || document.body.innerText.includes('暂无匹配人才'));
  },{prior},{timeout:25000});
  await readyCards(); result=await page.evaluate(readCards,{limit:REQUEST.limit});
} else if(REQUEST.action==='detail') {
  const item=REQUEST.item;
  const current=(await page.evaluate(readCards,{limit:100})).cards.find(c=>c.uid===item.uid);
  if(!compareListCard(item,current).equivalent) throw new Error('详情人选与采集卡片不一致，请重新采集');
  await page.snapshot();
  // Use the observed card DOM directly.  On long talent lists Ego's pointer
  // dispatch can time out while scrolling to an offscreen name; the marker
  // and name were just validated above, so a local click is equivalent and
  // keeps this read-only detail action reliable.
  await page.evaluate(({marker,name})=>{
    const card=document.getElementById(marker)?.closest('[class*="card___"]');
    const node=card?.querySelector('[class*="name___"]');
    if(!node || node.innerText.trim()!==name) throw new Error('详情目标卡片发生变化');
    node.click();
  },{marker:current.marker_id,name:item.name});
  await page.waitForFunction(({name})=>[...document.querySelectorAll('.ant-drawer-content [class*="left___"]')].some(e=>e.innerText.trim().startsWith(name+'\n') && e.innerText.includes('人才档案')),{name:item.name},{timeout:20000});
  // The drawer header and its sub-sections hydrate separately. Wait for a stable
  // body, not merely the new name; retain both card/detail if site data conflicts.
  await page.evaluate(()=>{delete window.__maimaiHrDetailStability;});
  await page.waitForFunction(({name})=>{
    const value=[...document.querySelectorAll('.ant-drawer-content [class*="left___"]')].map(e=>e.innerText.trim()).find(t=>t.startsWith(name+'\n') && t.includes('人才档案') && t.includes('工作经历'));
    if(!value)return false;
    const prev=window.__maimaiHrDetailStability;
    if(!prev || prev.value!==value){window.__maimaiHrDetailStability={value,since:performance.now()};return false;}
    return performance.now()-prev.since>1500;
  },{name:item.name},{timeout:20000});
  const detail=await page.evaluate(({name})=>[...document.querySelectorAll('.ant-drawer-content [class*="left___"]')].map(e=>e.innerText.trim()).find(t=>t.startsWith(name+'\n') && t.includes('人才档案')),{name:item.name});
  result={uid:item.uid,name:item.name,text:detail,url:await page.url(),captured_at:new Date().toISOString(),note:'当前已加载的详情正文，可能含截断；不是完整附件简历'};
  if(REQUEST.include_history) {
    const label=await page.evaluate(()=>[...document.querySelectorAll('.ant-drawer-content *')].map(e=>e.innerText?.trim()).find(x=>/^招聘动态·\d+$/.test(x)));
    if(!label) throw new Error('未找到招聘动态');
    await page.click(`css=.ant-drawer-content *:text-is("${label}")`);
    await page.waitForFunction(({name})=>[...document.querySelectorAll('.ant-drawer-content [class*="left___"]')].some(e=>e.innerText.startsWith(name+'\n') && (e.innerText.includes('查看人才档案') || e.innerText.includes('暂无')) && !e.innerText.includes('加载中')),{name:item.name},{timeout:20000});
    result.history_text=await page.evaluate(({name})=>[...document.querySelectorAll('.ant-drawer-content [class*="left___"]')].map(e=>e.innerText).find(t=>t.startsWith(name+'\n')),{name:item.name});
    const positions=result.history_text.match(/职位记录·(\d+)/);
    if(positions && +positions[1]>0){
      await page.click(`css=.ant-drawer-content *:text-is("职位记录·${positions[1]}")`);
      await page.waitForFunction(()=>[...document.querySelectorAll('.ant-drawer-content')].some(e=>(e.innerText.includes('当前状态')||e.innerText.includes('申请状态'))&&!e.innerText.includes('加载中')),undefined,{timeout:15000});
      result.positions_text=await page.evaluate(({name})=>[...document.querySelectorAll('.ant-drawer-content [class*="left___"]')].map(e=>e.innerText).find(t=>t.startsWith(name+'\n')),{name:item.name});
    }

  }
  await page.evaluate(()=>{delete window.__maimaiHrDetailStability;});
  await page.snapshot();await page.click('.ant-drawer-header span[tabindex="-1"]');
  await page.waitForFunction(()=>![...document.querySelectorAll('.ant-drawer-content')].some(e=>e.getClientRects().length),undefined,{timeout:10000});
  result.card_after_view=(await page.evaluate(readCards,{limit:100})).cards.find(c=>c.uid===item.uid);
  if(!result.card_after_view || result.card_after_view.name!==item.name) throw new Error('详情返回后未找到同一人选，请重新采集');
} else if(REQUEST.action==='preflight' || REQUEST.action==='send') {
  const d=await openDialog(REQUEST.item);
  // Do not change account settings implicitly. User reviews the actual switch state.
  if(REQUEST.action==='preflight') {
    result={candidate_uid:REQUEST.item.uid,candidate_name:REQUEST.item.name,...d,checked_at:new Date().toISOString(),sent:false};
    await page.snapshot();await page.click('button[aria-label="Close"]');
    await page.waitForFunction(()=>![...document.querySelectorAll('[role="dialog"]')].some(e=>e.getClientRects().length && e.innerText.includes('招聘立即沟通')),undefined,{timeout:10000});
  } else {
    if(d.auto_resume!==REQUEST.auto_resume) throw new Error('自动索要简历开关与批准值不一致；请人工核对设置');
    const unit=d.cost_text.match(/本次将消耗额度\s*(\d+)\s*次/);
    if(!unit || +unit[1]!==1 || REQUEST.max_units<1) throw new Error('未确认每人消耗 1 次额度，停止发送');
    if(!REQUEST.message || REQUEST.message.length>300) throw new Error('消息必须为 1–300 字');
    await page.fill('textarea[placeholder^="请写一份属于ta"]',REQUEST.message);
    const check=await page.evaluate(dialogState);
    if(!check || check.message!==REQUEST.message || check.auto_resume!==REQUEST.auto_resume) throw new Error('最终消息或开关核对失败');
    await page.snapshot();
    // Durable record is written BEFORE dispatch. An uncertain result is never retried automatically.
    await fs.appendFile(REQUEST.attempt_log,JSON.stringify({uid:REQUEST.item.uid,state:'dispatching',at:new Date().toISOString()})+'\n',{mode:0o600});
    await page.click('loc=role:button[name="发送后留在此页"]');
    let verified=false;
    try {
      await page.waitForFunction(({uid})=>{
        const m=document.querySelector(`[id^="talentDiscover_discover_list_pc_${uid}_"]`);
        const b=m?.closest('[class*="card___"]')?.querySelector('.directChatButtonPanel')?.innerText.trim();
        return b==='沟通' || b==='发消息';
      },{uid:REQUEST.item.uid},{timeout:15000});verified=true;
    } catch {}
    result={uid:REQUEST.item.uid,name:REQUEST.item.name,state:verified?'sent_button_verified':'uncertain',
      message:REQUEST.message,cost_text:d.cost_text,auto_resume:d.auto_resume,card_comparison:d.card_comparison,at:new Date().toISOString(),
      note:verified?'当前候选人按钮已变为沟通/发消息；尚需回收页核对':'不能以弹窗消失或候选人消失证明发送成功，需回收页核对'};
  }
} else if(REQUEST.action==='recover') {
  const target=new URL(REQUEST.url);assertMaimai(target.href);
  if(target.pathname!=='/ent/v41/recruit/talents' || target.searchParams.get('pid')!==String(REQUEST.job_id) || target.searchParams.get('tab')!=='7' || [...target.searchParams.keys()].some(k=>!['pid','tab'].includes(k))) throw new Error('目前只支持已核验岗位的我发起页（tab=7），不能将其他页面当成已回收');
  // Navigate only through the inspected semantic menu in the existing job page.
  if(new URL(await page.url()).searchParams.get('pid')!==String(REQUEST.job_id)) throw new Error('当前岗位不一致');
  await page.snapshot();await page.click('text=我发起');
  await page.waitForFunction(()=>new URL(location.href).searchParams.get('tab')==='7' && !document.body.innerText.includes('加载中...') && document.body.innerText.includes('对方已回复'),undefined,{timeout:25000});
  const actualURL=new URL(await page.url());
  if(actualURL.pathname!==target.pathname || actualURL.searchParams.get('pid')!==target.searchParams.get('pid') || actualURL.searchParams.get('tab')!==target.searchParams.get('tab')) throw new Error('实际回收页面与指定目标不一致');
  const snap=await page.snapshot({scope:'full_page'});
  const rows=await page.evaluate(()=>[...document.querySelectorAll('[class*="card___"]')].filter(e=>e.getClientRects().length).map(e=>({
    uid:e.querySelector('[id^="candidate_initiate_direct_list_pc_"]')?.id.match(/candidate_initiate_direct_list_pc_(\d+)_/)?.[1] || null,
    name:e.querySelector('[class*="name___"]')?.innerText.trim() || '',text:e.innerText,
    contact_button:e.querySelector('.directChatButtonPanel')?.innerText.trim() || '',reply_state:'unknown'
  })));
  result={url:await page.url(),expected_url:target.href,collected_at:new Date().toISOString(),rows,snapshot:snap,
    note:'只读回收当前已加载页面；未逐一打开会话，未回收附件；不按姓名自动确认发送成功'};
} else if(REQUEST.action==='posts') {
  const response=await page.fetch('/community/api/common/search?'+new URLSearchParams({frm:'website',query:REQUEST.query,__platform:'community_web',lim:String(REQUEST.limit||8)}),{timeout:20000});
  if(response.status!==200) throw new Error(`社区读取失败 HTTP ${response.status}`);
  const data=typeof response.body==='string'?JSON.parse(response.body):response.body;
  if(data.result!=='ok') throw new Error('社区返回未成功，未将空结果当成无帖子');
  const posts=[];
  for(const item of data.feeds?.feeds || []) {
    const f=item.feed || {},c=item.contact || {},fid=String(f.id||item.fid||''),efid=f.efid||item.efid;
    if(!fid || !efid)continue;
    posts.push({kind:'feed',id:fid,text:f.text||'',published_at:f.crtime,author_label:c.name||'',
      company_label:c.company||'',role_label:c.position||'',source_level:'实名资料字段；未独立核实任职和内容',
      url:'https://maimai.cn/community/feed-detail/'+fid+'?'+new URLSearchParams({efid}),
      original_page_verified:false,query:REQUEST.query,likes:f.likes,comments:f.total_cnt});
  }
  for(const item of data.gossips?.gossips || []) {
    const g=item.gossip||{},gid=String(g.id||item.gid||''),egid=g.egid||item.egid;
    if(!gid || !egid)continue;
    posts.push({kind:'gossip',id:gid,text:g.text||'',published_at:g.crtime,author_label:g.username||g.author||'',
      company_label:'',role_label:'',source_level:'职言昵称/身份自述；不能据此核实内部员工身份',
      url:'https://maimai.cn/community/gossip-detail/'+gid+'?'+new URLSearchParams({egid,gid}),
      original_page_verified:false,query:REQUEST.query,likes:g.likes,comments:g.total_cnt});
  }
  result={query:REQUEST.query,collected_at:new Date().toISOString(),posts:posts.slice(0,REQUEST.limit||8),
    more_available:!!(data.feeds?.more||data.gossips?.more),note:'当前搜索相关度样本，不是最新全量；不使用未验证分页参数'};
} else if(REQUEST.action==='inspect') {
  result={url:await page.url(),snapshot:await page.snapshot({scope:'full_page'})};
} else {throw new Error('不支持的浏览器动作');}
console.log('MAIMAI_RESULT:'+JSON.stringify(result));
