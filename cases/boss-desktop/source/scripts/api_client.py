#!/usr/bin/env python3
"""Warp entry point. Starts the passive local API on demand; queries never greet."""
import argparse
import fcntl
import json
from pathlib import Path
import subprocess
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, build_opener, ProxyHandler
from urllib.parse import urlencode

ROOT = Path(__file__).resolve().parent.parent
SERVICE = ROOT / 'api'
URL = 'http://127.0.0.1:49727'


def call(path, body=None):
    token_path = SERVICE / 'token'
    token = token_path.read_text().strip() if token_path.exists() else ''
    data = json.dumps(body).encode() if body is not None else None
    req = Request(URL + path, data=data, headers={'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json'})
    with build_opener(ProxyHandler({})).open(req, timeout=45) as response:
        return json.load(response)


def ensure_server():
    try:
        return call('/health')
    except URLError as error:
        if not isinstance(error.reason, ConnectionRefusedError):
            raise
    (ROOT / 'runs').mkdir(exist_ok=True, mode=0o700)
    SERVICE.mkdir(exist_ok=True, mode=0o700)
    with (SERVICE / 'start.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        try:
            return call('/health')
        except URLError as error:
            if not isinstance(error.reason, ConnectionRefusedError):
                raise
        with (SERVICE / 'server.log').open('ab') as log:
            process = subprocess.Popen([sys.executable, str(Path(__file__).resolve().with_name('api_server.py'))],
                                       stdin=subprocess.DEVNULL, stdout=log, stderr=log,
                                       start_new_session=True)
        for _ in range(60):
            if process.poll() is not None:
                raise RuntimeError('本机API启动失败，请检查server.log')
            try:
                return call('/health')
            except URLError as error:
                if not isinstance(error.reason, ConnectionRefusedError):
                    raise
                time.sleep(.1)
        raise RuntimeError('API尚未就绪；保留原进程，稍后重新查询，不重复启动')


def main():
    parser = argparse.ArgumentParser(description='BOSS桌面本机API，默认查询和演练不发送')
    parser.add_argument('command', choices=['health', 'status', 'scan', 'count', 'run', 'daily', 'daily-status'])
    parser.add_argument('--batch-id', default='current')
    parser.add_argument('--request-id')
    parser.add_argument('--target', type=int)
    parser.add_argument('--pages', type=int, default=80)
    parser.add_argument('--batch-size', type=int, choices=(25, 50), default=25)
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--jobs', choices=['current', 'ops-testing'], default='current')
    args = parser.parse_args()
    if args.target is None:
        args.target = 600 if args.command == 'daily' else 25
    if args.command in ('run', 'daily') and not args.request_id:
        parser.error('run必须指定request-id；重复提交同一编号不会重复发送')
    ensure_server()
    if args.command == 'daily':
        result = call('/daily-runs', {'request_id': args.request_id, 'target_total': args.target,
                                    'pages': args.pages, 'batch_size': args.batch_size, 'dry_run': not args.execute})
    elif args.command == 'run':
        result = call('/runs', {'request_id': args.request_id, 'batch_id': args.batch_id,
                               'target_total': args.target, 'pages': args.pages, 'dry_run': not args.execute, 'jobs': args.jobs})
    else:
        path = {'health': '/health', 'status': '/status?' + urlencode({'batch_id': args.batch_id}),
                'scan': '/scan', 'count': '/daily-count', 'daily-status': '/daily-status'}[args.command]
        result = call(path)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    try:
        main()
    except HTTPError as error:
        print(error.read().decode(), file=sys.stderr)
        sys.exit(1)
