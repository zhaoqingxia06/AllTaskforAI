import copy
import unittest
from build import messages_digest, summarize_task


class WholeTaskSummaryTests(unittest.TestCase):
    def task(self):
        return {'id': 'wardrobe', 'title': '有什么 Skill 推荐吗', 'group': '衣柜设计工具',
                'messages': [{'text': '有什么 Skill 推荐吗'}, {'text': '开发尺寸与分段功能'},
                             {'text': '修复设置面板滚动影响预览的问题'}]}

    def test_whole_conversation_title_preserves_source(self):
        task = self.task()
        source = copy.deepcopy(task)
        title = '开发衣柜尺寸与分段功能，并修复设置面板与预览的滚动联动'
        summary = {'wardrobe': {'text': title, 'messages_sha256': messages_digest(task)}}
        result = summarize_task(task, summary)
        self.assertEqual(result['title'], title)
        self.assertEqual(result['source_title'], source['title'])
        self.assertEqual(result['messages'], source['messages'])
        self.assertFalse(result['summary_needs_review'])

    def test_new_child_invalidates_old_summary_and_uses_all_messages(self):
        task = self.task()
        summary = {'wardrobe': {'text': '旧总结', 'messages_sha256': messages_digest(task)}}
        task['messages'].append({'text': '部署到 GitHub 并交付安装包'})
        result = summarize_task(task, summary)
        self.assertTrue(result['summary_needs_review'])
        self.assertNotEqual(result['title'], '旧总结')
        self.assertIn('功能开发', result['title'])
        self.assertIn('问题排查与修复', result['title'])
        self.assertIn('部署与交付', result['title'])


if __name__ == '__main__':
    unittest.main()
