from pathlib import Path
P=Path(__file__).parent;OLD=P.parent/'retry_9d1da9a04d564b03bc2b176f5b17ea42'
t=(OLD/'qualify_scan_start.py').read_text()
assert t.count('range(20)')==1
t=t.replace('range(20)','range(1000)')
with (P/'qualify_scan_start.py').open('x') as f:f.write(t)
