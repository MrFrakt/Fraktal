"""Replay completed captures after a stopped fixture, without accepting its exit.

The full 41-case gate is unchanged. This separate result records partial proof.
"""
from pathlib import Path
W=Path(__file__).parent
source=(W/'replay_cold_pairs_01.py').read_text(encoding='utf-8')
start=source.index("assert len(evidence['rows']) == 31")
end=source.index('rows = []',start)
source=source[:start]+"""expected={'rows':31,'s4bAccessRows':2,'s4bConfigRows':8}
counts={key:len(evidence.get(key,[])) for key in expected}
assert counts=={'rows':15,'s4bAccessRows':0,'s4bConfigRows':0},counts
assert all(row['passed'] for key in expected for row in evidence.get(key,[]))
assert evidence['error']=='part snapshot changed during every bounded read'
assert evidence['restored'] and evidence['policyRestored']
"""+source[end:]
before='controllerAccess=False, regressions=41,'
assert source.count(before)==1
source=source.replace(before,'controllerAccess=False, fullFixturePassed=False, expectedRegressions=41, regressions=15,')
assert source.count("'paired_replay_01.json'")==1
source=source.replace("'paired_replay_01.json'","'paired_replay_02.json'")
exec(compile(source,str(W/'replay_cold_pairs_01.py'),'exec'),{'__file__':__file__})
