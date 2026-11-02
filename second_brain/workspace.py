"""Versioned active workspaces and verified, non-destructive reset archives."""
from contextlib import contextmanager, closing, ExitStack
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
from uuid import uuid4

CONTENT = ('raw', 'inbox_raw', 'wiki', 'journal', 'crm', 'in_motion', 'lattices', 'system_triggers')
ROOT_NOTES = ('index.md', 'HOME.md', 'log.md')


def inside(root, relative):
    root = Path(root).resolve()
    path = (root / relative).resolve()
    if not path.is_relative_to(root):
        raise ValueError('Path workspace berada di luar proyek.')
    return path


def atomic_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.' + uuid4().hex + '.tmp')
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    os.replace(temporary, path)


@contextmanager
def process_lock(project, name='telegram'):
    path = inside(project, f'data/{name}.lock')
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = path.open('a+b')
    try:
        try:
            if os.name == 'nt':
                import msvcrt
                handle.seek(0)
                handle.write(b'0')
                handle.flush()
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            raise RuntimeError(f'Proses {name} masih aktif. Hentikan layanan sebelum mengganti workspace.') from None
        yield
    finally:
        handle.close()


def active_root(project):
    project = Path(project).resolve()
    pointer = inside(project, '.brain/active.json')
    if not pointer.exists():
        return project  # Existing installations remain readable until explicit reset.
    item = json.loads(pointer.read_text(encoding='utf-8'))
    identifier = item['workspace']
    if not identifier or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in identifier):
        raise ValueError('ID workspace tidak valid.')
    root = inside(project, f'.brain/workspaces/{identifier}')
    if not root.is_dir():
        raise ValueError('Workspace aktif tidak ditemukan; periksa arsip sebelum melanjutkan.')
    return root


def archives(project):
    result = []
    for path in sorted(inside(project, '.brain/archives').glob('*/manifest.json'), reverse=True):
        item = json.loads(path.read_text(encoding='utf-8'))
        result.append({'id': path.parent.name, 'created': item['created'], 'files': len(item['files'])})
    return result


def _snapshot(root, destination):
    files = []
    for folder in CONTENT:
        files.extend(path for path in (root / folder).rglob('*') if path.is_file())
    files.extend(root / name for name in ROOT_NOTES if (root / name).is_file())
    database = root / 'data/workspace.sqlite'
    checksums = {}
    for source in files:
        relative = source.relative_to(root).as_posix()
        if not source.resolve().is_relative_to(root.resolve()) or source.is_symlink():
            raise ValueError(f'Arsip tidak mengikuti symlink: {relative}')
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        before = hashlib.sha256(source.read_bytes()).hexdigest()
        if before != hashlib.sha256(target.read_bytes()).hexdigest():
            raise OSError(f'Verifikasi arsip gagal: {relative}')
        checksums[relative] = before
    if database.exists():
        target = destination / 'data/workspace.sqlite'
        target.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(database)) as original, closing(sqlite3.connect(target)) as backup:
            original.backup(backup)
        checksums['data/workspace.sqlite'] = hashlib.sha256(target.read_bytes()).hexdigest()
    return checksums


def reset(project, source=None):
    project = Path(project).resolve()
    source_project = Path(source).resolve() if source else project
    if not source_project.is_dir():
        raise ValueError('Folder sumber arsip tidak ditemukan.')
    # Also share the legacy bot lock; delivery ledger is never reset.
    with ExitStack() as locks:
        for base in dict.fromkeys((project, source_project)):
            for name in ('telegram', 'dashboard', 'workspace-reset'):
                locks.enter_context(process_lock(base, name))
        old = active_root(source_project)
        identifier = datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S-') + uuid4().hex[:6]
        archive = inside(project, f'.brain/archives/{identifier}')
        archive.mkdir(parents=True, exist_ok=False)
        files = _snapshot(old, archive / 'vault')
        atomic_json(archive / 'manifest.json', {'version': 1, 'created': datetime.now(timezone.utc).isoformat(), 'files': files, 'source': str(old)})
        fresh = inside(project, f'.brain/workspaces/{identifier}')
        fresh.mkdir(parents=True, exist_ok=False)
        for folder in CONTENT:
            (fresh / folder).mkdir()
        old_ledger = inside(source_project, 'data/telegram-state.sqlite')
        new_ledger = inside(project, 'data/telegram-state.sqlite')
        if source_project != project and old_ledger.exists() and not new_ledger.exists():
            new_ledger.parent.mkdir(parents=True, exist_ok=True)
            with closing(sqlite3.connect(old_ledger)) as original, closing(sqlite3.connect(new_ledger)) as copied:
                original.backup(copied)
        # Commit pointer only after the archive is verified and workspace exists.
        atomic_json(inside(project, '.brain/active.json'), {'workspace': identifier, 'archive': identifier, 'version': 3})
        return {'workspace': str(fresh), 'archive': str(archive), 'files': len(files), 'id': identifier}


def restore(project, identifier):
    if not identifier or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in identifier):
        raise ValueError('ID arsip tidak valid.')
    project = Path(project).resolve()
    with process_lock(project, 'telegram'), process_lock(project, 'dashboard'), process_lock(project, 'workspace-reset'):
        archive = inside(project, f'.brain/archives/{identifier}')
        manifest = json.loads((archive / 'manifest.json').read_text(encoding='utf-8'))
        restored_id = 'restored-' + uuid4().hex[:12]
        restored = inside(project, f'.brain/workspaces/{restored_id}')
        for name, expected in manifest['files'].items():
            source = inside(archive / 'vault', name)
            if hashlib.sha256(source.read_bytes()).hexdigest() != expected:
                raise ValueError(f'Arsip rusak/berubah: {name}')
        restored.mkdir(parents=True, exist_ok=False)
        for name in manifest['files']:
            target = inside(restored, name)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(inside(archive / 'vault', name), target)
        atomic_json(inside(project, '.brain/active.json'), {'workspace': restored_id, 'archive': identifier, 'version': 3})
        return restored
