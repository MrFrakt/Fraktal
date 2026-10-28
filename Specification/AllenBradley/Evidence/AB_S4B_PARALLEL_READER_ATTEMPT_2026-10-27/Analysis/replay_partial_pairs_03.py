"""Include the completed pre-walk Access/config cases in partial replay counts."""
from pathlib import Path
W=Path(__file__).parent
source=(W/'replay_partial_pairs_02.py').read_text(encoding='utf-8')
for before,after in (
 ("{'rows':15,'s4bAccessRows':0,'s4bConfigRows':0}","{'rows':15,'s4bAccessRows':2,'s4bConfigRows':8}"),
 ('regressions=15,','regressions=25,'),
 ("'paired_replay_02.json'","'paired_replay_03.json'")):
    assert source.count(before)==1,before
    source=source.replace(before,after)
exec(compile(source,str(W/'replay_partial_pairs_02.py'),'exec'),{'__file__':__file__})
