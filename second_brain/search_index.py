"""Fresh local full-text index with a dependency-free ranking fallback."""
import hashlib
from contextlib import closing
import re
import sqlite3
from .storage import safe_path
from .vault import notes

STOP = {'apa', 'yang', 'dan', 'di', 'ke', 'dari', 'saya', 'aku', 'untuk', 'bagaimana', 'the', 'is', 'of', 'a', 'an'}


def search(root, query, limit=10, category=None):
    terms = [t for t in re.findall(r'\w+', query.casefold()) if t not in STOP]
    if not terms:
        return []
    items = notes(root, False)
    if category:
        prefixes = {'inbox': ('inbox_raw/', 'raw/'), 'knowledge': ('wiki/', 'lattices/'), 'projects': ('in_motion/',)}
        if category not in prefixes:
            raise ValueError('Kategori tidak dikenal.')
        items = [n for n in items if n['path'].startswith(prefixes[category])]
    path = safe_path(root, 'data/search-v3.sqlite')
    path.parent.mkdir(parents=True, exist_ok=True)
    ranked = None
    with closing(sqlite3.connect(path)) as db, db:
        try:
            db.execute('CREATE VIRTUAL TABLE IF NOT EXISTS documents USING fts5(path UNINDEXED, title, body, digest UNINDEXED)')
            old = dict(db.execute('SELECT path,digest FROM documents'))
            current = {n['path']: n for n in items}
            for previous in set(old) - set(current):
                db.execute('DELETE FROM documents WHERE path=?', (previous,))
            for note in items:
                digest = hashlib.sha256(note['text'].encode()).hexdigest()
                if old.get(note['path']) != digest:
                    db.execute('DELETE FROM documents WHERE path=?', (note['path'],))
                    db.execute('INSERT INTO documents VALUES (?,?,?,?)', (note['path'], note['title'], note['body'], digest))
            expression = ' OR '.join('"' + t.replace('"', '""') + '"' for t in terms)
            rows = db.execute('SELECT path FROM documents WHERE documents MATCH ? ORDER BY bm25(documents,0,5,1,0) LIMIT ?', (expression, limit)).fetchall()
            ranked = [current[row[0]] for row in rows]
        except sqlite3.OperationalError:
            ranked = None
    if ranked is None:
        candidates = [(sum(n['text'].casefold().count(t) + 4 * n['title'].casefold().count(t) for t in terms), n) for n in items]
        ranked = [n for score, n in sorted(candidates, key=lambda pair: (-pair[0], pair[1]['path'])) if score][:limit]
    results = []
    for note in ranked:
        lines = note['text'].splitlines()
        line = next((i for i, value in enumerate(lines, 1) if any(t in value.casefold() for t in terms)), 1)
        results.append({'path': note['path'], 'title': note['title'], 'line': line, 'excerpt': lines[line - 1][:220]})
    return results
