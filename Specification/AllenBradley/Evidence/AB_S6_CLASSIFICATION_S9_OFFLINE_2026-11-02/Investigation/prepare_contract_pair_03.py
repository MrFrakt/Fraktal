from pathlib import Path
W=Path(__file__).parent
source=(W/'replay_s9_contract_pair_02.py').read_text(encoding='utf-8').replace('_02','_03')
with (W/'replay_s9_contract_pair_03.py').open('x',encoding='utf-8') as f:f.write(source)
print('New before/after replay with preserved declared RPC processing; no assertion changes')
