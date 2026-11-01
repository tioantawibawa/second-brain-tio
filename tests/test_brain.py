import contextlib
import importlib.util
import io
from pathlib import Path
import tempfile
import unittest

SPEC = importlib.util.spec_from_file_location('brain', Path(__file__).resolve().parents[1] / 'tools/brain.py')
brain = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(brain)


class BrainTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def write(self, path, content):
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding='utf-8')
        return target

    def test_capture_preserves_user_text_and_no_collision(self):
        text = 'Ide asli\n\n- [ ] Uji data'
        a = brain.capture(self.root, text, '../Judul: "A"')
        b = brain.capture(self.root, text, '../Judul: "A"')
        self.assertNotEqual(a, b)
        self.assertEqual(a.parent, self.root / 'inbox_raw')
        self.assertTrue(a.read_text(encoding='utf-8').endswith(text + '\n'))
        self.assertIn('CAPTURE', (self.root / 'log.md').read_text())
        meta, _ = brain.metadata(a.read_text(encoding='utf-8'))
        self.assertEqual(meta['title'], '../Judul: "A"')

    def test_empty_capture_writes_nothing(self):
        with self.assertRaises(ValueError):
            brain.capture(self.root, '  \n')
        self.assertFalse((self.root / 'inbox_raw').exists())

    def test_active_only_excludes_deployed_and_missing_status(self):
        for name, status in [('a', 'active'), ('b', 'deployed'), ('c', '')]:
            self.write(f'in_motion/{name}.md', f'---\nstatus: {status}\n---\n- [ ] task\n')
        self.write('wiki/work/projects/p.md', '---\nstatus: active\n---\n- [ ] project\n')
        _, streams, pending, _ = brain.snapshot(self.root)
        self.assertEqual(len(streams), 2)
        self.assertEqual(len(pending), 2)

    def test_tasks_skip_code_and_preserve_source_line(self):
        note = {'text': '---\nstatus: active\n---\n# Title\n- [ ] real\n```md\n- [ ] example\n```\n~~~\n- [ ] example2\n~~~\n- [x] done\n'}
        self.assertEqual(list(brain.tasks(note)), [(5, 'real')])

    def test_private_filtered_by_path_and_metadata(self):
        self.write('wiki/private/p.md', '# Secret token')
        self.write('journal/p.md', '---\ndomain: private\n---\n# Secret')
        self.write('wiki/visible.md', '# Secret research')
        self.assertEqual(len(brain.search(self.root, 'secret')), 1)
        self.assertEqual(len(brain.search(self.root, 'secret', True)), 3)
        home = brain.home(self.root).read_text(encoding='utf-8')
        self.assertNotIn('wiki/private', home)
        self.assertNotIn('journal/p', home)

    def test_search_reads_fresh_files_and_exact_lines(self):
        path = self.write('wiki/n.md', '# Model\nScoring drift naik\n')
        result = brain.search(self.root, 'SCORING drift')[0]
        self.assertEqual(result['line'], 2)
        path.write_text('# Model\nData berubah', encoding='utf-8')
        self.assertEqual(brain.search(self.root, 'drift'), [])
        self.assertEqual(brain.search(self.root, '!!!'), [])

    def test_search_requires_all_terms(self):
        self.write('wiki/n.md', '# scoring')
        self.assertEqual(brain.search(self.root, 'scoring drift'), [])

    def test_home_preserves_user_authored_file(self):
        path = self.write('HOME.md', '# My notes')
        with self.assertRaises(ValueError):
            brain.home(self.root)
        self.assertEqual(path.read_text(), '# My notes')

    def test_home_refreshes_only_its_generated_file(self):
        path = brain.home(self.root)
        self.write('in_motion/p.md', '---\nstatus: active\n---\n# Proyek\n- [ ] Kerjakan\n')
        brain.home(self.root)
        content = path.read_text(encoding='utf-8')
        self.assertIn('1 proyek aktif', content)
        self.assertIn('Kerjakan', content)
        self.assertNotIn('- [ ] Kerjakan', content)

    def test_archive_not_counted_in_inbox(self):
        self.write('inbox_raw/new.md', '# New')
        self.write('inbox_raw/processed/old.md', '# Old')
        self.assertEqual(len(brain.snapshot(self.root)[3]), 1)

    def test_doctor_no_secrets_and_no_write(self):
        self.write('.env', 'SECRET=hidden')
        before = list(self.root.rglob('*'))
        with contextlib.redirect_stdout(io.StringIO()) as output:
            brain.doctor(self.root)
        self.assertNotIn('hidden', output.getvalue())
        self.assertEqual(before, list(self.root.rglob('*')))

    def test_invalid_cli_capture_rejected(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            brain.main(['--vault', str(self.root), 'capture', 'text', '--file', 'also.txt'])


if __name__ == '__main__':
    unittest.main()
