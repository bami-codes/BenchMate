"""Loopback recorded conversation and supervised scripted mocks; no paid API or hardware routes."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.resources import files
import json
import secrets
from urllib.parse import urlsplit, parse_qs

from ..live_viewer import allowed_origin
from .service import CaseStore, Conflict
from .runner_bridge import RunnerBridge
from .runner_contract import CAPABILITIES as RUNNER_CAPABILITIES


def _exact(data, keys):
    if not isinstance(data, dict) or set(data) != set(keys):
        raise ValueError('Unexpected request fields')


def _constant(value):
    raise ValueError('Non-finite JSON values are not allowed')


def make_server(*, root, output, port=8770):
    store = CaseStore(root, output)
    token = secrets.token_urlsafe(24)
    bridge = RunnerBridge(root, store)

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
                "default-src 'none'; script-src 'self'; style-src 'self'; font-src 'self'; img-src 'self'; connect-src 'self'; frame-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'")
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
                elif parts in (['Archivo-var.woff2'], ['archivo-OFL.txt']):
                    self.send(200, files(__package__).joinpath(parts[0]).read_bytes(),
                              'font/woff2' if parts[0].endswith('.woff2') else 'text/plain')
                elif parts == ['schematic.png']:
                    self.send(200, store.demo['image'], 'image/png')
                elif parts == ['api', 'state']:
                    self.send(200, {'mode': 'recorded_walkthrough', 'paid_api_calls': 0, 'hardware_IO': False,
                                   'cases': store.summaries(), 'original_candidate': store.demo['result']['candidate']})
                elif parts == ['api', 'runner-capabilities']:
                    self.send(200, RUNNER_CAPABILITIES)
                elif len(parts) in (3, 4) and parts[:2] == ['api', 'runs']:
                    if len(parts) == 3:
                        self.send(200, bridge.snapshot(parts[2]))
                    elif parts[3] == 'events':
                        query = parse_qs(urlsplit(self.path).query, keep_blank_values=True)
                        raw = query.get('after', ['-1'])
                        if set(query) - {'after'} or len(raw) != 1 or len(raw[0]) > 5 or not raw[0].isascii():
                            raise ValueError('Invalid event cursor')
                        self.send(200, bridge.events(parts[2], int(raw[0])))
                    elif parts[3] == 'predictions':
                        self.send(200, bridge.predictions(parts[2]))
                    else:
                        self.send(404, {'error': 'Not found'})
                elif len(parts) in (3, 4) and parts[:2] == ['api', 'cases']:
                    identity = parts[2]
                    if len(parts) == 3:
                        self.send(200, store.get(identity))
                    elif parts[3] == 'runs':
                        self.send(200, bridge.list_runs(identity))
                    elif parts[3] == 'replay':
                        self.send(200, store.replay(identity), 'text/html; charset=utf-8', replay=True)
                    elif parts[3] in ('timeline', 'event'):
                        query = parse_qs(urlsplit(self.path).query, keep_blank_values=True)
                        keys = {'cursor'} if parts[3] == 'timeline' else {'cursor', 'sequence'}
                        if set(query) != keys or any(len(v) != 1 or not v[0].isascii() or not v[0].isdigit() or len(v[0]) > 3 for v in query.values()):
                            raise ValueError('Invalid replay position')
                        cursor = int(query['cursor'][0])
                        self.send(200, store.conversation_snapshot(identity, cursor) if parts[3] == 'timeline'
                                  else store.conversation_event(identity, int(query['sequence'][0]), cursor))
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
                    if parts[3] == 'runs':
                        self.send(200, bridge.launch(parts[2], data))
                    elif parts[3] == 'review':
                        _exact(data, ['revision', 'candidate', 'review_note'])
                        self.send(200, store.review(parts[2], data['revision'], data['candidate'], data['review_note']))
                    elif parts[3] == 'confirm':
                        _exact(data, ['revision', 'candidate'])
                        self.send(200, store.confirm_for_replay(parts[2], data['revision'], data['candidate']))
                    elif parts[3] == 'link-replay':
                        _exact(data, ['revision'])
                        self.send(200, store.link_replay(parts[2], data['revision']))
                    else:
                        self.send(404, {'error': 'No such action in recorded mode'})
                elif len(parts) == 4 and parts[:2] == ['api', 'runs']:
                    if parts[3] == 'respond':
                        self.send(200, bridge.respond(parts[2], data))
                    elif parts[3] == 'cancel':
                        _exact(data, ['reason'])
                        self.send(200, bridge.cancel(parts[2], data['reason']))
                    else:
                        self.send(404, {'error': 'No such action'})
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

    class Server(ThreadingHTTPServer):
        def server_close(self):
            bridge.close()
            super().server_close()

    server = Server(('127.0.0.1', port), Handler)
    server.runner_bridge = bridge
    server.case_store = store
    return server
