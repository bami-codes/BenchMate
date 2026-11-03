"""Agent-controlled experiment selection and prospective, immutable verification."""
from copy import deepcopy
import numpy as np

from ..agent import ToolRejected, function_tool
from ..netlist import ELEMENT_SCHEMA
from .design import checked, digest, elements as check_elements
from .menu import MENU, RESERVED, POLICY, template
from .models import assess, Fitter, predict, score, validate_capture

PROMPT = '''You direct BenchMate's versioned schematic-to-bench diagnosis.
All reasons, operator-facing requests and report fields must be concise English.
Start with inspect_experiment. The reviewed intended netlist is design knowledge,
not the actual assembly. Never infer specimen truth from a name or a photo.
Source says MOCK or PHYSICAL; never call a scripted/mock run a physical result.

You choose individual experiments from the same finite menu for every design.
The runtime never selects a training order for you. You have at most three
training actions; repeats spend that budget. Choose amplitudes, frequency and
known output load to distinguish the surviving explanations. Raw measured IN
conditions the predictions, so an input-parallel branch can be unobservable.
Fit results use training OUT only. Candidates are nominal and one intended R/C
value changed. Multiple fitting candidates are evidence of ambiguity, not a
reason to pick the smallest residual or the first component in the list.

Only when every declared candidate was successfully fitted and is inadequate
may you propose_structure with a literal bounded passive netlist. Preserve
intended R/C/D names and values; you may reconnect them and add at most two R/C
elements and bounded diodes. W1 is an ideal input-to-output jumper and may be
replaced in a proposal. The runtime fits only added R/C values and shared diode
IS/N, never silently changes your topology. At most two proposals. Numerical
fit errors and budget exhaustion are not evidence for a new structure.

When training supports an explanation, call verify_prediction. It freezes
models, parameters and command-input forecasts BEFORE either reserved capture.
The same two unused settings apply to all cases. Conditional checks then use
newly measured IN; reserved OUT is never fitted. Command forecasts and
conditional comparisons have separate scores. No retry or post-holdout fitting.
The 9 mV whole-waveform AND every-region threshold is an engineering allowance,
not calibrated confidence. Structural equivalence and unobserved components
remain unresolved even if all predictions pass.

finish_report must copy the runtime outcome and exact component list. A nominal
pass means no mismatch detected by these checks, not proof that every part is
correct. A proposed structure passing is predictive support, not uniqueness or
identification of an ESP32 interior. Finish with the tool call, not plain text.
'''

TOOLS = [
    function_tool('inspect_experiment', 'Inspect the reviewed design, evidence and the common action menu.'),
    function_tool('measure', 'Choose exactly one training measurement; physical rewiring awaits a human.', {
        'action': {'type': 'string', 'enum': list(MENU)}, 'reason': {'type': 'string'}}),
    function_tool('propose_structure', 'Propose a literal passive circuit after every component-value hypothesis fails.', {
        'elements': {'type': 'array', 'items': ELEMENT_SCHEMA}, 'rationale': {'type': 'string'}}),
    function_tool('verify_prediction', 'Freeze/publish models and forecasts before the two reserved measurements.'),
    function_tool('finish_report', 'Record only the outcome and components established by the runtime.', {
        'verdict': {'type': 'string', 'enum': ['consistent', 'changed', 'indistinguishable', 'structure_supported', 'abstained']},
        'components': {'type': 'array', 'items': {'type': 'string'}},
        'explanation': {'type': 'string'}, 'limits': {'type': 'string'}}),
]


def _brief(row):
    result = {k: deepcopy(v) for k, v in row.items() if k not in ('model', 'training_checks')}
    result['training_checks'] = [{'passed': c['passed'], 'RMS_mV': c['RMS_mV'],
                                  'worst_region_RMS_mV': max(r['RMS_mV'] for r in c['regions'])}
                                 for c in row.get('training_checks', [])]
    return result


def verification_brief(value):
    if value is None:
        return None
    return {k: deepcopy(v) for k, v in value.items() if k != 'checks'} | {
        'checks': [{'settings': c['settings'], 'conditional': {
            identity: {'passed': s['passed'], 'RMS_mV': s['RMS_mV'],
                       'worst_region_RMS_mV': max(r['RMS_mV'] for r in s['regions'])}
            for identity, s in c['conditional'].items()},
            'command_forecast_passed': {identity: s['passed'] for identity, s in c['command_forecast'].items()}}
            for c in value['checks']]}


class DiagnosisSession:
    def __init__(self, bench, log, design, publish, *, actor='muse_spark'):
        if bench.source not in ('mock', 'physical') or actor not in ('muse_spark', 'scripted_controller'):
            raise ValueError('Explicit source and actor required.')
        self.design = checked(design)
        if bench.source == 'physical' and self.design['operator_review_simulated']:
            raise ValueError('A simulated design review cannot authorize physical work.')
        self.bench, self.log, self.publish, self.actor = bench, log, publish, actor
        self.tools = TOOLS
        self.report = None
        self.inspected = self.fatal = self.verification_used = False
        self.training, self.actions, self.proposals = [], [], []
        self.assessment = None
        self.frozen = self.receipt = self.verification = None
        self.log.add('netlist_protocol', {'source': bench.source, 'actor': actor, 'policy': POLICY,
                     'reviewed_design': self.design, 'reviewed_design_sha256': digest(self.design),
                     'assembly_truth_transmitted': False, 'language': 'English'})

    def _adequate(self):
        rows = self.assessment['hypotheses'] if self.assessment else []
        return [r for r in rows + self.proposals if r['status'] == 'adequate']

    def snapshot(self):
        observations = []
        for action, c in zip(self.actions, self.training, strict=True):
            s, t, u, di, do, y = validate_capture(c)
            ix = np.linspace(0, len(t)-1, 9).astype(int)
            observations.append({'action': action, 'samples': [
                {'t_s': float(t[i]), 'IN_minus_REF_v': float(u[i]), 'OUT_minus_REF_v': float(y[i])} for i in ix]})
        available = not self.verification_used and not self.fatal and self.report is None
        return {'source': self.bench.source, 'actor': self.actor, 'intended_elements': deepcopy(self.design['elements']),
                'reviewed_design_sha256': digest(self.design), 'policy': deepcopy(POLICY),
                'allowed_measurements': list(MENU) if available and len(self.actions) < 3 and not self.proposals else [],
                'training_actions': list(self.actions), 'observations': observations,
                'assessment': None if self.assessment is None else {
                    **{k: v for k, v in self.assessment.items() if k != 'hypotheses'},
                    'hypotheses': [_brief(r) for r in self.assessment['hypotheses']]},
                'structure_available': bool(available and self.assessment and self.assessment['all_inadequate']
                                            and len(self.proposals) < 2 and not self._adequate()),
                'proposals': [_brief(p) for p in self.proposals],
                'verification_available': available and bool(self._adequate()),
                'verification': verification_brief(self.verification), 'expected_report': self.outcome(),
                'photos_received': False, 'assembly_truth_received': False}

    def dispatch(self, name, args):
        if self.report is not None or self.fatal:
            raise ToolRejected('Session stopped.')
        tool = next((t for t in TOOLS if t['name'] == name), None)
        if tool is None or not isinstance(args, dict) or set(args) != set(tool['parameters']['required']):
            raise ToolRejected('Unknown tool or fields.')
        for key in ('reason', 'rationale', 'explanation', 'limits'):
            if key in args and (not isinstance(args[key], str) or not args[key].strip() or len(args[key]) > 1600):
                raise ToolRejected('Bounded nonempty English text required.')
        if name == 'inspect_experiment':
            self.inspected = True
            return self.snapshot()
        if not self.inspected:
            raise ToolRejected('Inspect before choosing an experiment.')
        if name == 'finish_report':
            return self.finish(**args)
        try:
            if name == 'measure': self.measure(**args)
            elif name == 'propose_structure': self.propose(**args)
            elif name == 'verify_prediction': self.verify()
        except ToolRejected:
            raise
        except BaseException:
            self.fatal = True
            raise
        return self.snapshot()

    def _capture(self, settings, role):
        c = self.bench.acquire(deepcopy(settings), role)
        validate_capture(c, role=role)
        if c['source'] != self.bench.source or c['settings'] != settings:
            raise ValueError('Capture does not match requested source/settings.')
        self.log.add('netlist_observation', c)
        return c

    def measure(self, action, reason):
        if action not in self.snapshot()['allowed_measurements']:
            raise ToolRejected('Measurement unavailable or training budget spent.')
        settings = MENU[action]
        prior = self._adequate() or [{'id': 'nominal', 'model': {'elements': self.design['elements']}}]
        frozen = {'action': action, 'settings': settings, 'selected_by': self.actor, 'reason': reason,
                  'models': [{ 'id': r['id'], 'model': r['model'],
                      'command_forecast_v': predict(r['model'], template(settings))} for r in prior],
                  'scored_OUT_used': 0, 'future_measured_IN_used': False}
        self.log.add('training_forecasts_frozen', {**frozen, 'sha256': digest(frozen)})
        capture = self._capture(settings, 'training')
        self.actions.append(action); self.training.append(capture)
        self.assessment = assess(self.design['elements'], self.training)
        self.log.add('component_hypotheses_fitted', self.assessment)

    def propose(self, elements, rationale):
        if not self.snapshot()['structure_available']:
            raise ToolRejected('Every declared hypothesis must be inadequate; fit errors do not qualify.')
        try:
            proposed = check_elements(elements)
            original = {e['name']: e for e in self.design['elements'] if e['kind'] != 'W'}
            by_name = {e['name']: e for e in proposed}
            for name, old in original.items():
                new = by_name.get(name)
                if new is None or any(new[k] != old[k] for k in ('kind', 'value', 'model')):
                    raise ValueError('Keep intended component names, kinds and values; only reconnect or add.')
            added = [e['name'] for e in proposed if e['name'] not in original and e['kind'] in ('R', 'C')]
            if len(added) > 2:
                raise ValueError('At most two added R/C values may be fitted.')
        except (ValueError, TypeError, KeyError) as exc:
            raise ToolRejected(str(exc)) from None
        identity = 'proposal:' + str(len(self.proposals)+1)
        self.log.add('structure_proposed', {'id': identity, 'elements': proposed, 'rationale': rationale,
                     'topology_sha256': digest(proposed), 'selected_by': self.actor})
        fitter = Fitter(max_calls=420, max_seconds=60.)
        try:
            row = fitter.fit(proposed, self.training, hypothesis_id=identity, fit_names=added,
                             fit_diode=any(e['kind'] == 'D' for e in proposed))
        except (ValueError, RuntimeError) as exc:
            row = {'id': identity, 'status': 'fit_error', 'error': str(exc)}
        row['simulator_calls'] = fitter.calls
        self.proposals.append(row)
        self.log.add('structure_fit', row)

    def verify(self):
        if not self.snapshot()['verification_available']:
            raise ToolRejected('Unused verification and adequate training models required.')
        self.verification_used = True
        rows = deepcopy(self._adequate())
        frozen = {'policy': POLICY, 'reviewed_design_sha256': digest(self.design),
                  'source': self.bench.source, 'actor': self.actor, 'models': rows,
                  'command_forecasts': [{r['id']: predict(r['model'], template(s)) for r in rows} for s in RESERVED],
                  'verification_OUT_samples_used': 0, 'future_measured_IN_used': False}
        sha = digest(frozen)
        self.frozen = deepcopy(frozen)
        self.log.add('verification_forecast_frozen', {'sha256': sha, **frozen})
        receipt = self.publish(deepcopy(frozen), sha)
        if (receipt.get('sha256') != sha or receipt.get('published') is not True
                or (self.bench.source == 'physical' and receipt.get('remote') is not True)):
            raise ValueError('Matching publication required before verification acquisition.')
        self.receipt = deepcopy(receipt)
        self.log.add('verification_publication', receipt)
        self.bench.bind_forecast(sha)
        checks = []
        for s, commands in zip(RESERVED, frozen['command_forecasts'], strict=True):
            c = self._capture(s, 'verification')
            conditional = {r['id']: score(c, predict(r['model'], c['input_template'])) for r in rows}
            command = {r['id']: score(c, commands[r['id']]) for r in rows}
            checks.append({'settings': s, 'conditional': conditional, 'command_forecast': command})
            self.log.add('reserved_prediction_scored', {'prediction_sha256': sha, **checks[-1], 'OUT_refitted': False})
        survivors = [r['id'] for r in rows if all(c['conditional'][r['id']]['passed'] for c in checks)]
        self.verification = {'survivors': survivors, 'checks': checks, 'refitted': False,
                             'frozen_sha256': sha, 'source': self.bench.source}
        self.log.add('netlist_verification_completed', self.verification)

    def outcome(self):
        if self.verification is None:
            return {'verdict': 'abstained', 'components': []}
        survivors = self.verification['survivors']
        if 'nominal' in survivors:
            return {'verdict': 'consistent', 'components': []}
        changed = sorted(x.split(':', 1)[1] for x in survivors if x.startswith('changed:'))
        if changed:
            return {'verdict': 'changed' if len(changed) == 1 else 'indistinguishable', 'components': changed}
        return {'verdict': 'structure_supported' if survivors else 'abstained', 'components': []}

    def finish(self, verdict, components, explanation, limits):
        expected = self.outcome()
        if verdict != expected['verdict'] or components != expected['components']:
            raise ToolRejected('Report must match the runtime outcome and exact unresolved component set.')
        self.report = {**expected, 'explanation': explanation, 'limits': limits, 'source': self.bench.source,
                       'actor': self.actor, 'physical_repair_demonstrated': False}
        self.log.add('agent_report', self.report)
        return {'accepted': True}

    def summary(self):
        return {'version': POLICY['version'], 'source': self.bench.source, 'actor': self.actor,
                'llm_used': self.actor == 'muse_spark', 'agent_report': self.report,
                'selected_actions': list(self.actions), 'assessment': self.assessment,
                'proposals': self.proposals, 'verification': self.verification,
                'instrument': self.bench.metadata(), 'physical_repair_demonstrated': False}
