#!/usr/bin/env python3
"""Common six-circuit offline development runner, including BC547B/red LED.

No physical execution command is exposed. Meta mock runs need --execute after
separate user authorization; ordinary evaluation never constructs a provider.
"""
import argparse
import json
from pathlib import Path
import shutil
import sys

import numpy as np
import scipy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from benchmate.agent import drive_agent
from benchmate.netlist import ngspice_version
from benchmate.records import Recorder, canonical
from benchmate.netlist_diagnosis.bench import MockBench
from benchmate.netlist_diagnosis.controller import ScriptedController
from benchmate.netlist_diagnosis.design import digest
from benchmate.netlist_diagnosis_v2.bench import LEDMockBench
from benchmate.netlist_diagnosis_v2.cases import CATALOGUE, reviewed, truth
from benchmate.netlist_diagnosis_v2.protocol import source_hashes, prepare
from benchmate.netlist_diagnosis_v2.session import Session, PROMPT, TOOLS, checked

FROZEN_SOURCES = source_hashes()
ENVIRONMENT = {'python': sys.version.split()[0], 'numpy': np.__version__, 'scipy': scipy.__version__,
               'ngspice': ngspice_version(shutil.which('ngspice')) if shutil.which('ngspice') else None}


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)+'\n')


def run_one(case, output, *, repaired=False, provider='scripted', execute=False):
    if provider == 'meta' and not execute:
        raise ValueError('Paid requests require --execute after separate authorization.')
    if source_hashes() != FROZEN_SOURCES:
        raise ValueError('Source changed during this process; use a new recorded attempt.')
    design = reviewed(case)
    log = Recorder(output, mode='netlist_diagnosis_v2_mock_'+provider)
    save(log.path/'source-manifest.json', FROZEN_SOURCES)
    for name in FROZEN_SOURCES:
        dest = log.path/'source'/name
        dest.parent.mkdir(parents=True, exist_ok=True); dest.write_bytes((ROOT/name).read_bytes())
    log.add('source_manifest_frozen', {'sha256': FROZEN_SOURCES})
    log.add('numerical_environment', ENVIRONMENT)
    save(log.path/'evaluator-truth.json', {'case': case['id'], 'repaired': repaired, 'truth': truth(case, repaired),
                                         'source': 'mock', 'transmitted_to_agent': False})
    bench = (LEDMockBench(truth(case, repaired), log) if case['id'] == 'dim-led' else
             MockBench(truth(case, repaired), log, diode=case.get('diode_truth')))
    def publish(frozen, sha):
        if digest(frozen) != sha: raise ValueError('Forecast digest mismatch.')
        (log.path/'predictions-frozen.json').write_bytes(canonical(frozen)+b'\n')
        return {'sha256': sha, 'published': True, 'remote': False, 'scope': 'Local mock only'}
    session = Session(bench, log, design, publish, actor='muse_spark' if provider == 'meta' else 'scripted_controller')
    controller = None
    try:
        if provider == 'meta':
            from benchmate.providers import MetaToolSession
            controller = MetaToolSession(prompt=PROMPT, tools=TOOLS, log=log, effort='medium', max_requests=8,
                                         env_path=ROOT/'.env', budget_path=ROOT/'.private/api-budget.json')
        else:
            controller = ScriptedController()
        result = {**drive_agent(session, controller), **controller.metadata()}
        save(log.path/'result.json', result); log.add('run_completed', result)
        return log.path, result
    except BaseException as exc:
        result = {'source': 'mock', 'error': str(exc), 'automatic_retry': False,
                  **(controller.metadata() if controller else {})}
        save(log.path/'result.json', result); log.add('run_failed', result)
        raise
    finally:
        if controller: controller.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('catalogue')
    p = sub.add_parser('run-mock')
    p.add_argument('--case', choices=[c['id'] for c in CATALOGUE], required=True)
    p.add_argument('--repaired', action='store_true')
    p.add_argument('--provider', choices=['scripted', 'meta'], default='scripted')
    p.add_argument('--execute', action='store_true')
    p.add_argument('--output', default=str(ROOT/'runs/netlist-diagnosis-v2'))
    p = sub.add_parser('evaluate'); p.add_argument('--output', required=True)
    p = sub.add_parser('prepare'); p.add_argument('--reviewed-design', required=True); p.add_argument('--output', required=True)
    args = parser.parse_args()
    if args.command == 'catalogue':
        print(json.dumps({'version': 'v2', 'cases': CATALOGUE, 'physical_LED_qualified': False}, indent=2)); return
    if args.command == 'prepare':
        design = checked(json.loads(Path(args.reviewed_design).read_text()))
        out = Path(args.output); out.mkdir(parents=True, exist_ok=False)
        save(out/'protocol.json', prepare(design))
        print(json.dumps({'prepared': str(out), 'paid_requests': 0, 'hardware_commands': 0})); return
    if args.command == 'run-mock':
        case = next(c for c in CATALOGUE if c['id'] == args.case)
        path, result = run_one(case, args.output, repaired=args.repaired, provider=args.provider, execute=args.execute)
        print(json.dumps({'record': str(path), 'report': result['agent_report'], 'http_requests': result['http_requests']})); return
    out = Path(args.output); out.mkdir(parents=True, exist_ok=False)
    rows = []
    for case in CATALOGUE:
        for repaired in (False, True):
            path, result = run_one(case, out/'records', repaired=repaired)
            expected = {'verdict': 'consistent', 'components': []} if repaired else case['expected']
            actual = {k: result['agent_report'][k] for k in expected}
            row = {'case': case['id'], 'repaired': repaired, 'expected': expected, 'actual': actual,
                   'matches_expectation': actual == expected, 'record': str(path.relative_to(out)),
                   'assessment': result['assessment'], 'proposals': result['proposals'],
                   'source': 'mock', 'http_requests': 0, 'physical_measurements': 0}
            rows.append(row); save(out/'partial-results.json', rows)
            print(json.dumps({k: v for k, v in row.items() if k not in ('assessment', 'proposals')}), flush=True)
    result = {'version': 'netlist-diagnosis-v2', 'results': rows,
              'all_expectations_met': all(r['matches_expectation'] for r in rows),
              'source_sha256': FROZEN_SOURCES, 'environment': ENVIRONMENT,
              'validation': 'Shared-ngspice software rehearsal, scripted choices; not physical or Spark accuracy.',
              'case_count': 6, 'paid_requests': 0, 'hardware_commands': 0, 'physical_LED_qualified': False}
    save(out/'summary.json', result)
    raise SystemExit(0 if result['all_expectations_met'] else 1)


if __name__ == '__main__':
    main()
