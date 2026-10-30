from pathlib import Path
W=Path(__file__).parent
raw=(W/'qualify_peer_01.py').read_text(encoding='utf-8')
for name in ['observer_peer_wire_01.log','observer_01.log','observer_01.json.gz','configuration_peer_01.log',
 'configuration_peer_01.json.gz','configuration_peer_comparison_01.json','observer_peer_qualification_01.json']:
 raw=raw.replace(name,name.replace('_01','_02'))
raw=raw.replace("configuration=subprocess.run([str(DART),'--packages='", "configuration=subprocess.run([str(DART),'-Dfraktal.cip.trace=true','--packages='")
with (W/'qualify_peer_02.py').open('x') as f:f.write(raw)
