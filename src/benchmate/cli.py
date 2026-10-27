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
    sim=sub.add_parser("simulate",help="Synthetic engine-only experiment, no API calls")
    sim.add_argument("--case",required=True,choices=["b1","b6","d01-r","d01-c"])
    sim.add_argument("--seed",type=int,default=1)
    sim.add_argument("--output",default="runs")
    replay=sub.add_parser("replay",help="Verify and replay a stored run; no new model calls")
    replay.add_argument("path")
    api=sub.add_parser("api-smoke",help="At most two live API requests with a synthetic tool")
    api.add_argument("--provider",choices=["meta","baseten"],default="meta")
    api.add_argument("--effort",choices=["medium","max"],default="medium")
    api.add_argument("--output",default="runs")
    hardware=sub.add_parser("capture",help="Acquire uncalibrated raw counts from bring-up firmware")
    hardware.add_argument("--port",required=True)
    hardware.add_argument("--output",default="runs")
    args=parser.parse_args()
    try:
        if args.command=="doctor":
            from serial.tools.list_ports import comports
            show({"keys_present":{k:bool(v) for k,v in load_keys().items()},
                  "tools":{x:shutil.which(x) for x in ("arduino-cli","ngspice","gh")},
                  "serial_ports":[p.device for p in comports()],
                  "hardware_calibrated":False})
        elif args.command=="simulate":
            path,result=run_synthetic(args.case,seed=args.seed,output=args.output)
            show({"run":str(path),**result})
        elif args.command=="replay":
            events=read_events(args.path)
            show({"replay_kind":"exact_recording","integrity":"passed","events":len(events),
                  "terminal_event":events[-1]["kind"],"result":events[-1]["payload"]})
        elif args.command=="api-smoke":
            from .providers import smoke
            path,result=smoke(args.provider,effort=args.effort,output=args.output)
            show({"run":str(path),**result})
        elif args.command=="capture":
            from .hardware import capture_raw
            path,result=capture_raw(args.port,output=args.output)
            show({"run":str(path),**result})
    except (ValueError,RuntimeError,OSError) as exc:
        print(f"benchmate: {exc}",file=sys.stderr)
        return 1
    return 0


if __name__=="__main__": sys.exit(main())

