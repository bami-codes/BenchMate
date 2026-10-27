"""Read-only bring-up transport; raw counts are never treated as calibrated volts."""
import json
import time
import serial
from .records import Recorder


def validate_capture(data, *, protocol="benchmate-bringup-v1"):
    if data.get("protocol")!=protocol or data.get("type")!="capture":
        raise ValueError("Unexpected firmware protocol")
    if data.get("source")!="hardware_uncalibrated" or data.get("adc_bits")!=14:
        raise ValueError("Unexpected capture provenance")
    if data.get("channels")!=["A1","A2","A3","A4"]:
        raise ValueError("Unexpected channel order")
    samples=data.get("samples",[])
    if not 1<=len(samples)<=64: raise ValueError("Invalid block length")
    previous=-1
    for sample in samples:
        times=sample.get("t_us",[]);raw=sample.get("raw",[])
        if len(times)!=4 or len(raw)!=4: raise ValueError("Invalid block dimensions")
        for t,v in zip(times,raw):
            if type(t) is not int or t<0 or t<previous:
                raise ValueError("Invalid channel timestamp")
            if type(v) is not int or not 0<=v<16384:
                raise ValueError("ADC sample outside 14-bit range")
            previous=t
    return data


def capture_raw(port, *, output="runs"):
    log=Recorder(output,mode="hardware_uncalibrated")
    try:
        with serial.Serial(port,115200,timeout=1,write_timeout=2) as board:
            time.sleep(2)
            board.reset_input_buffer()
            board.write(b"PING\n")
            pong=json.loads(board.readline())
            if pong.get("protocol")!="benchmate-bringup-v1" or pong.get("type")!="pong":
                raise ValueError("Board did not answer bring-up PING")
            log.add("firmware_handshake",pong)
            board.write(b"CAPTURE\n")
            raw=board.read_until(b"\n",size=65536)
            capture=validate_capture(json.loads(raw))
            log.add("raw_capture",capture)
            summary={"source":"hardware_uncalibrated","samples":len(capture["samples"]),
                     "diagnosis_performed":False,"stimulus_generated":False}
            log.add("run_completed",summary)
            return log.path,summary
    except Exception as exc:
        log.add("run_failed",{"error":type(exc).__name__,"source":"hardware_uncalibrated"})
        raise RuntimeError(f"Board capture failed ({type(exc).__name__}); record: {log.path}") from None
