"""Explicit Git sync, restricted to notes that the operator has selected."""
import subprocess


def git(root, *args):
    result = subprocess.run(['git', *args], cwd=root, capture_output=True, text=True, timeout=60)
    if result.returncode:
        raise RuntimeError(f'Git {args[0]} failed (exit {result.returncode}). Inspect the VPS terminal.')
    return result.stdout.strip()


def sync(settings, push=False):
    status = git(settings.root, 'status', '--short')
    if not push:
        return 'Git status (tidak ada file yang di-stage/commit/push):\n' + (status or 'Working tree bersih.')
    if settings.env.get('SECOND_BRAIN_ALLOW_GIT_SYNC') != '1':
        return 'Push belum diaktifkan. Review perubahan di terminal, stage/commit yang dipilih, lalu push manual; atau aktifkan SECOND_BRAIN_ALLOW_GIT_SYNC=1 untuk /sync push.'
    if status:
        return 'Working tree belum bersih. Review dan commit perubahan yang dipilih melalui terminal sebelum push. Bot tidak menjalankan git add . atau commit otomatis.'
    git(settings.root, 'push', 'origin', 'HEAD')
    return 'git push origin HEAD berhasil. Tidak ada file tambahan yang di-stage oleh bot.'
