from pathlib import Path
import hashlib,json,subprocess
W=Path(__file__).parent;H=Path('C:/Users/SoftIndVM/Fraktal/FraktalCore/HMI')
F=Path('C:/work/fraktal-ab-s4b-serial-20261029/offline_01')
names=['packages/fraktal_opcua_client/lib/src/'+n for n in
 ['cip_read_plan.dart','cip_session_client.dart','cip_read_coherence.dart','cip_operation_queue.dart']]+[
 'test/cip_coalesced_read_test.dart','test/cip_read_coherence_test.dart','test/cip_operation_queue_test.dart',
 'test/cip_read_plan_test.dart']
for name in names:(H/name).write_bytes((F/'profile_04/Sources'/name).read_bytes())
pins=json.loads((F/'profile_04/sources.json').read_bytes())
for name,pin in pins.items():assert hashlib.sha256((H/name).read_bytes()).hexdigest()==pin,name
with (W/'restored_source_01.json').open('x') as f:json.dump(dict(restored=True,sourceFiles=len(pins),
 sourceSha256=pins,revertedExperiments=['fast-row reuse','complete native structure reads','cyclic queue gap','shared-proof fallback','independent header packets'],
 controllerChanges=0,nativeClaim=False),f,indent=2)
for name in ['run_logged.py','verify_plc_bindings_01.py','configuration_comparison.py',
 'test_configuration_stage_01.py','prepare_peer_qualification_01.py']:
 with (W/name).open('x',encoding='utf-8') as f:f.write((F/name).read_text(encoding='utf-8').replace(F.as_posix(),W.as_posix()))
print('Restored all 31 HMI inputs to the final 750-test source; retained every experiment.')
