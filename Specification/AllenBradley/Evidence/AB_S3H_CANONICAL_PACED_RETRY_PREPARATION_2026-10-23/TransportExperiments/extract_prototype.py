from pathlib import Path
W=Path(__file__).parent;p=W/'paced_equivalence.py';t=p.read_text()
p.write_text('import time\n\n'+t[t.index('def stable_scan_pair('):t.index('\ndef main():')])
