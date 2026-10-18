from contextlib import ExitStack
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch, Mock

import daily
from desktop_ui import parse_quota
from greet import evaluate, snapshot, ready_snapshot
from resumes_desktop import decision


class DailyTests(unittest.TestCase):
    def test_account_cap_and_batch_plan(self):
        self.assertEqual(daily.quota_target({'used': 75, 'total': 400}), (400, 325))
        self.assertEqual(daily.quota_target({'used': 0, 'total': 600}), (600, 600))
        self.assertEqual(daily.batch_plan(325, 50), [50] * 6 + [25])
        self.assertEqual(daily.batch_plan(400, 25), [25] * 16)
        self.assertEqual(daily.quota_target({'used': 400, 'total': 400}), (400, 0))
        with self.assertRaises(RuntimeError):
            daily.quota_target({'used': -1, 'total': 400})

    def test_yesterday_unknown_excluded_today_unknown_stops(self):
        summary = daily.ledger_summary([
            {'identity': 'old', 'event': 'pending', 'time': '2026-09-14T10:00:00'},
            {'identity': 'new', 'event': 'pending', 'time': '2026-09-15T10:00:00'},
            {'identity': 'done', 'event': 'verified_relationship', 'time': '2026-09-14T10:00:00'},
        ], '2026-09-15')
        self.assertEqual(summary['previous_unknown'], {'old'})
        self.assertEqual(summary['today_unknown'], {'new'})
        self.assertEqual(summary['excluded'], {'old', 'new', 'done'})

    def test_quota_requires_entitlement_context_and_direct_count(self):
        def state(values):
            return {'nodes': [{'role': 'AXStaticText', 'value': x} for x in values]}
        self.assertEqual(parse_quota(state(['账号权益', '今日沟通额度', '0/400']))['total'], 400)
        for values in [['简历正文', '0/400'], ['账号权益', '简历正文0/400'], ['账号权益', '今日沟通额度', '450/400']]:
            with self.assertRaises(RuntimeError):
                parse_quota(state(values))

    def test_no_filter_file_accepts_bachelor_but_rejects_explicit_nonfulltime(self):
        card = {'button': '打招呼', 'text': 'AI', 'education': [
            {'start': 2016, 'end': 2020, 'school': '大学', 'major': '计算机', 'degree': '本科'}]}
        self.assertTrue(evaluate(card, False, 2026)['pass'])
        self.assertFalse(evaluate(card, False, 2026)['fulltime_verified'])
        card['text'] = 'AI 全日制本科'
        self.assertTrue(evaluate(card, False, 2026)['pass'])
        card['text'] = 'AI 非全日制本科'
        self.assertFalse(evaluate(card, False, 2026)['pass'])

    def test_filter_count_can_change_between_days_not_during_batch(self):
        mac = SimpleNamespace()
        state = {'nodes': [{'role': 'AXStaticText', 'value': '测试工程师（外包） _ 厦门 12-24K'}, {'value': '筛选·1'}, {'role': 'AXWebArea', 'url': 'https://www.zhipin.com/web/frame/recommend/?jobid=one'}]}
        with patch('greet.read_tail', return_value=state), patch('greet.inspect', return_value={'cards': [{'a': 1}]}):
            self.assertEqual(snapshot(mac), [{'a': 1}])
            state['nodes'][1]['value'] = '筛选·2'
            with self.assertRaises(RuntimeError):
                snapshot(mac)

    def test_temporary_list_refresh_waits_without_reclicking(self):
        mac = SimpleNamespace(ax=SimpleNamespace(dump=Mock(return_value={'nodes': []})))
        with patch('greet.snapshot', side_effect=[RuntimeError('无法唯一定位人选列表'), [{'identity': 'same'}]]), patch('greet.time.sleep'):
            self.assertEqual(ready_snapshot(mac), [{'identity': 'same'}])

    def test_resume_decision_does_not_accept_phone_or_wechat(self):
        self.assertEqual(decision('对方想发送附件简历给您，您是否同意'), 'accept_attachment')
        self.assertEqual(decision('对方想交换微信，是否同意'), 'unavailable')
        self.assertEqual(decision('简历请求已发送', request_enabled=True), 'already_requested')
        self.assertEqual(decision('点击预览附件简历', request_enabled=True), 'already_received')

    def test_daily_runs_all_batches_and_resumes_after_count_verification(self):
        with tempfile.TemporaryDirectory() as folder, ExitStack() as stack:
            base = Path(folder); (base / 'runs').mkdir()
            stack.enter_context(patch.object(daily, 'BASE', base))
            stack.enter_context(patch.object(daily, 'today', return_value='2026-09-15'))
            stack.enter_context(patch.object(daily, 'history', return_value=[]))
            stack.enter_context(patch.object(daily, 'MacOS', return_value=SimpleNamespace(_boss_expected_filter='筛选·1')))
            stack.enter_context(patch.object(daily, 'open_recommendations'))
            stack.enter_context(patch.object(daily, 'ready_snapshot'))
            stack.enter_context(patch('desktop_ui.close_filter'))
            stack.enter_context(patch('desktop_ui.read_quota', return_value={'used': 75, 'total': 400}))
            stack.enter_context(patch.object(daily, 'daily_count', side_effect=[
                {'daily_greetings': 75, 'communication_entitlements_used': 75},
                {'daily_greetings': 400, 'communication_entitlements_used': 400}]))
            sizes = []
            def batch(mac, audit, **kwargs):
                sizes.append(kwargs['limit'])
                for i in range(kwargs['limit']): kwargs['on_verified']({'identity': str(i)})
                return dict(verified_relationships=kwargs['limit'], reject_counts={}, screened=kwargs['limit'])
            stack.enter_context(patch.object(daily, 'run_batch', side_effect=batch))
            collect = stack.enter_context(patch('resumes_desktop.collect', return_value={'received': 2}))
            result = daily.run(SimpleNamespace(execute=True, batch_size=50, target=600, pages=80))
            self.assertEqual(sizes, [50] * 6 + [25])
            self.assertEqual(result['real_sends'], 325)
            self.assertEqual(result['state'], 'complete')
            self.assertTrue(result['official_count_verified'])
            collect.assert_called_once()


if __name__ == '__main__':
    unittest.main()
