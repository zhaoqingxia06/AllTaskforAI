import unittest
from renderer import message_button, message_summary


class SummaryTests(unittest.TestCase):
    def test_long_request_is_one_compact_sentence(self):
        text = '请你优化侧边文档的保存体验，记住用户选择的目录。后续会话无需重复选择。'
        self.assertEqual(message_summary(text), '优化侧边文档的保存体验，记住用户选择的目录')
        self.assertLessEqual(len(message_summary('需要改善' * 100)), 64)

    def test_curated_summary_does_not_replace_original(self):
        original = '<原始需求>\n完整的第二行。'
        message = {'id': 'm1', 'text': original, 'time': '2026-10-16T12:00:00+08:00', 'repeat': 1}
        markup = message_button({'id': 't1'}, message, 1, {'t1': {'m1': '优化保存体验'}})
        self.assertIn('优化保存体验', markup)
        self.assertNotIn('完整的第二行', markup)
        self.assertEqual(message['text'], original)


if __name__ == '__main__':
    unittest.main()
