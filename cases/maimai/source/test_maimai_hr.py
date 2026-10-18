import copy
import datetime as dt
import unittest
from unittest.mock import patch
import maimai_hr as m


class ApprovalTests(unittest.TestCase):
    def setUp(self):
        self.cfg = {'job_id': '1', 'job_title': '测试岗位'}
        c = {'uid': '123', 'name': '测试人选', 'text': '负责 SEO，上线 Python 自动化，转化提升 10%',
             'contact_button': '立即沟通'}
        c['evidence_hash'] = m.digest({k: c[k] for k in ['uid', 'name', 'text']})
        self.a = {'approved': True, 'approved_by': '测试批准人', 'job_id': '1', 'job_title': '测试岗位',
                  'expires_at': (dt.datetime.now(dt.timezone.utc)+dt.timedelta(hours=1)).isoformat(),
                  'max_messages': 1, 'max_units': 1,
                  'items': [{'candidate': c, 'message': '这是一条测试消息。',
                             'preflight': {'candidate_uid': '123', 'candidate_name': '测试人选', 'auto_resume': False}}]}

    def verify(self, a=None, cfg=None, token=None):
        a = a or self.a
        return m.validate_approval(a, cfg or self.cfg, token or m.digest(a))

    def test_concrete_approved_batch(self):
        self.assertEqual(self.verify()[0]['candidate']['uid'], '123')

    def test_unapproved_never_sends(self):
        self.a['approved'] = False
        with self.assertRaisesRegex(ValueError, '未明确批准'): self.verify()

    def test_message_changed_after_confirmation(self):
        old = m.digest(self.a)
        self.a['items'][0]['message'] = '正文已经变更'
        with self.assertRaisesRegex(ValueError, '指纹'): self.verify(token=old)

    def test_wrong_job(self):
        with self.assertRaisesRegex(ValueError, '岗位'): self.verify(cfg={'job_id': '2', 'job_title': '另一岗位'})

    def test_duplicate_person(self):
        self.a['items'].append(copy.deepcopy(self.a['items'][0]))
        self.a['max_messages'] = self.a['max_units'] = 2
        with self.assertRaisesRegex(ValueError, '重复'): self.verify()

    def test_credit_budget(self):
        self.a['max_units'] = 0
        with self.assertRaisesRegex(ValueError, '额度'): self.verify()

    def test_unknown_resume_request_switch(self):
        self.a['items'][0]['preflight']['auto_resume'] = None
        with self.assertRaisesRegex(ValueError, '索要'): self.verify()

    def test_profile_tampering(self):
        self.a['items'][0]['candidate']['text'] += '伪造的经历'
        with self.assertRaisesRegex(ValueError, '原文'): self.verify()

    def test_expired_approval(self):
        self.a['expires_at'] = '2020-01-01T00:00:00+00:00'
        with self.assertRaisesRegex(ValueError, '过期'): self.verify()

    def test_matching_keywords_remain_unknown(self):
        c = self.a['items'][0]['candidate']
        p = {'requirements': [{'id': 'growth', 'description': '增长经验', 'recall_terms': ['SEO']}]}
        r = m.screen({'cards': [c]}, p)['reviews'][0]
        self.assertTrue(r['requirements'][0]['recall_fragments'])
        self.assertEqual(r['requirements'][0]['decision'], 'unknown')
        self.assertFalse(r['can_greet'])

    def test_missing_evidence_rejects_pass(self):
        c = self.a['items'][0]['candidate']
        p = {'confirmed': True, 'requirements': [{'id': 'g', 'description': '增长', 'recall_terms': ['SEO']}]}
        reviews = {'policy_hash': m.digest(p), 'reviews': [{'uid': '123', 'decision': 'pass',
                   'evidence_hash': c['evidence_hash'], 'reviewer': '测试审阅者', 'history_checked': True,
                   'history_evidence': '测试历史记录', 'requirements': [{'requirement_id': 'g',
                   'decision': 'pass', 'evidence_quote': '不存在的证据', 'reason': 'test'}]}]}
        with self.assertRaisesRegex(ValueError, '原文证据'):
            m.prepare({'cards': [c]}, reviews, p, [], self.cfg)


if __name__ == '__main__': unittest.main()
