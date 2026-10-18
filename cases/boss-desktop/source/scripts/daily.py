"""One daily writer: live quota, bounded batches, durable progress, resume stages."""
import argparse
from collections import Counter
from datetime import datetime
import fcntl
import json
import os
from pathlib import Path
import time
from zoneinfo import ZoneInfo

from macos_harness.macos import MacOS
from greet import BASE, ROLE, open_recommendations, ready_snapshot, run_batch
from read_cards import read_state, label
from api_server import daily_count


def today():
    return datetime.now(ZoneInfo('Asia/Shanghai')).date().isoformat()


def write_status(path, status):
    status['updated_at'] = datetime.now().astimezone().isoformat()
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(status, ensure_ascii=False, indent=2))
    tmp.replace(path)


def history():
    result = []
    for path in [BASE / 'runs/greetings.ndjson', *(BASE / 'runs/batches').glob('*/greetings.ndjson')]:
        if path.exists():
            result.extend(json.loads(line) for line in path.read_text().splitlines() if line)
    return result


def ledger_summary(events, date):
    done = {e['identity'] for e in events if e['event'] == 'verified_relationship'}
    attempted = {e['identity'] for e in events if e['event'] in ('pending', 'unknown')}
    today_attempted = {e['identity'] for e in events if e['event'] in ('pending', 'unknown') and e.get('time', '').startswith(date)}
    return dict(excluded=done | attempted, previous_unknown=(attempted - done) - today_attempted,
                today_unknown=today_attempted - done)


def quota_target(quota, requested=600):
    used, total = quota['used'], quota['total']
    if type(used) is not int or type(total) is not int or not 0 <= used <= total or total <= 0:
        raise RuntimeError('账户额度读数无效')
    target = min(requested, total)
    return target, max(0, target - used)


def batch_plan(remaining, batch_size):
    if batch_size not in (25, 50):
        raise ValueError('每批只能25或50人')
    result = []
    while remaining > 0:
        count = min(batch_size, remaining)
        result.append(count)
        remaining -= count
    return result


def run(args):
    date = today()
    folder = BASE / 'runs/daily' / date
    folder.mkdir(parents=True, exist_ok=True)
    status_path = folder / ('preview.json' if not args.execute else 'status.json')
    old = json.loads(status_path.read_text()) if status_path.exists() else {}
    status = dict(date=date, stage='preflight', state='running', batch_size=args.batch_size,
                  requested_max=args.target, batches=old.get('batches', []), real_sends=0,
                  started_at=old.get('started_at', datetime.now().astimezone().isoformat()))
    with (BASE / 'runs/writer.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        write_status(status_path, status)
        try:
            mac = MacOS()
            mac._boss_run_date = date
            from desktop_ui import read_quota, close_filter
            close_filter(mac)
            quota = read_quota(mac)
            target, remaining = quota_target(quota, args.target)
            status.update(quota=quota, target_total=target, remaining=remaining)
            write_status(status_path, status)
            counts = daily_count(mac, already_locked=True)
            status['before'] = counts
            if counts['communication_entitlements_used'] != quota['used']:
                raise RuntimeError('账号额度消耗与今日数据不一致，先核对账号和数据更新时间')
            summary = ledger_summary(history(), date)
            status['excluded_previous_unknown'] = len(summary['previous_unknown'])
            if summary['today_unknown']:
                raise RuntimeError('今天存在结果不明的点击；已排除重发，须先核实后再续跑')
            open_recommendations(mac)
            ready_snapshot(mac)
            verified = False
            proof_path = BASE / 'runs' / ('filter-' + date.replace('-', '') + '.json')
            if proof_path.exists():
                proof = json.loads(proof_path.read_text())
                verified = (proof.get('date') == date and proof.get('role') == ROLE and
                            proof.get('filter') == mac._boss_expected_filter and proof.get('first_degree_fulltime') is True)
            status['education_check'] = 'readable_bachelor_history_excluding_explicit_disallowed_types'
            status['filter_label'] = mac._boss_expected_filter
            status['stage'] = 'greeting'
            seen, reasons = set(), Counter()
            def verified_one(card):
                status['real_sends'] += 1
                status['remaining'] = max(0, remaining - status['real_sends'])
                write_status(status_path, status)
            existing_batches = [int(p.name.rsplit('-', 1)[-1]) for p in (BASE / 'runs/batches').glob(date + '-daily-*')
                                if p.name.rsplit('-', 1)[-1].isdigit()]
            sequence = max([len(status['batches']), *existing_batches])
            # A restart uses fresh quota and the global identity ledger; never repeats a pending person.
            for count in batch_plan(remaining, args.batch_size):
                if today() != date:
                    raise RuntimeError('日期变化，停止本日任务并重新读取新日额度')
                sequence += 1
                batch = BASE / 'runs/batches' / (date + '-daily-' + str(sequence).zfill(3))
                batch.mkdir(parents=True, exist_ok=True)
                result = run_batch(mac, batch / 'greetings.ndjson', verified=verified,
                                   limit=count, pages=args.pages, execute=args.execute,
                                   excluded=summary['excluded'], seen=seen, on_verified=verified_one)
                reasons.update(result['reject_counts'])
                status['batches'].append(dict(batch_id=batch.name, requested=count, **result))
                status['reject_counts'] = dict(reasons)
                write_status(status_path, status)
                if not args.execute:
                    status.update(state='dry_run_complete', stage='greeting_preview')
                    return status
                if result['verified_relationships'] < count:
                    status['greeting_stop_reason'] = 'no_more_qualified_candidates'
                    break
            status['stage'] = 'verify_counts'
            write_status(status_path, status)
            after = daily_count(mac, already_locked=True)
            status['after'] = after
            delta = after['communication_entitlements_used'] - counts['communication_entitlements_used']
            if delta != status['real_sends']:
                raise RuntimeError('平台新增记账与逐人回查不同，停止并保留记录')
            status['official_count_verified'] = True
            status['stage'] = 'resume_collection'
            write_status(status_path, status)
            from resumes_desktop import collect
            status['resumes'] = collect(mac, date=date, execute=args.execute, status_path=folder / 'resumes.json')
            status['state'] = 'complete' if after['communication_entitlements_used'] >= target else 'partial_candidates_exhausted'
            status['stage'] = 'finished'
            return status
        except Exception as error:
            status.update(state='stopped', reason=str(error))
            raise
        finally:
            write_status(status_path, status)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--batch-size', type=int, choices=(25, 50), default=25)
    parser.add_argument('--target', type=int, choices=(400, 600), default=600)
    parser.add_argument('--pages', type=int, default=120)
    args = parser.parse_args()
    if not 1 <= args.pages <= 240:
        parser.error('pages范围1至240')
    os.umask(0o077)
    result = run(args)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()
