import json
from pathlib import Path
import unittest
import build


class OrganizedArchiveTests(unittest.TestCase):
    def setUp(self):
        self.root=Path(__file__).resolve().parents[1]
        self.data=build.page_data((self.root/'index.html').read_text())

    def test_v2_groups_requirements_and_preserves_source_kind(self):
        self.assertEqual(self.data['schema_version'],2)
        self.assertEqual(len({r['id'] for r in self.data['requirements']}),len(self.data['requirements']))
        for r in self.data['requirements']:
            self.assertTrue(r['summary'])
            for ref in r['message_refs']:self.assertIn(ref,self.data['messages'])
        legacy=[m for m in self.data['messages'].values() if m.get('record_kind')=='legacy_summary']
        self.assertTrue(legacy)
        self.assertTrue(all(m['sent_at'] is None for m in legacy))

    def test_independent_chatnote_demands_are_split(self):
        projects={p['id']:p for p in self.data['projects']}
        reqs=[r for r in self.data['requirements'] if projects[r['project_id']]['name']=='ChatNote']
        self.assertTrue(any('保存目录' in r['summary'] for r in reqs))
        self.assertTrue(any('局部摘录' in r['summary'] for r in reqs))
        self.assertTrue(any('会话列表' in r['summary'] for r in reqs))

    def test_project_time_is_based_on_evidence(self):
        for project in self.data['projects']:
            vals=[self.data['messages'][ref]['sent_at'] for r in self.data['requirements'] if r['project_id']==project['id'] for ref in r['message_refs']]
            self.assertEqual(project['first_at'] is None,not any(vals))
            if project['first_at']:self.assertIn(project['first_at'],vals)
            if project['last_at']:self.assertIn(project['last_at'],vals)


if __name__=='__main__':unittest.main()
