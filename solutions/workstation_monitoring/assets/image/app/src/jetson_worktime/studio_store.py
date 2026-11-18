"""Durable studio metadata. Artifacts live outside source and are never overwritten."""
from contextlib import contextmanager, closing
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import time
import uuid


class StudioError(ValueError):
    def __init__(self, code, status=400, **params):
        self.code, self.status, self.params = code, status, params
        super().__init__(code)


def uid():
    return uuid.uuid4().hex


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024*1024), b''):
            h.update(block)
    return h.hexdigest()


def atomic(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    name = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as f:
            name = f.name
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(name, path)
        fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    finally:
        if name and os.path.exists(name):
            os.unlink(name)


class StudioStore:
    def __init__(self, root):
        self.root = Path(root)
        self.data = self.root/'data'
        self.data.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.path = self.data/'worktime.sqlite'
        with closing(self.connect()) as db:
            db.executescript('''
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS objects (
                    kind TEXT NOT NULL, id TEXT NOT NULL, revision INTEGER NOT NULL,
                    value TEXT NOT NULL, updated REAL NOT NULL,
                    PRIMARY KEY(kind,id));
                CREATE TABLE IF NOT EXISTS operations (
                    scope TEXT NOT NULL, token TEXT NOT NULL, value TEXT NOT NULL,
                    PRIMARY KEY(scope,token));
                CREATE TABLE IF NOT EXISTS material_events (
                    id TEXT PRIMARY KEY, session_id TEXT NOT NULL, value TEXT NOT NULL);
                CREATE INDEX IF NOT EXISTS material_session ON material_events(session_id);
                PRAGMA user_version=1;
            ''')
        os.chmod(self.path, 0o600)

    def connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA synchronous=FULL')
        return db

    @contextmanager
    def transaction(self):
        db = self.connect()
        try:
            db.execute('BEGIN IMMEDIATE')
            yield db
            db.commit()
        except sqlite3.Error as exc:
            db.rollback()
            raise OSError('Studio database unavailable') from exc
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def get(self, kind, ident, db=None):
        if not isinstance(ident,str) or not 1<=len(ident)<=128:
            raise StudioError('request')
        if db is None:
            with closing(self.connect()) as conn:
                return self.get(kind, ident, conn)
        row = db.execute('SELECT value FROM objects WHERE kind=? AND id=?', (kind, ident)).fetchone()
        if row is None:
            raise StudioError('notFound', 404)
        return json.loads(row['value'])

    def list(self, kind, db=None):
        if db is None:
            with closing(self.connect()) as conn:
                return self.list(kind, conn)
        return [json.loads(r['value']) for r in db.execute('SELECT value FROM objects WHERE kind=? ORDER BY updated DESC', (kind,))]

    def put(self, kind, value, expected=None, db=None):
        if db is None:
            with self.transaction() as conn:
                return self.put(kind, value, expected, conn)
        value = deepcopy(value)
        row = db.execute('SELECT revision FROM objects WHERE kind=? AND id=?', (kind, value['id'])).fetchone()
        revision = row[0] if row else 0
        if expected is not None and expected != revision:
            raise StudioError('conflict', 409)
        value.update(revision=revision+1, updated_at=time.time())
        db.execute('INSERT INTO objects VALUES (?,?,?,?,?) ON CONFLICT(kind,id) DO UPDATE SET revision=excluded.revision,value=excluded.value,updated=excluded.updated',
                   (kind, value['id'], value['revision'], json.dumps(value, allow_nan=False), value['updated_at']))
        return value

    def operation(self, scope, token, callback):
        if not isinstance(token, str) or not 8 <= len(token) <= 128:
            raise StudioError('idempotency')
        with self.transaction() as db:
            row = db.execute('SELECT value FROM operations WHERE scope=? AND token=?', (scope, token)).fetchone()
            if row:
                return json.loads(row[0])
            result = callback(db)
            db.execute('INSERT INTO operations VALUES (?,?,?)', (scope, token, json.dumps(result, allow_nan=False)))
            return result

    def event(self, session_id, kind, key, delta=0, db=None, **metadata):
        if db is None:
            with self.transaction() as conn:
                return self.event(session_id, kind, key, delta, conn, **metadata)
        ident = hashlib.sha256((session_id+'|'+kind+'|'+str(key)).encode()).hexdigest()
        value = dict(id=ident, session_id=session_id, kind=kind, delta=delta, timestamp=time.time(), **metadata)
        db.execute('INSERT OR IGNORE INTO material_events VALUES (?,?,?)', (ident, session_id, json.dumps(value, allow_nan=False)))
        return value

    def events(self, session_id, db=None):
        if db is None:
            with closing(self.connect()) as conn:
                return self.events(session_id, conn)
        return [json.loads(r[0]) for r in db.execute('SELECT value FROM material_events WHERE session_id=? ORDER BY rowid', (session_id,))]

    def total(self, session_id, db=None):
        return sum(v['delta'] for v in self.events(session_id, db)) if session_id else 0
