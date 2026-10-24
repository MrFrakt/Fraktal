from pathlib import Path
W=Path(__file__).parent
t=(W/'qualify_baseline.py').read_text().replace('import read_burst','import socket')
t=t.replace("samples={'sequential':[],'burst':[]}","samples={'default':[],'nodelay':[]}")
t=t.replace("for mode in ('sequential','burst'):","for mode in ('default','nodelay'):")
t=t.replace("                    acquire=reads.acquire if mode=='sequential' else read_burst.acquire",
    "                    acquire=reads.acquire\n                    for channel in channels:channel.conn.Socket.setsockopt(socket.IPPROTO_TCP,socket.TCP_NODELAY,int(mode=='nodelay'))")
t=t.replace('maximumPendingPerConnection=16','maximumPendingPerConnection=1')
assert 'read_burst' not in t
with (W/'qualify_nodelay.py').open('x') as f:f.write(t)
print('Read-only one-outstanding-request TCP_NODELAY probe prepared')
