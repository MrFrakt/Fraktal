from pathlib import Path
W=Path(__file__).parent;T=Path('C:/Users/SoftIndVM/Fraktal/FraktalCore/PLC/Allen-Bradley/tools')
text=(T/'fraktal_ab_paired_socket_reads.py').read_text()
assert text.count('2<=len(channels)<=4')==1
text=text.replace('2<=len(channels)<=4','2<=len(channels)<=8').replace('two to four distinct','two to eight distinct')
with (W/'socket_reads.py').open('x') as f:f.write(text)
text=(T/'fraktal_ab_canonical_equivalence.py').read_text()
assert text.count("            row['waitingFreshScan'] = True\n            continue")==1
text=text.replace("            row['waitingFreshScan'] = True\n            continue", "            row['waitingFreshScan'] = True\n            time.sleep(.001)\n            continue")
with (W/'paced_equivalence.py').open('x') as f:f.write(text)
P=W.parent/'retry_9d1da9a04d564b03bc2b176f5b17ea42'
text=(P/'qualify_scan_start.py').read_text()
text=text.replace("P=Path(__file__).parent;T=",f"P=Path('{P.as_posix()}');W=Path(__file__).parent;T=")
text=text.replace('import fraktal_ab_paired_socket_reads as sockets','import socket_reads as sockets')
text=text.replace('from fraktal_ab_canonical_equivalence import stable_scan_pair','from paced_equivalence import stable_scan_pair')
text=text.replace('connections=4','connections=8').replace('range(4)','range(8)').replace('i::4','i::8')
text=text.replace('range(20)','range(100)').replace("(P/'scan_start_proxy_01.json')","(W/'scan_start_proxy_01.json')")
text=text.replace("transportModuleSha256=hashlib.sha256((T/'fraktal_ab_paired_socket_reads.py').read_bytes()).hexdigest()", "transportModuleSha256=hashlib.sha256((W/'socket_reads.py').read_bytes()).hexdigest(),pacedWaitingPollSeconds=.001")
with (W/'qualify_scan_start.py').open('x') as f:f.write(text)
with (W/'run_logged.py').open('x') as f:f.write((P/'run_logged.py').read_text())
