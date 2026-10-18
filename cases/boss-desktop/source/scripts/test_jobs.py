import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from jobs import context
from greet import run_jobs, run_batch


class JobsTests(unittest.TestCase):
    def test_data_page_with_cached_header_is_not_recommendation(self):
        with self.assertRaises(RuntimeError):
            context({'nodes': [
                {'role': 'AXStaticText', 'value': '测试工程师（外包） _ 厦门 12-24K'},
                {'role': 'AXWebArea', 'url': 'https://www.zhipin.com/web/client/data-recruit'}]})

    def test_remaining_target_and_cross_job_dedup(self):
        jobs = [{'job_id': 'a'}, {'job_id': 'a'}, {'job_id': 'b'}, {'job_id': 'c'}]
        excluded = set()
        calls = []

        def batch(mac, audit, **kw):
            calls.append(kw)
            kw['excluded'].add('already-greeted')
            return {'verified_relationships': 10 if len(calls) == 1 else 15}

        with patch('greet.list_jobs', return_value=['one', 'duplicate', 'two', 'unused']), \
                patch('greet.select_job', side_effect=jobs) as select, \
                patch('greet.run_batch', side_effect=batch):
            result = run_jobs(SimpleNamespace(), None, limit=25, pages=10, execute=True, excluded=excluded)
        self.assertEqual(result['verified_relationships'], 25)
        self.assertEqual([c['limit'] for c in calls], [25, 15])
        self.assertEqual(select.call_count, 3)
        self.assertIs(calls[0]['seen'], calls[1]['seen'])
        self.assertIs(calls[1]['excluded'], excluded)
        self.assertFalse(calls[1]['verified'])

    def test_no_footer_scrolls_last_card_instead_of_stopping(self):
        card = {'identity': 'one', 'outside_saved_filters': False, 'button_index': 17}
        mac = SimpleNamespace(ax=SimpleNamespace(perform=Mock()))
        with patch('greet.ready_snapshot', return_value=[card]), \
                patch('greet.evaluate', return_value={'pass': False, 'rejects': ['缺少AI证据']}), \
                patch('greet.read_tail', return_value={'nodes': []}), \
                patch('greet.inspect', return_value={'cards': [card]}), \
                patch('greet.time.sleep'):
            run_batch(mac, None, pages=2)
        mac.ax.perform.assert_called_once_with(17, 'AXScrollToVisible')


if __name__ == '__main__':
    unittest.main()
