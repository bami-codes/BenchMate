"""Validated passive proposals, rendered into a fixed ngspice harness.

The model supplies topology and values only, never SPICE directives or code.
Node names/orientation are preserved. Bounded diode parameters can be fitted
on training observations; they are not characterized physical 1N4148 parameters.
"""
import hashlib
from functools import lru_cache
import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
import numpy as np
from .physics import Acquisition

NODES = ('IN','OUT','REF','N1','N2')
DIODE_INITIAL = {'is_a':1e-9, 'n':1.8}
DIODE_BOUNDS = {'is_a':(1e-10,1e-7), 'n':(1.,2.5)}
SETTLING_TOLERANCE_V=1e-5
MAX_WARMUP_SECONDS=32.
MAX_STIMULUS_POINTS=50000


@lru_cache(maxsize=4)
def ngspice_version(executable):
    result=subprocess.run([executable,'--version'],capture_output=True,text=True,timeout=5)
    match=re.search(r'\bngspice-(\d+)\b',result.stdout)
    if result.returncode or not match or int(match[1])<47:
        raise RuntimeError('ngspice 47 or newer is required: older PWL breakpoint handling can change the commanded stimulus')
    return int(match[1])


def diode_parameters(parameters=None):
    p = dict(DIODE_INITIAL if parameters is None else parameters)
    if set(p) != set(DIODE_INITIAL):
        raise ValueError('Only bounded IS and N diode parameters are accepted')
    for key,value in p.items():
        lo,hi=DIODE_BOUNDS[key]
        if type(value) not in (float,int) or not np.isfinite(value) or not lo<=value<=hi:
            raise ValueError('Diode parameter outside development bounds')
    return p


def render_diode(parameters=None):
    p=diode_parameters(parameters)
    return f".model BM_DIODE D(IS={p['is_a']:.12g} N={p['n']:.12g} RS=1 TNOM=27)"
ELEMENT_SCHEMA = {'type':'object','properties':{
    'name':{'type':'string'},'kind':{'type':'string','enum':['R','C','D']},
    'a':{'type':'string','enum':list(NODES)},'b':{'type':'string','enum':list(NODES)},
    'value':{'type':'number'},'model':{'type':'string','enum':['none','generic_diode']}},
    'required':['name','kind','a','b','value','model'],'additionalProperties':False}


def validate_netlist(elements):
    if not isinstance(elements,list) or not 1<=len(elements)<=6:
        raise ValueError('Proposal must contain 1–6 passive elements')
    names=set();graph={node:set() for node in NODES}
    # The fixture supplies a voltage source from IN (or series shunt) to REF.
    graph['IN'].add('REF');graph['REF'].add('IN')
    used={'IN','OUT','REF'}
    for e in elements:
        if not isinstance(e,dict) or set(e)!=set(ELEMENT_SCHEMA['required']):
            raise ValueError('Unexpected element fields')
        name,kind=e['name'],e['kind']
        if kind not in ('R','C','D') or not isinstance(name,str) or not re.fullmatch(kind+r'[A-Za-z0-9]{1,15}',name):
            raise ValueError('Invalid passive element name/type')
        if name.lower() in names or name.lower().startswith(('rfixture','cload','dload')):
            raise ValueError('Duplicate or reserved element name')
        names.add(name.lower())
        a,b=e['a'],e['b']
        if a not in NODES or b not in NODES or a==b:
            raise ValueError('Invalid node connection')
        value=e['value']
        if type(value) not in (int,float) or not np.isfinite(value):
            raise ValueError('Invalid component value')
        if kind=='R' and (e['model']!='none' or not 1000<=value<=100000):
            raise ValueError('Resistor outside 1k–100k development range')
        if kind=='C' and (e['model']!='none' or not 1e-9<=value<=10e-6):
            raise ValueError('Capacitor outside 1n–10u development range')
        if kind=='D' and (e['model']!='generic_diode' or value!=0):
            raise ValueError('Use the bounded development diode family; value=0')
        graph[a].add(b);graph[b].add(a);used|={a,b}
    reached={'IN'}
    while True:
        extended=reached|set().union(*(graph[n] for n in reached))
        if extended==reached:break
        reached=extended
    if not used<=reached:
        raise ValueError('Floating/disconnected proposed nodes')
    return json.loads(json.dumps(elements,allow_nan=False))


def topology_fingerprint(elements):
    checked=validate_netlist(elements)
    graph=[{k:e[k] for k in ('name','kind','a','b','model')} for e in checked]
    return hashlib.sha256(json.dumps(graph,sort_keys=True).encode()).hexdigest()


def render_proposal(elements):
    lines=[]
    for e in validate_netlist(elements):
        a='0' if e['a']=='REF' else e['a'].lower()
        b='0' if e['b']=='REF' else e['b'].lower()
        value='BM_DIODE' if e['kind']=='D' else f"{e['value']:.12g}"
        lines.append(f"{e['name']} {a} {b} {value}")
    return '\n'.join(lines)


def simulate_netlist(elements,template,*,diode=None,before_run=None):
    executable=shutil.which('ngspice')
    if not executable:raise RuntimeError('ngspice is required for proposal simulation')
    version=ngspice_version(executable)
    checked=validate_netlist(elements)
    diode=diode_parameters(diode)
    settings=Acquisition(**template['settings'])
    if settings.kind=='dc_pair':raise ValueError('Proposal runner currently supports step/sine traces')
    data=template['data'];t=np.asarray(data['time_s']);ref=np.asarray(data['ref_v'])
    u=np.asarray(data['drive_v'])-ref
    if t.ndim!=1 or len(t)<2 or len(t)>5000 or ref.shape!=t.shape or u.shape!=t.shape or not np.all(np.isfinite(t+ref+u)) or not np.all(np.diff(t)>0):
        raise ValueError('Invalid input waveform')
    if t[0]!=0 or np.max(np.abs(u))>1.000001 or t[-1]>5:
        raise ValueError('Proposal stimulus outside development limits')
    source='drive' if settings.shunt_ohm else 'in'
    internal=sorted({e[k].lower() for e in checked for k in ('a','b') if e[k] in ('N1','N2')})
    vectors=['v(in)','v(out)',*[f'v({n})' for n in internal],'i(Vdrive)']
    dt=float(np.min(np.diff(t)))/4
    invocations=[]

    def run(warmup_samples):
        warmup=warmup_samples*settings.sample_period_s
        if warmup>MAX_WARMUP_SECONDS or warmup_samples+len(t)>MAX_STIMULUS_POINTS:
            raise ValueError('Periodic settling exceeds bounded simulator horizon')
        # Extend the SAME sampling grid backward; even non-integer samples per
        # period retain phase and ZOH history at capture t=0. Never use OUT.
        pre_t=np.arange(-warmup_samples,0)*settings.sample_period_s
        times=np.concatenate([pre_t,t])+warmup
        values=np.concatenate([settings.amplitude_v*np.sin(2*np.pi*settings.frequency_hz*pre_t),u]) if warmup_samples else u
        points=[(0.,values[0])]
        for i in range(1,len(times)):
            epsilon=min(1e-8,(times[i]-times[i-1])*1e-3)
            points.extend([(times[i]-epsilon,values[i-1]),(times[i],values[i])])
        lines=['BenchMate generated proposal — fixed harness',f'Vdrive {source} 0 PWL(']
        lines.extend(f'+ {time:.12g} {value:.12g}' for time,value in points)
        lines.append('+ )')
        if settings.shunt_ohm:lines.append(f'RfixtureShunt drive in {settings.shunt_ohm:.12g}')
        if settings.load_ohm:lines.append(f'RfixtureLoad out 0 {settings.load_ohm:.12g}')
        lines.extend([render_proposal(checked),render_diode(diode),'.temp 27',
                      '.options reltol=1e-7 abstol=1e-14 vntol=1e-8 minbreak=1e-12'])
        lines.extend([f'.tran {dt:.12g} {times[-1]:.12g} 0 {dt:.12g}',
                  '.control','set wr_singlescale','set numdgt=15','run',
                  'wrdata output.dat '+' '.join(vectors),'quit','.endc','.end'])
        netlist='\n'.join(lines)+'\n'
        if before_run is not None:before_run()
        with tempfile.TemporaryDirectory(prefix='benchmate-spice-') as directory:
            path=Path(directory);(path/'proposal.cir').write_text(netlist)
            completed=subprocess.run([executable,'-b','proposal.cir'],cwd=path,capture_output=True,text=True,timeout=15)
            table=path/'output.dat'
            if completed.returncode or not table.exists():
                raise ValueError('ngspice rejected the proposed topology or failed to converge')
            raw=np.loadtxt(table)
        if raw.ndim!=2 or raw.shape[1]!=len(vectors)+1 or not np.all(np.isfinite(raw)):
            raise ValueError('Invalid simulator output')
        peak=float(np.max(np.abs(raw[:,-1])))
        if peak>.01 or np.max(np.abs(raw[:,1:-1]))>1.05:
            raise ValueError('Proposed circuit exceeds development current/voltage limits')
        if raw[0,0]>1e-12 or raw[-1,0]<times[-1]-1e-9:
            raise ValueError('Incomplete simulator time span')
        sample_times=np.minimum(t+warmup+1e-10,times[-1])
        sampled=np.column_stack([np.interp(sample_times,raw[:,0],raw[:,i]) for i in range(1,len(vectors))])
        invocations.append({'warmup_s':warmup,'stimulus_points':len(times),
                            'harness_sha256':hashlib.sha256(netlist.encode()).hexdigest(),'peak_source_current_a':peak})
        return sampled

    dynamic_sine=settings.kind=='sine' and any(e['kind']=='C' for e in checked)
    settling={'method':'dc_operating_point' if settings.kind=='step' else 'memoryless_no_capacitor',
              'numerical_pre_roll_only':True}
    if dynamic_sine:
        ideal=settings.amplitude_v*np.sin(2*np.pi*settings.frequency_hz*t)
        if not np.allclose(u,ideal,atol=1e-12,rtol=0) or not np.allclose(np.diff(t),settings.sample_period_s,atol=1e-12,rtol=0):
            raise ValueError('Periodic warm-up currently requires the declared ideal command grid')
        rc_bound=sum(e['value'] for e in checked if e['kind']=='R')*sum(e['value'] for e in checked if e['kind']=='C')
        # Use a circuit-scale initial horizon rather than an entire slow sine
        # period. The doubled-history comparison below, not this estimate,
        # decides convergence on every node over the full capture interval.
        n=max(4,int(np.ceil(10*rc_bound/settings.sample_period_s)))
        previous=run(n)
        while True:
            n*=2;sampled=run(n)
            difference=float(np.max(np.abs(sampled-previous)))
            if difference<=SETTLING_TOLERANCE_V:break
            previous=sampled
        settling.update(method='doubled_pre_roll_same_capture_grid',converged=True,
                        max_node_difference_v=difference,tolerance_v=SETTLING_TOLERANCE_V,
                        warmup_s=n*settings.sample_period_s,
                        scope='Numerical convergence of all recorded node voltages; not physical settling calibration.')
    else:sampled=run(0)
    prediction={**data,'in_v':(ref+sampled[:,0]).tolist(),'out_v':(ref+sampled[:,1]).tolist()}
    return prediction,{'rendered_proposal':render_proposal(checked),
                       'topology_sha256':topology_fingerprint(checked),
                       'harness_sha256':invocations[-1]['harness_sha256'],
                       'initial_state':settling,'simulator_invocations':invocations,
                       'simulator':'ngspice','simulator_version':version,
                       'peak_source_current_a':max(r['peak_source_current_a'] for r in invocations),
                       'diode_parameters':diode,'diode_fixed_assumptions':{'rs_ohm':1.,'temperature_c':27.},
                       'physical_part_calibrated':False}
