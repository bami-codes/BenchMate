"""Versioned acquisition mixin; frozen instrument and diagnosis stay unchanged."""
from copy import deepcopy
import math

import numpy as np

from .instrument import capture_command, validate_block
from .netlist_diagnosis.physical import PhysicalNetlistBench
from .ref_reproducibility import POLICY, digest, evaluate, origin, raw_checks


class ReproducibilityCaptureMixin:
    """Transport/layout unchanged; explicitly replaces only stimulus REF criterion.

Training QA may collect input-linked variation before k exists. All raw electrical
and raw HOLD checks still stop. Production requires qualified calibration.
"""
    fixed_model = None
    qa_training_only = False

    def reset_reproducibility_context(self):
        self.reference_means = []
        self.repro_blocks = []
        self.repro_origin = None
        self.raw_hold_means = []

    def _capture(self, board, continuity, label, settings):
        if self.stopped: raise RuntimeError('Acquisition stopped; no retry')
        if not self.reference_means:
            self.reset_reproducibility_context()
        command = capture_command(self.config, boot_id=continuity.boot_id, **settings)
        self.capture_attempts += 1
        self.last_confirmed_park = False
        block = self._request(board, continuity, command, label+'_raw_capture', 30)
        validate_block(block, expected_command=command)
        if block.get('parked_ref_code') != self.config.ref_code:
            raise ValueError('REF park not reported')
        self.frames += len(block['rows'])
        self._ping(board, continuity, label+'_postcheck', True)
        self.last_confirmed_park = True
        rows = np.asarray(block['rows'])
        checks, means = raw_checks(rows, settings, self.config, self.p['guard_limits'], self.raw_hold_means)
        self.log.add('raw_electrical_and_HOLD_guard', {'label':label,'checks':checks,'means_v':means})
        if not all(checks.values()):
            self.stopped = True
            raise ValueError('Raw electrical/HOLD guard failed; no next stimulus')
        if settings['kind'] == 'hold': self.raw_hold_means.append(means)
        self.reference_means.append({'label':label,'hold':settings['kind']=='hold','means':means})
        raw_span = np.ptp(np.asarray([r['means'] for r in self.reference_means])[:, 3])*1000
        self.log.add('legacy_REF_span_preserved', {'label':label,'raw_A4_block_mean_span_mV':float(raw_span),
            'original_3mV_guard_passed':bool(raw_span <= 3.),'retroactive_reclassification':False})
        entry = {'label':label,'settings':deepcopy(settings),'rows':block['rows']}
        self.repro_blocks.append(entry)
        if self.repro_origin is None:
            if settings['kind'] != 'hold': raise ValueError('Three raw origin HOLDs required before any stimulus')
            if len(self.repro_blocks) == 3:
                self.repro_origin = origin(self.repro_blocks)
                self.log.add('fixed_boot_origin_frozen', {'sha256':digest(self.repro_origin),**self.repro_origin})
        if self.fixed_model is not None and self.repro_origin is not None:
            result = evaluate(self.repro_blocks, self.repro_origin, self.config.vref_v, self.fixed_model['fixed_k'])
            self.log.add('fixed_k_reproducibility_guard', {'label':label,'policy':POLICY,
                'calibration_sha256':digest(self.fixed_model),'result':result,
                'diagnostic_IN_OUT_corrected':False})
            if not result['passed']:
                self.stopped = True
                raise ValueError('Fixed-k reproducibility guard failed; no next stimulus')
        elif not self.qa_training_only:
            if self.fixed_model is None: raise ValueError('Qualified fixed model required')
        self.last_reference_reproducibility = {
            'policy':POLICY['version'],'legacy_raw_A4_span_mV':float(raw_span),
            'legacy_3mV_guard_passed':bool(raw_span <= 3.),
            'new_guard_passed':None if self.fixed_model is None or self.repro_origin is None else True,
            'physical_REF_stability_established':False}
        return rows


def validate_qualification(candidate, receipt, fixture='unloaded'):
    k = candidate.get('fixed_k')
    if (candidate.get('schema') != 'benchmate.fixed-k-ref-model.v1' or candidate.get('policy') != POLICY
        or type(k) not in (int, float) or not math.isfinite(k) or abs(k) > POLICY['hard_abs_k_max']
        or candidate.get('fit_OUT_used') is not False):
        raise ValueError('Invalid fixed calibration or policy')
    if (receipt.get('schema') != 'benchmate.fixed-k-ref-qualification.v1' or receipt.get('passed') is not True
        or receipt.get('candidate_sha256') != digest(candidate)
        or receipt.get('fault_injection_passed') is not True
        or receipt.get('source') != 'physical_instrument_QA'
        or receipt.get('validation_refit') is not False
        or receipt.get('freeze_receipt', {}).get('remote') is not True
        or receipt.get('freeze_receipt', {}).get('candidate_sha256') != digest(candidate)
        or fixture not in receipt.get('qualified_fixtures', [])):
        raise ValueError('Matching passed fixed-k QA required for this fixture')
    return True


class FixedKPhysicalNetlistBench(ReproducibilityCaptureMixin, PhysicalNetlistBench):
    """Existing Spark-selected menu/forecasts; IN and OUT remain uncorrected."""
    def __init__(self, *args, candidate, qualification, **kwargs):
        validate_qualification(candidate, qualification)
        self.fixed_model = deepcopy(candidate)
        self.qualification = deepcopy(qualification)
        self.qa_training_only = False
        super().__init__(*args, **kwargs)

    def acquire(self, settings, role):
        fixture = 'unloaded' if settings['load_ohm'] is None else 'output_load'
        validate_qualification(self.fixed_model, self.qualification, fixture)
        capture = super().acquire(settings, role)
        capture['reference_reproducibility'] = deepcopy(self.last_reference_reproducibility)
        capture['reference_scope'] += (' Fixed input-linked REF reproducibility mode; '
            'physical REF stability is not established. IN/OUT are not detrended.')
        return capture

    def metadata(self):
        return {**super().metadata(),'reference_guard_version':POLICY['version'],
                'calibration_sha256':digest(self.fixed_model),'qualified_fixtures':self.qualification['qualified_fixtures'],
                'physical_REF_stability_established':False,'IN_OUT_corrected':False}
