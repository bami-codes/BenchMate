"""Explicit software test actor; never attributed to Spark or shipped as its choice."""
from copy import deepcopy
import json


class ScriptedController:
    def __init__(self, actions=None):
        self.actions = list(actions or ['unloaded_step_small', 'loaded_step_small', 'unloaded_sine_1hz_large'])
        self.state = None
        self.calls = 0

    def next_call(self):
        self.calls += 1
        if self.calls > 10:
            raise RuntimeError('Scripted rehearsal budget exhausted.')
        s = self.state
        if s is None:
            name, args = 'inspect_experiment', {}
        elif len(s['training_actions']) < len(self.actions) and s['allowed_measurements']:
            name, args = 'measure', {'action': self.actions[len(s['training_actions'])],
                                     'reason': 'SOFTWARE REHEARSAL SCRIPT: common development condition; not a Spark decision.'}
        elif s['verification_available']:
            name, args = 'verify_prediction', {}
        elif s['structure_available'] and not s['proposals']:
            value = deepcopy(s['intended_elements'])
            if any(e['kind'] == 'W' for e in value):
                value = [e for e in value if e['kind'] != 'W']
                value.append(dict(name='Rextra', kind='R', a='IN', b='OUT', value=10000., model='none'))
            elif len(value) == 2 and all(e['kind'] == 'R' for e in value):
                value.append(dict(name='Dextra', kind='D', a='OUT', b='REF', value=0., model='generic_diode'))
            else:
                return self._finish(s)
            name, args = 'propose_structure', {'elements': value,
                         'rationale': 'SOFTWARE SCRIPT ONLY: development proposal from the public circuit shape; no hidden assembly input.'}
        else:
            return self._finish(s)
        return self._call(name, args)

    def _call(self, name, args):
        return {'call_id': 'scripted-' + str(self.calls), 'name': name, 'arguments': json.dumps(args)}

    def _finish(self, s):
        return self._call('finish_report', {**s['expected_report'],
            'explanation': 'SOFTWARE REHEARSAL ONLY: numerical development outcome, not a Spark or physical result.',
            'limits': 'Shared simulator, provisional engineering threshold, and conditional input. Unseen parts and equivalent circuits remain unresolved.'})

    def submit_result(self, call_id, result):
        if 'error' in result:
            raise RuntimeError('Rehearsal tool rejected: ' + result['error'])
        self.state = result

    def sanitize(self, value): return value
    def metadata(self): return {'provider': 'scripted', 'http_requests': 0, 'Spark_authored': False, 'tool_calls': self.calls}
    def close(self): pass
