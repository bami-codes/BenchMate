"""Validated passive proposals, rendered into a fixed ngspice harness.

The model supplies topology and values only, never SPICE directives or code.
Node names/orientation are preserved. Development diode parameters are shared
library assumptions, not characterized physical 1N4148 parameters.
"""
import hashlib
import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
import numpy as np
from .physics import Acquisition

NODES = ('IN','OUT','REF','N1','N2')
DIODE_MODEL = '.model BM_DIODE D(IS=1e-9 N=1.8 RS=1 TNOM=27)'
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
            raise ValueError('Use the fixed development diode library; value=0')
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


def simulate_netlist(elements,template):
    executable=shutil.which('ngspice')
    if not executable:raise RuntimeError('ngspice is required for proposal simulation')
    checked=validate_netlist(elements)
    settings=Acquisition(**template['settings'])
    if settings.kind=='dc_pair':raise ValueError('Proposal runner currently supports step/sine traces')
    data=template['data'];t=np.asarray(data['time_s']);ref=np.asarray(data['ref_v'])
    u=np.asarray(data['drive_v'])-ref
    if t.ndim!=1 or len(t)<2 or len(t)>5000 or ref.shape!=t.shape or u.shape!=t.shape or not np.all(np.isfinite(t+ref+u)) or not np.all(np.diff(t)>0):
        raise ValueError('Invalid input waveform')
    if t[0]!=0 or np.max(np.abs(u))>1.000001 or t[-1]>5:
        raise ValueError('Proposal stimulus outside development limits')
    # PWL with an epsilon just before each update represents the recorded ZOH.
    points=[(0.,u[0])]
    for i in range(1,len(t)):
        epsilon=min(1e-8,(t[i]-t[i-1])*1e-3)
        points.extend([(t[i]-epsilon,u[i-1]),(t[i],u[i])])
    source='drive' if settings.shunt_ohm else 'in'
    lines=['BenchMate generated proposal — fixed harness',f'Vdrive {source} 0 PWL(']
    lines.extend(f'+ {time:.12g} {value:.12g}' for time,value in points)
    lines.append('+ )')
    if settings.shunt_ohm:lines.append(f'RfixtureShunt drive in {settings.shunt_ohm:.12g}')
    if settings.load_ohm:lines.append(f'RfixtureLoad out 0 {settings.load_ohm:.12g}')
    lines.extend([render_proposal(checked),DIODE_MODEL,'.temp 27','.options reltol=1e-5 abstol=1e-12'])
    internal=sorted({e[k].lower() for e in checked for k in ('a','b') if e[k] in ('N1','N2')})
    vectors=['v(in)','v(out)',*[f'v({n})' for n in internal],'i(Vdrive)']
    dt=float(np.min(np.diff(t)))/4
    lines.extend([f'.tran {dt:.12g} {t[-1]:.12g} 0 {dt:.12g}',
                  '.control','set wr_singlescale','set numdgt=15','run',
                  'wrdata output.dat '+' '.join(vectors),'quit','.endc','.end'])
    netlist='\n'.join(lines)+'\n'
    with tempfile.TemporaryDirectory(prefix='benchmate-spice-') as directory:
        path=Path(directory);(path/'proposal.cir').write_text(netlist)
        completed=subprocess.run([executable,'-b','proposal.cir'],cwd=path,capture_output=True,text=True,timeout=15)
        table=path/'output.dat'
        if completed.returncode or not table.exists():
            raise ValueError('ngspice rejected the proposed topology or failed to converge')
        raw=np.loadtxt(table)
    if raw.ndim!=2 or raw.shape[1]!=len(vectors)+1 or not np.all(np.isfinite(raw)):
        raise ValueError('Invalid simulator output')
    if np.max(np.abs(raw[:,-1]))>.01 or np.max(np.abs(raw[:,1:-1]))>1.05:
        raise ValueError('Proposed circuit exceeds development current/voltage limits')
    if raw[0,0]>t[0]+1e-12 or raw[-1,0]<t[-1]-1e-9:
        raise ValueError('Incomplete simulator time span')
    # Step transitions are compared at the post-update sample for algebraic nodes.
    sample_times=np.minimum(t+1e-10,t[-1])
    prediction={**data,'in_v':(ref+np.interp(sample_times,raw[:,0],raw[:,1])).tolist(),
                'out_v':(ref+np.interp(sample_times,raw[:,0],raw[:,2])).tolist()}
    return prediction,{'rendered_proposal':render_proposal(checked),
                       'topology_sha256':topology_fingerprint(checked),
                       'harness_sha256':hashlib.sha256(netlist.encode()).hexdigest(),
                       'simulator':'ngspice','peak_source_current_a':float(np.max(np.abs(raw[:,-1]))),
                       'physical_part_calibrated':False}
