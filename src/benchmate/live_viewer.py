"""Read-only loopback log transport. No API, stimulus or hardware commands."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import time
from urllib.parse import urlsplit
from .viewer import load_record,render_viewer


def allowed_origin(host,origin,port):
    allowed={f'127.0.0.1:{port}',f'localhost:{port}'}
    return host in allowed and (origin is None or origin in {f'http://{h}' for h in allowed})


def make_server(run,port=8765):
    path=Path(run).resolve()
    if path.is_dir():path=path/'events.jsonl'
    load_record(path,live=True)  # Refuse an already-corrupt record before serving.

    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass

        def do_GET(self):
            if not allowed_origin(self.headers.get('Host'),self.headers.get('Origin'),self.server.server_port):
                self.send_error(403);return
            route=urlsplit(self.path).path
            if route not in ('/','/events'):
                self.send_error(404);return
            if route=='/':
                try:body=render_viewer(load_record(path,live=True)).encode()
                except (ValueError,KeyError,OSError):self.send_error(409,'Record integrity error');return
                self.send_response(200);self.send_header('Content-Type','text/html; charset=utf-8')
                self.send_header('Content-Length',str(len(body)));self.send_header('Cache-Control','no-store')
                self.send_header('X-Content-Type-Options','nosniff');self.end_headers();self.wfile.write(body);return
            self.send_response(200);self.send_header('Content-Type','text/event-stream')
            self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff');self.end_headers()
            previous=None
            try:
                while True:
                    try:record=load_record(path,live=True)
                    except (ValueError,KeyError,OSError):
                        self.wfile.write(b'event: integrity_error\ndata: {}\n\n');self.wfile.flush();break
                    if record['source_sha256']!=previous:
                        self.wfile.write(('data: '+json.dumps(record,allow_nan=False)+'\n\n').encode());previous=record['source_sha256']
                    else:self.wfile.write(b': heartbeat\n\n')
                    self.wfile.flush();time.sleep(.5)
            except (BrokenPipeError,ConnectionResetError):pass
    return ThreadingHTTPServer(('127.0.0.1',port),Handler)


def serve_viewer(run,port=8765):
    if type(port) is not int or not 1024<=port<=65535:raise ValueError('Choose a port in 1024–65535')
    server=make_server(run,port)
    print(f'BenchMate live log: http://127.0.0.1:{server.server_port} (read-only; Ctrl-C to stop)',flush=True)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close()
