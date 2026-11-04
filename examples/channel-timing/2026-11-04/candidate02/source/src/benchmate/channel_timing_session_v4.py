"""One passive tool loop using the frame-anchored backend for every design."""
from copy import deepcopy

from .agent import ToolRejected
from . import channel_timing_v4 as timing
from .netlist_diagnosis.models import score
from .netlist_diagnosis.design import elements as check_elements, digest
from .netlist_diagnosis.menu import MENU, RESERVED
from .netlist_diagnosis_v2.session import Session as PreservedSession, POLICY as BASE_POLICY
from .netlist_diagnosis.menu import template
from .passive_pilot import INSTRUMENT, command_model

POLICY = {**deepcopy(BASE_POLICY), 'version': timing.VERSION,
          'conditional_input_reconstruction': 'hold_to_DAC_frame_then_linear_to_A1_and_between_no_change_frames',
          'fitted_timing_parameters': [], 'command_forecasts': 'preserved_DAC_hold_with_1kohm_instrument'}


class Session(PreservedSession):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.active:
            raise ValueError('This qualification is passive only; LED physical DC remains unqualified.')
        self.log.add('channel_timing_model_bound', {'version': timing.VERSION, 'policy': POLICY,
            'all_passive_designs_same_rule': True, 'OUT_fitted_timing_parameters': [],
            'original_electrical_guards_unchanged': True})

    def _predict(self, model, inp):
        return timing.predict(command_model(model) if inp['source'] == 'command_input_only' else model, inp)

    def snapshot(self):
        result = super().snapshot()
        result['policy'] = deepcopy(POLICY)
        result['timing_model_version'] = timing.VERSION
        return result

    def measure(self, action, reason):
        if action not in self.snapshot()['allowed_measurements']:
            raise ToolRejected('Measurement unavailable or training budget spent.')
        settings = MENU[action]
        prior = self._adequate() or [{'id': 'nominal', 'model': {'elements': self.design['elements']}}]
        frozen = {'action': action, 'settings': settings, 'selected_by': self.actor, 'reason': reason,
                  'models': [{'id': r['id'], 'model': r['model'],
                              'command_forecast_v': self._predict(r['model'], template(settings))} for r in prior],
                  'scored_OUT_used': 0, 'future_measured_IN_used': False}
        self.log.add('training_forecasts_frozen', {'sha256': digest(frozen), **frozen})
        capture = self._capture(settings, 'training')
        self.actions.append(action); self.training.append(capture)
        self.assessment = timing.assess(self.design['elements'], self.training)
        self.log.add('component_hypotheses_fitted', self.assessment)

    def propose(self, elements, rationale):
        if not self.snapshot()['structure_available']:
            raise ToolRejected('Every declared hypothesis must be inadequate; fit errors do not qualify.')
        try:
            proposed = check_elements(elements)
            original = {e['name']: e for e in self.design['elements'] if e['kind'] != 'W'}
            by_name = {e['name']: e for e in proposed}
            for name, old in original.items():
                item = by_name.get(name)
                if item is None or any(item[k] != old[k] for k in ('kind', 'value', 'model')):
                    raise ValueError('Keep intended component names, kinds and values; only reconnect or add.')
            added = [e['name'] for e in proposed if e['name'] not in original and e['kind'] in ('R', 'C')]
            if len(added) > 2:
                raise ValueError('At most two added R/C values may be fitted.')
        except (ValueError, TypeError, KeyError) as exc:
            raise ToolRejected(str(exc)) from None
        identity = 'proposal:'+str(len(self.proposals)+1)
        self.log.add('structure_proposed', {'id': identity, 'elements': proposed, 'rationale': rationale,
                     'topology_sha256': digest(proposed), 'selected_by': self.actor})
        fitter = timing.Fitter(max_calls=420, max_seconds=60.)
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
                  'command_forecasts': [{r['id']: self._predict(r['model'], template(s)) for r in rows} for s in RESERVED],
                  'verification_OUT_samples_used': 0, 'future_measured_IN_used': False}
        h = digest(frozen); self.frozen = deepcopy(frozen)
        self.log.add('verification_forecast_frozen', {'sha256': h, **frozen})
        receipt = self.publish(deepcopy(frozen), h)
        if (receipt.get('sha256') != h or receipt.get('published') is not True
                or (self.bench.source == 'physical' and receipt.get('remote') is not True)):
            raise ValueError('Matching publication required before verification acquisition.')
        self.receipt = deepcopy(receipt)
        self.bench.bind_forecast(h)
        self.log.add('verification_publication', receipt)
        checks = []
        for settings, commands in zip(RESERVED, frozen['command_forecasts'], strict=True):
            capture = self._capture(settings, 'verification')
            conditional = {r['id']: score(capture, self._predict(r['model'], capture['input_template'])) for r in rows}
            command = {r['id']: score(capture, commands[r['id']]) for r in rows}
            checks.append({'settings': settings, 'conditional': conditional, 'command_forecast': command})
            self.log.add('reserved_prediction_scored', {'prediction_sha256': h, **checks[-1], 'OUT_refitted': False})
        survivors = [r['id'] for r in rows if all(c['conditional'][r['id']]['passed'] for c in checks)]
        self.verification = {'survivors': survivors, 'checks': checks, 'refitted': False,
                             'frozen_sha256': h, 'source': self.bench.source}
        self.log.add('netlist_verification_completed', self.verification)

    def summary(self):
        return {**super().summary(), 'version': timing.VERSION, 'timing_model_version': timing.VERSION,
                'fitted_timing_parameters': []}


class PhysicalSession(Session):
    def __init__(self, bench, *args, **kwargs):
        if bench.source != 'physical':
            raise ValueError('Physical runtime cannot relabel a mock bench.')
        super().__init__(bench, *args, **kwargs)

    def snapshot(self):
        return {**super().snapshot(), 'instrument': deepcopy(INSTRUMENT),
                'official': True, 'pilot': False, 'excluded_from_evaluation': False,
                'reference_monitor': {'version': 'primary-REF-A3-v1', 'primary': 'A3',
                    'block_mean_span_mV_max': 3., 'A4': 'auxiliary_record_only'}}

    def summary(self):
        result = super().summary(); report = result['agent_report']
        return {**result, 'official': True, 'pilot': False, 'excluded_from_evaluation': False,
                'guard_version': 'primary-REF-A3-v1', 'primary_REF_channel': 'A3',
                'A4_role': 'record_and_report_only',
                'display_caption': 'No mismatch in the tests Spark chose' if report and report['verdict'] == 'consistent' else None}
