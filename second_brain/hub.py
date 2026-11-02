"""Durable tasks, plans, and short-lived conversational sessions."""
from contextlib import contextmanager
from datetime import datetime, timezone
import json
import sqlite3
import time
from uuid import uuid4
from .storage import safe_path


class Hub:
    def __init__(self, root):
        self.root = root
        self.path = safe_path(root, 'data/workspace.sqlite')

    @contextmanager
    def connection(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        db = sqlite3.connect(self.path, timeout=15)
        try:
            db.row_factory = sqlite3.Row
            db.executescript('''
                CREATE TABLE IF NOT EXISTS tasks(id TEXT PRIMARY KEY, title TEXT NOT NULL, state TEXT NOT NULL, plan_id TEXT, created TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS plans(id TEXT PRIMARY KEY, idea TEXT NOT NULL, state TEXT NOT NULL, version INTEGER NOT NULL, tasks TEXT, proposal TEXT, engine TEXT, created TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS sessions(owner TEXT PRIMARY KEY, action TEXT NOT NULL, expires REAL NOT NULL);
            ''')
            with db:
                yield db
        finally:
            db.close()

    def add_task(self, title, plan_id=None, identifier=None):
        title = title.strip()
        if not title or len(title) > 500:
            raise ValueError('Tulis task sepanjang 1–500 karakter.')
        identifier = identifier or 'T-' + uuid4().hex[:8]
        with self.connection() as db:
            db.execute('INSERT OR IGNORE INTO tasks VALUES (?,?,?,?,?)', (identifier, title, 'todo', plan_id, datetime.now(timezone.utc).isoformat()))
        return identifier

    def tasks(self, state=None):
        with self.connection() as db:
            rows = db.execute('SELECT * FROM tasks ' + ('WHERE state=? ' if state else '') + 'ORDER BY created DESC', (state,) if state else ()).fetchall()
        return [dict(row) for row in rows]

    def set_task(self, identifier, state):
        if state not in ('todo', 'doing', 'done'):
            raise ValueError('Status task tidak valid.')
        with self.connection() as db:
            if db.execute('UPDATE tasks SET state=? WHERE id=?', (state, identifier)).rowcount != 1:
                raise ValueError('Task tidak ditemukan.')

    def session(self, owner, action=None):
        with self.connection() as db:
            if action is not None:
                db.execute('INSERT OR REPLACE INTO sessions VALUES (?,?,?)', (str(owner), action, time.time() + 900))
                return action
            row = db.execute('SELECT * FROM sessions WHERE owner=?', (str(owner),)).fetchone()
            return row['action'] if row and row['expires'] > time.time() else None

    def clear_session(self, owner):
        with self.connection() as db:
            db.execute('DELETE FROM sessions WHERE owner=?', (str(owner),))

    def new_plan(self, idea):
        if not idea.strip() or len(idea) > 16000:
            raise ValueError('Isi ide antara 1 dan 16.000 karakter.')
        identifier = 'P-' + uuid4().hex[:8]
        with self.connection() as db:
            db.execute('INSERT INTO plans VALUES (?,?,?,?,?,?,?,?)', (identifier, idea.strip(), 'draft', 1, None, None, None, datetime.now(timezone.utc).isoformat()))
        return identifier

    def plans(self):
        with self.connection() as db:
            return [dict(row) for row in db.execute('SELECT * FROM plans ORDER BY created DESC')]

    def plan(self, identifier):
        with self.connection() as db:
            row = db.execute('SELECT * FROM plans WHERE id=?', (identifier,)).fetchone()
        if not row:
            raise ValueError('Proposal tidak ditemukan.')
        return dict(row)

    def update_plan(self, identifier, **fields):
        if not fields or not set(fields).issubset({'state', 'tasks', 'proposal', 'engine'}):
            raise ValueError('Field proposal tidak valid.')
        with self.connection() as db:
            db.execute('UPDATE plans SET ' + ','.join(key + '=?' for key in fields) + ' WHERE id=?', (*fields.values(), identifier))

    def approve(self, identifier):
        # Read the reviewed version and activate its tasks in one transaction.
        with self.connection() as db:
            row = db.execute('SELECT * FROM plans WHERE id=?', (identifier,)).fetchone()
            if not row or row['state'] not in ('ready_for_review', 'approved'):
                raise ValueError('Proposal belum siap direview. Jalankan dua agen terlebih dahulu.')
            for task in json.loads(row['tasks']):
                db.execute('INSERT OR IGNORE INTO tasks VALUES (?,?,?,?,?)', (identifier + '-' + task['id'], task['title'], 'todo', identifier, datetime.now(timezone.utc).isoformat()))
            db.execute("UPDATE plans SET state='approved' WHERE id=?", (identifier,))
