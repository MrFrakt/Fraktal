from pathlib import Path
import shutil
W=Path(__file__).parent
original=Path('C:/work/fraktal-ab-s4b-status-20261027/offline_01/prepare_session_01.py')
source=original.read_text(encoding='utf-8')
for before,after in (
 ("OLD=Path('C:/work/fraktal-ab-s4b-cold-20261026/session_01')","OLD=Path('C:/work/fraktal-ab-s4b-partdiag-20261027/session_01')"),
 ("G=OLD.parent/'offline_01'","G=Path('C:/work/fraktal-ab-s4b-cold-20261026/offline_01')")):
    assert source.count(before)==1,before
    source=source.replace(before,after)
before="approval['Scope']+=' The generic cyclic read plan reads discovered module Status groups at the end of each full walk; no additional reads, changed freshness limits or altered row proofs.'"
assert source.count(before)==1
source=source.replace(before,"approval['Scope']+=' Diagnostic-only CIP snapshot phase/queue/delivery tracing is enabled with fraktal.cip.trace=true in the read-only CLI and desktop helper. The existing refusal log separates snapshot wait, service decode and validation time. Payloads, native reads, proof/retry/freshness rules and write vectors are unchanged; the session may reproduce the desktop refusal. Existing Part tracing remains enabled.'")
exec(compile(source,str(original),'exec'),{'__file__':__file__})
S=W.parent/'session_01';Q=Path('C:/work/fraktal-ab-s4b-partdiag-20261027/session_01')
shutil.copyfile(Q/'part_read_diagnostics.py',S/'part_read_diagnostics.py')
for name in ('part_read_diagnostics.py','test_part_read_diagnostics.py'):
    shutil.copyfile(Q.parent/'offline_01'/name,W/name)
path=S/'candidate_regressions_v2.py';text=path.read_text(encoding='utf-8')
before="command=['C:/work/fraktal-toolchains/flutter-3.47.5/bin/cache/dart-sdk/bin/dart.exe',"
assert text.count(before)==1
text=text.replace(before,before+"'-Dfraktal.cip.trace=true',")
compile(text,str(path),'exec');path.write_text(text,encoding='utf-8',newline='')
path=S/'desktop_readonly.py';text=path.read_text(encoding='utf-8')
before="'test','--no-pub',";assert text.count(before)==1
text=text.replace(before,"'test','--dart-define=fraktal.cip.trace=true','--no-pub',")
compile(text,str(path),'exec');path.write_text(text,encoding='utf-8',newline='')
print('Prepared unapproved timing session; same image/write vectors, trace flags only in launchers; no controller access.')
