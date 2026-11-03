#!/usr/bin/env python3
"""Versioned R/C/D diagnosis. Default commands are offline; never open serial.

The physical adapter is deliberately not exposed before its frozen acquisition
protocol is reviewed. --provider meta requires --execute and separate user
authorization; this implementation task does not authorize that command.
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
from benchmate.records import Recorder, canonical
from benchmate.netlist import ngspice_version
from benchmate.netlist_diagnosis.bench import MockBench
from benchmate.netlist_diagnosis.cases import CATALOGUE, LED, mock_review, specimen
from benchmate.netlist_diagnosis.controller import ScriptedController
from benchmate.netlist_diagnosis.design import digest, checked
from benchmate.netlist_diagnosis.session import DiagnosisSession, PROMPT, TOOLS
from benchmate.netlist_diagnosis.protocol import source_hashes, prepare

FROZEN_SOURCES = source_hashes()
ENVIRONMENT = {'python': sys.version.split()[0], 'numpy': np.__version__, 'scipy': scipy.__version__,
               'ngspice': ngspice_version(shutil.which('ngspice')) if shutil.which('ngspice') else None}


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)+'\n')


def local_publication(log):
    def publish(frozen, sha):
        if digest(frozen) != sha:
            raise ValueError('Forecast hash mismatch.')
        (log.path/'predictions-frozen.json').write_bytes(canonical(frozen)+b'\n')
        return {'sha256': sha, 'published': True, 'remote': False, 'scope': 'Local mock only'}
    return publish


def run_one(case, output, *, repaired=False, provider='scripted', execute=False, design_file=None):
    if provider == 'meta' and not execute:
        raise ValueError('Paid requests require --execute after separate authorization.')
    design = checked(json.loads(Path(design_file).read_text())) if design_file else mock_review(case)
    if design['elements'] != case['design']:
        raise ValueError('The selected development fixture must match the supplied reviewed netlist.')
    if source_hashes() != FROZEN_SOURCES:
        raise ValueError('Source changed since this process started; use a new recorded attempt.')
    log = Recorder(output, mode='netlist_diagnosis_mock_' + provider)
    save(log.path/'source-manifest.json', FROZEN_SOURCES)
    for name in FROZEN_SOURCES:
        target = log.path/'source'/name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((ROOT/name).read_bytes())
    log.add('source_manifest_frozen', {'sha256': FROZEN_SOURCES, 'paid_requests': 0, 'hardware_commands': 0})
    log.add('numerical_environment', ENVIRONMENT)
    # Evaluation truth is local and is never included in session.snapshot().
    save(log.path/'evaluator-truth.json', {'development_case': case['id'], 'repaired': repaired,
                                         'elements': specimen(case, repaired=repaired),
                                         'diode': case.get('diode_truth'), 'source': 'mock'})
    bench = MockBench(specimen(case, repaired=repaired), log, diode=case.get('diode_truth'))
    session = DiagnosisSession(bench, log, design, local_publication(log),
                               actor='muse_spark' if provider == 'meta' else 'scripted_controller')
    model = None
    try:
        if provider == 'meta':
            from benchmate.providers import MetaToolSession
            model = MetaToolSession(prompt=PROMPT, tools=TOOLS, log=log, effort='medium', max_requests=8,
                                    env_path=ROOT/'.env', budget_path=ROOT/'.private/api-budget.json')
        else:
            model = ScriptedController()
        result = {**drive_agent(session, model), **model.metadata()}
        save(log.path/'result.json', result)
        log.add('run_completed', result)
        return log.path, result
    except BaseException as exc:
        result = {'source': 'mock', 'error': str(exc), 'automatic_retry': False,
                  **(model.metadata() if model else {})}
        save(log.path/'result.json', result)
        log.add('run_failed', result)
        raise
    finally:
        if model: model.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('run-mock')
    p.add_argument('--case', choices=[c['id'] for c in CATALOGUE], required=True)
    p.add_argument('--repaired', action='store_true')
    p.add_argument('--provider', choices=['scripted', 'meta'], default='scripted')
    p.add_argument('--execute', action='store_true')
    p.add_argument('--reviewed-design')
    p.add_argument('--output', default=str(ROOT/'runs/netlist-diagnosis'))
    p = sub.add_parser('evaluate')
    p.add_argument('--output', required=True)
    p = sub.add_parser('identify')
    p.add_argument('--output', required=True)
    p = sub.add_parser('prepare')
    p.add_argument('--reviewed-design', required=True)
    p.add_argument('--output', required=True)
    p = sub.add_parser('catalogue')
    args = parser.parse_args()
    if args.command == 'catalogue':
        print(json.dumps({'cases': CATALOGUE, 'deferred': LED}, indent=2)); return
    if args.command == 'prepare':
        design = checked(json.loads(Path(args.reviewed_design).read_text()))
        out = Path(args.output)
        out.mkdir(parents=True, exist_ok=False)
        save(out/'protocol.json', prepare(design))
        save(out/'reviewed-design.json', design)
        save(out/'operator-confirmation-template.json', {
            'template_only': True, 'choice': None, 'fixture': None,
            'reviewed_design_sha256': digest(design), 'USB_connected': False,
            'USB_off_wiring_confirmed': False})
        print(json.dumps({'prepared': str(out), 'paid_requests': 0, 'hardware_commands': 0,
                          'execution_authorized': False})); return
    if args.command == 'identify':
        from benchmate.netlist_diagnosis.identifiability import evaluate
        path = Path(args.output)
        if path.exists():
            raise ValueError('Use a new output file; prior results are never overwritten.')
        path.parent.mkdir(parents=True, exist_ok=True)
        result = evaluate()
        save(path, result)
        print(json.dumps({'output': str(path), 'all_expectations_met': result['all_expectations_met'], 'paid_requests': 0}))
        raise SystemExit(0 if result['all_expectations_met'] else 1)
    if args.command == 'run-mock':
        case = next(c for c in CATALOGUE if c['id'] == args.case)
        path, result = run_one(case, args.output, repaired=args.repaired, provider=args.provider,
                               execute=args.execute, design_file=args.reviewed_design)
        print(json.dumps({'record': str(path), 'report': result['agent_report'], 'http_requests': result['http_requests']})); return
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=False)
    rows = []
    for case in CATALOGUE:
        for repaired in (False, True):
            path, result = run_one(case, out/'records', repaired=repaired)
            expected = {'verdict': 'consistent', 'components': []} if repaired else case['expected']
            got = {k: result['agent_report'][k] for k in expected}
            row = {'case': case['id'], 'repaired': repaired, 'record': str(path.relative_to(out)),
                   'expected': expected, 'actual': got, 'matches_expectation': got == expected,
                   'assessment': result['assessment'], 'proposals': result['proposals'],
                   'source': 'mock', 'http_requests': 0, 'physical_measurements': 0}
            rows.append(row)
            save(out/'partial-results.json', rows)
            print(json.dumps({k: v for k, v in row.items() if k not in ('assessment', 'proposals')}), flush=True)
    summary = {'version': 'netlist-diagnosis-v1', 'validation': 'Shared-ngspice development rehearsal, not a blinded physical accuracy evaluation.',
               'results': rows, 'all_expectations_met': all(r['matches_expectation'] for r in rows),
               'source_sha256': FROZEN_SOURCES, 'environment': ENVIRONMENT,
               'deferred': LED, 'paid_requests': 0, 'hardware_commands': 0}
    save(out/'summary.json', summary)
    raise SystemExit(0 if summary['all_expectations_met'] else 1)


if __name__ == '__main__':
    main()
