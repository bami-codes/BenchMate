"""Official passive cohort adapter around the preserved diagnosis and guards."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

from .instrument import validate_boot_id
from .netlist_diagnosis.design import checked, digest
from .netlist_diagnosis.models import predict
from .netlist_diagnosis.physical import PhysicalNetlistBench
from .netlist_diagnosis.protocol import prepare as base_prepare
from .netlist_diagnosis_v2.session import Session as V2Session, PROMPT as V2_PROMPT
from .passive_pilot import INSTRUMENT, command_model, source_hashes as preserved_sources
from .providers import MetaToolSession, ProviderError

ROOT = Path(__file__).resolve().parents[2]
POLICY_FILE = 'docs/2026-11-03-official-run-policy.json'
AMENDMENT = 'docs/2026-11-03-official-passive-amendment.md'
PROMPT = V2_PROMPT + '''
This is a PHYSICAL OFFICIAL evaluation, using one reviewed intended schematic.
No previous run, assembly truth, case label or photo is supplied to you.
Choose the training experiments yourself from the unchanged common menu.
The public instrument has a fixed 1 kohm series resistor BEFORE measured IN.
It is a known instrument component, not a DUT defect. Command forecasts include
it with an ideal buffered DAC; conditional predictions use measured IN after it.
Command forecast failures remain visible separately from conditional checks.
A3 and A4 both monitor REF. GND and REF are distinct. No k correction is used.
If the outcome is consistent, say: No mismatch in the tests Spark chose.
Training experiments are your choices; the two reserved inputs were fixed by
the protocol. Do not claim all parts are correct or that you repaired anything.
'''


def source_hashes():
    sources = preserved_sources()
    for name in ('src/benchmate/official_passive.py', 'scripts/official_passive.py',
                 'src/benchmate/verify.py', AMENDMENT):
        sources[name] = hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
    return sources


def prepare(design):
    design = checked(design)
    if design['operator_review_simulated']:
        raise ValueError('Real reviewed intended schematic required.')
    p = base_prepare(design)
    selection = json.loads((ROOT / POLICY_FILE).read_text())
    p.update(official=True, pilot=False, excluded_from_evaluation=False,
             official_runtime_version='official-passive-v1',
             cohort_plan_id=selection['cohort_plan_id'],
             selection_policy_sha256=digest(selection),
             official_source_sha256=source_hashes(), instrument=deepcopy(INSTRUMENT),
             ADC_roles={'A1': 'measured IN', 'A2': 'buffered OUT',
                        'A3': 'REF via A23–A45', 'A4': 'REF via D50–G50 and I50'},
             hardware_revision='single renewed GND return; renewed D50–G50; fixed 1 kohm instrument resistor',
             reference_guard='Original uncorrected PhysicalBench raw block-mean guard; no new sample-RMS rule',
             k_correction=False,
             QA_evidence='examples/original-guard-QA/2026-11-03/session01-ground-single/result.json',
             calibration_is_new=False,
             photo_input_to_diagnosis=False, assembly_truth_input_to_diagnosis=False)
    p['api_plan']['prompt'] = PROMPT
    return p


class Session(V2Session):
    def __init__(self, bench, *args, **kwargs):
        if bench.source != 'physical':
            raise ValueError('Official physical session cannot relabel a mock bench.')
        super().__init__(bench, *args, **kwargs)

    def _predict(self, model, inp):
        if self.active:
            raise ValueError('LED physical execution requires separate absolute-DC qualification.')
        return predict(command_model(model) if inp['source'] == 'command_input_only' else model, inp)

    def snapshot(self):
        return {**super().snapshot(), 'instrument': deepcopy(INSTRUMENT),
                'official': True, 'pilot': False, 'excluded_from_evaluation': False}

    def summary(self):
        result = super().summary()
        report = result['agent_report']
        return {**result, 'official': True, 'pilot': False, 'excluded_from_evaluation': False,
                'display_caption': ('No mismatch in the tests Spark chose'
                                    if report and report['verdict'] == 'consistent' else None)}


class Bench(PhysicalNetlistBench):
    """Bind the first read to the PING preflight, including an initial rewire."""
    def __init__(self, *args, preflight_boot_id, **kwargs):
        self.preflight_boot = validate_boot_id(preflight_boot_id)
        self.expect_preflight_boot = True
        super().__init__(*args, **kwargs)
        self.confirm_external = self.confirm
        self.confirm = self._confirm

    def _confirm(self, fixture):
        if self.fixture is None:
            # If Spark's first choice is loaded, its intervention requires a
            # boot different from the observed preflight, not an older boot.
            self.boot_id = self.preflight_boot
            self.expect_preflight_boot = False
            self.log.add('preflight_boot_bound_before_initial_intervention', {'boot_id': self.boot_id})
        return self.confirm_external(fixture)

    def _ping(self, board, continuity, label, armed):
        super()._ping(board, continuity, label, armed)
        if self.expect_preflight_boot:
            if continuity.boot_id != self.preflight_boot or armed:
                raise ValueError('Initial unarmed boot changed since the preflight; no ARM.')
            self.expect_preflight_boot = False


class OfficialModel(MetaToolSession):
    """The explicit extra allowance retains the old ledger and the 8-call bound."""
    def next_call(self):
        data = json.loads(Path(self.budget_path).read_text())
        used = float(data.get('reserved_usd', {}).get('meta', 0))
        limit = data['authorized_request_limit']
        if data.get('authorized_by_operator') is not True or used + 1 > limit:
            raise ProviderError('Official case allowance exhausted before request; no automatic retry.')
        return super().next_call()
