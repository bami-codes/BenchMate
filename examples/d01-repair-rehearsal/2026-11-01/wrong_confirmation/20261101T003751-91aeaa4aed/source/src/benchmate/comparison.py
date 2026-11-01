"""Frozen-model comparisons, separate from original verification evidence.

Historical reconstructions are sidecars bound to an unchanged source record.
Predictions never use verification observations. Residual checks necessarily do.
Historical reconstruction never mutates the original event chain.
"""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
from .inference import families_for, fit_family
from .noise import NoiseModel, adequacy
from .physics import Acquisition
from .stimulus import command_template
from .vector import predict_many
from .records import decode_events


def best_linear_comparison(fits, captures,*,legacy_rc=False):
    family,fit=max(fits,key=lambda pair:pair[1]['log_likelihood'])
    return {'family':family.to_dict(),'parameters':fit['model'].tolist(),
            'comparison_scope':'legacy_rc_families' if legacy_rc else 'declared_linear_families_v2',
            'candidate_families':[f.to_dict() for f,_ in fits],
            'selection':'Maximum training likelihood among the declared '+('RC' if legacy_rc else 'linear')+' families',
            'conditions':[{'settings':c['settings'],'time_s':c['data']['time_s'],
                'out_v':predict_many(fit['model'],c)['out_v'][0].tolist()} for c in captures]}


def frozen_linear_prediction(comparison, settings):
    """Evaluate training-frozen parameters on commands, without any observations."""
    template=command_template(Acquisition(**settings))
    values=predict_many(np.asarray(comparison['parameters']),template)
    return {**template['data'],**{k:v[0].tolist() for k,v in values.items()}}


def prediction_separation(baseline, proposal):
    delta=np.asarray(baseline['out_v'])-np.asarray(proposal['out_v'])
    return {'out_rms_mv':float(1000*np.sqrt(np.mean(delta**2))),
            'out_peak_mv':float(1000*np.max(np.abs(delta)))}


def verification_comparison(baseline, proposal, capture, noise):
    def score(prediction):
        residual=np.asarray(capture['data']['out_v'])-np.asarray(prediction['out_v'])
        gate=adequacy(prediction,capture,noise)
        return {'out_rms_mv':float(1000*np.sqrt(np.mean(residual**2))),
                'out_peak_mv':float(1000*np.max(np.abs(residual))),
                'worst_normalized_regional_rms':max(c['normalized_rms'] for c in gate['checks']),
                'adequacy':gate}
    rc,spark=score(baseline),score(proposal)
    passed=(rc['adequacy']['passed'],spark['adequacy']['passed'])
    return {'settings':capture['settings'],'baseline':rc,'proposal':spark,
            'separation':prediction_separation(baseline,proposal),
            'discrimination':{(False,True):'proposal_only_passes',(True,True):'both_pass',
                              (False,False):'neither_passes',(True,False):'baseline_only_passes'}[passed],
            'refitted_on_verification':False,
            'scope':'One best training-fit model among the declared linear topologies; not all possible circuits. RMS separation is descriptive, not a calibrated power estimate.'}


def reconstruct_comparisons(run):
    from .netlist import simulate_netlist
    path=Path(run)
    if path.is_dir():path=path/'events.jsonl'
    raw=path.read_bytes();events=decode_events(raw,include_hash=True)
    entries=[];rc=None;baseline_predictions={};noise=None
    for i,event in enumerate(events):
        kind=event['kind'];p=event['payload']
        if kind=='discovery_configuration':noise=NoiseModel(**p['noise'])
        if kind not in ('initial_family_assessment','proposal_fit','prediction_committed','verification'):continue
        # Only data available before this assessment; never use later captures.
        training=[e for e in events[:i] if e['kind']=='acquisition']
        captures=[e['payload'] for e in training]
        if not captures or any(c.get('source')!='synthetic' for c in captures):continue
        if kind=='initial_family_assessment':
            rc=p.get('training_comparison')
            if rc is not None:continue
            # Old records predate the C=0 expansion. Never substitute a newer
            # candidate grammar into their original assessment or agent story.
            config=next(e['payload'] for e in events[:i] if e['kind']=='discovery_configuration')
            from .inference import Family
            families=[Family(**{k:v for k,v in f.items() if k in ('name','r_bounds','c_bounds','rp_bounds','output_bounds')}) for f in config['families']] if 'families' in config else [f for f in families_for('mystery') if f.c_bounds is not None]
            fits=[(family,fit_family(family,captures,noise)) for family in families]
            comparison=rc=best_linear_comparison(fits,captures,legacy_rc='families' not in config)
        elif kind=='proposal_fit':
            if 'training_predictions' in p:continue
            conditions=[]
            for capture in captures:
                template=command_template(Acquisition(**capture['settings']))
                predicted,meta=simulate_netlist(p['elements'],template,diode=p.get('diode_parameters'))
                conditions.append({'settings':capture['settings'],'time_s':predicted['time_s'],
                                   'out_v':predicted['out_v'],'simulator':meta})
            comparison={'conditions':conditions}
        elif kind=='prediction_committed':
            if rc is None or noise is None:continue
            comparison=p.get('baseline_comparison') or {
                'prediction':frozen_linear_prediction(rc,p['settings']),
                'parameters':rc['parameters'],'family':rc['family'],
                'comparison_scope':rc.get('comparison_scope','legacy_rc_families'),
                'training_frozen':True}
            baseline_predictions[event['sequence']]=comparison['prediction']
            if 'baseline_comparison' in p:continue
            comparison['separation']=prediction_separation(comparison['prediction'],p['prediction'])
        else:
            if 'comparison_conditions' in p or not baseline_predictions:continue
            conditions=[]
            for observation in events[:i]:
                if observation['kind']!='verification_acquisition':continue
                capture=observation['payload']
                prediction=next((e for e in reversed(events[:i]) if e['kind']=='prediction_committed'
                    and e['sequence']<observation['sequence'] and e['payload']['settings']==capture['settings']),None)
                if prediction is None or prediction['sequence'] not in baseline_predictions:continue
                conditions.append(verification_comparison(baseline_predictions[prediction['sequence']],
                    prediction['payload']['prediction'],capture,noise))
            if not conditions:continue
            comparison={'conditions':conditions}
        entries.append({'event_sequence':event['sequence'],'event_sha256':event['sha256'],
                        'kind':kind,
                        'training_event_sequences':[e['sequence'] for e in training],
                        'comparison':comparison})
    result={'schema_version':2,'source_sha256':hashlib.sha256(raw).hexdigest(),
            'generated_at':datetime.now(timezone.utc).isoformat(),
            'implementation_sha256':{name:hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
                for name in ('comparison.py','inference.py','vector.py','noise.py','netlist.py','stimulus.py')},
            'provenance':'reconstructed_frozen_model_comparison',
            'note':'Computed after the run. RC counterfactuals use training-frozen parameters and command settings only; they were not originally committed predictions. Verification observations are used only to score residuals, never to fit or select models.',
            'entries':entries}
    target=path.parent/'comparison.json'
    target.write_text(json.dumps(result,allow_nan=False)+'\n')
    return target


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('run')
    print(reconstruct_comparisons(parser.parse_args().run))
