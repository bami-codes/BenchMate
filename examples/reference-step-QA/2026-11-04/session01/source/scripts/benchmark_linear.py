#!/usr/bin/env python3
"""Preregistered synthetic benchmark of experiment choice (protocol linear-benchmark-v1.1).

Every arm gets the same specimens, noise seeds, menu, budget and verification rule.
Scripted arms run offline. Spark arms make API calls only with --execute and stop
before a run that could cross --max-requests. Every finished run appends one row to
results.jsonl; score reads every row. Nothing here chooses favourable runs.

  plan                    print protocol hash, specimen hash and request estimate
  write-specimens         generate specimens.json from protocol.json (truth table)
  run --arm ARM           run every pending specimen for ARM; resumable, never repeats a finished run
  score                   one table over every arm and specimen

Docs: docs/linear-benchmark.md
"""
import argparse, ast, hashlib, json, subprocess, sys, time, traceback
from math import sqrt
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
import numpy as np
from benchmate.simulation import acquire
from benchmate.physics import RCModel
from benchmate.records import Recorder
from benchmate.continuous_agent import ContinuousSession, CONTINUOUS_PROMPT
from benchmate.experiments import drive_engine
from benchmate.agent import drive_agent

BENCH = ROOT / 'examples/linear-benchmark/2026-11-01'
PROTOCOL = BENCH / 'protocol.json'
SPECIMENS = BENCH / 'specimens.json'
RUNS = ROOT / 'runs/linear-benchmark/v1.1'
SOURCE_MANIFEST = BENCH / 'source-manifest.json'
SCRIPTED = ('engine', 'fixed', 'random')
LIVE = ('spark', 'spark_hidden', 'spark_open', 'no_tool')
ARMS = SCRIPTED + LIVE
import platform, scipy
ENVIRONMENT = {'python': platform.python_version(), 'numpy': np.__version__, 'scipy': scipy.__version__,
               'platform': platform.platform(terse=True)}
TRANSPORT = ('Provider network failure', 'returned HTTP 429', 'returned HTTP 5')


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_protocol():
    return json.loads(PROTOCOL.read_text())


def source_hashes():
    """Freeze the local import closure, including the optional provider adapter."""
    pending = [Path(__file__).resolve(), ROOT / 'src/benchmate/providers_baseten.py']
    seen = {}
    while pending:
        path = pending.pop()
        name = str(path.relative_to(ROOT))
        if name in seen:
            continue
        seen[name] = sha256(path)
        for node in ast.walk(ast.parse(path.read_text())):
            names = []
            if isinstance(node, ast.ImportFrom):
                module = node.module or ''
                if node.level:
                    names = [module.split('.')[0]] if module else [n.name for n in node.names]
                elif module == 'benchmate' or module.startswith('benchmate.'):
                    names = [module.split('.')[1]] if '.' in module else [n.name for n in node.names]
            elif isinstance(node, ast.Import):
                names = [n.name.split('.')[1] for n in node.names if n.name.startswith('benchmate.')]
            for module in names:
                target = ROOT / 'src/benchmate' / (module + '.py')
                if target.is_file():
                    pending.append(target)
    init = ROOT / 'src/benchmate/__init__.py'
    seen[str(init.relative_to(ROOT))] = sha256(init)
    return dict(sorted(seen.items()))


def validate_freeze(protocol, *, publication=False):
    manifest = json.loads(SOURCE_MANIFEST.read_text())
    if sha256(SOURCE_MANIFEST) != protocol.get('source_manifest_sha256') or manifest['files'] != source_hashes():
        raise SystemExit('Benchmark source freeze mismatch; no evaluation or provider call')
    if publication:
        # Fail closed before evaluation; this does not run specimens or call a model.
        def git(*args):
            return subprocess.check_output(['git', *args], cwd=ROOT, stderr=subprocess.PIPE)
        files = list(manifest['files']) + [str(p.relative_to(ROOT)) for p in (PROTOCOL, SPECIMENS, SOURCE_MANIFEST)]
        for name in files:
            if git('show', 'HEAD:' + name) != (ROOT / name).read_bytes():
                raise SystemExit('Uncommitted benchmark dependency: ' + name)
        head = git('rev-parse', 'HEAD').decode().strip()
        remote = git('ls-remote', 'origin', 'refs/heads/main').decode().split()[0]
        if head != remote:
            raise SystemExit('Current benchmark commit must be pushed to origin/main before evaluation')
        return head


def generate_specimens(protocol, dev=False):
    """Deterministic truth table from the protocol's master seed (or its separate
    development seed). Order is shuffled so run order is not grouped by class."""
    rng = np.random.default_rng(protocol['development_seed' if dev else 'master_seed'])
    rows = []
    for task, spec in protocol['tasks'].items():
        group = []
        for cls in spec['classes']:
            for _ in range(cls['count']):
                values = {k: float(np.exp(rng.uniform(*np.log(b)))) for k, b in cls['sampling_bounds'].items()}
                group.append({'task': task, 'mode': spec['mode'], 'truth_class': cls['name'],
                              'in_family': cls['in_family'], 'r_ohm': values['r_ohm'], 'c_f': values['c_f'],
                              'input_parallel_ohm': values.get('input_parallel_ohm')})
        order = rng.permutation(len(group))
        for index, k in enumerate(order, 1):
            row = group[k]
            row['id'] = ('dev' if dev else '') + f'{task}{index:02d}'
            row['noise_seed'] = int(rng.integers(2**31 - 1))
            rows.append(row)
    return rows


def load_specimens(protocol, dev=False):
    if dev:
        return generate_specimens(protocol, dev=True)
    data = json.loads(SPECIMENS.read_text())
    if sha256(SPECIMENS) != protocol['specimens_sha256']:
        raise SystemExit('specimens.json does not match the hash recorded in protocol.json')
    generated = generate_specimens(protocol)
    def same_row(a, b):
        if a.keys() != b.keys():
            return False
        return all(np.isclose(a[k], b[k], rtol=1e-12, atol=0.)
                   if isinstance(a[k], float) and isinstance(b[k], float) else a[k] == b[k] for k in a)
    # NumPy/libm exp(log(x)) may differ by a few ulps across platforms. The exact
    # committed table/hash is authoritative; only regeneration gets this tolerance.
    if len(data) != len(generated) or not all(same_row(a, b) for a, b in zip(data, generated)):
        raise SystemExit('specimens.json does not match the protocol generator')
    return data


class BenchSession(ContinuousSession):
    """ContinuousSession that also notes, before each measurement, the engine's top
    affordable action. Used for every arm; it never changes what the model sees."""
    def measure(self, action, reason):
        affordable = [a['action'] for a in self.ranked if a['physical_acquisitions'] <= 3 - self.diagnostic_acquisitions]
        top = affordable[0] if affordable else None
        result = super().measure(action, reason)
        self.choices = getattr(self, 'choices', []) + [{'chosen': action, 'engine_top': top}]
        return result


class HiddenRankingSession(BenchSession):
    """Same session, but the engine's action ranking is withheld from the model."""
    def snapshot(self):
        snap = super().snapshot()
        snap.pop('action_ranking', None)
        snap['menu_actions'] = list(self.menu)
        snap['ranking_note'] = HIDDEN_NOTE
        return snap


HIDDEN_NOTE = ('No engine ranking is provided. Names encode settings: step_a{half_amplitude_V}_s{series_shunt_ohm}_l{load_ohm}, '
               'sine_f{grid_index}_a{amplitude_V}_s{shunt}_l{load}; l0 means no load. shunt_dc_pair costs 2 diagnostic '
               'acquisitions, every other action costs 1. measurement_details returns the settings of any action.')
HIDDEN_PROMPT = CONTINUOUS_PROMPT.replace(
    'Read the\ncurrent candidate support, identifiability, numerical evidence and ranked menu.',
    'Read the\ncurrent candidate support, identifiability and numerical evidence. No ranking of the\n'
    'menu is provided in this run: choose each measurement from your own reasoning.')
assert HIDDEN_PROMPT != CONTINUOUS_PROMPT, 'hidden-ranking prompt edit did not apply'

NO_TOOL_TEMPLATE = {
    'A': ('Designed RC low-pass: 10 kΩ, 1 µF (τ = 10 ms). Driven by an ideal step and measured '
          'unloaded, its time constant is {tau_ms:.1f} ms. Declared explanations: nominal (R 9.5–10.5 kΩ, '
          'C 0.9–1.1 µF); r_changed (R 15–25 kΩ, C 0.9–1.1 µF); c_changed (R 9.5–10.5 kΩ, C 1.5–2.5 µF). '
          'You cannot request more measurements. Which explanation does this evidence support? Reply with '
          'JSON only: {{"answer": "nominal" | "r_changed" | "c_changed" | "cannot_tell" | "none_fit", '
          '"reason": "<under 40 words>"}}'),
}


def make_session(spec, protocol, log, hidden=False):
    truth = RCModel(spec['r_ohm'], spec['c_f'], spec['input_parallel_ohm'])
    rng = np.random.default_rng(spec['noise_seed'])
    cls = HiddenRankingSession if hidden else BenchSession
    return cls(lambda settings: acquire(truth, settings, rng=rng), log, mode=spec['mode'])


def scripted_finish(session, label):
    if session.analysis['status'] == 'verification_required':
        session.dispatch('verify_prediction', {})
    verified = session.analysis['status'] == 'verified_within_declared_candidates'
    session.dispatch('finish_report', {
        'verdict': 'verified' if verified else 'abstained',
        'candidate': session.analysis['supported_candidates'][0] if verified else '',
        'current_explanation': f'{label}: synthetic observations analyzed within the declared families.',
        'unresolved': 'Hardware performance and circuits outside the declared families remain unverified.',
        'next_observation': {'kind': 'menu_action', 'action': session.actions[-1] if session.actions else next(iter(session.menu)),
                             'requirement': '', 'reason': 'Repeat the last diagnostic condition on hardware.'}})


def drive_fixed(session, plan):
    session.dispatch('inspect_experiment', {})
    for action in plan:
        if session.analysis['status'] != 'unresolved':
            break
        if session.menu[action].physical_acquisitions > 3 - session.diagnostic_acquisitions:
            break
        session.dispatch('measure', {'action': action, 'reason': 'Preregistered fixed plan; no model call.'})
    scripted_finish(session, 'Fixed plan')


def drive_random(session, rng):
    session.dispatch('inspect_experiment', {})
    while session.analysis['status'] == 'unresolved':
        affordable = [a for a, s in session.menu.items() if s.physical_acquisitions <= 3 - session.diagnostic_acquisitions]
        if not affordable:
            break
        session.dispatch('measure', {'action': affordable[int(rng.integers(len(affordable)))],
                                     'reason': 'Seeded uniform choice among affordable actions; no model call.'})
    scripted_finish(session, 'Random choice')


def make_live_model(arm, session, log, protocol):
    live = protocol['live']
    if arm == 'spark_open':
        try:
            from benchmate.providers_baseten import BasetenToolSession
        except ImportError:
            raise SystemExit('spark_open needs benchmate.providers_baseten.BasetenToolSession (same tools/prompt, '
                             'chat-completions transport). Validate it on dev specimens first; otherwise report the arm as not run.')
        return BasetenToolSession(prompt=CONTINUOUS_PROMPT, tools=session.tools, log=log,
                                  env_path=str(ROOT / '.env'), budget_path=str(ROOT / '.private/api-budget.json'),
                                  max_requests=live['max_requests_per_run'], max_payload_bytes=live['max_payload_bytes'])
    from benchmate.providers import MetaToolSession
    return MetaToolSession(prompt=HIDDEN_PROMPT if arm == 'spark_hidden' else CONTINUOUS_PROMPT,
                           tools=session.tools, log=log, effort=live['effort'],
                           env_path=str(ROOT / '.env'), budget_path=str(ROOT / '.private/api-budget.json'),
                           max_requests=live['max_requests_per_run'], max_payload_bytes=live['max_payload_bytes'])


def ask_no_tool(spec, protocol, log, attempts):
    import httpx
    from benchmate.config import load_keys, redact
    from benchmate.providers import PROVIDERS, reserve_budget, ProviderError
    prompt = NO_TOOL_TEMPLATE[spec['task']].format(tau_ms=spec['r_ohm'] * spec['c_f'] * 1e3)
    payload = {'model': PROVIDERS['meta']['model'], 'reasoning': {'effort': protocol['live']['effort']},
               'store': False, 'max_output_tokens': 8192, 'input': [{'role': 'user', 'content': prompt}]}
    keys = load_keys(str(ROOT / '.env'))
    key = keys.get(PROVIDERS['meta']['key'])
    if not key:
        raise ProviderError('Local Meta key unavailable')
    log.add('no_tool_request', {'prompt': prompt, 'payload_without_input': {k: v for k, v in payload.items() if k != 'input'}})
    reserve_budget(ROOT / '.private/api-budget.json', 'meta', 1.)
    attempts['requests'] += 1
    log.add('provider_request_attempt', {'provider': 'meta', 'number': attempts['requests']})
    began = time.monotonic()
    try:
        with httpx.Client(timeout=90, follow_redirects=False) as client:
            response = client.post(PROVIDERS['meta']['url'], json=payload, headers={'Authorization': 'Bearer ' + key})
    except httpx.HTTPError as exc:
        raise ProviderError('Provider network failure: ' + type(exc).__name__) from None
    if response.status_code >= 400:
        raise ProviderError(f'meta returned HTTP {response.status_code}; no retry')
    body = response.json()
    text = '\n'.join(c.get('text', '') for item in body.get('output', []) if item.get('type') == 'message'
                     for c in item.get('content', []) if c.get('type') == 'output_text')
    answer = None
    try:
        start, end = text.index('{'), text.rindex('}') + 1
        parsed = json.loads(text[start:end])
        if parsed.get('answer') in ('nominal', 'r_changed', 'c_changed', 'cannot_tell', 'none_fit'):
            answer = parsed['answer']
    except ValueError:
        pass
    reply = redact({'response_id': body.get('id'), 'status': body.get('status'), 'usage': body.get('usage'),
                    'elapsed_s': time.monotonic() - began, 'visible_text_verbatim': text, 'parsed_answer': answer}, keys)
    log.add('no_tool_reply', reply)
    return answer, 1


def outcome(spec, verified, candidate, status):
    """Scoring rule (protocol: scoring). verified means an accepted report with verdict 'verified'."""
    if spec['in_family']:
        if verified:
            return 'correct' if candidate == spec['truth_class'] else 'wrong'
        return 'false_rejection' if status == 'all_candidates_inadequate' else 'abstained'
    if verified:
        return 'wrong'
    return 'rejected' if status == 'all_candidates_inadequate' else 'abstained'


def no_tool_outcome(spec, answer):
    if answer is None:
        return 'unparsed'
    if answer == 'cannot_tell':
        return 'abstained'
    if answer == 'none_fit':
        return 'false_rejection' if spec['in_family'] else 'rejected'
    return outcome(spec, True, answer, 'verified_within_declared_candidates')


def run_one(spec, arm, replicate, protocol, protocol_hash, runs):
    root = runs / arm / (spec['id'] + (f'-r{replicate}' if arm == 'random' else ''))
    log = Recorder(str(root), mode=f'linear_benchmark_{arm}')
    log.add('benchmark_context', {'protocol': protocol['protocol'], 'protocol_sha256': protocol_hash,
                                  'specimen': spec['id'], 'arm': arm, 'replicate': replicate,
                                  'truth_visible_to_model': False, 'environment': ENVIRONMENT})
    row = {'protocol_sha256': protocol_hash, 'specimen': spec['id'], 'task': spec['task'], 'arm': arm,
           'replicate': replicate, 'truth_class': spec['truth_class'], 'record': str(log.path.relative_to(ROOT) if log.path.is_relative_to(ROOT) else log.path)}
    if arm in LIVE:
        from benchmate.providers import PROVIDERS
        row['local_allowance_cap_usd'] = PROVIDERS['baseten' if arm=='spark_open' else 'meta']['cap_usd']
    began = time.monotonic()
    session = model = None
    no_tool_attempts = {'requests': 0}
    try:
        if arm == 'no_tool':
            answer, requests = ask_no_tool(spec, protocol, log, no_tool_attempts)
            row.update(answer=answer, provider_requests=requests, outcome=no_tool_outcome(spec, answer))
        else:
            session = make_session(spec, protocol, log, hidden=arm == 'spark_hidden')
            if arm == 'engine':
                drive_engine(session)
            elif arm == 'fixed':
                drive_fixed(session, protocol['tasks'][spec['task']]['fixed_plan'])
            elif arm == 'random':
                drive_random(session, np.random.default_rng([protocol['master_seed'], ord(spec['task']), int(spec['id'][-2:]), replicate]))
            else:
                model = make_live_model(arm, session, log, protocol)
                drive_agent(session, model)
    except Exception as exc:
        row['error'] = str(exc) if exc.__class__.__name__ in ('ProviderError', 'ToolRejected', 'ValueError') else type(exc).__name__
        log.add('run_failed', {'error': row['error'], 'traceback_tail': traceback.format_exc().splitlines()[-3:]})
    finally:
        if arm == 'no_tool':
            row['provider_requests'] = no_tool_attempts['requests']
        if model is not None:
            row['provider_requests'] = model.requests
            row['provider'] = model.metadata()
            model.close()
    if session is not None:
        report = session.report
        verified = bool(report and report['verdict'] == 'verified')
        row.update(status=session.analysis['status'], supported=session.analysis.get('supported_candidates', []),
                   report_accepted=report is not None, report_verdict=report and report['verdict'],
                   report_candidate=report and report['candidate'], actions=session.actions,
                   diagnostic_acquisitions=session.diagnostic_acquisitions,
                   choices=getattr(session, 'choices', []),
                   simulated_mountings=session.simulated_mountings)
        row['outcome'] = outcome(spec, verified, report and report['candidate'], session.analysis['status']) if report else 'incomplete'
    elif 'outcome' not in row:
        row['outcome'] = 'incomplete'
    row['elapsed_s'] = round(time.monotonic() - began, 2)
    log.add('benchmark_row', row)
    return row


def finished(arm, runs=RUNS):
    path = runs / arm / 'results.jsonl'
    rows = [json.loads(l) for l in path.read_text().splitlines()] if path.exists() else []
    return path, rows


def cmd_run(args):
    protocol, protocol_hash = load_protocol(), sha256(PROTOCOL)
    validate_freeze(protocol, publication=not args.dev)
    if args.arm == 'spark_open' and not args.dev:
        _, development = finished('spark_open', RUNS / 'dev')
        passed_tasks = {r['task'] for r in first_attempts(development).values()
            if r.get('protocol_sha256') == protocol_hash and r.get('report_accepted')
            and r.get('outcome') in ('correct', 'rejected') and not r.get('error')
            and r.get('provider', {}).get('provider') == 'baseten' and r.get('provider_requests', 0) > 0}
        if passed_tasks != {'A', 'B'}:
            raise SystemExit('Spark Open needs successful actual Baseten development runs in A and B before evaluation')
    runs = RUNS / 'dev' if args.dev else RUNS
    specs = [s for s in load_specimens(protocol, args.dev) if s['task'] in protocol['arms'][args.arm]['tasks']]
    if args.task:
        specs = [s for s in specs if s['task'] == args.task]
        if not specs:
            raise SystemExit('Selected task is unavailable for this arm')
    if args.limit:
        if not args.dev:
            raise SystemExit('--limit is for development specimens only; evaluation runs every specimen')
        specs = specs[:args.limit]
    if args.arm in LIVE and not args.execute:
        raise SystemExit(f'{args.arm} makes API calls; pass --execute and --max-requests after the user agrees to the count')
    path, rows = finished(args.arm, runs)
    if any(r['protocol_sha256'] != protocol_hash for r in rows):
        raise SystemExit('Existing rows use a different protocol; preserve them in a separate version directory')
    indexed = {(ROOT / r['record']).resolve() for r in rows if r.get('record')}
    orphans = [p.parent for p in (runs / args.arm).glob('*/*/events.jsonl') if p.parent.resolve() not in indexed]
    if orphans:
        raise SystemExit('Unindexed interrupted attempt exists; preserve and audit it before resuming. No automatic rerun.')
    allowance_cap = getattr(args, 'allowance_cap', None)
    if allowance_cap is not None:
        if args.arm not in LIVE or not np.isfinite(allowance_cap) or allowance_cap <= 0:
            raise SystemExit('--allowance-cap requires a positive finite amount and a live arm')
        from benchmate.providers import PROVIDERS
        # Explicit per-process setting, logged per run; never alters frozen shared sources.
        PROVIDERS['baseten' if args.arm == 'spark_open' else 'meta']['cap_usd'] = allowance_cap
    done = {}
    for r in rows:
        done.setdefault((r['specimen'], r['replicate']), []).append(r)
    replicates = range(protocol['arms']['random']['replicates']) if args.arm == 'random' else [0]
    # The cap survives process restarts and includes failed calls and other tasks in this arm.
    used = sum(r.get('provider_requests', 0) or 0 for r in rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    for spec in specs:
        for rep in replicates:
            previous = done.get((spec['id'], rep), [])
            if previous:
                last = previous[-1]
                transport = any(t in last.get('error', '') for t in TRANSPORT) and last.get('provider_requests', 0) <= 1
                if not (args.rerun_transport and transport and len(previous) == 1):
                    continue
            if args.arm in LIVE:
                cost = 1 if args.arm == 'no_tool' else protocol['live']['max_requests_per_run']
                if used + cost > args.max_requests:
                    print(json.dumps({'stopped': 'max_requests', 'used': used}), flush=True)
                    return
            row = run_one(spec, args.arm, rep, protocol, protocol_hash, runs)
            row['attempt'] = len(previous) + 1
            used += row.get('provider_requests', 0) or 0
            with path.open('a') as f:
                f.write(json.dumps(row, allow_nan=False) + '\n')
            print(json.dumps({k: row.get(k) for k in ('specimen', 'replicate', 'outcome', 'status', 'actions', 'provider_requests', 'elapsed_s', 'error')}), flush=True)


def first_attempts(rows):
    first = {}
    for row in rows:
        first.setdefault((row['specimen'], row['replicate']), row)
    return first


def interval(correct, rows, random=False):
    if not random:
        return {'wilson95': list(wilson(correct, len(rows))), 'interval_method': 'Wilson over specimens'}
    # Repeats of the same circuit are not independent circuits.
    groups = {}
    for row in rows:
        groups.setdefault(row['specimen'], []).append(row['outcome'] == 'correct')
    rates = np.array([np.mean(v) for v in groups.values()])
    if not len(rates):
        return {'wilson95': None, 'cluster_bootstrap95': None, 'interval_method': 'not available'}
    rng = np.random.default_rng(20261102)
    boot = rates[rng.integers(len(rates), size=(10000, len(rates)))].mean(axis=1)
    return {'wilson95': None, 'cluster_bootstrap95': np.quantile(boot, [.025, .975]).tolist(),
            'interval_method': 'percentile bootstrap over circuits; all random repeats kept together',
            'independent_specimens': len(rates)}


def wilson(k, n, z=1.96):
    if n == 0:
        return (0., 0.)
    p = k / n
    centre, half = (p + z * z / (2 * n)) / (1 + z * z / n), z * sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return (max(0., centre - half), min(1., centre + half))


def cmd_score(args):
    protocol = load_protocol()
    runs = RUNS / 'dev' if args.dev else RUNS
    specs = {s['id']: s for s in load_specimens(protocol, args.dev)}
    table = []
    for arm in ARMS:
        _, rows = finished(arm, runs)
        if any(r['protocol_sha256'] != sha256(PROTOCOL) for r in rows):
            raise SystemExit('Mixed protocol results cannot be scored together')
        first = first_attempts(rows)
        for task in protocol['tasks']:
            if task not in protocol['arms'][arm]['tasks']:
                continue
            expected = [s for s in specs.values() if s['task'] == task]
            reps = protocol['arms']['random']['replicates'] if arm == 'random' else 1
            got = [r for r in first.values() if r['task'] == task]
            all_attempts = [r for r in rows if r['task'] == task]
            if not got:
                table.append({'arm': arm, 'task': task, 'status': 'not run'})
                continue
            infam = [r for r in got if specs[r['specimen']]['in_family']]
            outfam = [r for r in got if not specs[r['specimen']]['in_family']]
            correct = sum(r['outcome'] == 'correct' for r in infam)
            line = {'arm': arm, 'task': task, 'runs': len(got), 'expected_runs': len(expected) * reps,
                    'status': 'complete' if len(got) == len(expected) * reps else 'partial',
                    'primary_basis': 'first attempt per specimen/replicate, including failures',
                    'in_family_correct': f'{correct}/{len(infam)}', 'correct_rate': round(correct / max(1, len(infam)), 3),
                    **interval(correct, infam, random=arm == 'random'),
                    'wrong_identifications': sum(r['outcome'] == 'wrong' for r in got),
                    'false_rejections': sum(r['outcome'] == 'false_rejection' for r in got),
                    'abstained_or_incomplete': sum(r['outcome'] in ('abstained', 'incomplete', 'unparsed') for r in got),
                    'out_of_family_rejected': f"{sum(r['outcome'] == 'rejected' for r in outfam)}/{len(outfam)}" if outfam else None,
                    'transport_reruns': len(all_attempts) - len(got),
                    'all_attempts': len(all_attempts),
                    'all_attempt_outcomes': {o: sum(r['outcome'] == o for r in all_attempts)
                        for o in ('correct', 'wrong', 'rejected', 'false_rejection', 'abstained', 'incomplete', 'unparsed')}}
            if arm != 'no_tool':
                line['mean_diagnostic_acquisitions'] = round(float(np.mean([r.get('diagnostic_acquisitions', 0) for r in got])), 2)
                line['mean_wiring_changes'] = round(float(np.mean([r.get('simulated_mountings', 0) for r in got])), 2)
            picks = [c for r in got for c in r.get('choices', [])]
            if arm != 'no_tool' and picks:
                line['matched_engine_top_choice'] = f"{sum(c['chosen'] == c['engine_top'] for c in picks)}/{len(picks)}"
            if arm in LIVE:
                line['provider_requests'] = sum(r.get('provider_requests', 0) or 0 for r in all_attempts)
            table.append(line)
    out = {'protocol_sha256': sha256(PROTOCOL), 'specimens': 'development' if args.dev else sha256(SPECIMENS),
           'table': table, 'paired': paired(specs, protocol, runs)}
    print(json.dumps(out, indent=1, ensure_ascii=False))
    if args.write:
        (runs / 'score.json').write_text(json.dumps(out, indent=1, ensure_ascii=False) + '\n')


def paired(specs, protocol, runs):
    """Exact two-sided McNemar on in-family correct/not-correct, preregistered pairs only."""
    from math import comb
    latest = {}
    for arm in ARMS:
        _, rows = finished(arm, runs)
        latest[arm] = {r['specimen']: r for r in first_attempts(rows).values() if r['replicate'] == 0}
    results = []
    for a, b, task in protocol['paired_comparisons']:
        common = [s for s in latest[a] if s in latest[b] and specs[s]['task'] == task and specs[s]['in_family']]
        expected = [s['id'] for s in specs.values() if s['task'] == task and s['in_family']]
        if len(common) != len(expected):
            results.append({'pair': [a, b], 'task': task, 'status': 'incomplete; no significance claim',
                            'specimens': len(common), 'expected_specimens': len(expected)})
            continue
        ca = [latest[a][s]['outcome'] == 'correct' for s in common]
        cb = [latest[b][s]['outcome'] == 'correct' for s in common]
        only_a = sum(x and not y for x, y in zip(ca, cb))
        only_b = sum(y and not x for x, y in zip(ca, cb))
        n = only_a + only_b
        p = min(1., 2 * sum(comb(n, k) for k in range(min(only_a, only_b) + 1)) / 2**n) if n else 1.
        results.append({'pair': [a, b], 'task': task, 'specimens': len(common), 'only_first_correct': only_a,
                        'only_second_correct': only_b, 'exact_mcnemar_p': p})
    # Holm adjustment across ALL preregistered pairs, including pairs not yet run.
    valid = sorted((r for r in results if 'exact_mcnemar_p' in r), key=lambda r: r['exact_mcnemar_p'])
    previous = 0.
    for index, row in enumerate(valid):
        previous = max(previous, min(1., (len(results) - index) * row['exact_mcnemar_p']))
        row['holm_adjusted_p'] = previous
        row['first_arm_superiority_supported'] = previous < .05 and row['only_first_correct'] > row['only_second_correct']
    return results


def cmd_plan(args):
    protocol = load_protocol()
    out = {'protocol_sha256': sha256(PROTOCOL), 'specimens_sha256': sha256(SPECIMENS) if SPECIMENS.exists() else None}
    specs = load_specimens(protocol) if SPECIMENS.exists() else generate_specimens(protocol)
    for arm, cfg in protocol['arms'].items():
        n = sum(s['task'] in cfg['tasks'] for s in specs)
        if arm in LIVE:
            ceiling = n if arm == 'no_tool' else n * protocol['live']['max_requests_per_run']
            out[arm] = {'runs': n, 'request_ceiling': ceiling, 'typical_requests': n if arm == 'no_tool' else n * 4}
        else:
            out[arm] = {'runs': n * cfg.get('replicates', 1), 'requests': 0}
    print(json.dumps(out, indent=1))


def cmd_write_specimens(args):
    protocol = load_protocol()
    if SPECIMENS.exists() and not args.force:
        raise SystemExit('specimens.json exists; it is part of the preregistration')
    SPECIMENS.write_text(json.dumps(generate_specimens(protocol), indent=1) + '\n')
    text = PROTOCOL.read_text()
    if text.count('FILLED_BY_WRITE_SPECIMENS') != 1:
        raise SystemExit('protocol.json has no specimens hash placeholder')
    PROTOCOL.write_text(text.replace('FILLED_BY_WRITE_SPECIMENS', sha256(SPECIMENS)))
    print(json.dumps({'specimens_sha256': sha256(SPECIMENS), 'protocol_sha256': sha256(PROTOCOL)}))


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest='cmd', required=True)
    sub.add_parser('plan')
    w = sub.add_parser('write-specimens'); w.add_argument('--force', action='store_true')
    r = sub.add_parser('run')
    r.add_argument('--arm', choices=ARMS, required=True)
    r.add_argument('--execute', action='store_true')
    r.add_argument('--max-requests', type=int, default=0)
    r.add_argument('--allowance-cap', type=float, help='explicitly authorised cumulative local reservation cap; not actual billing or credit')
    r.add_argument('--task', choices=['A', 'B'], help='preregistered complete task only; not individual evaluation specimens')
    r.add_argument('--rerun-transport', action='store_true')
    r.add_argument('--dev', action='store_true', help='development specimens (separate seed, runs/linear-benchmark/dev)')
    r.add_argument('--limit', type=int, default=0, help='first N development specimens per task set')
    s = sub.add_parser('score'); s.add_argument('--write', action='store_true'); s.add_argument('--dev', action='store_true')
    args = p.parse_args()
    {'plan': cmd_plan, 'write-specimens': cmd_write_specimens, 'run': cmd_run, 'score': cmd_score}[args.cmd](args)


if __name__ == '__main__':
    main()
