import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

HERE = Path(__file__).parent
spec = importlib.util.spec_from_file_location('archive', HERE/'archive.py')
a = importlib.util.module_from_spec(spec)
spec.loader.exec_module(a)
spec = importlib.util.spec_from_file_location('import_history', HERE/'import_history.py')
i = importlib.util.module_from_spec(spec)
spec.loader.exec_module(i)


class ArchiveTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.site = Path(self.temp.name)/'site'
        a.init(self.site)
        self.doc = {'schema_version':2,'source':'sample','client':'desktop','coverage':{'scope':'合成测试数据'},
            'conversations':[{'id':'c','messages':[
                {'id':'1','text':'修复引用块退出问题 </script><script>bad()</script>','sent_at':'2026-10-15T12:00:00+08:00'},
                {'id':'2','text':'还是无法退出引用块','sent_at':'2026-10-16T12:00:00+08:00'},
                {'id':'3','text':'好的','sent_at':'2026-10-17T12:00:00+08:00'},
                {'id':'4','text':'保存目录对全部聊天生效','sent_at':None}]}]}
        a.write(self.site/'data/contributions/sample.json',self.doc)
        refs = [a.key('sample','c',str(n)) for n in (1,2,4)]
        self.catalog={'schema_version':2,'categories':[{'id':'writing','name':'写作协作'}],
            'projects':[{'id':'notes','name':'示例笔记','category_id':'writing','description':'在对话中摘录并编辑笔记。'}],
            'requirements':[{'id':'quote','project_id':'notes','summary':'修复引用块无法退出到正文的问题','message_refs':refs[:2]},
                            {'id':'folder','project_id':'notes','summary':'所有聊天共用保存目录','message_refs':refs[2:]}],
            'excluded_messages':[{'ref':a.key('sample','c','3'),'reason':'纯执行确认'}]}
        self.save_catalog()

    def save_catalog(self):
        messages,_=a.load_messages(self.site)
        for r in self.catalog['requirements']:
            r['evidence_sha256']=a.fingerprint(r['message_refs'],messages)
        a.write(self.site/'data/catalog.json',self.catalog)

    def test_semantic_groups_and_time_span_exclude_confirmation(self):
        data=a.compile_site(self.site)
        self.assertEqual(data['stats']['requirements'],2)
        self.assertEqual(data['stats']['messages'],3)
        self.assertEqual(data['projects'][0]['last_at'],'2026-10-16T12:00:00+08:00')
        html=a.render(data)
        self.assertIn('写作协作',html)
        self.assertIn('时间未知',html)
        self.assertIn('&lt;/script&gt;',html)
        self.assertNotIn('<script>bad()',html)
        self.assertNotIn('好的',html)
        self.assertEqual(data['messages'][a.key('sample','c','4')]['sent_at'],None)

    def test_changed_source_requires_semantic_review(self):
        self.doc['conversations'][0]['messages'][0]['text']='新的需求方向'
        a.write(self.site/'data/contributions/sample.json',self.doc)
        with self.assertRaisesRegex(ValueError,'证据指纹'):
            a.compile_site(self.site)

    def test_cross_client_same_message_deduplicated(self):
        doc=copy.deepcopy(self.doc);doc['client']='web'
        a.write(self.site/'data/contributions/sample-web.json',doc)
        data=a.compile_site(self.site)
        self.assertEqual(data['stats']['messages'],3)
        self.assertEqual(data['messages'][a.key('sample','c','1')]['clients'],['desktop','web'])

    def test_unknown_reference_rejected(self):
        self.catalog['requirements'][0]['message_refs'].append('missing')
        a.write(self.site/'data/catalog.json',self.catalog)
        with self.assertRaisesRegex(ValueError,'引用'):
            a.compile_site(self.site)

    def test_original_loss_cannot_silently_publish(self):
        a.write(self.site/'tasks.json',a.compile_site(self.site))
        self.catalog['requirements'].pop()
        self.save_catalog()
        with self.assertRaisesRegex(ValueError,'原文缺少去向'):
            a.compile_site(self.site)

    def test_secret_in_public_evidence_rejected(self):
        self.doc['conversations'][0]['messages'][0]['text']='token ghp_'+'A'*30
        a.write(self.site/'data/contributions/sample.json',self.doc);self.save_catalog()
        with self.assertRaisesRegex(ValueError,'凭据'):
            a.compile_site(self.site)

    def test_duplicate_message_keeps_each_time_but_renders_text_once(self):
        m=copy.deepcopy(self.doc['conversations'][0]['messages'][0]);m['id']='5';m['sent_at']='2026-10-16T15:00:00+08:00'
        self.doc['conversations'][0]['messages'].append(m)
        a.write(self.site/'data/contributions/sample.json',self.doc)
        self.catalog['requirements'][0]['message_refs'].append(a.key('sample','c','5'));self.save_catalog()
        data=a.compile_site(self.site)
        page=a.render(data)
        self.assertEqual(page.count('<pre>修复引用块'),1)
        self.assertEqual(data['stats']['messages'],4)

    def test_chatgpt_export_keeps_user_only_and_unknown_times(self):
        path=Path(self.temp.name)/'export.json'
        a.write(path,[{'id':'c','mapping':{'u':{'message':{'id':'m','author':{'role':'user'},'content':{'parts':['需求']}}},
                                        'a':{'message':{'author':{'role':'assistant'},'content':{'parts':['回复']}}}}}])
        conv=i.chatgpt(path)[0]
        self.assertEqual(len(conv['messages']),1)
        self.assertIsNone(conv['messages'][0]['sent_at'])
        self.assertEqual(len(i.merge([conv],[conv])[0]['messages']),1)

    def test_codex_standard_user_messages_only(self):
        path=Path(self.temp.name)/'session.jsonl'
        records=[{'type':'session_meta','payload':{'id':'codex-c'}},
                 {'type':'response_item','timestamp':'2026-10-16T10:00:00Z','payload':{'type':'message','role':'user','content':[{'type':'input_text','text':'做个工具'}]}},
                 {'type':'response_item','payload':{'type':'message','role':'assistant','content':[{'text':'收到'}]}}]
        path.write_text('\n'.join(json.dumps(r) for r in records))
        self.assertEqual(len(i.codex(path)[0]['messages']),1)


if __name__=='__main__':
    unittest.main()
