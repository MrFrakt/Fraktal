"""Read-only identity check for this explicitly authorized Echo session only."""
import json
from pathlib import Path
import subprocess
import sys
from pylogix import PLC

subprocess.run(['powershell','-NoProfile','-NonInteractive','-Command',
                'if ((Get-Service -Name "FactoryTalk Logix Echo Service").Status -ne "Running") { exit 1 }'],
               check=True, stdout=subprocess.DEVNULL)
with PLC('127.0.0.1') as comm:
    comm.ProcessorSlot = 0
    comm.SocketTimeout = 3
    response = comm.GetDeviceProperties()
    value = response.Value
    if response.Status != 'Success' or value is None:
        raise SystemExit('Echo identity acquisition failed')
    identity = dict(address='127.0.0.1', serial=value.SerialNumber,
                    revision=value.Revision, product=value.ProductName,
                    productCode=value.ProductCode)
    print(json.dumps(identity), flush=True)
    if (str(value.SerialNumber).lower() != '0x601fc87b' or value.Revision != '38.11'
            or value.ProductName != 'Emulate 5580 Controller' or value.ProductCode != 288):
        raise SystemExit('Refusing unexpected controller identity')
    # The authorized address is served by the local Echo emulator process.
    command = ("$c=Get-NetTCPConnection -State Listen -LocalAddress 127.0.0.1 -LocalPort 44818; "
               "if ((Get-Process -Id $c.OwningProcess).ProcessName -ne 'EmulateControlLogix5580') {exit 1}")
    subprocess.run(['powershell','-NoProfile','-NonInteractive','-Command',command],check=True,
                   stdout=subprocess.DEVNULL)

# Refuse a faulted controller; clearing it is separately authorized.
inspection = subprocess.run(["C:/work/fraktal-echo-control-20261018/bin/Debug/net8.0-windows/EchoControl.exe", "inspect"], check=True, text=True, stdout=subprocess.PIPE)
state = json.loads(inspection.stdout)
if state["SerialNumber"] != 0x601FC87B or state["IsFaulted"] or state["KeySwitchPosition"] != 0:
    raise SystemExit("Echo mode readiness/fault/keyswitch guard failed; no fault clear permitted")
print(json.dumps(state), flush=True)
