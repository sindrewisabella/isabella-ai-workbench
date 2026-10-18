"""Authenticated loopback HTTP API for the verified BOSS desktop runner."""
import fcntl
from contextlib import nullcontext
import hmac
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import re
import secrets
import subprocess
import sys
import threading
import time
from urllib.parse import urlparse, parse_qs
from datetime import datetime
from zoneinfo import ZoneInfo

from greet import BASE, evaluate, snapshot, open_recommendations
from macos_harness.macos import MacOS
from read_cards import read_state
from read_daily_count import read_counts

PORT = 49727
SERVICE = BASE / 'api'
MUTEX = threading.Lock()
PROCESSES = {}
ACTIVE_REQUESTS = set()


def identifier(value):
    if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,80}', value):
        raise ValueError('编号只允许1至80个字母、数字、下划线或连字符')
    return value


def batch_dir(batch):
    identifier(batch)
    return BASE / 'runs' if batch == 'current' else BASE / 'runs' / 'batches' / batch


def audit_status(batch):
    path = batch_dir(batch) / 'greetings.ndjson'
    events = [json.loads(x) for x in path.read_text().splitlines()] if path.exists() else []
    sent = {e['identity'] for e in events if e['event'] == 'verified_relationship'}
    pending = {e['identity'] for e in events if e['event'] in ('pending', 'unknown')}
    return {'batch_id': batch, 'verified_relationships': len(sent), 'unknown': len(pending - sent)}


def save(path, data):
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2))
    temp.replace(path)


def recover_interrupted_requests():
    """Recover request metadata only; never automatically restart a writer."""
    try:
        lock = ui_lock()
    except ValueError:
        return
    with lock:
        for path in SERVICE.glob('*.json'):
            record = json.loads(path.read_text())
            if record.get('state') not in ('queued', 'running'):
                continue
            pid = record.get('pid')
            command = ''
            if type(pid) is int:
                result = subprocess.run(['ps', '-p', str(pid), '-o', 'command='], capture_output=True, text=True)
                command = result.stdout
            scripts = (str(Path(__file__).with_name('greet.py')), str(Path(__file__).with_name('daily.py')))
            if any(script in command for script in scripts):
                continue
            record.update(state='interrupted', reason='原执行进程已结束；保留台账，续跑须重新读取今日额度')
            save(path, record)


def ui_lock():
    if ACTIVE_REQUESTS:
        raise ValueError('招呼任务进行中；仅查询status，完成后再查看页面数据')
    f = (BASE / 'runs' / 'writer.lock').open('a')
    try:
        fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        f.close()
        raise ValueError('桌面操作正在运行；请只查询status，稍后再读页面')
    return f


def filter_proof():
    date = datetime.now(ZoneInfo('Asia/Shanghai')).date()
    path = BASE / 'runs' / f'filter-{date:%Y%m%d}.json'
    return path if path.exists() else None


def worker(record, path):
    log = SERVICE / (record['request_id'] + '.log')
    try:
        target = record['target_total']
        before = audit_status(record['batch_id'])
        while record['dry_run'] or before['verified_relationships'] < target:
            remaining = target - before['verified_relationships']
            limit = 1 if before['verified_relationships'] == 0 else remaining
            command = [sys.executable, str(Path(__file__).with_name('greet.py')),
                       '--limit', str(max(1, limit)), '--pages', str(record['pages']),
                       '--batch-id', record['batch_id'], '--jobs', record.get('jobs', 'current')]
            if filter_proof():
                command += ['--verified-filter-file', str(filter_proof())]
            if not record['dry_run']:
                command.append('--execute')
            with log.open('a') as output:
                process = subprocess.Popen(command, stdout=output, stderr=subprocess.STDOUT)
                PROCESSES[record['request_id']] = process
                record.update(state='running', pid=process.pid)
                save(path, record)
                code = process.wait()
            after = audit_status(record['batch_id'])
            record.update(after, exit_code=code)
            if code:
                record['state'] = 'failed'
                record['reason'] = log.read_text().splitlines()[-1] if log.exists() else '运行失败，检查日志'
                break
            if record['dry_run']:
                record['state'] = 'dry_run_complete'
                break
            if after['verified_relationships'] == before['verified_relationships']:
                record['state'] = 'incomplete_no_more_matches'
                record['scan_exhaustive'] = False
                record['reason'] = f"本次每岗最多扫描{record['pages']}页，未找到可新增联系的人选；不代表全部人选已耗尽。请查看筛选原因，不能跳过资格条件补数量。"
                break
            before = after
        else:
            record['state'] = 'target_reached'
        if not record['dry_run'] and record.get('verified_relationships', before['verified_relationships']) >= target:
            record['state'] = 'target_reached'
        record['official_count_verified'] = False
    except Exception as error:
        record.update(state='failed', error=str(error))
    finally:
        PROCESSES.pop(record['request_id'], None)
        record['finished_at'] = datetime.now().astimezone().isoformat()
        save(path, record)
        ACTIVE_REQUESTS.discard(record['request_id'])


def launch(body):
    if set(body) - {'request_id', 'batch_id', 'target_total', 'dry_run', 'pages', 'jobs'}:
        raise ValueError('包含不支持的字段')
    request = identifier(body.get('request_id'))
    batch = identifier(body.get('batch_id'))
    target, pages = body.get('target_total'), body.get('pages', 80)
    dry = body.get('dry_run', True)
    if type(target) is not int or not 1 <= target <= 50 or type(pages) is not int or not 1 <= pages <= 240 or type(dry) is not bool:
        raise ValueError('target_total为1至50，pages为1至240，dry_run必须为布尔值')
    if batch == 'current' and target > 25:
        raise ValueError('current是历史25人任务，请使用当日任务入口')
    jobs = body.get('jobs', 'current')
    if jobs not in ('current', 'ops-testing'):
        raise ValueError('jobs必须为current或ops-testing')
    normalized = dict(request_id=request, batch_id=batch, target_total=target, pages=pages, dry_run=dry, jobs=jobs)
    path = SERVICE / (request + '.json')
    with MUTEX:
        if path.exists():
            record = json.loads(path.read_text())
            if any(record.get(k, 'current' if k == 'jobs' else None) != v for k, v in normalized.items()):
                raise ValueError('相同request_id不能用于不同请求')
            return record
        for previous in SERVICE.glob('*.json'):
            if json.loads(previous.read_text()).get('state') in ('queued', 'running'):
                raise ValueError('已有运行或中断待核对的请求；不要另建请求重复发送')
        with ui_lock():
            filter_proof()
            status = audit_status(batch)
            if status['unknown']:
                raise ValueError('该批次有未核实的点击，先回查')
            if status['verified_relationships'] > target:
                raise ValueError('目标数量小于该批次已经完成的数量')
        record = {**normalized, **status, 'state': 'queued', 'created_at': datetime.now().astimezone().isoformat()}
        save(path, record)
        ACTIVE_REQUESTS.add(request)
        threading.Thread(target=worker, args=(record, path), daemon=True).start()
        return record.copy()


def launch_daily(body):
    allowed = {'request_id', 'target_total', 'batch_size', 'dry_run', 'pages'}
    if not isinstance(body, dict) or set(body) - allowed:
        raise ValueError('日任务字段不正确')
    request = identifier(body.get('request_id'))
    target, size, dry, pages = body.get('target_total', 600), body.get('batch_size', 25), body.get('dry_run', True), body.get('pages', 120)
    if type(target) is not int or target not in (400, 600) or type(size) is not int or size not in (25, 50) or type(dry) is not bool or type(pages) is not int or not 1 <= pages <= 240:
        raise ValueError('日目标400或600，每批25或50，dry_run为布尔值')
    normalized = dict(request_id=request, kind='daily', target_total=target, batch_size=size, dry_run=dry, pages=pages,
                      date=datetime.now(ZoneInfo('Asia/Shanghai')).date().isoformat())
    path = SERVICE / (request + '.json')
    with MUTEX:
        if path.exists():
            record = json.loads(path.read_text())
            if any(record.get(k) != v for k, v in normalized.items()):
                raise ValueError('请求编号已用于另一组参数或另一日期')
            return record
        if any(json.loads(p.read_text()).get('state') in ('queued', 'running') for p in SERVICE.glob('*.json')):
            raise ValueError('已有任务运行或中断待核对，请勿并发启动')
        with ui_lock():
            pass
        record = {**normalized, 'state': 'queued'}
        save(path, record)
        ACTIVE_REQUESTS.add(request)
        threading.Thread(target=daily_worker, args=(record, path), daemon=True).start()
        return record.copy()


def daily_worker(record, path):
    try:
        command = [sys.executable, str(Path(__file__).with_name('daily.py')),
                   '--target', str(record['target_total']), '--batch-size', str(record['batch_size']),
                   '--pages', str(record['pages'])]
        if not record['dry_run']:
            command.append('--execute')
        with (SERVICE / (record['request_id'] + '.log')).open('a') as output:
            process = subprocess.Popen(command, stdout=output, stderr=subprocess.STDOUT)
            PROCESSES[record['request_id']] = process
            record.update(state='running', pid=process.pid)
            save(path, record)
            code = process.wait()
        status_path = BASE / 'runs/daily' / record['date'] / ('preview.json' if record['dry_run'] else 'status.json')
        result = json.loads(status_path.read_text()) if status_path.exists() else {}
        record.update(state=result.get('state', 'failed'), exit_code=code, result=result)
    except Exception as error:
        record.update(state='failed', error=str(error))
    finally:
        record['finished_at'] = datetime.now().astimezone().isoformat()
        save(path, record)
        PROCESSES.pop(record['request_id'], None)
        ACTIVE_REQUESTS.discard(record['request_id'])


def daily_count(mac=None, already_locked=False):
    with nullcontext() if already_locked else ui_lock():
        mac = mac or MacOS()
        state = mac.ax.dump('BOSS直聘', max_depth=25, max_nodes=10000, include_actions=True, include_settable=False)
        if not any(n.get('role') == 'AXWebArea' and '/web/client/data-recruit' in str(n.get('url', '')) for n in state['nodes']):
            links = [n for n in state['nodes'] if n.get('role') == 'AXLink' and '/web/client/data-recruit' in str(n.get('url') or n.get('value') or '')]
            if len(links) != 1:
                raise ValueError('无法唯一定位数据入口')
            mac.ax.perform(links[0]['element_index'], 'AXPress')
        deadline = time.monotonic() + 30
        previous, stable = None, 0
        while True:
            try:
                result = read_counts(read_state(mac))
                values = (result['daily_greetings'], result['communication_entitlements_used'])
                stable = stable + 1 if values == previous else 1
                previous = values
                if stable >= 3:
                    return result
                if time.monotonic() >= deadline:
                    raise RuntimeError('数据数字仍在变化，暂不报告最终值')
                time.sleep(1)
            except RuntimeError:
                if time.monotonic() >= deadline:
                    raise
                time.sleep(1)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def reply(self, status, data):
        payload = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def authorized(self):
        return hmac.compare_digest(self.headers.get('Authorization', ''), 'Bearer ' + self.server.token)

    def do_GET(self):
        if not self.authorized():
            return self.reply(401, {'error': 'authentication_required'})
        try:
            route = urlparse(self.path)
            query = parse_qs(route.query)
            if route.path == '/health':
                result = {'ok': True, 'api_version': 2, 'features': ['ops-testing-jobs', 'recommendation-recovery'], 'backend': 'BOSS Mac accessibility', 'pid': os.getpid()}
            elif route.path == '/status':
                batch = query.get('batch_id', ['current'])[0]
                result = audit_status(batch)
                result['requests'] = [json.loads(p.read_text()) for p in SERVICE.glob('*.json') if json.loads(p.read_text()).get('batch_id') == batch]
            elif route.path == '/scan':
                with ui_lock():
                    mac = MacOS()
                    open_recommendations(mac)
                    cards = snapshot(mac)
                    path = filter_proof()
                    proof = json.loads(path.read_text()) if path else {}
                    verified = (proof.get('first_degree_fulltime') is True
                                and proof.get('job_id') == mac._boss_expected_job['job_id']
                                and proof.get('filter') == mac._boss_expected_filter
                                and proof.get('date') == datetime.now(ZoneInfo('Asia/Shanghai')).date().isoformat())
                    result = {'sends': 0, 'scope': 'current read window', 'cards': [
                        {'name': c['name'], 'identity': c['identity'], 'education': c['education'],
                         'button': c['button'], **evaluate(c, verified)} for c in cards]}
            elif route.path == '/daily-count':
                result = daily_count()
            elif route.path == '/daily-status':
                date = datetime.now(ZoneInfo('Asia/Shanghai')).date().isoformat()
                folder = BASE / 'runs/daily' / date
                result = {'date': date, 'runs': [json.loads(p.read_text()) for p in folder.glob('*.json')],
                          'requests': [json.loads(p.read_text()) for p in SERVICE.glob('*.json')
                                       if json.loads(p.read_text()).get('date') == date]}
            else:
                return self.reply(404, {'error': 'not_found'})
            self.reply(200, result)
        except Exception as error:
            self.reply(409, {'error': str(error)})

    def do_POST(self):
        if not self.authorized():
            return self.reply(401, {'error': 'authentication_required'})
        if self.path not in ('/runs', '/daily-runs'):
            return self.reply(404, {'error': 'not_found'})
        try:
            size = int(self.headers.get('Content-Length', '0'))
            if not 0 < size <= 4096:
                raise ValueError('请求大小不正确')
            body = json.loads(self.rfile.read(size))
            if not isinstance(body, dict):
                raise ValueError('请求必须为JSON对象')
            self.reply(202, launch_daily(body) if self.path == '/daily-runs' else launch(body))
        except Exception as error:
            self.reply(409, {'error': str(error)})


def main():
    os.umask(0o077)
    (BASE / 'runs').mkdir(exist_ok=True, mode=0o700)
    SERVICE.mkdir(exist_ok=True, mode=0o700)
    token = SERVICE / 'token'
    if not token.exists():
        token.write_text(secrets.token_urlsafe(32))
    recover_interrupted_requests()
    server = ThreadingHTTPServer(('127.0.0.1', PORT), Handler)
    server.token = token.read_text().strip()
    server.serve_forever()


if __name__ == '__main__':
    main()
