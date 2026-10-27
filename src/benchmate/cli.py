import argparse
import json
import shutil
import sys
from pathlib import Path
from .config import load_keys
from .workflow import run_synthetic
from .records import read_events


def show(value): print(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False))


def main():
    parser=argparse.ArgumentParser(prog="benchmate",description="BenchMate day-one development tools")
    sub=parser.add_subparsers(dest="command",required=True)
    sub.add_parser("doctor",help="Report setup status without displaying secrets")
    sim=sub.add_parser("simulate",help="Continuous engine-only experiment, no API calls")
    sim.add_argument("--case",required=True,choices=["b1","b6","d01-r","d01-c"])
    sim.add_argument("--seed",type=int,default=1)
    sim.add_argument("--output",default="runs")
    sim.add_argument("--mode",choices=["mystery","repair"],default="mystery")
    sim.add_argument("--max-hz",type=float,default=100)
    sim.add_argument("--r-scale",type=float,default=1)
    sim.add_argument("--c-scale",type=float,default=1)
    replay=sub.add_parser("replay",help="Verify and replay a stored run; no new model calls")
    replay.add_argument("path")
    api=sub.add_parser("api-smoke",help="At most two live API requests with a synthetic tool")
    api.add_argument("--provider",choices=["meta","baseten"],default="meta")
    api.add_argument("--effort",choices=["medium","max"],default="medium")
    api.add_argument("--output",default="runs")
    agent=sub.add_parser("agent",help="Live Muse Spark chooses tools on a synthetic circuit; at most 8 API requests")
    agent.add_argument("--case",required=True,choices=["b1","b6","d01-r","d01-c"])
    agent.add_argument("--seed",type=int,default=1)
    agent.add_argument("--effort",choices=["medium","max"],default="medium")
    agent.add_argument("--output",default="runs")
    agent.add_argument("--mode",choices=["mystery","repair"],default="mystery")
    agent.add_argument("--max-hz",type=float,default=100)
    agent.add_argument("--r-scale",type=float,default=1)
    agent.add_argument("--c-scale",type=float,default=1)
    hardware=sub.add_parser("capture",help="Acquire uncalibrated raw counts from bring-up firmware")
    hardware.add_argument("--port",required=True)
    hardware.add_argument("--output",default="runs")
    instrument=sub.add_parser("instrument",help="D2 raw stimulus/capture; establish REF with DUT disconnected before attaching a test circuit")
    instrument.add_argument("--port",required=True)
    instrument.add_argument("--vref-v",type=float,required=True,help="Measured board supply/DAC reference voltage")
    instrument.add_argument("--ref-v",type=float,default=1.6)
    instrument.add_argument("--kind",choices=["hold","step","sine"],default="step")
    instrument.add_argument("--samples",type=int,default=512)
    instrument.add_argument("--arm-only",action="store_true",help="Establish REF with DUT disconnected; capture is a separate command")
    instrument.add_argument("--boot-id",help="Boot ID returned by --arm-only; required for capture")
    instrument.add_argument("--period-us",type=int,default=500)
    instrument.add_argument("--amplitude-v",type=float,default=.5)
    instrument.add_argument("--frequency-hz",type=float)
    instrument.add_argument("--hold-v",type=float)
    instrument.add_argument("--output",default="runs")
    discovery=sub.add_parser("discover",help="Live Spark proposes and verifies a nonlinear netlist on synthetic observations")
    discovery.add_argument("--effort",choices=["medium","max"],default="max")
    discovery.add_argument("--output",default="runs")
    repair=sub.add_parser("repair",help="Synthetic D01 diagnosis, committed repair prediction, replacement and remeasurement")
    repair.add_argument("--case",required=True,choices=["d01-r","d01-c"])
    repair.add_argument("--live",action="store_true",help="Use live Spark for diagnosis; otherwise engine only")
    repair.add_argument("--r-scale",type=float,default=1)
    repair.add_argument("--c-scale",type=float,default=1)
    repair.add_argument("--output",default="runs")
    view=sub.add_parser("view",help="Export a self-contained evidence viewer; no API calls")
    view.add_argument("path")
    view.add_argument("--output")
    watch=sub.add_parser("watch",help="Read-only live log viewer on loopback; uses the same UI as replay")
    watch.add_argument("path")
    watch.add_argument("--port",type=int,default=8765)
    args=parser.parse_args()
    try:
        if args.command=="doctor":
            from serial.tools.list_ports import comports
            show({"keys_present":{k:bool(v) for k,v in load_keys().items()},
                  "tools":{x:shutil.which(x) for x in ("arduino-cli","ngspice","gh")},
                  "serial_ports":[p.device for p in comports()],
                  "hardware_calibrated":False})
        elif args.command=="simulate":
            from .experiments import run_experiment
            path,result=run_experiment(args.case,mode=args.mode,seed=args.seed,output=args.output,
                                     max_hz=args.max_hz,r_scale=args.r_scale,c_scale=args.c_scale)
            show({"run":str(path),**result})
        elif args.command=="replay":
            events=read_events(args.path)
            show({"replay_kind":"exact_recording","integrity":"passed","events":len(events),
                  "terminal_event":events[-1]["kind"],"result":events[-1]["payload"]})
        elif args.command=="api-smoke":
            from .providers import smoke
            path,result=smoke(args.provider,effort=args.effort,output=args.output)
            show({"run":str(path),**result})
        elif args.command=="agent":
            from .experiments import run_experiment
            path,result=run_experiment(args.case,mode=args.mode,live=True,seed=args.seed,effort=args.effort,
                                     output=args.output,max_hz=args.max_hz,r_scale=args.r_scale,c_scale=args.c_scale)
            show({"run":str(path),**result})
        elif args.command=="capture":
            from .hardware import capture_raw
            path,result=capture_raw(args.port,output=args.output)
            show({"run":str(path),**result})
        elif args.command=="instrument":
            from .instrument import InstrumentConfig,acquire_block
            path,result=acquire_block(args.port,InstrumentConfig(args.vref_v,args.ref_v),output=args.output,arm_only=args.arm_only,expected_boot_id=args.boot_id,
                kind=args.kind,samples=args.samples,period_us=args.period_us,amplitude_v=args.amplitude_v,
                frequency_hz=args.frequency_hz,hold_v=args.hold_v)
            show({"run":str(path),**result})
        elif args.command=="discover":
            from .discovery import run_discovery
            path,result=run_discovery(effort=args.effort,output=args.output)
            show({"run":str(path),**result})
        elif args.command=="repair":
            from .repair import run_repair
            path,result=run_repair(args.case,live=args.live,r_scale=args.r_scale,c_scale=args.c_scale,output=args.output)
            show({"run":str(path),**result})
        elif args.command=="view":
            from .viewer import export_viewer
            show({'report':str(export_viewer(args.path,args.output)),'api_calls':0})
        elif args.command=="watch":
            from .live_viewer import serve_viewer
            serve_viewer(args.path,args.port)
    except (ValueError,RuntimeError,OSError) as exc:
        print(f"benchmate: {exc}",file=sys.stderr)
        return 1
    return 0


if __name__=="__main__": sys.exit(main())
