#!/usr/bin/env python3
"""Local Maimai HR trial: inspect/search/screen/preflight/send/recover/posts.

Python standard library only. Browser actions use an existing Ego TaskSpace.
No login credentials are exported; no third-party package installation is needed.
"""
import argparse
import base64
import contextlib
import csv
import datetime as dt
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
DATA = ROOT / 'data'


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                     separators=(',', ':')).encode()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2))
    tmp.chmod(0o600)
    tmp.replace(path)


def browser(action, cfg, **kwargs):
    request = {'action': action, 'space': cfg['space'], 'page': cfg.get('page', 'p1'),
               'job_id': cfg.get('job_id'), 'job_title': cfg.get('job_title'), **kwargs}
    encoded = base64.b64encode(json.dumps(request, ensure_ascii=False).encode()).decode()
    source = "const REQUEST=JSON.parse(Buffer.from('" + encoded + "','base64').toString('utf8'));\n"
    source += (ROOT / 'card_compare.js').read_text().split('module.exports =')[0] + '\n'
    source += (ROOT / 'browser_worker.js').read_text()
    # shell=False: candidate text, queries and messages are never shell code.
    try:
        run = subprocess.run(['ego-browser', 'nodejs'], input=source, text=True,
                             capture_output=True, timeout=100)
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError('浏览器超时；若本次是发送，结果不确定，不要重试，先回收核对') from exc
    combined = run.stdout + '\n' + run.stderr
    # Protocol records use LF; Unicode separators can occur inside valid JSON.
    lines = combined.split('\n')
    for line in lines:
        if line.startswith('[ego-browser:notice]'):
            print(line, file=sys.stderr)
    matches = [line[len('MAIMAI_RESULT:'):] for line in lines
               if line.startswith('MAIMAI_RESULT:')]
    if run.returncode or len(matches) != 1:
        errors = '\n'.join(line for line in lines if not line.startswith('MAIMAI_RESULT:'))
        raise RuntimeError('浏览器未完成：' + errors[-1800:])
    return json.loads(matches[0])


def annotate(batch):
    for c in batch.get('cards', []):
        c['evidence_hash'] = digest({'uid': c['uid'], 'name': c['name'], 'text': c['text']})
    batch['captured_at'] = now()
    return batch


def screen(batch, policy):
    """Keyword recall only. A match is NOT evidence that a requirement is met."""
    result = []
    for c in batch['cards']:
        concepts = []
        for req in policy['requirements']:
            lines = [line for line in c['text'].splitlines()
                     if any(term.casefold() in line.casefold() for term in req['recall_terms'])]
            concepts.append({'requirement_id': req['id'], 'requirement': req['description'],
                             'recall_fragments': lines[:8], 'decision': 'unknown',
                             'evidence_quote': '', 'reason': '需读取具体经历确认，关键词命中不等于胜任'})
        result.append({'uid': c['uid'], 'name': c['name'], 'evidence_hash': c['evidence_hash'],
                       'requirements': concepts, 'reviewer': '', 'decision': 'needs_review',
                       'history_checked': False, 'history_evidence': '', 'message': '',
                       'priority_signals': [s for s in ['正在看机会', '近期有动向', '简历'] if s in c['text']],
                       'can_greet': False})
    return {'policy_hash': digest(policy), 'created_at': now(), 'reviews': result,
            'note': '只作检索线索；所有必须项需有原文证据且已审阅，才可进入待批准发送批次'}


def prepare(batch, reviews, policy, preflights, cfg):
    if policy.get('confirmed') is not True:
        raise ValueError('筛选标准尚未由岗位负责人确认')
    if reviews.get('policy_hash') != digest(policy):
        raise ValueError('筛选标准已经变化，请重新审阅')
    cards = {c['uid']: c for c in batch['cards']}
    pf = {p['candidate_uid']: p for p in preflights}
    required = {r['id'] for r in policy['requirements'] if r.get('required', True)}
    items = []
    seen = set()
    for review in reviews['reviews']:
        if review.get('decision') != 'pass':
            continue
        uid = review['uid']
        if uid in seen:
            raise ValueError('审核文件存在重复人选')
        seen.add(uid)
        c = cards.get(uid)
        if not c or review.get('evidence_hash') != c['evidence_hash']:
            raise ValueError('审核结果与候选人原文不一致')
        if not review.get('reviewer') or review.get('history_checked') is not True or not review.get('history_evidence'):
            raise ValueError('缺少审阅者或团队联系历史核验依据')
        checks = {r['requirement_id']: r for r in review.get('requirements', [])}
        for rid in required:
            rr = checks.get(rid, {})
            quote = rr.get('evidence_quote', '')
            if rr.get('decision') != 'pass' or not quote or quote not in c['text'] or not rr.get('reason'):
                raise ValueError('必须项缺少通过结论和候选人原文证据：' + rid)
        message = review.get('message', '').strip()
        if not message or len(message) > 300:
            raise ValueError('需提供 1–300 字待发送文案')
        if uid not in pf:
            raise ValueError('该人选未检查发送弹窗和索要简历开关：' + uid)
        if c['contact_button'] != '立即沟通':
            raise ValueError('候选人已在沟通或当前不可联系')
        items.append({'candidate': c, 'message': message, 'preflight': pf[uid],
                      'review': review})
    if not items:
        raise ValueError('没有通过全部标准的人选；不能为了测试而放宽标准发送')
    return {'version': 1, 'created_at': now(),
            'expires_at': (dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=2)).isoformat(),
            'job_id': cfg['job_id'], 'job_title': cfg['job_title'], 'policy_hash': digest(policy),
            'approved': False, 'approved_by': '', 'max_messages': len(items),
            'max_units': len(items), 'items': items,
            'scope': '仅本批明确人选、文案和弹窗中相同的自动索要简历开关；不加好友、不修改招聘状态'}


def validate_approval(a, cfg, confirmed_hash):
    if a.get('approved') is not True or not a.get('approved_by'):
        raise ValueError('批次未明确批准')
    if confirmed_hash != digest(a):
        raise ValueError('确认指纹与当前批准文件不同，需重新查看正文')
    expiry = dt.datetime.fromisoformat(a['expires_at'])
    if expiry.tzinfo is None or expiry <= dt.datetime.now(dt.timezone.utc):
        raise ValueError('批准已过期或缺少时区')
    if str(a['job_id']) != str(cfg['job_id']) or a['job_title'] != cfg['job_title']:
        raise ValueError('批准岗位与浏览器配置不同')
    items = a['items']
    if not items or len(items) > a['max_messages'] or len(items) > a['max_units']:
        raise ValueError('发送数量或额度超出批准范围')
    uids = [i['candidate']['uid'] for i in items]
    if len(set(uids)) != len(uids):
        raise ValueError('同一批次存在重复候选人')
    for item in items:
        c = item['candidate']
        if not re.fullmatch(r'\d+', c['uid']):
            raise ValueError('无效候选人编号')
        if c['evidence_hash'] != digest({'uid': c['uid'], 'name': c['name'], 'text': c['text']}):
            raise ValueError('候选人原文被改动')
        if not item['message'] or len(item['message']) > 300:
            raise ValueError('消息为空或超过 300 字')
        p = item['preflight']
        if p['candidate_uid'] != c['uid'] or p['candidate_name'] != c['name']:
            raise ValueError('弹窗人选不一致')
        if p['auto_resume'] not in (True, False):
            raise ValueError('未明确自动索要简历开关')
    return items


@contextlib.contextmanager
def locked():
    DATA.mkdir(exist_ok=True)
    with (DATA / '.send.lock').open('w') as f:
        try:
            fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RuntimeError('另一个发送任务正在运行') from exc
        yield


def append_event(event):
    path = DATA / 'send-events.jsonl'
    with path.open('a') as f:
        f.write(json.dumps(event, ensure_ascii=False) + '\n')
        f.flush()
        os.fsync(f.fileno())
    path.chmod(0o600)


def attempted_uids():
    path = DATA / 'send-events.jsonl'
    return {json.loads(line)['uid'] for line in path.read_text().splitlines()} if path.exists() else set()


def export_cards(batch, out):
    with Path(out).open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['平台候选人编号', '姓名', '当前沟通按钮', '期望', '原始页面', '个人主页_未核实则空', '资料原文', '采集时间'])
        for c in batch['cards']:
            # Avoid spreadsheet formula execution for arbitrary profile text.
            vals = [c['uid'], c['name'], c['contact_button'], c['expectation'], c['source_url'], c['profile_url'] or '', c['text'], c['collected_at']]
            writer.writerow(["'" + str(x) if str(x).startswith(('=', '+', '-', '@')) else x for x in vals])
    Path(out).chmod(0o600)


def main(argv=None):
    p = argparse.ArgumentParser(description='脉脉 HR 本地试用工具：默认只读，发送需要具体批次批准')
    p.add_argument('--config', default=str(ROOT / 'config.json'))
    sub = p.add_subparsers(dest='command', required=True)
    for name in ['collect', 'search']:
        s = sub.add_parser(name, help='读取当前候选人页' if name == 'collect' else '执行一轮关键词搜索并读取')
        if name == 'search': s.add_argument('query')
        s.add_argument('--limit', type=int, default=20); s.add_argument('--out', required=True)
    s = sub.add_parser('inspect');s.add_argument('--page');s.add_argument('--out', required=True)
    s = sub.add_parser('screen', help='关键词线索整理；不自动判定通过');s.add_argument('candidates');s.add_argument('--policy', default=str(ROOT/'policy.draft.json'));s.add_argument('--out', required=True)
    s = sub.add_parser('preflight', help='检查弹窗并关闭，不发送');s.add_argument('candidates');s.add_argument('--uid', required=True);s.add_argument('--out', required=True)
    s = sub.add_parser('detail', help='读取指定人选已加载详情，输出补充证据后的名单');s.add_argument('candidates');s.add_argument('--uid', required=True);s.add_argument('--out', required=True)
    s = sub.add_parser('prepare', help='生成待批准发送批次');s.add_argument('candidates');s.add_argument('--reviews', required=True);s.add_argument('--policy', required=True);s.add_argument('--preflight', nargs='+', required=True);s.add_argument('--out', required=True)
    s = sub.add_parser('approval', help='查看完整发送内容和文件指纹');s.add_argument('file')
    s = sub.add_parser('send', help='发送已明确批准的具体批次');s.add_argument('file');s.add_argument('--confirm', required=True);s.add_argument('--out', required=True)
    s = sub.add_parser('recover', help='只读回收已确认岗位的我发起页');s.add_argument('--url', required=True);s.add_argument('--out', required=True)
    s = sub.add_parser('posts', help='读取社区搜索样本，不代表最新全量');s.add_argument('query');s.add_argument('--limit', type=int, default=8);s.add_argument('--out', required=True)
    s = sub.add_parser('export');s.add_argument('candidates');s.add_argument('--out', required=True)
    args = p.parse_args(argv)
    cfg = read(args.config)
    if hasattr(args, 'limit') and not 1 <= args.limit <= 30:
        raise ValueError('试用每次读取范围为 1–30 条，不代表平台官方限额')
    if args.command in ('collect', 'search'):
        kw = {'limit': args.limit}
        if args.command == 'search':kw['query'] = args.query
        result = annotate(browser(args.command, cfg, **kw));save(args.out, result)
        print(f"已读取 {len(result['cards'])} 位；{result['total_display']}；尚未判定合适或发送")
    elif args.command == 'inspect':
        result = browser('inspect', cfg, page=args.page or cfg['page']);save(args.out, result)
    elif args.command == 'screen':
        result = screen(read(args.candidates), read(args.policy));save(args.out, result)
        print(f"已整理 {len(result['reviews'])} 位的检索线索，全部待审阅")
    elif args.command == 'detail':
        batch = read(args.candidates)
        items = [c for c in batch['cards'] if c['uid'] == args.uid]
        if len(items) != 1:raise ValueError('候选人必须唯一存在于采集文件')
        c = items[0]
        # Read the profile plus the in-product recruitment history so a
        # candidate with an existing contact/position record is never treated
        # as a new outreach target.  This remains read-only and does not fetch
        # an attachment resume.
        detail = browser('detail', cfg, item=c, include_history=True)
        current = detail.pop('card_after_view')
        c.update(current)
        c['list_text'] = current['text']
        c['detail'] = detail
        c['text'] = c['list_text'] + '\n\n【详情页补充，候选人自述】\n' + detail['text']
        save(args.out, annotate(batch))
        print('已补充当前详情原文，未下载附件。请用新名单重新 screen 和审阅。')
    elif args.command == 'preflight':
        items = [c for c in read(args.candidates)['cards'] if c['uid'] == args.uid]
        if len(items) != 1:raise ValueError('候选人必须唯一存在于采集文件')
        result = browser('preflight', cfg, item=items[0]);save(args.out, result)
        print('弹窗已检查并关闭，未发送。自动索要简历：', result['auto_resume'], '额度：', result['cost_text'])
    elif args.command == 'prepare':
        result = prepare(read(args.candidates), read(args.reviews), read(args.policy), [read(f) for f in args.preflight], cfg);save(args.out, result)
        print('已生成待批准批次，approved=false；请审阅具体人选、文案、额度与自动索要简历开关')
    elif args.command == 'approval':
        a = read(args.file)
        print(json.dumps(a, ensure_ascii=False, indent=2));print('文件指纹：', digest(a))
    elif args.command == 'send':
        a = read(args.file);items = validate_approval(a, cfg, args.confirm);results = []
        with locked():
            attempted = attempted_uids()
            if attempted.intersection(i['candidate']['uid'] for i in items):
                raise ValueError('人选已有发送尝试记录，先回收核对，不自动重试')
            for item in items:
                uid = item['candidate']['uid']
                append_event({'uid': uid, 'state': 'attempt_reserved', 'at': now(), 'approval_hash': digest(a)})
                try:
                    r = browser('send', cfg, item=item['candidate'], message=item['message'],
                                auto_resume=item['preflight']['auto_resume'], max_units=1,
                                attempt_log=str(DATA/'dispatch-events.jsonl'))
                except Exception as e:
                    r = {'uid': uid, 'state': 'uncertain_or_preflight_failed', 'error': str(e), 'at': now()}
                append_event(r);results.append(r);save(args.out, results)
                if r['state'] != 'sent_button_verified':
                    raise RuntimeError('结果不确定或前置核验失败，整批已停止，请先回收核对')
        print(f'本批 {len(results)} 条获得按钮变化回执，仍需在我发起/会话页面核对。')
    elif args.command == 'recover':
        result = browser('recover', cfg, url=args.url);save(args.out, result)
        print('已回收当前页，见', args.out, '；未下载附件、未更改跟进状态')
    elif args.command == 'posts':
        result = browser('posts', cfg, page=cfg['community_page'], query=args.query, limit=args.limit);save(args.out, result)
        print('社区搜索样本', len(result['posts']), '条；需要核对原帖、日期和发布者身份')
    elif args.command == 'export':
        export_cards(read(args.candidates), args.out);print('已导出', args.out)


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print('停止：' + str(exc), file=sys.stderr)
        sys.exit(1)
