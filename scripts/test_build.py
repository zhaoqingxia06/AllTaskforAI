import unittest
from build import normalize


class ContributionTests(unittest.TestCase):
    def task(self, **changes):
        value = dict(id='same-id', category='做产品', group='测试', created_at='2026-10-16T12:00:00+08:00',
                     messages=[dict(id='m1', text='第一条需求'), dict(id='m2', text='补充')])
        return dict(value, **changes)

    def test_source_namespacing_prevents_cross_platform_collision(self):
        ids = set()
        self.assertEqual(normalize(self.task(), 'zcode', ids)['id'], 'zcode:same-id')
        self.assertEqual(normalize(self.task(), 'another-platform', ids)['id'], 'another-platform:same-id')
        with self.assertRaisesRegex(ValueError, '任务ID冲突'):
            normalize(self.task(), 'zcode', ids)

    def test_nonconsecutive_requests_survive(self):
        task = self.task(messages=[dict(text=t) for t in ['A', 'A', 'B', 'A']])
        result = normalize(task, 'zcode', set())
        self.assertEqual([m['text'] for m in result['messages']], ['A', 'B', 'A'])
        self.assertEqual(result['children'], 2)

    def test_timezone_is_required(self):
        with self.assertRaisesRegex(ValueError, '时区'):
            normalize(self.task(created_at='2026-10-16T12:00:00'), 'zcode', set())

    def test_only_allowed_fields_are_exported(self):
        result = normalize(self.task(index_title='private transport context', ignored='ignored'), 'zcode', set())
        self.assertNotIn('index_title', result)
        self.assertNotIn('ignored', result)
        self.assertEqual(result['children'], 1)


if __name__ == '__main__':
    unittest.main()
