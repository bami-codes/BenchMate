"""Read-only conversation derived from the pinned Oct 30 physical event prefix.

Screen translations and summaries are editorial text, never new Spark output.
No fit, prediction, API call or hardware operation is performed here.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

from ..design_replay import D01, D01_SHA
from ..records import decode_events

STEPS = [0, 7, 48, 49, 52, 54, 55, 93, 94, 97, 132, 133, 137, 139]
LABELS = {'nominal_rc': 'Design unchanged', 'r_changed': 'A · Resistance changed',
          'c_changed': 'B · Capacitance changed'}
PHASES = {'unloaded_step': 'Unloaded step', 'attach_output_load_step': 'Loaded step',
          'reserved_sine': 'Reserved 5 Hz sine'}


class RecordedConversation:
    def __init__(self, root):
        raw = (Path(root) / D01 / 'events.jsonl').read_bytes()
        if hashlib.sha256(raw).hexdigest() != D01_SHA:
            raise ValueError('Physical archive does not match its pinned hash')
        self.events = decode_events(raw, include_hash=True)

    def _cursor(self, cursor):
        if type(cursor) is not int or not 0 <= cursor < len(self.events):
            raise ValueError('Invalid replay position')

    def event(self, sequence, cursor):
        self._cursor(cursor)
        if type(sequence) is not int or not 0 <= sequence <= cursor:
            raise ValueError('Event is outside the selected prefix')
        return deepcopy(self.events[sequence])

    def snapshot(self, cursor):
        self._cursor(cursor)
        # All derivation below uses only this prefix. No terminal score is cached.
        visible = self.events[:cursor + 1]
        payload = {e['sequence']: e['payload'] for e in visible}
        messages, plots = [], []
        ledger = [{'id': k, 'label': v, 'status': 'unresolved', 'scores': {}} for k, v in LABELS.items()]
        def message(seq, actor, title, text, *, source='summary', refs=None, **extra):
            messages.append(dict(id=f'event-{seq}', sequence=seq, actor=actor, title=title,
                                 text=text, source=source, refs=refs or [seq], **extra))
        def args(seq):
            return json.loads(payload[seq]['arguments'])
        def plot(seq, comparison=None):
            observation = payload[seq]
            data, base = observation['data'], observation['baseline']
            times = [t+d for t,d in zip(data['frame_time_s'], data['output_delay_s'], strict=True)]
            result = dict(id=observation['phase'], title=PHASES[observation['phase']], sequence=seq,
                          refs=[seq], time_s=times, observed_v=[v-base['output_v'] for v in data['output_v']],
                          baseline=deepcopy(base), predictions={}, scores={})
            if comparison in payload:
                result['refs'].append(comparison)
                for key, score in payload[comparison]['scores'].items():
                    result['predictions'][key] = [v-base['output_v'] for v in score['prediction']['predicted_output_v']]
                    result['scores'][key] = {k: deepcopy(score[k]) for k in ('RMS_mV', 'passed', 'regions')}
            plots.append(result)
        if 7 in payload:
            message(7, 'Muse Spark', 'Measure the response first',
                    'First identify the overall time constant with an unloaded step, to check the deviation from the nominal design.',
                    source='screen_translation', original=args(7)['reason'])
        if 47 in payload:
            plot(47)
        if 48 in payload:
            training = payload[48]
            nominal = training['point_models']['nominal_rc']
            tau = training['tau_s']
            message(48, 'BenchMate', 'The response is slower than designed',
                    f"Measured time constant: {tau*1000:.1f} ms. The nominal design gives {nominal['R_ohm']*nominal['C_f']*1000:.0f} ms. This step identifies R × C, not R and C separately.",
                    refs=[47, 48], plot='unloaded_step', metrics={'tau_ms':tau*1000},
                    models=deepcopy(training['point_models']))
        if 49 in payload:
            message(49, 'BenchMate', 'Two explanations, fixed before the loaded capture',
                    'A larger resistor or a larger capacitor can explain the first step. These model parameters are now fixed. Conditional curves will use the measured input when it arrives.',
                    frozen_models=deepcopy(payload[49]['models']))
        if 52 in payload:
            message(52, 'Muse Spark', 'Spark chose the load test over repeating the step',
                    'An unloaded step identifies only τ = R × C, so it cannot separate an R change from a C change, and repeating it adds no information. A 9.99 kΩ load from OUT to REF changes the steady-state gain through the R divider, which separates the two. The operator does the rewiring by hand.',
                    source='screen_translation', original=args(52)['reason'], refs=[50,52], emphasis=True,
                    choices=deepcopy(payload[50]['result']['allowed_measurements']))
        if 54 in payload:
            message(54, 'BenchMate', 'Recorded request · Connect the output load',
                    'The bench turns Spark’s choice into one wiring request. Disconnect USB and wait for the LED to go out; connect E30–A55, with the IN branch absent and the remaining wiring unchanged; reconnect USB and report completion.',
                    source='runner_instruction_translation', original=payload[54]['instruction'], request=deepcopy(payload[54]),
                    operator_confirmed=55 in payload)
        if 55 in payload:
            message(55, 'Operator', 'Wiring completion recorded',
                    'The operator reported the output load connected, the IN branch absent, and USB reconnected.',
                    source='summary', original=deepcopy(payload[55]))
        if 93 in payload:
            plot(93, 94)
            message(93, 'BenchMate', 'Loaded response captured',
                    'A new physical capture is available. Model scores appear when the recorded comparison completes.', plot='attach_output_load_step')
        if 94 in payload:
            scores=payload[94]['scores']
            message(94, 'BenchMate', 'The load separates the explanations',
                    f"A: {scores['r_changed']['RMS_mV']:.1f} mV RMS error. B: {scores['c_changed']['RMS_mV']:.1f} mV RMS error. Only B passes both the overall and regional 9 mV checks.",
                    plot='attach_output_load_step', refs=[49,93,94])
            for row in ledger:
                score=scores[row['id']]
                row.update(status='supported' if score['passed'] else 'rejected')
                row['scores']['loaded_step']=score['RMS_mV']
        if 97 in payload:
            message(97, 'BenchMate', 'Spark asks for the reserved check',
                    'Spark called verify_prediction with no arguments, asking the bench to run its reserved condition. The waveform was specified by the protocol.', refs=[97])
        if 132 in payload:
            plot(132,133)
            message(132, 'BenchMate', 'Reserved waveform captured',
                    'The bench measured the reserved 5 Hz sine using the same fixed models.', plot='reserved_sine', refs=[98,132])
        if 133 in payload:
            scores=payload[133]['scores']
            message(133, 'BenchMate', 'The fixed explanation passes another waveform',
                    f"B: {scores['c_changed']['RMS_mV']:.2f} mV RMS error; all regional checks pass. No model was refitted on this check.",
                    plot='reserved_sine', refs=[49,132,133])
            for row in ledger:
                score=scores[row['id']]
                row.update(status='supported' if score['passed'] else 'rejected')
                row['scores']['reserved_sine']=score['RMS_mV']
        answer, followups = None, []
        if 137 in payload:
            ratio=payload[48]['point_models']['c_changed']['C_f']/payload[48]['point_models']['nominal_rc']['C_f']
            answer=dict(title=f'Capacitance behaves like {ratio:.1f}× the design value.',
                        assumption='Assuming nominal R, within the tested RC alternatives.',
                        observed='The loaded step and reserved sine support the capacitance-change model.',
                        unknown='This does not identify the hidden parts or precise R and C independently. Absolute voltage accuracy and repair are not established.',
                        refs=[48,49,94,133,137], original=deepcopy(payload[137]), repair_performed=False)
            followups=[dict(id='resistor', question='Could it be the resistor?',
                           text=f"The tested R-change model has {payload[94]['scores']['r_changed']['RMS_mV']:.1f} mV RMS error on the loaded step, versus {payload[94]['scores']['c_changed']['RMS_mV']:.1f} mV for the C-change model. R-change fails the recorded checks. This comparison does not exclude every possible circuit fault.",
                           refs=[49,94], plot='attach_output_load_step'),
                       dict(id='certainty', question='What is still unknown?', text=answer['unknown']+' The 9 mV engineering allowance is not a calibrated confidence interval.', refs=[137]),
                       dict(id='prediction', question='What was fixed before measuring?',
                           text='Model parameters were fixed after the unloaded training step and before the loaded capture. The plotted voltage curves are conditional on the measured IN. They were not pre-acquisition DAC predictions.', refs=[49,93,94], plot='attach_output_load_step')]
        refs=sorted({r for m in messages for r in m['refs']} | {r for p in plots for r in p['refs']} | set(answer['refs'] if answer else []))
        return dict(schema='benchmate.recorded_conversation.v1', cursor=cursor, last_sequence=len(self.events)-1,
                    timestamp=visible[-1]['timestamp'], steps=STEPS, data_origin='Physical', mode='Replay',
                    record_path=D01, record_sha256=D01_SHA, messages=messages, hypotheses=ledger,
                    plots=plots, answer=answer, followups=followups,
                    evidence=[dict(sequence=i, kind=visible[i]['kind'], timestamp=visible[i]['timestamp'], sha256=visible[i]['sha256']) for i in refs])
