"""Existing Spark diagnosis with explicitly qualified fixed-k fixture eligibility."""
from copy import deepcopy

from .passive_pilot import Session as PilotSession
from .netlist_diagnosis_v2.session import PROMPT as BASE_PROMPT
from .netlist_diagnosis.menu import MENU
from .ref_reproducibility import POLICY, digest

PROMPT = BASE_PROMPT + '''
The instrument has a fixed 1 kohm resistor upstream of measured IN. Command
forecasts include it; measured-IN conditional predictions exclude it. It is not
a DUT defect. The declared cohort determines whether this run is a pilot excluded
from evaluation or a new prospectively fixed evaluation run. Never reclassify
historical pilots, and never claim absolute calibration or general accuracy.
This version uses a fixed, independently frozen input-linked REF reproducibility
check. Its 3 mV residual limit does not establish physical REF stability. Raw
absolute voltage, rail and HOLD checks are retained. Raw legacy REF span failures
remain visible and earlier pilots are never reclassified. The fixed coefficient
is never fitted to a diagnosis capture or to reserved OUT. Diagnostic IN and OUT
are not detrended. Predictive claims retain the original provisional scope.
Only fixture states listed in instrument_qualification have completed QA. The
same public menu exists for every case, but unqualified load states cannot run.
The runtime filters eligibility, never chooses an experiment order for you.
'''


class Session(PilotSession):
    def snapshot(self):
        value = super().snapshot()
        value['pilot'] = self.bench.p['pilot']
        value['excluded_from_evaluation'] = self.bench.p['excluded_from_evaluation']
        receipt = self.bench.qualification
        allowed = receipt['qualified_fixtures']
        value['allowed_measurements'] = [name for name in value['allowed_measurements']
            if ('unloaded' if MENU[name]['load_ohm'] is None else 'output_load') in allowed]
        value['instrument_qualification'] = {
            'reference_guard': POLICY['name'], 'version': POLICY['version'],
            'qualified_fixtures': deepcopy(allowed), 'calibration_sha256':digest(self.bench.fixed_model),
            'physical_REF_stability_established':False, 'diagnostic_IN_OUT_corrected':False,
            'past_failures_reclassified':False}
        return value
