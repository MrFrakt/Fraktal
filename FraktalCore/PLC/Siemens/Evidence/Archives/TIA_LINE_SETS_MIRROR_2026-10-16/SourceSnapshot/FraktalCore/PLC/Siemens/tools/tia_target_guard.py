"""Measured reference-simulator identity guard, shared by adapters and probes."""
import json,os,subprocess
from pathlib import Path

def guard():
    result=subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',
        str(Path(__file__).resolve().parents[1]/'Spikes/S12_TypeMap/simulator.ps1'),'-Action','status'],capture_output=True)
    if result.returncode:raise RuntimeError('simulator identity unavailable')
    status=json.loads(result.stdout.decode('utf-8-sig'))
    expected=os.environ.get('FRAKTAL_TIA_SIM_INSTANCE','FrkS12')
    if expected not in ('FrkS12','Fraktal') or status['name']!=expected or status['cpu']!='CPU1516' or status['comm']!='TCPIP' or '169.254.212.49' not in status['addresses'] or any(status[k]!=0 for k in ('ie1','ie2','ie3')):
        raise RuntimeError('isolated target guard failed')
    return status
