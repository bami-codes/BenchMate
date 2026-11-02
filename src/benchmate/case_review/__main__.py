"""Run the local recorded D01 case workflow. No API key or board required."""
import argparse
from pathlib import Path
from .web import make_server


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8770)
    parser.add_argument('--output', default='.private/case-review')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[3]
    output = (root / args.output).resolve()
    if not output.is_relative_to((root / '.private/case-review').resolve()):
        raise ValueError('Case questions and reviews must stay under .private/case-review/')
    server = make_server(root=root, output=output, port=args.port)
    print(f'BenchMate case review: http://127.0.0.1:{server.server_port} · recorded mode · API/USB off', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
