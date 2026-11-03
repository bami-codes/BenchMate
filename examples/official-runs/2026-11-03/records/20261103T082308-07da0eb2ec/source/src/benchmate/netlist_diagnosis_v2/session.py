"""One menu/tool loop for all six cases; backend is selected from public design.

Reuses the v1 lifecycle, validation, reporting and passive structure proposals.
Overrides only the model-dependent operations; no frozen module is patched.
"""
from copy import deepcopy
import numpy as np

from ..agent import ToolRejected
from ..netlist_diagnosis import models as passive
from ..netlist_diagnosis.design import checked as checked_passive, digest
from ..netlist_diagnosis.menu import MENU, RESERVED, POLICY as PASSIVE_POLICY, template
from ..netlist_diagnosis.session import DiagnosisSession as BaseSession, TOOLS, PROMPT as BASE_PROMPT
from . import VERSION
from . import led

POLICY = {**deepcopy(PASSIVE_POLICY), 'version': VERSION,
          'profiles': ['reviewed_passive_RCDW', 'reviewed_BC547B_red_LED'],
          'active_device_characterization_established': False,
          'active_physical_execution_enabled': False,
          'active_scope': 'Four-part layout with declared measurement attenuation; no arbitrary active topology discovery.'}
PROMPT = BASE_PROMPT + '''
This is the v2 common runtime. The reviewed schematic determines its public
device profile; the same finite action menu and verification conditions apply.
The active profile contains a BC547B and a red LED, plus Rbase and Rled. A
declared 47k/10k measurement divider is OUT; COL is the unattenuated collector.
GND, REF and 5V are distinct. Reasons and reports remain English.
BC547B BF and red-LED forward voltage are bounded development nuisances, not
known measured constants. Changed Rbase and changed Q1 can predict the same
output. Preserve their ambiguity and do not report a unique resistance from a
nonidentifiable fit. No optical brightness or LED current is measured by OUT.
The active layout is bounded to its declared components; if every such family
fails, abstain. Passive profiles retain the literal R/C/D structure-proposal tool.
An active physical run is disabled until its absolute-DC measurement path is
separately calibrated and approved. Mock runs do not establish that readiness.
'''


def checked(value):
    return led.checked(value) if value.get('schema') == 'benchmate.reviewed_active_netlist.v2' else checked_passive(value)


class Session(BaseSession):
    def __init__(self, bench, log, design, publish, *, actor='muse_spark'):
        self.design = checked(design)
        self.active = self.design['schema'] == 'benchmate.reviewed_active_netlist.v2'
        if bench.source not in ('mock', 'physical') or actor not in ('muse_spark', 'scripted_controller'):
            raise ValueError('Explicit source and actor required.')
        if bench.source == 'physical' and (self.active or self.design['operator_review_simulated']):
            raise ValueError('Active physical execution is disabled pending absolute-DC calibration; simulated reviews cannot authorize hardware.')
        self.bench, self.log, self.publish, self.actor = bench, log, publish, actor
        self.tools = deepcopy(TOOLS)
        self.report = None
        self.inspected = self.fatal = self.verification_used = False
        self.training, self.actions, self.proposals = [], [], []
        self.assessment = None
        self.frozen = self.receipt = self.verification = None
        log.add('netlist_v2_protocol', {'source': bench.source, 'actor': actor, 'policy': POLICY,
                'reviewed_design': self.design, 'reviewed_design_sha256': digest(self.design),
                'assembly_truth_transmitted': False, 'language': 'English'})

    def _predict(self, value, inp):
        return led.predict(value, inp) if self.active else passive.predict(value, inp)

    def snapshot(self):
        result = super().snapshot()
        result['policy'] = deepcopy(POLICY)
        result['profile'] = 'BC547B_red_LED' if self.active else 'passive_RCDW'
        # Do not declare a uniquely surviving explanation while another
        # declared value family was never successfully evaluated.
        if self.assessment and not self.assessment['fitting_complete']:
            result['verification_available'] = False
        if self.active:
            result['measurement_harness'] = deepcopy(self.design['harness'])
            result['device_assumptions'] = deepcopy(self.design['device_assumptions'])
            result['structure_available'] = False
            if result['assessment']:
                for row in result['assessment']['hypotheses']:
                    row.pop('device_assumptions', None)
        return result

    def _capture(self, settings, role):
        result = super()._capture(settings, role)
        if self.active and result.get('reference_method') != 'known_simulator_absolute_REF':
            raise ValueError('Active DC must be retained relative to an independent absolute REF, not a fitted/subtracted output HOLD origin.')
        return result

    def measure(self, action, reason):
        if action not in self.snapshot()['allowed_measurements']:
            raise ToolRejected('Measurement unavailable or training budget spent.')
        settings = MENU[action]
        initial = led.model() if self.active else {'elements': self.design['elements']}
        prior = self._adequate() or [{'id': 'nominal', 'model': initial}]
        frozen = {'action': action, 'settings': settings, 'selected_by': self.actor, 'reason': reason,
                  'models': [{'id': r['id'], 'model': r['model'],
                              'command_forecast_v': self._predict(r['model'], template(settings))} for r in prior],
                  'scored_OUT_used': 0, 'future_measured_IN_used': False}
        self.log.add('training_forecasts_frozen', {'sha256': digest(frozen), **frozen})
        capture = self._capture(settings, 'training')
        self.actions.append(action); self.training.append(capture)
        self.assessment = led.assess(self.design, self.training) if self.active else passive.assess(self.design['elements'], self.training)
        self.log.add('component_hypotheses_fitted', self.assessment)

    def propose(self, elements, rationale):
        if self.active:
            raise ToolRejected('The declared active layout is bounded; abstain if every component family fails.')
        return super().propose(elements, rationale)

    def verify(self):
        if not self.snapshot()['verification_available']:
            raise ToolRejected('Unused verification and adequate training models required.')
        self.verification_used = True
        rows = deepcopy(self._adequate())
        frozen = {'policy': POLICY, 'reviewed_design_sha256': digest(self.design),
                  'source': self.bench.source, 'actor': self.actor, 'models': rows,
                  'command_forecasts': [{r['id']: self._predict(r['model'], template(s)) for r in rows} for s in RESERVED],
                  'verification_OUT_samples_used': 0, 'future_measured_IN_used': False}
        sha = digest(frozen); self.frozen = deepcopy(frozen)
        self.log.add('verification_forecast_frozen', {'sha256': sha, **frozen})
        receipt = self.publish(deepcopy(frozen), sha)
        if (receipt.get('sha256') != sha or receipt.get('published') is not True
                or (self.bench.source == 'physical' and receipt.get('remote') is not True)):
            raise ValueError('Matching publication required before verification acquisition.')
        self.receipt = deepcopy(receipt)
        self.log.add('verification_publication', receipt)
        self.bench.bind_forecast(sha)
        checks = []
        for settings, commands in zip(RESERVED, frozen['command_forecasts'], strict=True):
            capture = self._capture(settings, 'verification')
            conditional = {r['id']: passive.score(capture, self._predict(r['model'], capture['input_template'])) for r in rows}
            command = {r['id']: passive.score(capture, commands[r['id']]) for r in rows}
            checks.append({'settings': settings, 'conditional': conditional, 'command_forecast': command})
            self.log.add('reserved_prediction_scored', {'prediction_sha256': sha, **checks[-1], 'OUT_refitted': False})
        survivors = [r['id'] for r in rows if all(c['conditional'][r['id']]['passed'] for c in checks)]
        self.verification = {'survivors': survivors, 'checks': checks, 'refitted': False,
                             'frozen_sha256': sha, 'source': self.bench.source}
        self.log.add('netlist_verification_completed', self.verification)

    def summary(self):
        return {**super().summary(), 'version': VERSION,
                'profile': 'BC547B_red_LED' if self.active else 'passive_RCDW',
                'active_hardware_qualified': False, 'optical_brightness_measured': False}
