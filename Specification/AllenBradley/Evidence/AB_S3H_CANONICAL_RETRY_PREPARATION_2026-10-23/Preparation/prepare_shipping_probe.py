from pathlib import Path
P=Path(__file__).parent;W=P.parent/'transport_2eff7b66442a4322a987fb2f7812268b'
t=(W/'qualify_multiplex.py').read_text();assert t.count('import socket_reads')==1
t=t.replace('import socket_reads','import fraktal_ab_paired_socket_reads as socket_reads',1)
with (P/'qualify_shipping.py').open('x') as f:f.write(t)
print('Direct qualification of the installed observer module prepared')
