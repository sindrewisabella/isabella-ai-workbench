import json
from pathlib import Path
import tempfile
import threading
import unittest
from contextlib import nullcontext
from types import SimpleNamespace
from unittest.mock import patch
from urllib.request import Request, build_opener, ProxyHandler
from urllib.error import HTTPError
from http.server import ThreadingHTTPServer

import api_server as api


class Tests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        root = Path(self.folder.name)
        (root / 'runs').mkdir()
        (root / 'api').mkdir()
        self.patches = [patch.object(api, 'BASE', root), patch.object(api, 'SERVICE', root / 'api'),
                        patch.object(api, 'filter_proof', return_value=root / 'proof'),
                        patch.object(api.threading, 'Thread'), patch.object(api, 'ACTIVE_REQUESTS', set())]
        for p in self.patches:
            p.start()
        self.body = dict(request_id='test', batch_id='current', target_total=25, dry_run=False, pages=2)

    def tearDown(self):
        for p in reversed(self.patches):
            p.stop()
        self.folder.cleanup()

    def test_request_replay_does_not_launch_twice(self):
        first = api.launch(self.body)
        self.assertEqual(api.launch(self.body), first)
        self.assertEqual(api.threading.Thread.call_count, 1)
        with self.assertRaises(ValueError):
            api.launch({**self.body, 'target_total': 24})

    def test_concurrent_requests_and_ui_queries_blocked(self):
        api.launch(self.body)
        with self.assertRaises(ValueError):
            api.launch({**self.body, 'request_id': 'second'})
        with self.assertRaises(ValueError):
            api.ui_lock()

    def test_cap_and_identity_input(self):
        for change in [{'target_total': 51}, {'target_total': True}, {'batch_id': '../escape'}, {'dry_run': 'false'}]:
            with self.assertRaises(ValueError):
                api.launch({**self.body, **change})

    def test_unknown_send_blocks(self):
        (api.BASE / 'runs' / 'greetings.ndjson').write_text(json.dumps({'event': 'pending', 'identity': 'candidate'}) + '\n')
        with self.assertRaises(ValueError):
            api.launch(self.body)

    def test_daily_request_cap_batch_size_and_replay(self):
        body = dict(request_id='daily-test', target_total=600, batch_size=50, dry_run=True)
        first = api.launch_daily(body)
        self.assertEqual(first, api.launch_daily(body))
        self.assertEqual(api.threading.Thread.call_count, 1)
        for change in [{'target_total': 1000}, {'batch_size': 100}, {'dry_run': 'false'}]:
            with self.assertRaises(ValueError):
                api.launch_daily({**body, **change})

    def test_dead_request_recovered_without_restarting(self):
        path = api.SERVICE / 'dead.json'
        api.save(path, {'state': 'running', 'pid': 99999999})
        api.recover_interrupted_requests()
        self.assertEqual(json.loads(path.read_text())['state'], 'interrupted')
        api.threading.Thread.assert_not_called()


class HTTPTests(unittest.TestCase):
    def test_daily_count_waits_for_animation_to_settle(self):
        mac = SimpleNamespace(ax=SimpleNamespace(dump=lambda *a, **k: {'nodes': [
            {'role': 'AXWebArea', 'url': 'https://www.zhipin.com/web/client/data-recruit'}]}))
        values = [dict(daily_greetings=n, communication_entitlements_used=37) for n in (19, 33, 37, 37, 37)]
        with patch.object(api, 'ui_lock', return_value=nullcontext()), patch.object(api, 'MacOS', return_value=mac), \
                patch.object(api, 'read_state'), patch.object(api, 'read_counts', side_effect=values) as read, \
                patch.object(api.time, 'sleep'):
            self.assertEqual(api.daily_count()['daily_greetings'], 37)
            self.assertEqual(read.call_count, 5)

    def test_authentication_and_malformed_body(self):
        server = ThreadingHTTPServer(('127.0.0.1', 0), api.Handler)
        server.token = 'test-only-token'
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        url = 'http://127.0.0.1:' + str(server.server_port)
        urlopen = build_opener(ProxyHandler({})).open
        try:
            with self.assertRaises(HTTPError) as error:
                urlopen(url + '/health', timeout=2)
            self.assertEqual(error.exception.code, 401)
            error.exception.close()
            headers = {'Authorization': 'Bearer test-only-token'}
            with urlopen(Request(url + '/health', headers=headers), timeout=2) as response:
                self.assertTrue(json.load(response)['ok'])
            with self.assertRaises(HTTPError) as error:
                urlopen(Request(url + '/runs', data=b'[]', headers=headers), timeout=2)
            self.assertEqual(error.exception.code, 409)
            error.exception.close()
        finally:
            server.shutdown()
            server.server_close()
            thread.join()


if __name__ == '__main__':
    unittest.main()
