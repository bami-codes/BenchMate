"""Per-specimen outcomes for the numbers scene, read only from benchmark results.

usage: python extract_benchmark.py <runs/linear-benchmark or .../dev> [--dev]
Writes data/benchmark.json. With --dev the scene shows a DEVELOPMENT watermark;
development numbers never go into the final video.
"""
import json, os, sys
from pathlib import Path

V = os.path.dirname(os.path.abspath(__file__))
ORDER = {'A': ['nominal', 'r_changed', 'c_changed'], 'B': ['rc', 'rc_input_branch']}
ROWS = {'A': [('no_tool', 'Spark, no measurements'), ('random', 'Random experiments'),
              ('fixed', 'Fixed expert plan'), ('engine', 'Engine ranking'), ('spark', 'Spark + bench'), ('spark_hidden', 'Spark, ranking hidden'), ('spark_open', 'Spark Open + bench')],
        'B': [('random', 'Random experiments'), ('engine', 'Engine ranking'),
              ('fixed', 'Fixed expert plan'), ('spark_hidden', 'Spark, ranking hidden'), ('spark', 'Spark + bench'), ('spark_open', 'Spark Open + bench')]}


def extract(runs, dev=False):
    runs = Path(runs)
    sys.path.insert(0, str(Path(os.environ.get('BENCHMATE_ROOT', Path(V).parent)) / 'scripts'))
    import benchmark_linear as bl
    specs = {s['id']: s for s in bl.load_specimens(bl.load_protocol(), dev)}
    out = {'attempt_basis': 'first attempt; failures are not replaced by retries', 'development': dev, 'label': 'Synthetic bench (development specimens)' if dev else 'Synthetic bench',
           'circuits': len(specs), 'tasks': {}}
    for task, rows in ROWS.items():
        inside = sorted((s for s in specs.values() if s['task'] == task and s['in_family']),
                        key=lambda s: (ORDER[task].index(s['truth_class']), s['id']))
        outside = sorted(s['id'] for s in specs.values() if s['task'] == task and not s['in_family'])
        table = []
        for arm, label in rows:
            path = runs / arm / 'results.jsonl'
            if not path.exists():
                table.append({'arm': arm, 'label': label, 'status': 'not run'}); continue
            latest = {}
            for line in path.read_text().splitlines():
                r = json.loads(line)
                if r['protocol_sha256'] != bl.sha256(bl.PROTOCOL):
                    raise SystemExit('Video data must match the reviewed benchmark protocol')
                if r['task'] == task:
                    latest.setdefault((r['specimen'], r['replicate']), r)
            if not latest:
                table.append({'arm': arm, 'label': label, 'status': 'not run'}); continue
            reps = list(range(bl.load_protocol()['arms']['random']['replicates'])) if arm == 'random' else [0]
            strips = [[latest.get((s['id'], k), {}).get('outcome', 'missing') for s in inside] for k in reps]
            far = [[latest.get((sid, k), {}).get('outcome', 'missing') for sid in outside] for k in reps]
            mounts = [r.get('simulated_mountings') for r in latest.values() if r['task'] == task and r.get('simulated_mountings') is not None]
            table.append({'arm': arm, 'label': label, 'strips': strips, 'outside': far,
                          'status': 'complete' if all(o != 'missing' for st in strips + far for o in st) else 'incomplete',
                          'independent_circuits': len(inside), 'repetitions': len(reps),
                          'correct_abstentions': sum(o == 'rejected' for st in far for o in st),
                          'correct': sum(o == 'correct' for st in strips for o in st), 'of': sum(len(st) for st in strips),
                          'wrong': sum(o == 'wrong' for st in strips + far for o in st),
                          'mean_wiring_changes': round(sum(mounts) / len(mounts), 2) if mounts else None})
        out['tasks'][task] = {'classes': [s['truth_class'] for s in inside], 'rows': table}
    return out


def main():
    out = extract(sys.argv[1], '--dev' in sys.argv)
    target = Path(V, 'data/benchmark.json'); target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(out, indent=1))
    for task, t in out['tasks'].items():
        print(task, [(r['arm'], r.get('correct'), r.get('of'), r.get('wrong')) for r in t['rows']])


if __name__ == '__main__':
    main()
