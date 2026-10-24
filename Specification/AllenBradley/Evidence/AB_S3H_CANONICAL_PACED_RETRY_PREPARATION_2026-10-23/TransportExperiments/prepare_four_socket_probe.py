from pathlib import Path
W=Path(__file__).parent;t=(W/'qualify_scan_start.py').read_text()
t=t.replace('connections=8','connections=4').replace('range(8)','range(4)').replace('i::8','i::4')
t=t.replace('range(100)','range(250)').replace('scan_start_proxy_01.json','four_paced_proxy_01.json')
with (W/'qualify_four_paced.py').open('x') as f:f.write(t)
