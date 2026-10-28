from pathlib import Path
import hashlib,json,shutil
W=Path(__file__).parent
original=Path('C:/work/fraktal-ab-s4b-status-20261027/offline_01/prepare_session_01.py')
source=original.read_text(encoding='utf-8')
for before,after in (
 ("OLD=Path('C:/work/fraktal-ab-s4b-cold-20261026/session_01')","OLD=Path('C:/work/fraktal-ab-s4b-pool-20261027/session_01')"),
 ("G=OLD.parent/'offline_01'","G=Path('C:/work/fraktal-ab-s4b-cold-20261026/offline_01')")):
    assert source.count(before)==1,before
    source=source.replace(before,after)
before="approval['Scope']+=' The generic cyclic read plan reads discovered module Status groups at the end of each full walk; no additional reads, changed freshness limits or altered row proofs.'"
assert source.count(before)==1
source=source.replace(before,"approval['Scope']+=' Session-only Part-read tracing records schema/revision words and per-request timing for the unchanged legacy reader, on success and failure. It adds no PLC requests, retries or write vectors and changes no acceptance rule. Trace logging has overhead; the session may reproduce the refusal. Four-connection native desktop acceptance remains unproven.'")
exec(compile(source,str(original),'exec'),{'__file__':__file__})
S=W.parent/'session_01'
shutil.copyfile(W/'part_read_diagnostics.py',S/'part_read_diagnostics.py')
path=S/'candidate_regressions_v2.py';text=path.read_text(encoding='utf-8')
before="            result=genealogy.main(run_type_factory=paired,schema='fraktal.ab.s4b-genealogy-fixture',expected_declaration='fraktal_ab_genealogy_s4b_demo')"
assert text.count(before)==1
text=text.replace(before,"            from part_read_diagnostics import trace_part_reads\n            with trace_part_reads(D/'part_read_diagnostics.jsonl'):\n    "+before)
path.write_text(text,encoding='utf-8',newline='')
compile(text,str(path),'exec')
mirror=json.loads(Path('C:/work/fraktal-ab-s4b-pool-20261027/offline_01/isolated_hmi_sources_03.json').read_bytes())
for row in mirror['files']:
    p=Path(row['source']);assert p.read_bytes()==Path(row['copy']).read_bytes()
    assert hashlib.sha256(p.read_bytes()).hexdigest()==row['sha256']
with (W/'isolated_hmi_sources_01.json').open('x',encoding='utf-8') as f:json.dump(mirror,f,indent=2)
assert not (S/'authorization.json').exists()
print(json.dumps(dict(prepared=True,currentOwnerApproved=False,controllerChanges=0,shippingInputsUnchanged=True,partTraceOnly=True,hmiMirrorInputs=len(mirror['files']))))
