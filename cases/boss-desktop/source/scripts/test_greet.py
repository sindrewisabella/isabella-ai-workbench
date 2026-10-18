import unittest
from collections import defaultdict
from pathlib import Path
import tempfile
from types import SimpleNamespace
from unittest.mock import patch, Mock

from macos_harness.macos import MacOS
from greet import evaluate, unique, greet_one, open_recommendations, snapshot
from read_tail import read_tail
from read_cards import inspect
from read_daily_count import read_counts


class SameHash:
    def __init__(self, name):
        self.name, self.children = name, []

    def __hash__(self):
        return 7


class Tests(unittest.TestCase):
    def card(self):
        return {'text': '期望\n厦门\n测试工程师\n优势\n' + ('测试工程师 Python Linux 自动化测试 AI工具 测试用例 ' * 4),
                'button': '打招呼', 'education': [
                    {'start': 2016, 'end': 2020, 'school': '大学', 'major': '计算机', 'degree': '本科'}]}

    def test_hash_collision_and_cycle(self):
        root, first, second = [SameHash(n) for n in ('root', 'one', 'two')]
        root.children = [first, second, first]
        second.children = [root]
        mac = object.__new__(MacOS)
        mac._copy_attributes = lambda e, keys: defaultdict(lambda: None, AXRole='AXGroup', AXTitle=e.name, AXChildren=e.children)
        mac._jsonable = lambda value: value
        mac._is_ax_element = lambda e: isinstance(e, SameHash)
        nodes = mac._snapshot_tree(root, max_depth=80, max_nodes=50, include_menu_bar=False,
                                   include_actions=False, include_settable=False)
        self.assertEqual([n['title'] for n in nodes], ['root', 'one', 'two'])

    def test_bachelor_history_does_not_require_fulltime_label(self):
        self.assertTrue(evaluate(self.card(), True, 2026)['pass'])
        self.assertTrue(evaluate(self.card(), False, 2026)['pass'])
        self.assertFalse(evaluate(self.card(), False, 2026)['fulltime_verified'])

    def test_explicit_disallowed_bachelor_history_is_rejected(self):
        for kind in ['专升本', '成人本科', '函授本科', '自考本科', '非全日制本科']:
            card = self.card()
            card['text'] += '\n' + kind
            self.assertFalse(evaluate(card, False, 2026)['pass'], kind)
        for kind in ['成人教育', '函授', '自考', '非全日制']:
            card = self.card()
            card['education'][0]['major'] += kind
            self.assertFalse(evaluate(card, False, 2026)['pass'], kind)

    def test_postal_university_is_not_open_university(self):
        card = self.card()
        for school in ['南京邮电大学', '北京邮电大学', '重庆邮电大学']:
            card['education'][0]['school'] = school
            self.assertTrue(evaluate(card, True, 2026)['pass'])
        for school in ['电大', '厦门电大', '中央广播电视大学']:
            card['education'][0]['school'] = school
            self.assertFalse(evaluate(card, True, 2026)['pass'])

    def test_future_highest_degree_and_junior_first(self):
        card = self.card()
        card['education'].append({'start': 2024, 'end': 2027, 'school': '大学', 'major': '计算机', 'degree': '硕士'})
        self.assertIn('最高学历尚未毕业', evaluate(card, True, 2026)['rejects'])
        card['education'] = [{'start': 2016, 'end': 2019, 'school': '大学', 'major': '计算机', 'degree': '大专'}] + self.card()['education']
        self.assertIn('第一学历不是本科', evaluate(card, True, 2026)['rejects'])

    def test_no_incidental_ai_or_missing_linux(self):
        card = self.card()
        card['text'] = card['text'].replace('AI工具', 'detail').replace('Linux', 'Windows')
        rejected = evaluate(card, True, 2026)['rejects']
        self.assertIn('缺少AI证据', rejected)
        self.assertNotIn('缺少Linux/Shell证据', rejected)

    def test_identity_ambiguity_fails_closed(self):
        with self.assertRaises(RuntimeError):
            unique([{'identity': 'a'}, {'identity': 'a'}], 'a')

    def test_navigation_uses_recommend_label_not_message_index(self):
        initial = {'nodes': [{'role': 'AXWindow'},
            {'role': 'AXLink', 'title': '消息', 'url': 'https://www.zhipin.com/web/client/index', 'element_index': 1},
            {'role': 'AXLink', 'title': '推荐', 'element_index': 2}]}
        ready = {'nodes': [{'role': 'AXStaticText', 'value': '测试工程师（外包） _ 厦门 12-24K'}, {'role': 'AXWebArea', 'url': 'https://www.zhipin.com/web/frame/recommend/?jobid=one'}]}
        ax = SimpleNamespace(dump=Mock(side_effect=[initial, ready]), perform=Mock())
        open_recommendations(SimpleNamespace(ax=ax))
        ax.perform.assert_called_once_with(2, 'AXPress')

    def test_snapshot_pins_actual_job_not_city(self):
        for header in ['测试工程师（外包） _ 深圳 12-24K', '运维工程师（外包） _ 厦门 13-26K']:
            mac = SimpleNamespace()
            state = {'nodes': [{'role': 'AXStaticText', 'value': header}, {'value': '筛选·18'},
                               {'role': 'AXWebArea', 'url': 'https://www.zhipin.com/web/frame/recommend/?jobid=one'}]}
            with patch('greet.read_tail', return_value=state), patch('greet.inspect', return_value={'cards': [self.card()]}):
                self.assertEqual(len(snapshot(mac)), 1)
                state['nodes'][2]['url'] = 'https://www.zhipin.com/web/frame/recommend/?jobid=other'
                with self.assertRaisesRegex(RuntimeError, '岗位变化'):
                    snapshot(mac)

    def test_platform_fallback_uses_card_education(self):
        card = self.card()
        card['outside_saved_filters'] = True
        self.assertTrue(evaluate(card, True, 2026)['pass'])
        card['education'] = []
        self.assertFalse(evaluate(card, True, 2026)['pass'])

    def test_user_ai_education_scope_ignores_city_and_role(self):
        card = self.card()
        card['text'] = card['text'].replace('厦门', '南京')
        self.assertTrue(evaluate(card, True, 2026)['pass'])
        card = self.card()
        card['text'] = card['text'].replace('期望\n厦门\n测试工程师', '期望\n厦门\n兼职·测试工程师')
        self.assertTrue(evaluate(card, True, 2026)['pass'])
        card['text'] = '期望\n南京\n研发\n优势\nAI'
        self.assertTrue(evaluate(card, True, 2026)['pass'])

    def test_uncertain_click_is_never_retried(self):
        card = {**self.card(), 'identity': 'a', 'fully_in_window': True, 'button_index': 42}
        perform = Mock()
        mac = SimpleNamespace(ax=SimpleNamespace(perform=perform))
        with tempfile.TemporaryDirectory() as folder, patch('greet.snapshot', return_value=[card]), \
                patch('greet.time.monotonic', side_effect=[0, 0, 61]), patch('greet.time.sleep'):
            audit = Path(folder) / 'audit'
            with self.assertRaisesRegex(RuntimeError, '禁止补点'):
                greet_one(mac, card, audit, True)
            perform.assert_called_once_with(42, 'AXPress')
            self.assertIn('unknown', audit.read_text())

    def test_recheck_eligibility_after_scroll(self):
        before = {**self.card(), 'identity': 'a', 'fully_in_window': False, 'button_index': 42}
        after = {**before, 'fully_in_window': True, 'button_index': 73,
                 'text': before['text'].replace('AI工具', '普通工具')}
        perform = Mock()
        mac = SimpleNamespace(ax=SimpleNamespace(perform=perform))
        with tempfile.TemporaryDirectory() as folder, patch('greet.snapshot', side_effect=[[before], [after]]):
            audit = Path(folder) / 'audit'
            with self.assertRaisesRegex(RuntimeError, '滚动后的最新卡片筛选未通过'):
                greet_one(mac, before, audit, True)
            perform.assert_called_once_with(42, 'AXScrollToVisible')
            self.assertFalse(audit.exists())

    def test_tail_preserves_older_fallback_divider(self):
        def element(title, role='AXGroup', children=()):
            e = SameHash(title)
            e.role, e.children = role, list(children)
            return e
        rows = []
        for i in range(8):
            rows.append(element('card', children=[element(str(i), 'AXImage'),
                        element(str(i), 'AXStaticText'), element('打招呼', 'AXButton')]))
        rows.insert(2, element('divider', children=[element('暂无符合牛人，为你推荐', 'AXStaticText')]))
        root = element('list', 'AXList', rows)
        originals = {0: root, **{i + 1: r for i, r in enumerate(rows)}}
        shallow = [{'element_index': 0, 'depth': 24, 'role': 'AXList'}] + [
            {'element_index': i + 1, 'depth': 25, 'role': 'AXGroup'} for i in range(len(rows))]
        mac = object.__new__(MacOS)
        mac._jsonable = lambda x: x
        mac._is_ax_element = lambda x: isinstance(x, SameHash)
        mac._actions = lambda e: ['AXPress'] if e.role == 'AXButton' else []
        mac._copy_attribute = lambda e, key: e.children if key == 'AXChildren' else None
        mac._copy_attributes = lambda e, keys: defaultdict(lambda: None, AXRole=e.role, AXTitle=e.name, AXChildren=e.children)
        def dump(*args, **kwargs):
            mac._elements = dict(originals)
            return {'nodes': shallow, 'app': 'BOSS直聘'}
        mac.ax = SimpleNamespace(dump=dump)
        cards = inspect(read_tail(mac, count=3), internal=True)['cards']
        self.assertEqual(len(cards), 3)
        self.assertTrue(all(c['outside_saved_filters'] for c in cards))
        self.assertTrue(all(mac._elements[c['button_index']].name == '打招呼' for c in cards))

    def test_last_clipped_card_loads_footer_and_rechecks_identity(self):
        before = {**self.card(), 'identity': 'a', 'fully_in_window': False, 'button_index': 42}
        visible = {**before, 'fully_in_window': True, 'button_index': 73}
        after = {**visible, 'button': '继续沟通'}
        mac = SimpleNamespace(ax=SimpleNamespace(perform=Mock()))
        footer = {'nodes': [{'role': 'AXStaticText', 'value': '滚动加载更多',
                            'element_index': 88, 'actions': ['AXScrollToVisible']}]}
        with tempfile.TemporaryDirectory() as folder, \
                patch('greet.snapshot', side_effect=[[before], [before], [before], [visible], [after]]), \
                patch('greet.read_tail', return_value=footer), patch('greet.time.sleep'):
            audit = Path(folder) / 'audit'
            greet_one(mac, before, audit, True)
            self.assertEqual([c.args for c in mac.ax.perform.call_args_list],
                             [(42, 'AXScrollToVisible'), (88, 'AXScrollToVisible'), (73, 'AXPress')])
            self.assertIn('verified_relationship', audit.read_text())

    def test_daily_count_ignores_heading_level_and_comparison(self):
        nodes = [
            {'role': 'AXWebArea', 'depth': 0, 'url': '/report/data-center'},
            {'role': 'AXStaticText', 'depth': 1, 'value': '今日数据'},
            {'role': 'AXStaticText', 'depth': 1, 'value': '全部职位'},
            {'role': 'AXGroup', 'depth': 1},
            {'role': 'AXHeading', 'depth': 2, 'title': '我打招呼', 'value': 4},
            {'role': 'AXStaticText', 'depth': 2, 'value': '16'},
            {'role': 'AXStaticText', 'depth': 2, 'value': '13'},
            {'role': 'AXStaticText', 'depth': 1, 'value': '沟通 >'},
            {'role': 'AXStaticText', 'depth': 1, 'value': '账号权益'},
            {'role': 'AXStaticText', 'depth': 1, 'value': '16'},
        ]
        state = {'nodes': [dict(n, element_index=i) for i, n in enumerate(nodes)]}
        result = read_counts(state)
        self.assertEqual(result['daily_greetings'], 16)
        self.assertEqual(result['communication_entitlements_used'], 16)


if __name__ == '__main__':
    unittest.main()
