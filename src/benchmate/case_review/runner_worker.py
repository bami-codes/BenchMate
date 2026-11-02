"""One supervised scripted mock. Never constructs a provider or physical bench."""
import argparse
from pathlib import Path
import signal

from ..agent import drive_agent
from ..d01_repair import D01RepairSession, reviewed_design
from ..d01_repair_bench import MockRepairBench, validate_repair_report
from ..records import Recorder
from .runner_contract import (MODE, FAULTS, PROTOCOL_SHA, atomic_json, digest,
                              frozen_runner, read_json, validate_response)


class Cancelled(Exception):
    pass


def stop_worker(*_):
    raise Cancelled('Mock cancelled; no hardware was operated')


class MockBenchLog:
    """Keep auto-mount bookkeeping distinct from the bridge's awaited UI request."""
    def __init__(self, log):
        self.log = log
    def add(self, kind, payload):
        if kind == 'operator_action_requested':
            self.log.add('mock_fixture_transition', {'original_kind': kind, **payload})
        else:
            self.log.add(kind, payload)


class InteractiveMockBench:
    source = 'mock'
    def __init__(self, runner, protocol, log, fault, timeout):
        self.inner = MockRepairBench(protocol, MockBenchLog(log), fault=fault)
        self.runner, self.log, self.timeout = runner, log, timeout
        self.wiring_revision = 0
        self.config = self.inner.config

    @property
    def boot_id(self):
        return self.inner.boot_id

    def confirm(self, action, prediction):
        context = {'action': action, 'prediction_sha256': prediction, 'boot_id': self.boot_id,
                   'wiring_revision': self.wiring_revision, 'source': 'mock', 'physical_action_requested': False}
        self.log.add('bridge_operator_context', context)
        # Reuses the frozen runner's exact UUID request / exclusive response-file channel.
        report = self.runner.operator_channel(self.log, action, prediction, timeout_s=self.timeout)
        request = read_json(self.log.path / 'operator-request.json')
        validate_response(report, request)
        if report.get('expected_boot_id') != context['boot_id'] or report.get('wiring_revision') != context['wiring_revision']:
            raise ValueError('Stale simulated boot or wiring revision')
        if action == 'restore_nominal_capacitance':
            validate_repair_report(report, prediction)
        self.log.add('bridge_operator_response_consumed', {'source': 'mock', 'request_id': request['request_id'],
                      'action': action, 'wiring_revision': self.wiring_revision, 'response': report})
        self.wiring_revision += 1

    def acquire(self, settings, models, fixture, phase):
        if self.inner.fixture is not None and fixture != self.inner.fixture:
            if fixture != 'output_load':
                raise ValueError('Unregistered simulated wiring change')
            self.confirm('attach_output_load', None)
        return self.inner.acquire(settings, models, fixture, phase)

    def prepare_repair(self, prediction, receipt):
        if receipt.get('sha256') != prediction or receipt.get('published') is not True:
            raise ValueError('Prediction freeze receipt required before mock confirmation')
        self.confirm('restore_nominal_capacitance', prediction)
        return self.inner.prepare_repair(prediction, receipt)

    def metadata(self):
        return {**self.inner.metadata(), 'bridge_wiring_revision': self.wiring_revision,
                'software_confirmation_only': True}


def run(run_dir):
    run_dir = Path(run_dir).resolve()
    root = Path(__file__).resolve().parents[3]
    launch = read_json(run_dir / 'launch.json')
    if launch['mode'] != MODE or launch['fault'] not in FAULTS or launch['protocol_sha256'] != PROTOCOL_SHA:
        raise ValueError('Only registered scripted mocks can run')
    if not 0 < launch['confirmation_timeout_s'] <= 300:
        raise ValueError('Invalid mock timeout')
    runner, protocol = frozen_runner(root)
    design = read_json(run_dir / 'reviewed-design.json')
    nominal, design_sha = reviewed_design(design)
    if design_sha != launch['reviewed_design_sha256']:
        raise ValueError('Reviewed design changed after launch')
    original, vision_sha = runner.vision_design(root / runner.VISION)
    if design['model_original_candidate_sha256'] != digest(original['candidate']):
        raise ValueError('Design review does not match the frozen vision record')
    log = Recorder(run_dir / 'records', mode='scripted_interactive_d01_mock')
    atomic_json(run_dir / 'record-location.json', {'path': str(log.path.relative_to(run_dir))})
    log.add('repair_run_protocol', {'source': 'mock', 'provider': 'scripted', 'nominal_design': nominal,
        'reviewed_design_sha256': design_sha, 'vision_record_sha256': vision_sha,
        'protocol_sha256': PROTOCOL_SHA, 'source_sha256': protocol['source_sha256'],
        'operator_review_simulated': True, 'physical_repair_demonstrated': False,
        'source_is_new_observations': True, 'question_sent_to_model': False,
        'bridge_launch_id': launch['run_id'], 'case_manifest_sha256': launch['case_manifest_sha256']})
    atomic_json(log.path / 'protocol.json', protocol)
    atomic_json(log.path / 'reviewed-design.json', design)
    bench = InteractiveMockBench(runner, protocol, log, launch['fault'], launch['confirmation_timeout_s'])
    model = runner.ScriptedController()
    def publish(frozen, sha):
        if launch['fault'] == 'publication_failure':
            raise ValueError('Injected mock publication failure')
        return runner.publish(log, frozen, sha, False)  # Local only; no git or network branch.
    signal.signal(signal.SIGTERM, stop_worker)
    signal.signal(signal.SIGINT, stop_worker)
    try:
        if (run_dir / 'cancel-request.json').exists():
            raise Cancelled('Cancelled before the first mock measurement')
        session = D01RepairSession(bench, log, design, publish, actor='scripted_controller')
        result = {**drive_agent(session, model), **model.metadata(), 'termination': 'completed'}
        log.add('run_completed', result)
        atomic_json(run_dir / 'result.json', result)
        return 0
    except (Exception, KeyboardInterrupt) as error:
        termination = 'cancelled' if isinstance(error, (Cancelled, KeyboardInterrupt)) else ('timed_out' if 'Operator timeout' in str(error) else 'failed')
        result = {'source': 'mock', 'decision_actor': 'scripted_controller', 'llm_used': False,
                  'termination': termination, 'error': str(error), 'repair_verified': False,
                  'physical_repair_demonstrated': False, 'automatic_retry': False,
                  **model.metadata(), 'instrument': bench.metadata()}
        log.add('run_failed', result)
        atomic_json(run_dir / 'result.json', result)
        return 1
    finally:
        model.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-dir', required=True)
    args = parser.parse_args()
    raise SystemExit(run(args.run_dir))
