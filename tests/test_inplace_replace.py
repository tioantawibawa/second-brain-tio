import importlib.util
from io import BytesIO
import json
from pathlib import Path
import tarfile
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location('replace_vps', Path(__file__).resolve().parents[1] / 'deploy/replace_vps.py')
helper = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(helper)


class InPlaceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.repo = self.root / 'repo'
        self.repo.mkdir()
        self.backup = self.root / 'second-brain-backups' / 'fixture'
        self.backup.mkdir(parents=True)

    def archive(self, files):
        result = BytesIO()
        with tarfile.open(fileobj=result, mode='w') as archive:
            for name, content in files.items():
                item = tarfile.TarInfo(name)
                item.size = len(content)
                archive.addfile(item, BytesIO(content))
        return result.getvalue()

    def test_release_accepts_only_allowlisted_code(self):
        files = {'second_brain/__init__.py': b'code', 'README.md': b'docs'}
        with patch.object(helper, 'run', return_value=SimpleNamespace(stdout='\n'.join(files))), patch.object(helper.subprocess, 'check_output', return_value=self.archive(files)):
            self.assertEqual(helper.release_files(self.repo, 'source'), files)

    def test_release_rejects_data_and_traversal(self):
        for name in ('.env', '.brain/active.json', 'wiki/note.md', '../outside.py'):
            with patch.object(helper, 'run', return_value=SimpleNamespace(stdout=name)):
                with self.assertRaises(ValueError):
                    helper.release_files(self.repo, 'source')

    def test_missing_release_file_is_rejected_before_install(self):
        with patch.object(helper, 'run', return_value=SimpleNamespace(stdout='README.md\nsecond_brain/bot.py')), patch.object(helper.subprocess, 'check_output', return_value=self.archive({'README.md': b'code'})):
            with self.assertRaises(ValueError):
                helper.release_files(self.repo, 'source')
        self.assertEqual(list(self.repo.iterdir()), [])

    def test_install_backs_up_old_code_and_preserves_data(self):
        (self.repo / 'old.py').write_bytes(b'old code')
        (self.repo / '.env').write_bytes(b'private configuration')
        (self.repo / 'notes.md').write_bytes(b'user note')
        previous = helper.install_files(self.repo, {'old.py': b'new code', 'new.py': b'new file'}, self.backup)
        self.assertEqual((self.backup / 'code/old.py').read_bytes(), b'old code')
        self.assertEqual((self.repo / 'old.py').read_bytes(), b'new code')
        self.assertIsNone(previous['new.py'])
        self.assertEqual((self.repo / '.env').read_bytes(), b'private configuration')
        self.assertEqual((self.repo / 'notes.md').read_bytes(), b'user note')

    def test_rollback_preserves_new_data_and_restores_code(self):
        (self.repo / 'old.py').write_bytes(b'old code')
        helper.install_files(self.repo, {'old.py': b'new code', 'new.py': b'new module'}, self.backup)
        (self.backup / 'repo-path').write_text(str(self.repo))
        (self.backup / 'service-name').write_text('second-brain-bot')
        (self.backup / 'service-before.service').write_text('[Service]')
        (self.backup / 'was-active').write_text('1')
        (self.repo / '.brain').mkdir()
        (self.repo / '.brain/active.json').write_text('{"workspace":"new"}')
        (self.repo / '.brain/new-note.md').write_text('New note after replacement')
        with patch.object(helper, 'run', return_value=SimpleNamespace(returncode=0)):
            helper.rollback(self.repo, self.backup, 'second-brain-bot')
        self.assertEqual((self.repo / 'old.py').read_bytes(), b'old code')
        self.assertTrue((self.backup / 'active-after-replacement.json').exists())
        self.assertEqual((self.repo / '.brain/new-note.md').read_text(), 'New note after replacement')


if __name__ == '__main__':
    unittest.main()
