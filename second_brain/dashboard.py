"""Loopback-only dashboard with per-process bearer authorization."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import secrets
import webbrowser
from . import __version__, vault
from .controller import Commands
from .hub import Hub
from .storage import read_note
from .workspace import archives, process_lock


def snapshot(settings):
    hub = Hub(settings.root)
    notes = sorted(vault.notes(settings.root, False), key=lambda n: n['mtime'], reverse=True)
    return {'version': __version__, 'workspace': settings.root.name, 'notes': [{'title': n['title'], 'path': n['path'], 'modified': n['mtime']} for n in notes], 'tasks': hub.tasks(),
            'plans': hub.plans(), 'archives': archives(settings.project), 'ai_configured': bool((settings.env.get('GEMINI_API_KEY') and settings.env.get('GEMINI_MODEL')) or (settings.env.get('GROQ_API_KEY') and settings.env.get('GROQ_MODEL')))}


def make_server(settings, port=8765, token=None):
    token = token or secrets.token_urlsafe(32)
    assets = Path(__file__).resolve().parent / 'web'

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format, *args):
            pass  # URLs and authorization data do not go to logs.

        def reply(self, status, value, kind='application/json; charset=utf-8'):
            data = value if isinstance(value, bytes) else json.dumps(value, ensure_ascii=False).encode('utf-8')
            self.send_response(status)
            self.send_header('Content-Type', kind)
            self.send_header('Content-Length', str(len(data)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'")
            self.end_headers()
            self.wfile.write(data)

        def authorized(self):
            host = self.headers.get('Host', '')
            expected = f'127.0.0.1:{self.server.server_port}'
            if host != expected:
                return False
            origin = self.headers.get('Origin')
            if origin and origin != 'http://' + expected:
                return False
            return secrets.compare_digest(self.headers.get('Authorization', ''), 'Bearer ' + token)

        def do_GET(self):
            if self.path == '/api/snapshot':
                if not self.authorized():
                    return self.reply(401, {'error': 'Buka dashboard melalui URL sesi yang dicetak terminal.'})
                return self.reply(200, snapshot(settings))
            routes = {'/': ('index.html', 'text/html; charset=utf-8'), '/app.js': ('app.js', 'text/javascript; charset=utf-8'), '/style.css': ('style.css', 'text/css; charset=utf-8')}
            if self.path not in routes:
                return self.reply(404, {'error': 'Tidak ditemukan.'})
            name, kind = routes[self.path]
            self.reply(200, (assets / name).read_bytes(), kind)

        def do_POST(self):
            if self.path != '/api/command':
                return self.reply(404, {'error': 'Tidak ditemukan.'})
            if not self.authorized():
                return self.reply(401, {'error': 'Sesi dashboard tidak valid.'})
            try:
                size = int(self.headers.get('Content-Length', '0'))
                if not 0 < size <= 65536 or not self.headers.get('Content-Type', '').startswith('application/json'):
                    return self.reply(400, {'error': 'Body harus JSON dan maksimal 64 KB.'})
                request = json.loads(self.rfile.read(size).decode('utf-8'))
                if not isinstance(request, dict):
                    raise ValueError('Body harus berupa objek JSON.')
                command = request.get('command', '')
                if not isinstance(command, str) or not command.startswith('/'):
                    raise ValueError('Perintah tidak valid.')
                allowed = {'/capture', '/search', '/read', '/task', '/done', '/plan', '/proposal', '/prompt', '/planrun', '/approve', '/revise', '/ask', '/ingest'}
                if command.split(maxsplit=1)[0] not in allowed:
                    raise ValueError('Perintah tidak tersedia pada dashboard.')
                commands = Commands(settings)
                commands.owner = 'dashboard'
                result = commands.dispatch(command)
                self.reply(200, {'result': str(result), 'snapshot': snapshot(settings)})
            except (ValueError, OSError, RuntimeError) as error:
                self.reply(400, {'error': settings.redact(error)})

    server = ThreadingHTTPServer(('127.0.0.1', port), Handler)
    server.daemon_threads = True
    return server, token


def run(settings, port=8765, open_browser=True):
    with process_lock(settings.project, 'dashboard'):
        server, token = make_server(settings, port)
        url = f'http://127.0.0.1:{server.server_port}/#{token}'
        print('Dashboard hanya untuk mesin ini. Gunakan URL sesi berikut; Ctrl+C untuk berhenti:\n' + url, flush=True)
        if open_browser:
            webbrowser.open(url)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            server.shutdown()
            server.server_close()
