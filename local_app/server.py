"""Loopback HTTP interface with per-launch authentication and no request-content logging."""
import argparse
import hmac
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import secrets
import subprocess
import sys
import threading
import uuid
import webbrowser
from urllib.parse import urlsplit, parse_qs, quote
from pathlib import Path

from . import __version__
from .input_text import MAX_INPUT_BYTES, MAX_REQUEST_BYTES, validate_input
from .storage import Store
from .runtime import Runtime, MODELS
from .pipeline import analyze, renderer, ROOT
from .research import fetch_public, TOPICS


class RequestError(ValueError):
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status


class App:
    def __init__(self, directory=None, runtime=None):
        self.store = Store(directory)
        self.runtime = runtime or Runtime(self.store.directory)
        self.token = secrets.token_urlsafe(32)
        self.jobs = {}
        self.lock = threading.RLock()
        self.active = None
        self.server = None

    def job(self, kind, function):
        with self.lock:
            if self.active:
                raise ValueError('Another local AI job is running. Wait or cancel it first.')
            jid = uuid.uuid4().hex
            cancel = threading.Event()
            item = {'id': jid, 'kind': kind, 'status': 'running', 'message': 'Starting', 'cancel': cancel}
            self.jobs[jid] = item; self.active = jid
            def progress(message):
                with self.lock: item['message'] = message
            def run():
                try:
                    function(progress, cancel)
                    with self.lock: item.update(status='cancelled' if cancel.is_set() else 'completed', message='Cancelled' if cancel.is_set() else 'Complete')
                except Exception as exc:
                    with self.lock:
                        item.update(status='cancelled' if cancel.is_set() else 'failed', message='Cancelled; previous reports are unchanged.' if cancel.is_set() else (str(exc)[:350] if isinstance(exc, (ValueError, RuntimeError)) else 'Local operation failed. Check that the runtime is available and retry; previous reports are unchanged.'))
                finally:
                    with self.lock: self.active = None
            item['thread'] = threading.Thread(target=run, daemon=True)
            item['thread'].start()
            return jid

    def close(self):
        with self.lock:
            jobs = list(self.jobs.values())
            for j in jobs: j['cancel'].set()
        self.runtime.stop()
        for j in jobs: j['thread'].join(timeout=3)
        self.store.close()


def make_server(app, port=0):
    static = ROOT / 'local_app/static'
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args): pass

        def send(self, status, data, content_type='application/json', cookie=False, download=None):
            body = json.dumps(data).encode() if content_type == 'application/json' and not isinstance(data, bytes) else (data.encode() if isinstance(data, str) else data)
            self.send_response(status)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Referrer-Policy', 'no-referrer')
            if not self.path.startswith('/reports/'):
                self.send_header('Content-Security-Policy', "default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; frame-src 'self'; img-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'")
            else:
                self.send_header('Content-Security-Policy', "frame-ancestors 'self'")
            if cookie:
                self.send_header('Set-Cookie', f'local_report={app.token}; HttpOnly; SameSite=Strict; Path=/reports')
            if download: self.send_header('Content-Disposition', 'attachment; filename="' + download + '"')
            self.end_headers(); self.wfile.write(body)

        def valid_host(self):
            return self.headers.get('Host') == f'127.0.0.1:{self.server.server_port}'

        def authorized(self, report=False):
            token = self.headers.get('X-Local-Token', '')
            if report:
                pairs = dict(x.strip().split('=', 1) for x in self.headers.get('Cookie', '').split(';') if '=' in x)
                token = pairs.get('local_report', '')
            return bool(token) and hmac.compare_digest(token, app.token)

        def body(self):
            try:
                length = int(self.headers.get('Content-Length', '0'))
            except ValueError:
                raise RequestError(400, 'Invalid request length; your text was not saved')
            if self.headers.get('Content-Type', '').split(';')[0] != 'application/json':
                raise RequestError(415, 'This local endpoint requires JSON; reload the application and retry')
            if length > MAX_REQUEST_BYTES:
                self.close_connection = True
                raise RequestError(413, f'The pasted request is too large (limit {MAX_REQUEST_BYTES:,} bytes). The project text limit is {MAX_INPUT_BYTES:,} UTF-8 bytes. Nothing was saved or sent to the model.')
            if length <= 0:
                raise RequestError(400, 'The request was empty; your text was not saved')
            value = json.loads(self.rfile.read(length))
            if not isinstance(value, dict): raise ValueError('Expected an object')
            return value

        def do_GET(self):
            if not self.valid_host(): return self.send(403, {'error': 'Invalid host'})
            path = urlsplit(self.path).path
            if path == '/favicon.ico': return self.send(204, b'', 'image/x-icon')
            if path in ('/', '/app.js', '/app.css'):
                file, content_type = {'/': ('index.html', 'text/html; charset=utf-8'), '/app.js': ('app.js', 'text/javascript; charset=utf-8'), '/app.css': ('app.css', 'text/css; charset=utf-8')}[path]
                return self.send(200, (static / file).read_bytes(), content_type)
            if not self.authorized(path.startswith('/reports/')):
                return self.send(401, {'error': 'Open the app using its launcher to start an authenticated local session.'})
            try:
                parts = path.strip('/').split('/')
                if path == '/api/status':
                    return self.send(200, dict(app.runtime.status(), active_job=app.active, topics=list(TOPICS), data_directory=str(app.store.directory), input_limit_bytes=MAX_INPUT_BYTES, app_version=__version__), cookie=True)
                if path == '/api/projects': return self.send(200, app.store.list())
                if len(parts) == 3 and parts[:2] == ['api', 'projects']:
                    return self.send(200, app.store.get(parts[2]))
                if len(parts) == 3 and parts[:2] == ['api', 'jobs']:
                    with app.lock:
                        item = app.jobs[parts[2]]
                        return self.send(200, {k: item[k] for k in ('id', 'kind', 'status', 'message')})
                if (len(parts) == 4 and parts[:2] == ['api', 'reports']) or (len(parts) == 3 and parts[0] == 'reports'):
                    pid, number = parts[-2], int(parts[-1])
                    report = app.store.revision(pid, number)
                    markdown, html = renderer.Report(report).build()
                    format = parse_qs(urlsplit(self.path).query).get('format', ['html'])[0]
                    if path.startswith('/reports/'): return self.send(200, html, 'text/html; charset=utf-8')
                    choices = {'html': (html, 'text/html; charset=utf-8'), 'md': (markdown, 'text/markdown; charset=utf-8'), 'json': (report, 'application/json')}
                    if format not in choices: raise ValueError('Unknown report format')
                    content, mime = choices[format]
                    return self.send(200, content, mime, download='disclosure.' + format)
                return self.send(404, {'error': 'Not found'})
            except KeyError: return self.send(404, {'error': 'Not found'})
            except ValueError as exc: return self.send(400, {'error': str(exc)})
            except Exception: return self.send(500, {'error': 'Local operation failed'})

        def do_POST(self):
            origin = self.headers.get('Origin')
            expected = f'http://127.0.0.1:{self.server.server_port}'
            if not self.valid_host() or origin != expected or not self.authorized():
                return self.send(403, {'error': 'Invalid local session or origin'})
            try:
                data = self.body(); path = urlsplit(self.path).path
                if path == '/api/runtime/start':
                    return self.send(202, {'job_id': app.job('start', lambda p, c: app.runtime.start())})
                if path == '/api/runtime/pull':
                    model = data.get('model')
                    if model not in MODELS: raise ValueError('Choose a supported local model')
                    return self.send(202, {'job_id': app.job('download', lambda p, c: app.runtime.pull(model, p, c))})
                if path == '/api/jobs/cancel':
                    with app.lock:
                        if not app.active: raise ValueError('No active job')
                        app.jobs[app.active]['cancel'].set()
                        app.jobs[app.active]['message'] = 'Cancelling; earlier reports remain saved'
                    app.runtime.stop()
                    return self.send(200, {'ok': True})
                if path == '/api/shutdown':
                    threading.Thread(target=self.server.shutdown, daemon=True).start()
                    return self.send(200, {'ok': True})
                if path == '/api/projects':
                    title, description = data.get('title', ''), data.get('description', '')
                    if not isinstance(title, str) or not 1 <= len(title.strip()) <= 120: raise ValueError('Enter a project title (up to 120 characters)')
                    validate_input(description, minimum=20)
                    return self.send(201, {'id': app.store.create(title.strip(), description)})
                parts = path.strip('/').split('/')
                if len(parts) == 4 and parts[:2] == ['api', 'projects']:
                    pid, action = parts[2:]
                    with app.lock:
                        if app.active: raise ValueError('Wait for the active local operation before changing project evidence')
                        project = app.store.get(pid)
                        if action == 'inputs':
                            text = data.get('text', '')
                            validate_input(text)
                            app.store.add_input(pid, text); return self.send(200, {'ok': True})
                        if action == 'search':
                            topic = data.get('topic')
                            if topic not in TOPICS: raise ValueError('Choose a predefined public topic; private search text is not accepted')
                            query = topic + ' products research'
                            app.store.log_search(pid, query)
                            return self.send(200, {'url': 'https://www.google.com/search?q=' + quote(query)})
                        if action == 'sources':
                            if data.get('approved') is not True: raise ValueError('Confirm this is a public URL before retrieving it')
                            # Explicit operator action; no automatic fetch from model output.
                            source = fetch_public(data.get('url', ''))
                            app.store.add_source(pid, source); return self.send(200, {'ok': True})
                        if action == 'generate':
                            model = data.get('model')
                            if model not in MODELS: raise ValueError('Choose a supported local model')
                            if data.get('expected_revision') != len(project['revisions']): raise ValueError('Project changed; reload before generating')
                            def generate(progress, cancel):
                                previous = app.store.revision(pid, len(project['revisions'])) if project['revisions'] else None
                                report = analyze(project, app.runtime, model, cancel, progress, previous)
                                if hasattr(app.runtime, 'metadata'): report['generation']['model_metadata'] = app.runtime.metadata(model)
                                with app.lock:
                                    if cancel.is_set(): raise RuntimeError('Cancelled')
                                    app.store.commit(pid, len(project['revisions']), report, model)
                            return self.send(202, {'job_id': app.job('analysis', generate)})
                return self.send(404, {'error': 'Not found'})
            except RequestError as exc: return self.send(exc.status, {'error': str(exc)})
            except (ValueError, json.JSONDecodeError) as exc: return self.send(400, {'error': str(exc)[:350]})
            except KeyError: return self.send(404, {'error': 'Project not found'})
            except Exception: return self.send(500, {'error': 'Local operation failed; no report was replaced'})

    server = ThreadingHTTPServer(('127.0.0.1', port), Handler)
    server.daemon_threads = True
    app.server = server
    return server


def open_interface(url):
    if sys.platform == 'darwin':
        try:
            subprocess.run(['open', '-a', 'Google Chrome', url], check=True, timeout=10,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return
        except (OSError, subprocess.SubprocessError):
            pass
    webbrowser.open(url)


def main():
    parser = argparse.ArgumentParser(description='Start the local Invention Disclosure browser app')
    parser.add_argument('--data-dir', type=Path)
    parser.add_argument('--no-browser', action='store_true')
    parser.add_argument('--self-check', action='store_true', help='Check packaged resources without opening a workspace')
    args = parser.parse_args()
    if args.self_check:
        for resource in ('local_app/static/index.html', 'local_app/static/app.js', 'skills/inventor-brief-v2/scripts/dashboard.css', 'skills/inventor-brief-v2/scripts/dashboard.js'):
            if not (ROOT / resource).is_file(): raise RuntimeError('A required application resource is missing')
        print('Application resources and renderer import OK')
        return
    app = App(args.data_dir); server = make_server(app)
    import signal
    signal.signal(signal.SIGTERM, lambda *_: threading.Thread(target=server.shutdown, daemon=True).start())
    url = f'http://127.0.0.1:{server.server_port}/#session={app.token}'
    if args.no_browser:
        print('Local development session (keep private): ' + url, flush=True)
    else:
        open_interface(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close(); app.close()


if __name__ == '__main__': main()
