from pathlib import Path
W=Path(__file__).parent
raw=(W/'run_header_probe_01.py').read_text(encoding='utf-8')
raw=raw.replace('header_peer_wire_01.log','header_peer_wire_02.log')
raw=raw.replace('header_probe_01.log','header_client_02.log').replace('header_probe_01.json.gz','header_probe_02.json.gz')
with (W/'run_header_probe_02.py').open('x') as f:f.write(raw)
