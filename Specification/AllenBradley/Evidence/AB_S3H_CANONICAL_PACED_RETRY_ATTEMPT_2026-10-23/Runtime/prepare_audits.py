from pathlib import Path
import json
R=Path(__file__).parent;prior=R.parent/'runtime_fd53835fe9684f598bdd829da6d29c8d'
P=R.parent/'retry_fc306d330cc642499a52abbb53bae945'
for name in ('verify_candidate_surface.py','replay_runtime_captures.py','measure_native_records.py',
             'close_native_measurements.py','verify_retry_proof.py'):
 with (R/name).open('x') as f:f.write((prior/name).read_text())
with (R/'trace_observations.py').open('x') as f:f.write((P/'trace_observations.py').read_text())
t=(prior/'verify_runtime.py').read_text()
for old,new in {
 'retry_9d1da9a04d564b03bc2b176f5b17ea42':P.name,
 'abTests=2148':'abTests=2149',
 'len(seals)==30 and sum(row[\'artifacts\'] for row in seals)==7199':"len(seals)==32 and sum(row['artifacts'] for row in seals)==7749",
 'predecessorRecords=30,predecessorArtifacts=7199':'predecessorRecords=32,predecessorArtifacts=7749',
 "'native_record_sizes_01','native_measurements_01','trace_observations_01')":"'native_record_sizes_01','native_measurements_01','trace_observations_01','retry_proof_01')",
 }.items():
 assert t.count(old)==1,(old,t.count(old));t=t.replace(old,new,1)
with (R/'verify_runtime.py').open('x') as f:f.write(t)
print(json.dumps(dict(passed=True,controllerAccess=False,auditorsPrepared=True)))
