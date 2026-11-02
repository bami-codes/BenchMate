"""Prepare an entirely local development library; never call a model or bench."""
from __future__ import annotations

import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import shutil

from .media import SUPPORTED, clean_derivative, import_photo, sha256


ROOT = Path(__file__).resolve().parents[3]
PRIVATE = ROOT / '.private' / 'photo-bench'


def private_path(value: str) -> Path:
    path = Path(value).resolve()
    if not path.is_relative_to(PRIVATE.resolve()):
        raise ValueError('Photo outputs must stay under .private/photo-bench/')
    return path


def prepare(source: Path, output: Path) -> dict:
    photos = sorted(p for p in source.iterdir() if p.is_file() and p.suffix.lower() in SUPPORTED)
    if not photos:
        raise ValueError('No supported still images')
    output.mkdir(parents=True, exist_ok=False)
    records, failures, seen = [], [], {}
    for photo in photos:
        digest = sha256(photo)
        if digest in seen:
            records.append({'source_name': photo.name, 'duplicate_of': seen[digest], 'source_sha256': digest})
            continue
        identifier = 'photo-' + digest[:16]
        try:
            record = import_photo(photo, output / identifier)
            record['directory'] = identifier
            records.append(record)
            seen[digest] = identifier
            print(json.dumps({'source': photo.name, 'status': 'prepared',
                              'dimensions': [record['master']['width'], record['master']['height']]}), flush=True)
        except Exception as exc:
            failures.append({'source_name': photo.name, 'source_sha256': digest,
                             'status': 'failed', 'error_type': type(exc).__name__, 'error': str(exc)})
            print(json.dumps({'source': photo.name, 'status': 'failed', 'error_type': type(exc).__name__}), flush=True)
    manifest = {'schema': 'benchmate.photo_library.v1', 'use': 'local development only',
                'same_state_groups': [], 'grouping_note': 'No photos assumed to show the same wiring state.',
                'records': records, 'failures': failures, 'external_requests': 0, 'hardware_commands': 0}
    (output / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    shutil.copyfile(Path(__file__).with_name('viewer.html'), output / 'index.html')
    return manifest


class LocalGalleryHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        allowed = {f'127.0.0.1:{self.server.server_port}', f'localhost:{self.server.server_port}'}
        if self.headers.get('Host') not in allowed:
            self.send_error(403)
            return
        target = Path(self.translate_path(self.path)).resolve()
        if not target.is_relative_to(Path(self.directory).resolve()):
            self.send_error(403)
            return
        super().do_GET()

    def do_HEAD(self):
        self.send_error(405)

    def end_headers(self):
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Referrer-Policy', 'no-referrer')
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Content-Security-Policy', "default-src 'self'; img-src 'self' blob:; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'")
        super().end_headers()

    def list_directory(self, path):
        self.send_error(403)
        return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    ingest = commands.add_parser('prepare')
    ingest.add_argument('--source', default='pictures')
    ingest.add_argument('--output', required=True)
    crop = commands.add_parser('crop')
    crop.add_argument('--master', required=True)
    crop.add_argument('--box', type=int, nargs=4, required=True, metavar=('LEFT', 'TOP', 'RIGHT', 'BOTTOM'))
    crop.add_argument('--output', required=True)
    serve = commands.add_parser('serve')
    serve.add_argument('--library', required=True)
    serve.add_argument('--port', type=int, default=8768)
    args = parser.parse_args()
    if args.command == 'prepare':
        result = prepare(Path(args.source), private_path(args.output))
        print(json.dumps({'prepared': sum('master' in x for x in result['records']), 'failed': len(result['failures']),
                          'same_state_groups': 0, 'external_requests': 0, 'hardware_commands': 0}))
        if result['failures']:
            raise SystemExit(1)
    elif args.command == 'crop':
        out = private_path(args.output)
        if out.with_suffix('.json').exists():
            raise FileExistsError('Preserve existing crop record')
        result = clean_derivative(private_path(args.master), out, tuple(args.box))
        out.with_suffix('.json').write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps(result))
    else:
        folder = private_path(args.library)
        if not (folder / 'manifest.json').is_file():
            raise ValueError('Expected a prepared photo library')
        server = ThreadingHTTPServer(('127.0.0.1', args.port), partial(LocalGalleryHandler, directory=str(folder)))
        print(f'Local photo review: http://127.0.0.1:{server.server_port}', flush=True)
        server.serve_forever()


if __name__ == '__main__':
    main()
