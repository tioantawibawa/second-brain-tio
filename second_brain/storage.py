"""Collision-safe writes and path-constrained reads of vault documents."""
from datetime import datetime
import json
from pathlib import Path
import re
from uuid import uuid4
from . import vault


def slug(text):
    return re.sub(r'[^a-z0-9]+', '-', text.casefold()).strip('-')[:65] or 'catatan'


def safe_path(root, relative):
    root = Path(root).resolve()
    path = (root / relative).resolve()
    if not path.is_relative_to(root):
        raise ValueError('Path berada di luar vault.')
    return path


def audit(root, operation, path, private=False):
    shown = 'private (details omitted)' if private else str(path).replace('|', '/').replace('\n', ' ')
    with safe_path(root, 'log.md').open('a', encoding='utf-8') as handle:
        handle.write(f'\n| {datetime.now().astimezone():%Y-%m-%d %H:%M} | {operation} | {shown} | Second Brain v2 |\n')


def save_note(root, text, title, folder='raw', kind='source', domain='work', sources=(), filename=None):
    now = datetime.now().astimezone()
    name = filename or f'{now:%Y%m%d-%H%M%S}-{slug(title)}-{uuid4().hex[:8]}.md'
    if Path(name).name != name or not name.endswith('.md'):
        raise ValueError('Invalid note filename')
    path = safe_path(root, str(Path(folder) / name))
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = dict(title=title, type=kind, domain=domain, status='seed', updated=f'{now:%Y-%m-%d}', sources=list(sources), summary='User capture' if kind == 'source' else 'Generated analysis; verify against sources', tags=['second-brain'])
    front = '\n'.join(f'{key}: {json.dumps(value, ensure_ascii=False)}' for key, value in fields.items())
    with path.open('x', encoding='utf-8', newline='\n') as handle:
        handle.write(f'---\n{front}\n---\n\n# {title}\n\n{text.rstrip()}\n')
    audit(root, kind.upper(), path.relative_to(root), domain == 'private')
    return path


def read_note(root, query, include_private=False):
    items = vault.notes(root, include_private)
    target = query.strip().removesuffix('.md')
    exact = [n for n in items if n['path'].removesuffix('.md') == target or Path(n['path']).stem == target]
    if not exact:
        normalized = target.replace('_', '-').casefold()
        exact = [n for n in items if Path(n['path']).stem.replace('_', '-').casefold() == normalized]
    if not exact:
        exact = [n for n in items if target.casefold() in n['title'].casefold() or target.casefold() in n['path'].casefold()]
    if len(exact) > 1:
        return 'Ada beberapa catatan. Gunakan path lengkap:\n' + '\n'.join(n['path'] for n in exact[:15])
    if not exact:
        return 'Catatan tidak ditemukan atau berada pada domain private. Gunakan /search atau /list.'
    note = exact[0]
    return f'{note["title"]}\n{note["path"]}\n\n{note["text"]}'


def append_index(root, folder, path, title, private=False):
    # Never leak a private capture into a shared index.
    if private:
        return
    index = safe_path(root, f'{folder}/index.md')
    index.parent.mkdir(parents=True, exist_ok=True)
    if not index.exists():
        index.write_text(f'# {folder.title()}\n\n', encoding='utf-8')
    safe_title = title.replace('|', '/').replace('[', '(').replace(']', ')').replace('\n', ' ')
    with index.open('a', encoding='utf-8') as handle:
        handle.write(f'\n- [[{path.relative_to(root).as_posix()[:-3]}|{safe_title}]]\n')
