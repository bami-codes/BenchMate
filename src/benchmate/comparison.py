"""Training-fit illustrations, separate from precommitted verification evidence.

Historical reconstructions are sidecars bound to an unchanged source record.
They never see verification observations or mutate the original event chain.
"""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from .inference import families_for, fit_family
from .noise import NoiseModel
from .vector import predict_many
from .records import decode_events


def best_rc_comparison(fits, captures):
    family,fit=max(fits,key=lambda pair:pair[1]['log_likelihood'])
    return {'family':family.to_dict(),'parameters':fit['model'].tolist(),
            'selection':'Maximum training likelihood among the declared RC families',
            'conditions':[{'settings':c['settings'],'time_s':c['data']['time_s'],
                'out_v':predict_many(fit['model'],c)['out_v'][0].tolist()} for c in captures]}


def reconstruct_comparisons(run):
    from .netlist import simulate_netlist
    from .physics import Acquisition
    from .stimulus import command_template
    path=Path(run)
    if path.is_dir():path=path/'events.jsonl'
    raw=path.read_bytes();events=decode_events(raw,include_hash=True)
    entries=[]
    for i,event in enumerate(events):
        if event['kind'] not in ('initial_family_assessment','proposal_fit'):continue
        # Only data available before this assessment; never use later captures.
        training=[e for e in events[:i] if e['kind']=='acquisition']
        captures=[e['payload'] for e in training]
        if not captures or any(c.get('source')!='synthetic' for c in captures):continue
        if event['kind']=='initial_family_assessment':
            if 'training_comparison' in event['payload']:continue
            config=next(e['payload'] for e in events[:i] if e['kind']=='discovery_configuration')
            noise=NoiseModel(**config['noise'])
            fits=[(family,fit_family(family,captures,noise)) for family in families_for('mystery')]
            comparison=best_rc_comparison(fits,captures)
        else:
            if 'training_predictions' in event['payload']:continue
            p=event['payload'];conditions=[]
            for capture in captures:
                template=command_template(Acquisition(**capture['settings']))
                predicted,meta=simulate_netlist(p['elements'],template,diode=p.get('diode_parameters'))
                conditions.append({'settings':capture['settings'],'time_s':predicted['time_s'],
                                   'out_v':predicted['out_v'],'simulator':meta})
            comparison={'conditions':conditions}
        entries.append({'event_sequence':event['sequence'],'event_sha256':event['sha256'],
                        'training_event_sequences':[e['sequence'] for e in training],
                        'comparison':comparison})
    result={'schema_version':1,'source_sha256':hashlib.sha256(raw).hexdigest(),
            'generated_at':datetime.now(timezone.utc).isoformat(),
            'implementation_sha256':{name:hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
                for name in ('comparison.py','inference.py','vector.py','noise.py','netlist.py','stimulus.py')},
            'provenance':'reconstructed_training_fit',
            'note':'Recomputed for presentation after the run. These curves are not recorded pre-observation predictions. Verification data were not used.',
            'entries':entries}
    target=path.parent/'comparison.json'
    target.write_text(json.dumps(result,allow_nan=False)+'\n')
    return target


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('run')
    print(reconstruct_comparisons(parser.parse_args().run))
