"""BOSS Mac recommendation-card runner. Default is read-only candidate screening.

Port of the web runner's test-role gates. No chat-page actions or message typing.
AX indices are consumed only from a fresh snapshot in this process.
"""
import argparse
from collections import Counter
from datetime import datetime
import fcntl
import json
import os
from pathlib import Path
import re
import subprocess
import time
from zoneinfo import ZoneInfo

from macos_harness.macos import MacOS
from read_cards import inspect, label, read_state
from read_tail import read_tail
from jobs import context, open_recommendations, list_jobs, select_job

BASE = Path(__file__).resolve().parent.parent
ROLE = '测试工程师（外包）'
TERMS = {
    '测试岗位': ['测试工程师', '软件测试', '测试开发', 'QA', '质量保障', '功能测试', '自动化测试', '接口测试', '性能测试', '白盒测试'],
    '测试实践': ['功能测试', '性能测试', '白盒测试', '接口测试', '自动化测试', '回归测试', '测试用例', '缺陷管理', 'JMeter', 'Postman', 'Pytest', 'Selenium'],
    'Python': ['Python', 'Pytest'],
    'Linux/Shell': ['Linux', 'Shell', 'Bash'],
    'AI': ['AI', '人工智能', 'AIGC', 'AI Agent', '智能体', 'Agent', 'Agentic', 'LLM', '大模型', 'RAG', 'MCP', 'LangChain', 'LangGraph', 'Claude Code', 'Codex', 'Cursor', 'ChatGPT', 'DeepSeek', 'Copilot', 'AI测试', '智能测试', '模型测试', '算法测试', '机器学习', '深度学习', '生成式AI', '生成式 AI', 'AI工具', 'AI 工具'],
}
RANK = {'大专': 1, '专科': 1, '本科': 2, '学士': 2, '硕士': 3, '研究生': 3, '博士': 4}
REJECT_EDU = ['大专', '专科', '中专', '高中', '专升本', '成人', '函授', '自考', '开放大学', '广播电视大学', '非全日制']


def evaluate(card, first_degree_verified=False, year=None):
    year = year or datetime.now(ZoneInfo('Asia/Shanghai')).year
    text = card['text']
    rejects, evidence = [], {}
    if card['button'] != '打招呼':
        rejects.append('已经沟通')
    edu = [e for e in card['education'] if e['degree'] in RANK]
    if not edu:
        rejects.append('缺少可核对的学历经历')
    else:
        first = min(edu, key=lambda e: e['start'])
        highest = max(edu, key=lambda e: (RANK[e['degree']], e['end']))
        if RANK[first['degree']] != 2:
            rejects.append('第一学历不是本科')
        if (any(t in ' '.join(str(v) for v in first.values()) for t in REJECT_EDU)
                or first['school'].strip().endswith('电大')):
            rejects.append('第一学历不符合要求')
        if highest['end'] > year:
            rejects.append('最高学历尚未毕业')
    # Latest authorization: readable bachelor history is sufficient; absence of
    # a full-time label is not a rejection and is never proof of full-time study.
    excluded_labels = re.findall(
        r'专升本|(?:成人|函授|自考|非全日制)[^\n。；]{0,12}(?:本科|学士|学历|教育)|'
        r'(?:本科|学士)[^\n。；]{0,12}(?:成人|函授|自考|非全日制)', text)
    if excluded_labels and '第一学历不符合要求' not in rejects:
        rejects.append('明确不符合的学历类型')
    for name, terms in TERMS.items():
        # Avoid counting e.g. 'detail' as the standalone AI abbreviation.
        evidence[name] = [t for t in terms if re.search(
            r'(?<![A-Za-z])' + re.escape(t) + r'(?![A-Za-z])' if t in ('AI', 'QA', 'RAG', 'MCP', 'LLM') else re.escape(t), text, re.I)]
        if name == 'AI' and not evidence[name]:
            rejects.append('缺少' + name + '证据')
    return {'pass': not rejects, 'rejects': rejects, 'evidence': evidence,
            'education_basis': 'readable_bachelor_history_excluding_explicit_disallowed_types',
            'fulltime_verified': False}


def snapshot(mac, full=False):
    state = read_state(mac) if full else read_tail(mac)
    labels = [label(n) for n in state['nodes']]
    current_job = context(state)
    expected_job = getattr(mac, '_boss_expected_job', None)
    if expected_job is not None and current_job != expected_job:
        raise RuntimeError('发送过程中岗位变化，停止以免发错岗位')
    mac._boss_expected_job = current_job
    filters = [t for t in labels if re.fullmatch(r'筛选(?:·\d+)?', t)]
    expected = getattr(mac, '_boss_expected_filter', None)
    if len(filters) != 1 or (expected is not None and filters[0] != expected) or '筛选条件' in labels:
        raise RuntimeError('筛选变化或弹窗尚未关闭')
    mac._boss_expected_filter = filters[0]
    cards = inspect(state, internal=True)['cards']
    for node in state['nodes']:
        if label(node) not in ('安全验证', '请完成验证', '账号异常', '请登录', '打招呼次数已用完', '当前网络不可用'):
            continue
        in_candidate_card = any(c['card_index'] <= node['element_index'] <= c['card_end_index'] for c in cards)
        if not in_candidate_card:
            raise RuntimeError('平台验证、登录或权益异常')
    if not cards:
        raise RuntimeError('没有可读人选卡片')
    return cards


def ready_snapshot(mac, full=False):
    """Only retry a temporarily missing list; never retry an outbound click."""
    deadline = None
    transient_messages = (
        '无法唯一定位人选列表',
        '没有可读人选卡片',
        '当前岗位不符或推荐页未就绪',
    )
    while True:
        try:
            return snapshot(mac, full=full)
        except RuntimeError as error:
            if deadline is None:
                deadline = time.monotonic() + 60
            transient = any(message in str(error) for message in transient_messages)
            if not transient or time.monotonic() >= deadline:
                raise
            # The shallow tail reader can see multiple nested AXList nodes.
            # Fall back to one fresh complete tree before retrying; this is a
            # read-only recovery and never repeats an outbound click.
            try:
                return snapshot(mac, full=True)
            except RuntimeError as full_error:
                if not any(message in str(full_error) for message in transient_messages):
                    raise
            shallow = mac.ax.dump('BOSS直聘', max_depth=25, max_nodes=10000,
                                  include_actions=True, include_settable=False)
            labels = [label(n) for n in shallow['nodes']]
            if any(t in labels for t in ('安全验证', '请完成验证', '账号异常', '请登录', '当前网络不可用')):
                raise RuntimeError('页面恢复过程中出现平台验证或网络异常')
            time.sleep(1)


class AmbiguousIdentity(RuntimeError):
    pass

def unique(cards, identity):
    found = [c for c in cards if c['identity'] == identity]
    if len(found) != 1:
        raise AmbiguousIdentity('无法按姓名及完整学历经历唯一确认同一人选')
    return found[0]


def append_event(path, event):
    with path.open('a', encoding='utf-8') as f:
        f.write(json.dumps({'time': datetime.now().astimezone().isoformat(), **event}, ensure_ascii=False) + '\n')
        f.flush()
        os.fsync(f.fileno())


def greet_one(mac, candidate, audit, verified):
    if getattr(mac, '_boss_run_date', datetime.now(ZoneInfo('Asia/Shanghai')).date().isoformat()) != datetime.now(ZoneInfo('Asia/Shanghai')).date().isoformat():
        raise RuntimeError('已跨天，先重新核对今日额度')
    card = unique(ready_snapshot(mac), candidate['identity'])
    if not evaluate(card, verified)['pass']:
        raise RuntimeError('发送前重新筛选未通过')
    if not card['fully_in_window']:
        mac.ax.perform(card['button_index'], 'AXScrollToVisible')
        card = unique(ready_snapshot(mac), candidate['identity'])
    if not card['fully_in_window']:
        rows = ready_snapshot(mac)
        card = unique(rows, candidate['identity'])
        position = rows.index(card)
        # Scrolling the next row into view moves a clipped bottom button upward.
        if position + 1 < len(rows):
            mac.ax.perform(rows[position + 1]['button_index'], 'AXScrollToVisible')
            card = unique(ready_snapshot(mac), candidate['identity'])
        else:
            # The last loaded row has no next card. Load once, then resolve
            # this same identity again; never press a clipped button.
            state = read_tail(mac)
            footer = [n for n in state['nodes'] if label(n) == '滚动加载更多']
            if len(footer) == 1 and 'AXScrollToVisible' in footer[0].get('actions', []):
                mac.ax.perform(footer[0]['element_index'], 'AXScrollToVisible')
                time.sleep(1.5)
                card = unique(ready_snapshot(mac), candidate['identity'])
    if not card['fully_in_window'] or card['button'] != '打招呼':
        raise RuntimeError('当前按钮不可安全操作')
    if not evaluate(card, verified)['pass']:
        raise RuntimeError('滚动后的最新卡片筛选未通过')
    # The pending event is durable BEFORE the single irreversible action.
    append_event(audit, {'event': 'pending', 'identity': card['identity']})
    mac.ax.perform(card['button_index'], 'AXPress')
    deadline = time.monotonic() + 60
    full_lookup_used = False
    while time.monotonic() < deadline:
        cards = ready_snapshot(mac)
        try:
            after = unique(cards, card['identity'])
        except AmbiguousIdentity:
            if not full_lookup_used:
                full_lookup_used = True
                cards = ready_snapshot(mac, full=True)
                try:
                    after = unique(cards, card['identity'])
                except AmbiguousIdentity:
                    time.sleep(1)
                    continue
            else:
                time.sleep(1)
                continue
        if after['button'] == '继续沟通':
            append_event(audit, {'event': 'verified_relationship', 'identity': card['identity']})
            return
        time.sleep(1)
    append_event(audit, {'event': 'unknown', 'identity': card['identity']})
    raise RuntimeError('点击后未核实同一人选状态；停止，禁止补点')


def run_batch(mac, audit, *, verified=False, limit=25, pages=80, execute=False, excluded=None, seen=None, on_verified=None):
    excluded = excluded if excluded is not None else set()
    seen = seen if seen is not None else set()
    sent, stable = 0, 0
    reasons = Counter()
    for page in range(pages):
        cards = ready_snapshot(mac)
        fresh = [c for c in cards if c['identity'] not in seen]
        stable = stable + 1 if not fresh else 0
        print(json.dumps({'page': page + 1, 'new_cards': len(fresh),
                          'outside_saved_filters': sum(c['outside_saved_filters'] for c in cards)}, ensure_ascii=False), flush=True)
        for card in fresh:
            seen.add(card['identity'])
            result = evaluate(card, verified)
            reasons.update(result['rejects'])
            if result['pass']:
                print(json.dumps({'identity': card['identity'][:16], **result}, ensure_ascii=False), flush=True)
            if result['pass'] and execute and card['identity'] not in excluded:
                try:
                    greet_one(mac, card, audit, verified)
                except AmbiguousIdentity as error:
                    # Same-name/duplicate-card ambiguity before AXPress: skip this
                    # card and continue scanning; no irreversible action occurred.
                    reasons.update({'身份歧义已跳过': 1})
                    print(json.dumps({'identity': card['identity'][:16], 'skipped': 'ambiguous_identity'}, ensure_ascii=False), flush=True)
                    continue
                sent += 1
                excluded.add(card['identity'])
                if on_verified:
                    on_verified(card)
                if sent >= limit:
                    break
        if sent >= limit or stable >= 3 or page + 1 == pages:
            break
        try:
            state = read_tail(mac)
        except RuntimeError as error:
            if '无法唯一定位人选列表' not in str(error):
                raise
            state = read_state(mac)
        footer = [n for n in state['nodes'] if label(n) == '滚动加载更多']
        if len(footer) == 1:
            mac.ax.perform(footer[0]['element_index'], 'AXScrollToVisible')
        else:
            # Some recommendation tabs load the next 15 rows when the last
            # card enters the viewport, without a text-labelled footer.
            tail_cards = inspect(state, internal=True)['cards']
            if not tail_cards:
                # The virtual list can briefly expose no rows while the
                # "latest" tab redraws. Resolve a new full snapshot before
                # choosing the last card; never reuse an index from the empty
                # state.
                tail_cards = ready_snapshot(mac, full=True)
            mac.ax.perform(tail_cards[-1]['button_index'], 'AXScrollToVisible')
        time.sleep(1.5)
    result = {'screened': len(seen), 'verified_relationships': sent,
                  'reject_counts': dict(reasons), 'official_count_verified': False}
    print(json.dumps(result, ensure_ascii=False), flush=True)
    return result

def run_jobs(mac, audit, *, limit, pages, execute, excluded):
    titles = list_jobs(mac)
    # Prefer the explicit Shenzhen operations outsourcing job when it is
    # present in the observed dropdown; otherwise retain observed order.
    preferred = [t for t in titles if t.startswith('运维工程师（外包） _ 深圳') ]
    titles = preferred + [t for t in titles if t not in preferred]
    jobs_seen, seen = set(), set()
    total = 0
    results = []
    for position in range(len(titles)):
        job = select_job(mac, position, titles)
        if job['job_id'] in jobs_seen:
            continue
        jobs_seen.add(job['job_id'])
        print(json.dumps({'job': job}, ensure_ascii=False), flush=True)
        # A filter proof for one job never transfers to another job.
        result = run_batch(mac, audit, verified=False, limit=limit-total,
                           pages=pages, execute=execute, excluded=excluded, seen=seen)
        results.append({'job': job, **result})
        total += result['verified_relationships']
        if total >= limit:
            break
    summary = {'jobs_checked': len(results), 'verified_relationships': total,
               'target': limit, 'jobs': results, 'official_count_verified': False}
    print(json.dumps(summary, ensure_ascii=False), flush=True)
    return summary


def main():
    parser = argparse.ArgumentParser(description='BOSS 桌面推荐页筛选；默认不发送')
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--jobs', choices=['current', 'ops-testing'], default='current')
    parser.add_argument('--limit', type=int, default=1)
    parser.add_argument('--pages', type=int, default=1)
    parser.add_argument('--verified-filter-file', type=Path)
    parser.add_argument('--batch-id', default='current', help='本次用户授权批次；current继续当前25人任务')
    args = parser.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,80}', args.batch_id):
        parser.error('batch-id只能包含字母、数字、下划线和连字符')
    if args.execute and (BASE / 'runs' / 'scope-review-required.json').exists():
        parser.error('本轮4个已发送人选的城市/兼职范围待用户确认，暂不继续发送；可只读检查')
    if not 1 <= args.limit <= 50 or not 1 <= args.pages <= 240:
        parser.error('limit 必须1至50；pages 必须1至240')
    verified = False
    if args.verified_filter_file:
        proof = json.loads(args.verified_filter_file.read_text())
        verified = (proof.get('role') == ROLE and bool(re.fullmatch(r'筛选(?:·\d+)?', proof.get('filter', '')))
                    and proof.get('first_degree_fulltime') is True
                    and proof.get('date') == datetime.now(ZoneInfo('Asia/Shanghai')).date().isoformat())
    os.umask(0o077)
    runs = BASE / 'runs'
    logs = runs if args.batch_id == 'current' else runs / 'batches' / args.batch_id
    logs.mkdir(exist_ok=True, parents=True)
    with (runs / 'writer.lock').open('w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        audit = logs / 'greetings.ndjson'
        previous = [json.loads(x) for x in audit.read_text().splitlines()] if audit.exists() else []
        pending = {e['identity'] for e in previous if e['event'] in ('pending', 'unknown')}
        confirmed = {e['identity'] for e in previous if e['event'] == 'verified_relationship'}
        history = []
        for ledger in [runs / 'greetings.ndjson', *runs.glob('batches/*/greetings.ndjson')]:
            if ledger.exists():
                history.extend(json.loads(x) for x in ledger.read_text().splitlines())
        global_pending = {e['identity'] for e in history if e['event'] in ('pending', 'unknown')}
        global_confirmed = {e['identity'] for e in history if e['event'] == 'verified_relationship'}
        today = datetime.now(ZoneInfo('Asia/Shanghai')).date().isoformat()
        today_pending = {e['identity'] for e in history if e['event'] in ('pending', 'unknown') and e.get('time', '').startswith(today)}
        if args.execute and today_pending - global_confirmed:
            raise RuntimeError('今日存在点击结果未知，先回查，不启动新发送；往日未知人选永久排除，不影响其他新人')
        if args.execute and pending - confirmed:
            raise RuntimeError('存在未确认的点击，须先回查；禁止启动新一轮发送')
        if args.execute and args.limit > 1 and not confirmed:
            raise RuntimeError('先用 limit=1 完成一次同人选状态验证，再运行剩余数量')
        cap = 25 if args.batch_id == 'current' else 50
        if args.execute and len(confirmed) + args.limit > cap:
            raise RuntimeError(f'本批台账加上请求数量会超过{cap}人；减少limit')
        mac, seen, sent, stable = MacOS(), set(), 0, 0
        mac._boss_run_date = today
        open_recommendations(mac)
        if args.execute:
            # Only prevent idle sleep for this runner's lifetime. Manual
            # locking remains detectable and stops the run normally.
            subprocess.Popen(['/usr/bin/caffeinate', '-di', '-w', str(os.getpid())],
                             stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL, start_new_session=True)
        if args.jobs == 'ops-testing':
            run_jobs(mac, audit, limit=args.limit, pages=args.pages, execute=args.execute, excluded=global_pending)
        else:
            if verified:
                mac._boss_expected_filter = proof['filter']
            run_batch(mac, audit, verified=verified, limit=args.limit, pages=args.pages, execute=args.execute, excluded=global_pending)


if __name__ == '__main__':
    main()
