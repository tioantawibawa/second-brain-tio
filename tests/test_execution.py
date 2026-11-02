import contextlib
import importlib.util
import io
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

TOOLS = Path(__file__).resolve().parents[1] / 'tools'
SPEC = importlib.util.spec_from_file_location('execution', TOOLS / 'execution.py')
execution = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(execution)


class ExecutionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_packet_preserves_idea_and_has_resolvable_links(self):
        idea = 'Ide pengguna\n\nButuh laporan, bukan aplikasi.'
        paths, prompt = execution.prepare(self.root, idea, 'Laporan "tim"', 'work')
        self.assertEqual(len(paths), 5)
        self.assertIn(idea, paths['brief'].read_text(encoding='utf-8'))
        for path in paths.values():
            text = path.read_text(encoding='utf-8')
            self.assertIn('review_status: pending', text)
            for other in paths.values():
                if other != path:
                    self.assertIn(other.stem, text)
        self.assertIn(str(paths['brief']), prompt)
        self.assertIn(str(self.root / '.agents/skills/second-brain-execution/SKILL.md'), prompt)

    def test_repeated_ideas_do_not_overwrite(self):
        a, _ = execution.prepare(self.root, 'Sama')
        b, _ = execution.prepare(self.root, 'Sama')
        self.assertNotEqual(a['brief'], b['brief'])
        self.assertEqual(len(list((self.root / 'wiki/work/projects').glob('*.md'))), 10)

    def test_private_does_not_leak_to_shared_audit(self):
        paths, _ = execution.prepare(self.root, 'Rahasia pribadi', domain='private')
        audit = (self.root / 'log.md').read_text(encoding='utf-8')
        self.assertNotIn('Rahasia', audit)
        self.assertNotIn(paths['brief'].name, audit)
        self.assertEqual(paths['brief'].parent, self.root / 'wiki/private/projects')

    def test_invalid_domain_and_empty_idea_write_nothing(self):
        for idea, domain in [(' ', 'work'), ('Ide', '../../escape')]:
            with self.assertRaises(ValueError):
                execution.prepare(self.root, idea, domain=domain)
        self.assertEqual(list(self.root.iterdir()), [])

    def test_cli_creates_packet_home_and_copyable_prompt(self):
        result = subprocess.run([sys.executable, str(TOOLS / 'brain.py'), '--vault', str(self.root), 'plan', 'Ide uji'], capture_output=True, text=True, encoding='utf-8')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('AI belum dijalankan', result.stdout)
        import sqlite3
        from contextlib import closing
        with closing(sqlite3.connect(self.root / 'data/workspace.sqlite')) as db:
            self.assertEqual(db.execute('SELECT state FROM plans').fetchone()[0], 'draft')
        self.assertEqual(len(list((self.root / 'wiki/work/projects').glob('*.md'))), 1)

    def test_cli_private_packet_excluded_from_home(self):
        result = subprocess.run([sys.executable, str(TOOLS / 'brain.py'), '--vault', str(self.root), 'plan', 'Jangan bocorkan ini', '--domain', 'private'], capture_output=True, text=True, encoding='utf-8')
        self.assertEqual(result.returncode, 0, result.stderr)
        home = (self.root / 'HOME.md').read_text(encoding='utf-8')
        self.assertNotIn('Jangan bocorkan', home)
        self.assertNotIn('wiki/private/projects/', home)


if __name__ == '__main__':
    unittest.main()
