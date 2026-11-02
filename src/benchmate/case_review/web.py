"""Loopback-only P0 UI. Deliberately has no API, serial, upload or live-run routes."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.resources import files
import json
import secrets
from urllib.parse import urlsplit

from ..live_viewer import allowed_origin
from .service import CaseStore, Conflict


def _exact(data, keys):
    if not isinstance(data, dict) or set(data) != set(keys):
        raise ValueError('Unexpected request fields')


def _constant(value):
    raise ValueError('Non-finite JSON values are not allowed')


def make_server(*, root, output, port=8770):
    store = CaseStore(root, output)
    token = secrets.token_urlsafe(24)

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def permitted(self, mutation=False):
            origin = allowed_origin(self.headers.get('Host'), self.headers.get('Origin'), self.server.server_port)
            return origin and (not mutation or secrets.compare_digest(self.headers.get('X-BenchMate-Session', ''), token))

        def send(self, code, value, mime='application/json', replay=False, download=None):
            body = json.dumps(value, ensure_ascii=False, allow_nan=False).encode() if mime == 'application/json' else value
            self.send_response(code)
            self.send_header('Content-Type', mime)
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Referrer-Policy', 'no-referrer')
            self.send_header('Content-Security-Policy',
                "default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; font-src data:; frame-ancestors 'self'; base-uri 'none'" if replay else
                "default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self'; connect-src 'self'; frame-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'")
            if download:
                self.send_header('Content-Disposition', f'attachment; filename="{download}"')
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if not self.permitted():
                self.send(403, {'error': 'Local origin required'}); return
            parts = urlsplit(self.path).path.strip('/').split('/')
            try:
                if parts == ['']:
                    page = files(__package__).joinpath('index.html').read_text().replace('SESSION_TOKEN', token)
                    self.send(200, page.encode(), 'text/html; charset=utf-8')
                elif parts in (['app.js'], ['style.css']):
                    name = parts[0]
                    self.send(200, files(__package__).joinpath(name).read_bytes(), 'text/javascript' if name.endswith('.js') else 'text/css')
                elif parts == ['schematic.png']:
                    self.send(200, store.demo['image'], 'image/png')
                elif parts == ['api', 'state']:
                    self.send(200, {'mode': 'recorded_walkthrough', 'paid_api_calls': 0, 'hardware_IO': False,
                                   'cases': store.summaries(), 'original_candidate': store.demo['result']['candidate']})
                elif len(parts) in (3, 4) and parts[:2] == ['api', 'cases']:
                    identity = parts[2]
                    if len(parts) == 3:
                        self.send(200, store.get(identity))
                    elif parts[3] == 'replay':
                        self.send(200, store.replay(identity), 'text/html; charset=utf-8', replay=True)
                    elif parts[3] == 'export':
                        self.send(200, store.get(identity), download=f'benchmate-case-{identity}.json')
                    else:
                        self.send(404, {'error': 'Not found'})
                else:
                    self.send(404, {'error': 'Not found'})
            except Conflict as error:
                self.send(409, {'error': str(error)})
            except KeyError:
                self.send(404, {'error': 'Unknown case'})
            except (ValueError, OSError, TypeError):
                self.send(400, {'error': 'Invalid local record'})

        def do_POST(self):
            if not self.permitted(mutation=True):
                self.send(403, {'error': 'Local session required'}); return
            try:
                length = int(self.headers.get('Content-Length', '0'))
                if not 0 < length <= 64_000 or self.headers.get('Content-Type') != 'application/json' or self.headers.get('Transfer-Encoding'):
                    raise ValueError('Bounded JSON body required')
                data = json.loads(self.rfile.read(length), parse_constant=_constant)
                parts = urlsplit(self.path).path.strip('/').split('/')
                if parts == ['api', 'cases']:
                    _exact(data, ['question', 'scope'])
                    self.send(201, store.create(data['question'], data['scope']))
                elif len(parts) == 4 and parts[:2] == ['api', 'cases']:
                    if parts[3] == 'review':
                        _exact(data, ['revision', 'candidate', 'review_note'])
                        self.send(200, store.review(parts[2], data['revision'], data['candidate'], data['review_note']))
                    elif parts[3] == 'link-replay':
                        _exact(data, ['revision'])
                        self.send(200, store.link_replay(parts[2], data['revision']))
                    else:
                        self.send(404, {'error': 'No such action in recorded mode'})
                else:
                    self.send(404, {'error': 'No such action in recorded mode'})
            except Conflict as error:
                self.send(409, {'error': str(error)})
            except KeyError:
                self.send(404, {'error': 'Unknown case'})
            except ValueError as error:
                self.send(400, {'error': str(error)})
            except (TypeError, OSError):
                self.send(400, {'error': 'Invalid request; no action performed'})

    server = ThreadingHTTPServer(('127.0.0.1', port), Handler)
    server.case_store = store
    return server
