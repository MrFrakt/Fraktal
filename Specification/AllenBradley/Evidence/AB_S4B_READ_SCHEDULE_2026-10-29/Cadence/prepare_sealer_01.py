from pathlib import Path
W=Path(__file__).parent;F=Path('C:/work/fraktal-ab-s4b-serial-20261029/offline_01')
raw=(F/'seal_qualification_01.py').read_text(encoding='utf-8')
raw=raw.replace("'windows_profile_01'","'windows_profile_02'").replace("'analyze_02'","'analyze_02'")
raw=raw.replace("'peer_qualification_01'","'peer_qualification_02'").replace('+750 ~12: All tests passed!','+752 ~12: All tests passed!')
raw=raw.replace("W/'observer_peer_qualification_01.json'","W/'observer_peer_qualification_02.json'")
raw=raw.replace("W/'configuration_peer_comparison_01.json'","W/'configuration_peer_comparison_02.json'")
needle='current={}\n'
addition="""# Preserve the superseded serial-only experiment and both failed profile sequences.
F=Path('C:/work/fraktal-ab-s4b-serial-20261029/offline_01')
for p in sorted(F.rglob('*')):
 if not p.is_file() or p.suffix.lower() not in {'.py','.ps1','.json','.jsonl','.log','.gz','.dart','.png','.csv'}:continue
 if any(s in p.parts for s in ['__pycache__','bin','obj','.dart_tool','build']):continue
 assert not any(x in p.name.lower() for x in ['credential','password'])
 copy(p,'BeforeCadence/'+p.relative_to(F).as_posix())
current={}
"""
assert raw.count(needle)==1;raw=raw.replace(needle,addition)
with (W/'seal_qualification_01.py').open('x',encoding='utf-8') as f:f.write(raw)
