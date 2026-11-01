"""Loopback-only image intake. API disabled unless explicitly enabled at startup."""
import base64
import hashlib
from http.server import BaseHTTPRequestHandler, HTTPServer
from importlib.resources import files
import json
from pathlib import Path
import secrets
from urllib.parse import urlsplit

from .known_design import KINDS, MAX_IMAGE_BYTES, confirm_design, extract, sanitize_image
from .live_viewer import allowed_origin
from .records import Recorder
from .design_replay import matches_d01


def make_server(*, output, env_path, budget_path, port=8766, enable_api=False, max_requests=10, extractor=extract, demo=None):
    if type(max_requests) is not int or not 1<=max_requests<=10:raise ValueError('At most ten image requests')
    log=Recorder(output,mode='known_design_intake_ui')
    log.add('intake_session_policy',{'paid_API_enabled':enable_api,'max_requests':max_requests,
        'hardware_IO':False,'automatic_retry':False})
    token=secrets.token_urlsafe(24);images={};results={};requests=0;reviews={}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass

        def send(self,status,value,mime='application/json',replay=False):
            body=json.dumps(value,ensure_ascii=False).encode() if mime=='application/json' else value
            self.send_response(status);self.send_header('Content-Type',mime)
            self.send_header('Content-Length',str(len(body)));self.send_header('Cache-Control','no-store')
            self.send_header('X-Content-Type-Options','nosniff')
            self.send_header('Content-Security-Policy', ("default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; font-src data:; frame-ancestors 'self'; base-uri 'none'" if replay else "default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self'; connect-src 'self'; frame-src 'self'; frame-ancestors 'none'; base-uri 'none'"))
            self.end_headers();self.wfile.write(body)

        def permitted(self,post=False):
            return (allowed_origin(self.headers.get('Host'),self.headers.get('Origin'),self.server.server_port)
                and (not post or self.headers.get('X-BenchMate-Session')==token))

        def do_GET(self):
            if not self.permitted():self.send(403,{'error':'Local origin required'});return
            path=urlsplit(self.path).path
            if path=='/':
                page=files('benchmate').joinpath('known_design.html').read_text().replace('SESSION_TOKEN',token)
                self.send(200,page.encode(),'text/html; charset=utf-8')
            elif path in ('/known_design.css','/known_design.js'):
                self.send(200,files('benchmate').joinpath(path[1:]).read_bytes(),
                    'text/css' if path.endswith('.css') else 'text/javascript')
            elif path=='/state':self.send(200,{'api_enabled':enable_api,'requests':requests,'max_requests':max_requests,'recorded_demo_available':demo is not None})
            elif path=='/replay/d01' and demo and any(matches_d01(v) for v in reviews.values()):
                self.send(200,demo['viewer'],'text/html; charset=utf-8',replay=True)
            elif path.startswith('/image/') and path[7:] in images:self.send(200,images[path[7:]][0],'image/png')
            else:self.send(404,{'error':'Not found'})

        def do_POST(self):
            nonlocal requests
            if not self.permitted(post=True):self.send(403,{'error':'Local session required'});return
            try:
                length=int(self.headers.get('Content-Length','0'))
                if not 0<length<=MAX_IMAGE_BYTES*2 or self.headers.get('Content-Type')!='application/json':
                    raise ValueError('Bounded JSON body required')
                data=json.loads(self.rfile.read(length))
                path=urlsplit(self.path).path
                if path=='/recorded-example':
                    if demo is None:raise ValueError('Start with --demo to load the recorded example')
                    identity='recorded-'+secrets.token_hex(8)
                    images[identity]=(demo['image'],demo['info'],'intended_schematic')
                    run=log.path/identity;run.mkdir()
                    results[identity]={'run':str(run),'result':demo['result']}
                    log.add('recorded_vision_loaded',{'id':identity,**demo['provenance']})
                    self.send(200,{'id':identity,'image':demo['info'],'source_kind':'intended_schematic',
                        'already_requested':True,'recorded':True,'result':demo['result'],'provenance':demo['provenance']})
                elif path=='/prepare':
                    kind=data.get('source_kind')
                    if kind not in KINDS:raise ValueError('Choose intended schematic or assembly photo')
                    raw=base64.b64decode(data['image_base64'],validate=True)
                    image,info=sanitize_image(raw)
                    identity=hashlib.sha256(image+kind.encode()).hexdigest()
                    images[identity]=(image,info,kind)
                    log.add('image_prepared',{'id':identity,'source_kind':kind,'image':info})
                    self.send(200,{'id':identity,'image':info,'source_kind':kind,'already_requested':identity in results})
                elif path=='/extract':
                    if not enable_api:raise ValueError('Preview mode: paid API calls are disabled')
                    identity=data['id']
                    if identity not in images:raise ValueError('Prepare this image first')
                    if identity in results:raise ValueError('This image was already attempted; review its retained result')
                    if requests>=max_requests:raise ValueError('Session request limit reached')
                    image,info,kind=images[identity]
                    requests+=1;results[identity]={'status':'attempt_started'}
                    log.add('image_attempt_started',{'id':identity,'attempt':requests})
                    run,result=extractor(image,info,kind,output=log.path/'extractions',env_path=env_path,budget_path=budget_path)
                    results[identity]={'run':str(run),'result':result}
                    log.add('image_attempt_finished',{'id':identity,'status':result['status'],'requests':requests})
                    self.send(200,{'id':identity,'result':result,'requests':requests})
                elif path=='/confirm':
                    entry=results.get(data['id'],{})
                    reviewed=confirm_design(entry.get('result',{}),data['candidate'],reviewer_note=data['reviewer_note'])
                    reviewed['historical_example']={'available':demo is not None and matches_d01(reviewed),
                        'same_specimen_established':False,'new_measurement':False,
                        'record_sha256':demo['provenance']['physical_record_sha256'] if demo else None}
                    target=Path(entry['run'])/'confirmed-design.json'
                    with target.open('x') as file:json.dump(reviewed,file,ensure_ascii=False,indent=2);file.write('\n')
                    reviews[data['id']]=reviewed
                    log.add('design_confirmed_by_operator',{'image_id':data['id'],'design':reviewed})
                    self.send(200,reviewed)
                else:self.send(404,{'error':'Not found'})
            except (ValueError,KeyError,TypeError,OSError) as exc:
                self.send(400,{'error':str(exc) if isinstance(exc,ValueError) else type(exc).__name__})

    server=HTTPServer(('127.0.0.1',port),Handler)
    server.intake_log=log
    return server
