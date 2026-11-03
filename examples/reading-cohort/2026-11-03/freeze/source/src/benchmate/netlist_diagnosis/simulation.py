"""Reuse the frozen measured-IN solver, with an explicit ideal jumper adapter.

Branches directly across an ideal measured IN do not affect conditional OUT.
They are logged as unobservable and excluded from source-current checks: the
artificial PWL edge is not a measured capacitor charging-current waveform.
"""
from pathlib import Path
import shutil
import subprocess
import tempfile
import numpy as np

from ..physical_netlist import simulate_physical_netlist, validate_input_template
from ..netlist import ngspice_version
from .design import elements as check_elements, digest


def conditional_elements(value):
    checked = check_elements(value)
    wired = any(e['kind'] == 'W' for e in checked)
    removed, kept = [], []
    for e in checked:
        terminals = {e['a'], e['b']}
        across_input = terminals == {'IN', 'REF'} or (wired and e['kind'] != 'W')
        (removed if across_input else kept).append(e)
    return kept, removed


def simulate(value, input_template, *, diode=None, before_run=None):
    checked = check_elements(value)
    kept, removed = conditional_elements(checked)
    if any(e['kind'] == 'W' for e in kept):
        # The only allowed wire ties OUT directly to the already measured IN.
        # Execute that literal connection in ngspice rather than add a fake R.
        s, t, u, di, do, cycle = validate_input_template(input_template)
        executable = shutil.which('ngspice')
        if not executable:
            raise RuntimeError('ngspice is required.')
        version = ngspice_version(executable)
        edge = 1e-8
        points = [(0., float(u[0]))]
        for i in range(1, len(t)):
            points.extend([(float(t[i] - edge), float(u[i-1])), (float(t[i]), float(u[i]))])
        stop = float(t[-1] + do[-1] + 1e-7)
        points.append((stop, float(u[-1])))
        lines = ['BenchMate explicit IN-OUT jumper', 'Vdrive in 0 PWL(']
        lines += [f'+ {a:.12g} {b:.12g}' for a, b in points]
        lines += ['+ )', 'Vwire out in 0', '.options reltol=1e-7 vntol=1e-8',
                  f'.tran {s["period_us"]*1e-6/4:.12g} {stop:.12g}',
                  '.control', 'set wr_singlescale', 'set numdgt=15', 'run',
                  'wrdata output.dat v(out)', 'quit', '.endc', '.end']
        if before_run:
            before_run()
        with tempfile.TemporaryDirectory(prefix='benchmate-wire-') as directory:
            p = Path(directory)
            (p/'wire.cir').write_text('\n'.join(lines)+'\n')
            result = subprocess.run([executable, '-b', 'wire.cir'], cwd=p,
                                    capture_output=True, text=True, timeout=15)
            if result.returncode or not (p/'output.dat').exists():
                raise ValueError('ngspice rejected the explicit jumper.')
            data = np.loadtxt(p/'output.dat')
        if data.ndim != 2 or data.shape[1] != 2 or not np.isfinite(data).all():
            raise ValueError('Invalid jumper simulator output.')
        output = np.interp(t+do, data[:, 0], data[:, 1])
        result = {'predicted_output_minus_ref_v': output.tolist(), 'simulator': 'ngspice',
                  'simulator_version': version, 'simulator_invocations': [{'explicit_ideal_jumper': True}],
                  'scored_output_samples_used': 0, 'model_refitted': False}
    else:
        result = simulate_physical_netlist(kept, input_template, diode=diode, before_run=before_run)
    return {**result, 'declared_topology_sha256': digest(checked),
            'unobservable_input_branches': [e['name'] for e in removed],
            'conditional_source_current_is_not_total_DUT_current': bool(removed)}
