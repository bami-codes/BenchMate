"""Passive proposals driven by independently anchored measured IN-minus-REF.

This simulator never accepts scored OUT. It reconstructs one held input level
per command frame and samples at each recorded A2 completion delay. Its sine
history repeats the first measured input cycle, an explicit physical assumption
whose numerical settling is checked, not a measurement of the prior history.
"""
import hashlib
import math
from pathlib import Path
import shutil
import subprocess
import tempfile
import numpy as np
from .netlist import (validate_netlist, render_proposal, topology_fingerprint,
                      diode_parameters, render_diode, ngspice_version,
                      SETTLING_TOLERANCE_V, MAX_WARMUP_SECONDS, MAX_STIMULUS_POINTS)


def validate_input_template(template):
    if not isinstance(template,dict) or set(template)!={'source','settings','data'}:
        raise ValueError('Input-only template required; scored OUT is not accepted')
    if template['source'] not in ('physical_input_only','adc_input_only','mock_adc_input_only','command_input_only'):
        raise ValueError('Explicit physical input-only provenance required')
    s=template['settings'];d=template['data']
    input_key='input_minus_ref_v' if template['source']=='physical_input_only' else 'input_relative_origin_v'
    if set(s)!={'kind','period_us','samples','frequency_hz','step_index','load_ohm'}:
        raise ValueError('Unexpected physical input settings')
    if set(d)!={'frame_time_s',input_key,'input_delay_s','output_delay_s'}:
        raise ValueError('Only measured input and channel timestamps are accepted')
    arrays=[np.asarray(d[k],dtype=float) for k in
            ('frame_time_s',input_key,'input_delay_s','output_delay_s')]
    t,u,di,do=arrays
    if (type(s['samples']) is not int or not 16<=s['samples']<=512 or
        any(a.shape!=(s['samples'],) or not np.isfinite(a).all() for a in arrays)):
        raise ValueError('Finite matching physical input arrays required')
    if (type(s['period_us']) is not int or not 250<=s['period_us']<=20000 or
        t[0]<0 or t[0]>25e-6 or np.any(np.diff(t)<=0)):
        raise ValueError('Invalid command frame timing')
    period=s['period_us']*1e-6
    if np.max(np.abs(t-(t[0]+np.arange(len(t))*period)))>25e-6:
        raise ValueError('Frame timing differs from declared grid')
    t=t-t[0]
    if t[-1]>5 or np.max(np.abs(u))>.95:
        raise ValueError('Measured input exceeds the physical development envelope')
    durations=np.r_[np.diff(t),period]
    if np.any(di<0) or np.any(do<di) or np.any(do>=durations):
        raise ValueError('OUT completion must follow IN within each command frame')
    load=s['load_ohm']
    if load is not None and (type(load) not in (int,float) or not math.isfinite(load) or not 1000<=load<=100000):
        raise ValueError('Invalid independently measured output load')
    cycle=None
    if s['kind']=='step':
        if s['frequency_hz'] is not None or type(s['step_index']) is not int or not 1<=s['step_index']<len(t):
            raise ValueError('Declared step index and no sine frequency required')
    elif s['kind']=='sine':
        f=s['frequency_hz']
        if type(f) not in (int,float) or not math.isfinite(f) or not 1<=f<=500 or s['step_index'] is not None:
            raise ValueError('Valid sine frequency required')
        cycle=round(1/(f*period))
        if not 20<=cycle<len(t) or abs(t[cycle]-1/f)>25e-6:
            raise ValueError('A complete measured input cycle on the declared grid is required')
    else:raise ValueError('Only step or sine input supported')
    return s,t,u,di,do,cycle


def simulate_physical_netlist(elements,template,*,diode=None,before_run=None):
    """Return an OUT prediction conditional on measured IN, with no output fit."""
    s,t,u,di,do,cycle=validate_input_template(template)
    checked=validate_netlist(elements);diode=diode_parameters(diode)
    executable=shutil.which('ngspice')
    if not executable:raise RuntimeError('ngspice is required for physical proposal simulation')
    version=ngspice_version(executable)
    internal=sorted({e[k].lower() for e in checked for k in ('a','b') if e[k] in ('N1','N2')})
    vectors=['v(in)','v(out)',*[f'v({node})' for node in internal],'i(Vdrive)']
    invocations=[]

    def run(cycles):
        warmup=cycles*t[cycle] if cycles else 0.
        pre_count=cycles*cycle if cycles else 0
        if warmup>MAX_WARMUP_SECONDS or pre_count+len(t)>MAX_STIMULUS_POINTS:
            raise ValueError('Measured-cycle settling exceeds bounded simulator horizon')
        if cycles:
            starts=np.concatenate([t[:cycle]+j*t[cycle] for j in range(cycles)])
            times=np.r_[starts,t+warmup]
            values=np.r_[np.tile(u[:cycle],cycles),u]
            initial=float(values[0])
        else:
            times=t.copy();values=u.copy()
            initial=float(u[:s['step_index']].mean()) if s['kind']=='step' else float(u[0])
        # Start at the pre-step mean; A2 is sampled after the initial transition.
        # Edges remain small compared with the recorded per-channel delays.
        edge=min(1e-8,float(np.min(np.diff(times)))*1e-3)
        points=[(0.,initial),(edge,float(values[0]))]
        for i in range(1,len(times)):
            points.extend([(float(times[i]-edge),float(values[i-1])),
                           (float(times[i]),float(values[i]))])
        sample_times=t+warmup+do
        stop=float(sample_times[-1]+max(edge,1e-7))
        points.append((stop,float(values[-1])))
        # The measured input is conditioned on the DUT. No source/shunt model is
        # inferred here, so IN-to-REF branches are not identifiable from OUT alone.
        lines=['BenchMate physical measured-IN fixed harness','Vdrive in 0 PWL(']
        lines.extend(f'+ {when:.12g} {value:.12g}' for when,value in points)
        lines.append('+ )')
        if s['load_ohm'] is not None:lines.append(f"RfixtureLoad out 0 {s['load_ohm']:.12g}")
        lines.extend([render_proposal(checked),render_diode(diode),'.temp 27',
            '.options reltol=1e-7 abstol=1e-14 vntol=1e-8 minbreak=1e-12'])
        dt=float(np.min(np.diff(times)))/4
        lines.extend([f'.tran {dt:.12g} {stop:.12g} 0 {dt:.12g}',
            '.control','set wr_singlescale','set numdgt=15','run',
            'wrdata output.dat '+' '.join(vectors),'quit','.endc','.end'])
        netlist='\n'.join(lines)+'\n'
        if before_run is not None:before_run()
        with tempfile.TemporaryDirectory(prefix='benchmate-physical-spice-') as directory:
            path=Path(directory);(path/'proposal.cir').write_text(netlist)
            completed=subprocess.run([executable,'-b','proposal.cir'],cwd=path,
                capture_output=True,text=True,timeout=15)
            table=path/'output.dat'
            if completed.returncode or not table.exists():
                raise ValueError('ngspice rejected the proposed topology or failed to converge')
            raw=np.loadtxt(table)
        if raw.ndim!=2 or raw.shape[1]!=len(vectors)+1 or not np.isfinite(raw).all():
            raise ValueError('Invalid simulator output')
        peak=float(np.max(np.abs(raw[:,-1])))
        if peak>.01 or np.max(np.abs(raw[:,1:-1]))>1.05:
            raise ValueError('Proposed circuit exceeds development current/voltage limits')
        if raw[0,0]>1e-12 or raw[-1,0]<stop-1e-9:
            raise ValueError('Incomplete simulator time span')
        sampled=np.column_stack([np.interp(sample_times,raw[:,0],raw[:,i])
                                 for i in range(1,len(vectors))])
        invocations.append({'warmup_cycles':cycles,'warmup_s':warmup,
            'stimulus_points':len(times),'peak_source_current_a':peak,
            'harness_sha256':hashlib.sha256(netlist.encode()).hexdigest()})
        return sampled

    dynamic_sine=s['kind']=='sine' and any(e['kind']=='C' for e in checked)
    initialization={'method':'settled_pre_step_input_mean' if s['kind']=='step' else 'memoryless_no_capacitor'}
    if dynamic_sine:
        rc_bound=sum(e['value'] for e in checked if e['kind']=='R')*sum(e['value'] for e in checked if e['kind']=='C')
        cycles=max(1,math.ceil(10*rc_bound/t[cycle]))
        previous=run(cycles)
        while True:
            cycles*=2;sampled=run(cycles)
            difference=float(np.max(np.abs(sampled-previous)))
            if difference<=SETTLING_TOLERANCE_V:break
            previous=sampled
        initialization={'method':'repeated_first_measured_input_cycle','input_samples_used':cycle,
            'cycle_duration_s':float(t[cycle]),'warmup_cycles':cycles,
            'numerical_convergence':True,'max_node_difference_v':difference,
            'tolerance_v':SETTLING_TOLERANCE_V,
            'assumption':'The first captured IN cycle represents the preceding settled periodic drive.',
            'physical_history_measured':False}
    else:sampled=run(0)
    return {'predicted_output_minus_ref_v':sampled[:,1].tolist(),
        'input_provenance':template['source'],
        'predicted_input_minus_ref_v':sampled[:,0].tolist(),
        'initialization':initialization,'simulator_invocations':invocations,
        'topology_sha256':topology_fingerprint(checked),'rendered_proposal':render_proposal(checked),
        'diode_parameters':diode,'diode_fixed_assumptions':{'rs_ohm':1.,'temperature_c':27.},
        'simulator':'ngspice','simulator_version':version,
        'scored_output_samples_used':0,'model_refitted':False,
        'input_delay_interpretation':'A1 completion reports the held level for its command frame.',
        'scope':'Measured-IN conditional physical-bias prediction; provisional channel gains and assumed settled input history.',
        'input_parallel_branches_identifiable':False,'physical_part_calibrated':False}
