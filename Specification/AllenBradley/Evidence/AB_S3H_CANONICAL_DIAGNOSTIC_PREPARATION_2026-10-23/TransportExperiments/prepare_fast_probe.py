from pathlib import Path
W=Path(__file__).parent;T=Path('C:/Users/SoftIndVM/Fraktal/FraktalCore/PLC/Allen-Bradley/tools')
t=(T/'fraktal_ab_paired_socket_reads.py').read_text()
needle="    states=[]\n    def next_request(s):"
assert t.count(needle)==1
t=t.replace(needle,"""    states=[]
    def send_pending(s):
        try:sent=s['sock'].send(s['tx'][s['sent']:])
        except BlockingIOError:return
        if sent<=0:raise OSError('connected read send ended early')
        s['sent']+=sent
    def next_request(s):""")
needle="        s.update(tx=frame[:12]+b'\\0'*8+frame[20:],sent=0,rx=bytearray(),total=None)"
assert t.count(needle)==1
t=t.replace(needle,needle+'\n        send_pending(s)')
needle="""                try:sent=sock.send(s['tx'][s['sent']:])
                except BlockingIOError:continue
                if sent<=0:raise OSError('connected read send ended early')
                s['sent']+=sent"""
assert t.count(needle)==1;t=t.replace(needle,'                send_pending(s)')
with (W/'socket_fast.py').open('x') as f:f.write(t)
old=W.parent/'transport_2eff7b66442a4322a987fb2f7812268b'
t=(old/'qualify_multiplex.py').read_text().replace('import socket_reads','import socket_fast as socket_reads')
t=t.replace('range(20)','range(100)')
with (W/'qualify_fast.py').open('x') as f:f.write(t)
t=(T/'test_fraktal_ab_paired_socket_reads.py').read_text().replace('import fraktal_ab_paired_socket_reads as reads','import socket_fast as reads')
with (W/'test_socket_fast.py').open('x') as f:f.write(t)
P=W.parent/'retry_fc306d330cc642499a52abbb53bae945'
with (W/'run_logged.py').open('x') as f:f.write((P/'run_logged.py').read_text())
