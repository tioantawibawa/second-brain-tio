"""Verify rollback code archives exclude evolving vault data."""
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile
import unittest


class DeploymentBackupTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('bash'), 'Bash not available on this host')
    def test_code_backup_excludes_vault_root_files_and_cadences(self):
        script = Path(__file__).resolve().parents[1] / 'deploy/update_vps.sh'
        command = next(line for line in script.read_text(encoding='utf-8').splitlines() if line.startswith('tar -czf "$backup/code-before.tgz"'))
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            repo, backup = root / 'repo', root / 'backup'
            backup.mkdir()
            for name in ('second_brain/bot.py', 'README.md', 'index.md', 'log.md', 'HOME.md', 'wiki/topic.md', 'system_triggers/cadences/weekly.md', '.env', 'Untitled.base'):
                target = repo / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text('fixture', encoding='utf-8')

            def shell_path(path):
                text = path.as_posix()
                return '/' + text[0].lower() + text[2:] if len(text) > 2 and text[1] == ':' else text

            result = subprocess.run([shutil.which('bash'), '-c', 'repo="$1"; backup="$2"; ' + command, 'backup-test', shell_path(repo), shell_path(backup)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            with tarfile.open(backup / 'code-before.tgz') as archive:
                files = {name.removeprefix('./') for name in archive.getnames()}
            self.assertIn('second_brain/bot.py', files)
            self.assertIn('README.md', files)
            for name in ('index.md', 'log.md', 'HOME.md', 'wiki/topic.md', 'system_triggers/cadences/weekly.md', '.env', 'Untitled.base'):
                self.assertNotIn(name, files)


if __name__ == '__main__':
    unittest.main()
