import os,sys,json,subprocess
from pylogix import PLC
subprocess.run([sys.executable,'C:/work/fraktal-ab-s2-20261021/prepare_3701f795c13b4329891f4eca1346b3a5/scripts/guard_echo.py'],check=True)
os.environ['FRAKTAL_AB_DECLARATION']='fraktal_ab_genealogy_demo'
sys.path.insert(0,'C:/Users/SoftIndVM/Fraktal/FraktalCore/PLC/Allen-Bradley/tools')
import fraktal_ab_manifest_read as reader
import fraktal_ab_manifest as manifest
import fraktal_ab_station as station
with PLC('127.0.0.1') as c:
    c.ProcessorSlot=0;c.ConnectionSize=4000;c.SocketTimeout=5
    raw,status,unused=reader._read_raw(c,manifest.header_tag(station.application()))
    if raw is None:raise SystemExit('known genealogy header required for Run recovery')
    h=reader.decode_header(raw)
    print(json.dumps(h))
    if h['ContentHash']!='6DEC4C1DC2F7F78A':raise SystemExit('unexpected image header')
