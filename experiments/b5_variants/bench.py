"""Independent fixed-grid truth solver. No ngspice and no inference imports.

The agent receives acquisitions only. The hidden truth is never placed in an
observation, metadata, boot identifier or tool result.
"""
from copy import deepcopy
from functools import lru_cache
import hashlib
import json
import math
import numpy as np
from scipy.optimize import brentq
from scipy.special import wrightomega
from benchmate.b5_session import CONTROL, TRAINING, RESERVED, template
from benchmate.b5_bench import observation

IDS=tuple([f'D{i}' for i in range(1,9)]+['L1','L2','G1','G2','G3'])
VT=8.617333262145e-5*300.15
IS=2.7e-9
N=1.87
REF=.023
BIAS=.001

def seed(phase,variant,replicate=None):
    value=f'b5-variants-{phase}:{variant}'+(':'+str(replicate) if replicate is not None else '')
    return int.from_bytes(hashlib.sha256(value.encode()).digest()[:8],'big')

def element(kind,a,b,value=0.,i=1):
    return {'name':kind+str(i),'kind':kind,'a':a,'b':b,'value':value,
            'model':'generic_diode' if kind=='D' else 'none'}

def truth_elements(v):
    r=element('R','IN','OUT',10000.)
    up=element('D','OUT','REF');down=element('D','REF','OUT',i=2)
    definitions={
        'D1':[r,up],'D2':[r,down],'D3':[r,up,down],
        'D4':[r,up,element('R','OUT','REF',47000.,2)],
        'D5':[element('D','IN','OUT'),element('R','OUT','REF',10000.)],
        'D6':[r,up,element('C','OUT','REF',1e-6)],
        'D7':[element('R','IN','OUT',4700.),element('D','OUT','N1'),element('D','N1','REF',i=2)],
        'D8':[element('D','IN','OUT'),element('D','OUT','IN',i=2),element('R','OUT','REF',10000.)],
        'L1':[element('C','IN','OUT',1e-6),element('R','OUT','REF',10000.)],
        'L2':[element('C','IN','OUT',4.7e-6),element('R','OUT','REF',47000.)],
        'G1':[r],'G2':[r,element('C','OUT','REF',1e-6)],
        'G3':[r,element('R','OUT','REF',22000.,2)]}
    return deepcopy(definitions[v])

def diode(v,count=1):
    # Shockley junction plus 1 ohm series resistance per diode, solved via W.
    a=N*VT*count;rs=float(count)
    w=float(wrightomega(math.log(rs*IS/a)+(v+rs*IS)/a))
    return a*w/rs-IS

def static(v,u):
    if v=='G1':return u
    if v=='G3':return u*22000/32000
    if v in ('G2','L1','L2'):return u if v=='G2' else 0.
    if v in ('D1','D6'):f=lambda y:(u-y)/10000-diode(y)
    elif v=='D2':f=lambda y:(u-y)/10000+diode(-y)
    elif v=='D3':f=lambda y:(u-y)/10000-diode(y)+diode(-y)
    elif v=='D4':f=lambda y:(u-y)/10000-y/47000-diode(y)
    elif v=='D5':f=lambda y:diode(u-y)-y/10000
    elif v=='D7':f=lambda y:(u-y)/4700-diode(y,2)
    elif v=='D8':f=lambda y:diode(u-y)-diode(y-u)-y/10000
    else:raise ValueError('Unknown truth circuit')
    return brentq(f,min(0.,u)-.01,max(0.,u)+.01,xtol=1e-13)

def advance(v,state,u,dt,period,substeps):
    if dt<=0:return state
    tau=.2209 if v=='L2' else .01
    if v!='D6':return u+(state-u)*math.exp(-dt/tau)
    # Implicit Euler on a distinct physical solver, at least 20 substeps/frame.
    count=max(1,math.ceil(dt/(period/substeps)));h=dt/count
    for _ in range(count):
        previous=state
        state=brentq(lambda y:(y-previous)*1e-6/h-(u-y)/10000+diode(y),
            min(previous,u,0.)-.01,max(previous,u,0.)+.01,xtol=1e-12)
    return state

@lru_cache(maxsize=256)
def _truth(variant,serialized,substeps):
    settings=json.loads(serialized);t=template(settings,'mock_adc_input_only')
    drive=.997*np.asarray(t['data']['input_relative_origin_v'])+.0012*np.sin(np.arange(settings['samples'])*.31)
    u=drive-REF;period=settings['period_us']*1e-6
    dynamic=variant in ('G2','D6','L1','L2')
    if not dynamic:y=np.array([static(variant,float(x)) for x in u])
    else:
        if settings['kind']=='step':
            initial=float(u[:settings['samples']//10].mean())
            state=static('D6',initial) if variant=='D6' else initial
        else:
            cycle=round(1/(settings['frequency_hz']*period));state=0.
            # Repeat the first input cycle until the state itself has settled.
            for n in range(100):
                previous=state
                for val in u[:cycle]:state=advance(variant,state,float(val),period,period,substeps)
                if n>=1 and abs(state-previous)<1e-9:break
            else:raise ValueError('Truth solver warmup did not settle')
        values=[]
        for i,val in enumerate(u):
            sampled=advance(variant,state,float(val),t['data']['output_delay_s'][i],period,substeps)
            values.append(float(val)-sampled if variant.startswith('L') else sampled)
            state=advance(variant,sampled,float(val),period-t['data']['output_delay_s'][i],period,substeps)
        y=np.asarray(values)
    return t,drive,y+REF+BIAS

def noiseless(variant,settings,substeps=20):
    t,u,y=_truth(variant,json.dumps(settings,sort_keys=True),substeps)
    t=deepcopy(t);t['data']['input_relative_origin_v']=u.tolist()
    return t,y.copy()

class VariantBench:
    source='mock'
    def __init__(self,log,variant,noise_seed,noise=True):
        if variant not in IDS:raise ValueError('Variant outside frozen grid')
        self.log=log;self._variant=variant;self._seed=noise_seed;self.noise=noise
        self.prepared=False;self.count=0;self._occurrences={}
    def prepare_specimen(self):
        if self.prepared:raise ValueError('One simulated installation only')
        self.prepared=True
        self.log.add('operator_wiring_confirmation',{'source':'mock','simulated':True})
    def acquire(self,settings,role):
        if (settings not in CONTROL+TRAINING+RESERVED or role not in ('control','training','verification')
            or (role=='control')==self.prepared):raise ValueError('Invalid role, menu or mock fixture state')
        key=json.dumps({'purpose':role,'settings':settings},sort_keys=True)
        occurrence=self._occurrences.get(key,0);self._occurrences[key]=occurrence+1
        derived=hashlib.sha256(f'{self._seed}:{key}:{occurrence}'.encode()).digest()
        rng=np.random.default_rng(int.from_bytes(derived[:8],'big'))
        t,y=noiseless(self._variant if self.prepared else 'G1',settings)
        u=np.asarray(t['data']['input_relative_origin_v'])
        if self.noise:
            t['data']['input_relative_origin_v']=(u+rng.normal(0,.0012,len(u))).tolist()
            y+=rng.normal(0,.0015,len(y))
        self.count+=1
        return observation('mock',deepcopy(settings),role,'mock-specimen' if self.prepared else 'mock-control',
                           'mock-origin',t,y)
    def metadata(self):
        return {'source':'mock','waveforms':self.count,'real_serial_commands':0,
                'physical_measurements':0,'operator_actions_simulated':True}

def captures(variant,noise_seed,noise=True):
    class Null:
        def add(self,*args):pass
    b=VariantBench(Null(),variant,noise_seed,noise);b.prepare_specimen()
    return [b.acquire(s,'training') for s in TRAINING],[b.acquire(s,'verification') for s in RESERVED]
