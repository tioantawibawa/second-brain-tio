"""Persist update IDs; uncertain writes are never replayed automatically."""
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


class State:
    def __init__(self, path):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path)
        self.db.execute('CREATE TABLE IF NOT EXISTS updates (id INTEGER PRIMARY KEY, status TEXT NOT NULL, at TEXT NOT NULL)')
        self.db.execute('CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)')
        self.db.commit()

    def close(self):
        self.db.close()

    @property
    def offset(self):
        row = self.db.execute("SELECT value FROM meta WHERE key='offset'").fetchone()
        return int(row[0]) if row else 0

    def reserve(self, update_id):
        with self.db:
            cursor = self.db.execute('INSERT OR IGNORE INTO updates VALUES (?, ?, ?)',
                                     (update_id, 'processing', datetime.now(timezone.utc).isoformat()))
            self.db.execute("INSERT OR REPLACE INTO meta VALUES ('offset', ?)", (str(max(self.offset, update_id + 1)),))
        return cursor.rowcount == 1

    def finish(self, update_id, status='done'):
        if status not in ('done', 'uncertain', 'ignored'):
            raise ValueError('Invalid state')
        with self.db:
            self.db.execute('UPDATE updates SET status=? WHERE id=?', (status, update_id))

    def counts(self):
        return dict(self.db.execute('SELECT status, COUNT(*) FROM updates GROUP BY status'))
