"""Independent circuit-solver cross-check. Skipped if ngspice is unavailable."""
import shutil
import subprocess
import numpy as np
import pytest
from benchmate.physics import Acquisition,RCModel,predict


@pytest.mark.skipif(shutil.which("ngspice") is None,reason="ngspice not installed")
@pytest.mark.parametrize("parallel,drive",[(None,1.0),(10000,1.0),(10000,-1.0)])
def test_dc_shunt_against_ngspice_operating_point(tmp_path,parallel,drive):
    shunt=1000
    resistor="" if parallel is None else f"Rp in 0 {parallel}\n"
    netlist=(f"BenchMate independent DC check\nVdrive drive 0 DC {drive}\n"
             f"Rs drive in {shunt}\nR1 in out 10000\nC1 out 0 1u\n{resistor}"
             ".control\nset wr_singlescale\nset numdgt=15\nop\nwrdata result.dat v(in) v(out)\nquit\n.endc\n.end\n")
    path=tmp_path/"circuit.cir";path.write_text(netlist)
    subprocess.run([shutil.which("ngspice"),"-b",str(path)],cwd=tmp_path,check=True,capture_output=True,text=True,timeout=10)
    actual=np.loadtxt(tmp_path/"result.dat").reshape(-1)
    expected=predict(RCModel(10000,1e-6,parallel),Acquisition(kind="dc_pair",shunt_ohm=1000,amplitude_v=1))
    index=1 if drive>0 else 0
    np.testing.assert_allclose(actual[-2:],np.array([expected["in_v"][index],expected["out_v"][index]])-1.6,atol=1e-9)

