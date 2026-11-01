import sys
from pathlib import Path
import numpy as np
import pytest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'experiments'))
from b5_variants.bench import VariantBench,captures,noiseless,seed,diode,REF,BIAS,IDS
from benchmate.b5_session import TRAINING,RESERVED
from benchmate.b5_models import predict,score,validate

class Null:
    def add(self,*args):pass

def test_truth_linear_controls_agree_with_independent_prediction():
    for v,pars in [('G1',{'r_ohm':10000.}),('G2',{'r_ohm':10000.,'c_f':1e-6}),
                   ('G3',{'r_ohm':10000.,'output_parallel_ohm':22000.})]:
        model={'kind':'linear','family':v,'parameters':pars,'reference_v':REF,'output_offset_v':BIAS}
        train,res=captures(v,seed('dev',v),noise=False)
        for c in train+res:
            result=score(c,predict(model,c['input_template']))
            assert max([result['RMS_mV']]+[r['RMS_mV'] for r in result['regions']])<4.5

def test_waveforms_are_reproducible_and_order_independent():
    a,b=[VariantBench(Null(),'D1',seed('dev','D1')) for _ in range(2)]
    a.prepare_specimen();b.prepare_specimen()
    first=a.acquire(TRAINING[0],'training');a.acquire(TRAINING[0],'training')
    second=a.acquire(TRAINING[1],'training')
    assert b.acquire(TRAINING[1],'training')==second
    assert b.acquire(TRAINING[0],'training')==first
    assert seed('select','D1',1)!=seed('eval','D1')

def test_hidden_truth_not_in_observation_metadata_or_identifiers():
    b=VariantBench(Null(),'D4',seed('dev','D4'));b.prepare_specimen()
    c=b.acquire(TRAINING[1],'training');validate(c,'training')
    assert set(c)=={'source','voltage_basis','all_guards_passed','purpose','settings','boot_id','origin_id','input_template','output_relative_origin_v'}
    assert c['boot_id']=='mock-specimen'
    assert set(b.metadata())=={'source','waveforms','real_serial_commands','physical_measurements','operator_actions_simulated'}

def test_diode_truth_satisfies_kirchhoff_and_polarity():
    for v in ('D1','D2'):
        t,y=noiseless(v,TRAINING[2]);u=np.array(t['data']['input_relative_origin_v'])-REF;out=y-REF-BIAS
        i=np.array([diode(x) if v=='D1' else -diode(-x) for x in out])
        assert np.max(np.abs((u-out)/10000-i))<1e-10
    _,positive=noiseless('D1',TRAINING[2]);_,negative=noiseless('D2',TRAINING[2])
    assert max(positive)<.6 and min(negative)>-.6

def test_dynamic_diode_numerical_convergence():
    for settings in (TRAINING[1],RESERVED[1]):
        _,coarse=noiseless('D6',settings,20);_,fine=noiseless('D6',settings,40)
        assert np.max(np.abs(coarse-fine))<.002

def test_every_registered_waveform_is_valid():
    for v in IDS:
        train,res=captures(v,seed('dev',v))
        for c in train+res:validate(c)

def test_failed_alternative_cannot_create_distinguishability():
    from copy import deepcopy
    from b5_variants.run import classify
    row={'variant':'D1','session_gate':{'status':'all_candidates_inadequate','candidates':[{'optimizer_converged':True}]},
         'alternatives':{'linear:resistor':{'status':'finished','training_passed':False,'all_passed':False},
                         'netlist:D1':{'status':'finished','training_passed':True,'all_passed':True},
                         'netlist:D2':{'status':'fit_failed'}}}
    reps=[deepcopy(row) for _ in range(3)]
    verdict=classify(reps)
    assert verdict['class']=='distinguishability_unresolved' and not verdict['primary']
    for r in reps:r['alternatives']['netlist:D2']={'status':'finished','training_passed':False,'all_passed':False}
    assert classify(reps)['primary']
    reps[0]['alternatives']['netlist:D2']['all_passed']=True
    assert classify(reps)['class']=='confusable'


def test_unfinished_selection_and_actual_gate_mismatch_are_not_primary():
    from b5_variants.run import classify
    assert classify([])['class']=='selection_incomplete'
    assert not classify([{'incomplete':True}]*3)['primary']
