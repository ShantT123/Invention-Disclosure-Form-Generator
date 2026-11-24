"""Private project storage and immutable report snapshots."""
import json
import os
from pathlib import Path
import sqlite3
import sys
import threading
import uuid
from .input_text import validate_input
from datetime import datetime, timezone


def now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def default_directory():
    if sys.platform == 'darwin':
        return Path.home() / 'Library/Application Support/Invention Disclosure Generator'
    return Path.home() / '.local/share/invention-disclosure-generator'


class Store:
    def __init__(self, directory=None):
        self.directory = Path(directory or default_directory()).resolve()
        repository = Path(__file__).resolve().parents[1]
        if self.directory == repository or repository in self.directory.parents:
            raise ValueError('Client data must be outside the application/repository directory')
        self.directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(self.directory, 0o700)
        self.lock = threading.RLock()
        self.db = sqlite3.connect(self.directory / 'projects.sqlite3', check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.executescript('''
        CREATE TABLE IF NOT EXISTS projects(id TEXT PRIMARY KEY,title TEXT,created TEXT);
        CREATE TABLE IF NOT EXISTS inputs(id TEXT PRIMARY KEY,project_id TEXT,text TEXT,created TEXT);
        CREATE TABLE IF NOT EXISTS revisions(project_id TEXT,number INTEGER,created TEXT,report TEXT,model TEXT,prompt_version TEXT,PRIMARY KEY(project_id,number));
        CREATE TABLE IF NOT EXISTS searches(project_id TEXT,query TEXT,created TEXT);
        CREATE TABLE IF NOT EXISTS public_sources(id TEXT PRIMARY KEY,project_id TEXT,url TEXT,title TEXT,text TEXT,digest TEXT,accessed TEXT);
        ''')
        self.db.commit()
        os.chmod(self.directory / 'projects.sqlite3', 0o600)

    def create(self, title, description):
        validate_input(description, minimum=20)
        pid = uuid.uuid4().hex
        with self.lock, self.db:
            self.db.execute('INSERT INTO projects VALUES(?,?,?)', (pid, title, now()))
            self.db.execute('INSERT INTO inputs VALUES(?,?,?,?)', (uuid.uuid4().hex, pid, description, now()))
        return pid

    def list(self):
        with self.lock:
            return [dict(r) for r in self.db.execute('SELECT p.*, (SELECT count(*) FROM revisions r WHERE r.project_id=p.id) AS revisions FROM projects p ORDER BY created DESC')]

    def get(self, pid):
        with self.lock:
            p = self.db.execute('SELECT * FROM projects WHERE id=?', (pid,)).fetchone()
            if not p:
                raise KeyError('Project not found')
            value = dict(p)
            value['inputs'] = [dict(r) for r in self.db.execute('SELECT * FROM inputs WHERE project_id=? ORDER BY created,rowid', (pid,))]
            value['revisions'] = [dict(r) for r in self.db.execute('SELECT number,created,model,prompt_version FROM revisions WHERE project_id=? ORDER BY number', (pid,))]
            value['searches'] = [dict(r) for r in self.db.execute('SELECT query,created FROM searches WHERE project_id=? ORDER BY rowid', (pid,))]
            value['sources'] = [dict(r) for r in self.db.execute('SELECT * FROM public_sources WHERE project_id=? ORDER BY rowid', (pid,))]
            return value

    def add_input(self, pid, text):
        with self.lock, self.db:
            p = self.get(pid)
            validate_input(text, existing_bytes=sum(len(x['text'].encode()) for x in p['inputs']))
            self.db.execute('INSERT INTO inputs VALUES(?,?,?,?)', (uuid.uuid4().hex, pid, text, now()))

    def log_search(self, pid, query):
        with self.lock, self.db:
            self.get(pid)
            self.db.execute('INSERT INTO searches VALUES(?,?,?)', (pid, query, now()))

    def add_source(self, pid, source):
        with self.lock, self.db:
            self.get(pid)
            if self.db.execute('SELECT count(*) FROM public_sources WHERE project_id=?', (pid,)).fetchone()[0] >= 3:
                raise ValueError('The prototype supports up to three public source pages per project')
            self.db.execute('INSERT INTO public_sources VALUES(?,?,?,?,?,?,?)', (uuid.uuid4().hex, pid, source['url'], source['title'], source['text'], source['digest'], source['accessed']))

    def revision(self, pid, number):
        with self.lock:
            r = self.db.execute('SELECT report FROM revisions WHERE project_id=? AND number=?', (pid, number)).fetchone()
            if not r:
                raise KeyError('Report revision not found')
            return json.loads(r[0])

    def commit(self, pid, expected_number, report, model):
        with self.lock, self.db:
            current = self.db.execute('SELECT count(*) FROM revisions WHERE project_id=?', (pid,)).fetchone()[0]
            if current != expected_number:
                raise ValueError('Project revision changed; reload before generating again')
            self.db.execute('INSERT INTO revisions VALUES(?,?,?,?,?,?)', (pid, current + 1, now(), json.dumps(report, ensure_ascii=False), model, report.get('generation', {}).get('prompt_version', 'local-pipeline-1')))

    def close(self):
        self.db.close()
