import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import build


class UnifiedEntryTests(unittest.TestCase):
    def source(self, source, text):
        return {'source': source, 'tasks': [{'id': 'same-id', 'category': '做产品', 'group': '同一个产品',
                'created_at': '2026-10-16T12:00:00+08:00', 'messages': [{'id': 'm1', 'text': text}]}]}

    def test_every_platform_rebuilds_same_entry_without_losing_original_text(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            contributions = root / 'data/contributions'
            contributions.mkdir(parents=True)
            codex = self.source('codex', 'Codex 原始需求 </script> & <原文>')
            codex.update(generated_at='2026-10-16T12:00:00+08:00', coverage=dict(excluded=[], system_messages=0,
                         consecutive_duplicates=0, metadata_only=[], classification_pending=0))
            (root / 'data/codex.json').write_text(json.dumps(codex))
            (root / 'data/curation.json').write_text('{"groups":{}}')
            zcode = contributions / 'zcode.json'
            zcode.write_text(json.dumps(self.source('zcode', 'ZCode 需求')))
            with patch.object(build, 'ROOT', root), contextlib.redirect_stdout(io.StringIO()):
                build.main()
                entry = root / 'index.html'
                first = entry.read_bytes()
                data = build.page_data(entry.read_text())
                self.assertEqual(data['stats']['tasks'], 2)
                self.assertEqual(data['source_counts'], {'codex': 1, 'zcode': 1})
                self.assertEqual(data['tasks'][0]['messages'][0]['text'], codex['tasks'][0]['messages'][0]['text'])
                self.assertEqual(entry.read_text().count('class="task" data-id='), 2)
                build.main()
                self.assertEqual(first, entry.read_bytes())
                zcode_bytes = zcode.read_bytes()
                (contributions / 'third.json').write_text(json.dumps(self.source('third-agent', '第三平台需求')))
                build.main()
                self.assertEqual(build.page_data(entry.read_text())['stats']['tasks'], 3)
                self.assertEqual(zcode_bytes, zcode.read_bytes())
                last_good = entry.read_bytes()
                zcode.unlink()
                with self.assertRaisesRegex(ValueError, '合并任务减少'):
                    build.main()
                self.assertEqual(last_good, entry.read_bytes())


if __name__ == '__main__':
    unittest.main()
