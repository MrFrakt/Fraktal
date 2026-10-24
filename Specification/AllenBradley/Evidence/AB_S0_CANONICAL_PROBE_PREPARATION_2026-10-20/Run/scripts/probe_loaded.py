"""Read-only: the exact local Echo, and the S0 probe is the image loaded."""
import subprocess, sys
from pylogix import PLC
subprocess.run([sys.executable, 'C:/work/fraktal-ab-s0-20261020/readiness_20edac489b6c46e2b6229c76d400e9e7/scripts/guard_echo.py'], check=True)
with PLC('127.0.0.1') as c:
    c.ProcessorSlot = 0; c.SocketTimeout = 10
    tags = c.GetTagList(allTags=False).Value
    probe = next((t for t in tags if t.TagName == 'FRK_S12_Probe'), None)
    if probe is None or probe.DataType != 'FRK_T_S0Probe' or any(t.TagName.startswith('FRK_Press_') for t in tags):
        raise SystemExit('loaded image is not the S0 probe')
    print('{"probeLoaded": true}')
