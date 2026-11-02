#!/usr/bin/env python3
"""Replace allowlisted code in-place, preserving Git history and private data."""
import argparse
from contextlib import ExitStack
from datetime import datetime, timezone
import hashlib
from io import BytesIO
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import sys
import tarfile

ORIGINS = {'https://github.com/tioantawibawa/second-brain-tio', 'https://github.com/tioantawibawa/second-brain-tio.git', 'git@github.com:tioantawibawa/second-brain-tio.git'}
DATA = ('.brain', 'data', 'raw', 'inbox_raw', 'wiki', 'journal', 'crm', 'in_motion', 'lattices', 'system_triggers', '.obsidian')


def run(args, cwd, check=True):
    result = subprocess.run(args, cwd=cwd, text=True, capture_output=True)
    if check and result.returncode:
        raise RuntimeError(f'{args[0]} {args[1] if len(args)>1 else ""} failed (exit {result.returncode}). Check the VPS terminal configuration.')
    return result


def safe(root, name):
    path = (root / name).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError('Path escapes repository: ' + name)
    return path


def release_files(repo, revision):
    listing = run(['git', 'show', revision + ':deploy/code-files.txt'], repo).stdout
    names = [line.strip() for line in listing.splitlines() if line.strip() and not line.startswith('#')]
    for name in names:
        parts = PurePosixPath(name).parts
        if '\\' in name or PurePosixPath(name).is_absolute() or '..' in parts or not parts or parts[0] in (*DATA, '.git', '.env', 'log.md', 'HOME.md', 'index.md'):
            raise ValueError('Unsafe code allowlist entry: ' + name)
        safe(repo, name)
        if any((repo / Path(*parts[:i])).is_symlink() for i in range(1, len(parts) + 1)):
            raise ValueError('Code destination may not use symlinks: ' + name)
    if not names or len(names) > 1000:
        raise ValueError('Invalid code allowlist')
    data = subprocess.check_output(['git', 'archive', '--format=tar', revision, '--', *names], cwd=repo)
    files = {}
    with tarfile.open(fileobj=BytesIO(data)) as archive:
        for member in archive.getmembers():
            if member.isdir():
                continue
            if not member.isfile() or member.name not in names:
                raise ValueError('Unexpected release member: ' + member.name)
            files[member.name] = archive.extractfile(member).read()
    if set(files) != set(names):
        raise ValueError('Incomplete release archive')
    return files


def install_files(repo, files, backup):
    previous = {}
    for name in files:
        path = safe(repo, name)
        if path.exists() and not path.is_file():
            raise ValueError('Code destination is not a regular file: ' + name)
        previous[name] = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None
        if path.is_file():
            saved = backup / 'code' / name
            saved.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, saved)
    (backup / 'code-manifest.json').write_text(json.dumps(previous, indent=2), encoding='utf-8')
    for name, content in files.items():
        path = safe(repo, name)
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(path.name + '.replace-tmp')
        temporary.write_bytes(content)
        os.replace(temporary, path)
    return previous


def rollback(repo, backup, service):
    backup = backup.resolve()
    expected = repo.parent / 'second-brain-backups'
    if not backup.is_relative_to(expected.resolve()) or (backup / 'repo-path').read_text().strip() != str(repo):
        raise ValueError('Backup does not belong to this repository')
    if (backup / 'service-name').read_text().strip() != service:
        raise ValueError('Service does not match backup')
    previous = json.loads((backup / 'code-manifest.json').read_text())
    for name, checksum in previous.items():
        safe(repo, name)
        if checksum and hashlib.sha256(safe(backup / 'code', name).read_bytes()).hexdigest() != checksum:
            raise ValueError('Backup checksum mismatch: ' + name)
    run(['sudo', 'systemctl', 'stop', service], repo)
    for name, checksum in previous.items():
        if checksum:
            shutil.copy2(safe(backup / 'code', name), safe(repo, name))
    pointer = repo / '.brain/active.json'
    if (backup / 'active-before.json').is_file():
        shutil.copy2(backup / 'active-before.json', pointer)
    elif pointer.exists():
        # Keep the failed/new pointer recoverable instead of deleting it.
        pointer.rename(backup / 'active-after-replacement.json')
    run(['sudo', 'install', '-m', '644', str(backup / 'service-before.service'), f'/etc/systemd/system/{service}.service'], repo)
    run(['sudo', 'systemctl', 'daemon-reload'], repo)
    if (backup / 'was-active').read_text().strip() == '1':
        run(['sudo', 'systemctl', 'start', service], repo)
    print('Previous code/unit/workspace pointer restored. All archive/workspace directories retained. Git history unchanged.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, required=True)
    parser.add_argument('--service', default='second-brain-bot')
    parser.add_argument('--reset-workspace', action='store_true')
    parser.add_argument('--rollback', type=Path)
    args = parser.parse_args()
    repo = args.repo.resolve()
    service = args.service
    if os.name != 'posix' or not service or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-' for c in service):
        parser.error('Run on the Linux VPS with a valid service name.')
    if sys.version_info < (3, 10):
        parser.error('Python 3.10+ is required.')
    if any(c in str(repo) for c in ('\n', '\r', '%', ' ')):
        parser.error('Service requires a repository path without spaces, percent signs, or newlines.')
    if os.geteuid() == 0:
        parser.error('Run as the checkout owner (ubuntu), not sudo python; sudo is requested only for systemd.')
    if run(['git', 'rev-parse', '--show-toplevel'], repo).stdout.strip() != str(repo):
        parser.error('Use the repository root.')
    if args.rollback:
        subprocess.run(['sudo', '-v'], cwd=repo, check=True)
        return rollback(repo, args.rollback, service)
    if run(['git', 'remote', 'get-url', 'origin'], repo).stdout.strip() not in ORIGINS:
        parser.error('Unexpected Git origin.')
    if not (repo / '.env').is_file():
        parser.error('Missing .env. Configure it on VPS before replacement.')
    other = 'secondbrain-telegram' if service != 'secondbrain-telegram' else 'second-brain-bot'
    if run(['systemctl', 'is-active', '--quiet', other], repo, False).returncode == 0:
        parser.error('Another bot unit is active; stop the duplicate before replacement.')
    print('1/5 Fetching source code from origin/main...', flush=True)
    run(['git', 'fetch', 'origin', 'main'], repo)
    revision = run(['git', 'rev-parse', 'origin/main'], repo).stdout.strip()
    files = release_files(repo, revision)
    python = repo / '.venv/bin/python'
    # Preflight venv before stopping the existing service.
    run([sys.executable, '-m', 'venv', str(repo / '.venv')], repo)
    subprocess.run(['sudo', '-v'], cwd=repo, check=True)
    unit = run(['systemctl', 'cat', service], repo).stdout
    backup = repo.parent / 'second-brain-backups' / ('inplace-' + datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S-%f'))
    backup.mkdir(parents=True, mode=0o700)
    (backup / 'repo-path').write_text(str(repo))
    (backup / 'service-name').write_text(service)
    (backup / 'service-before.service').write_text(unit)
    active = run(['systemctl', 'is-active', '--quiet', service], repo, False).returncode == 0
    (backup / 'was-active').write_text('1' if active else '0')
    (backup / 'git-head-before').write_text(run(['git', 'rev-parse', 'HEAD'], repo).stdout)
    print('Source commit:', revision, '\nBackup:', backup, flush=True)
    print('2/5 Stopping service and backing up code/data...', flush=True)
    run(['sudo', 'systemctl', 'stop', service], repo)
    try:
        import fcntl
        with ExitStack() as locks:
            for name in ('telegram', 'dashboard', 'workspace-reset'):
                path = safe(repo, 'data/' + name + '.lock')
                path.parent.mkdir(parents=True, exist_ok=True)
                handle = locks.enter_context(path.open('a+b'))
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            with tarfile.open(backup / 'data-before.tgz', 'w:gz', dereference=False) as archive:
                for name in (*DATA, '.env', 'log.md', 'index.md', 'HOME.md'):
                    path = repo / name
                    if path.exists():
                        archive.add(path, arcname=name, recursive=True)
            shutil.copy2(repo / '.env', backup / 'env-before')
            pointer = repo / '.brain/active.json'
            if pointer.is_file():
                shutil.copy2(pointer, backup / 'active-before.json')
            print('3/5 Replacing allowlisted code in the existing folder...', flush=True)
            install_files(repo, files, backup)
        # Locks are released for the reset command, which acquires them itself.
        print('4/5 Running tests and checking configuration...', flush=True)
        result = run([str(python), '-m', 'unittest', 'discover', '-s', 'tests', '-p', 'test_*.py', '-v'], repo)
        print(result.stderr or result.stdout, flush=True)
        run([str(python), '-m', 'second_brain', 'bot', '--check'], repo)
        if args.reset_workspace:
            print(run([str(python), '-m', 'second_brain', 'reset', '--archive'], repo).stdout)
        if (repo / '.env').read_bytes() != (backup / 'env-before').read_bytes():
            raise ValueError('.env changed unexpectedly. Inspect the backup before restarting.')
        print('5/5 Installing the unit and restarting the bot...', flush=True)
        template = (repo / 'deploy/secondbrain-telegram.service.in').read_text()
        import pwd
        unit = template.replace('@REPO_DIR@', str(repo)).replace('@RUN_USER@', pwd.getpwuid(os.getuid()).pw_name)
        (backup / 'service-new.service').write_text(unit)
        run(['sudo', 'install', '-m', '644', str(backup / 'service-new.service'), f'/etc/systemd/system/{service}.service'], repo)
        run(['sudo', 'systemctl', 'daemon-reload'], repo)
        run(['sudo', 'systemctl', 'restart', service], repo)
        run(['systemctl', 'is-active', '--quiet', service], repo)
        marker = repo / '.brain/release.json'
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text(json.dumps({'source_commit': revision, 'backup': str(backup), 'git_history_changed': False}, indent=2))
        print('Code replaced in the SAME folder. Service active. Verify /start in Telegram.')
        print('Git HEAD/history preserved; use this helper for future in-place replacements, not git pull.')
        print('Installed source commit:', revision)
    except Exception:
        print('Replacement stopped. Service may be stopped; inspect the error. Backup retained:', backup, file=sys.stderr)
        if (backup / 'code-manifest.json').is_file():
            print(f'Rollback: python3 {repo}/deploy/replace_vps.py --repo {repo} --service {service} --rollback {backup}', file=sys.stderr)
        else:
            print(f'Code replacement has not started. Resolve the backup/lock issue, then start the original service: sudo systemctl start {service}', file=sys.stderr)
        raise


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, RuntimeError, subprocess.SubprocessError) as error:
        print('Failed:', error, file=sys.stderr)
        raise SystemExit(1)
