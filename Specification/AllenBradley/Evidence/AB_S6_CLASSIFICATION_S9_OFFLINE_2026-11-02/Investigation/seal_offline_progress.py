"""Append-only S6 WP6.1/first WP6.2 evidence; no stage exit or controller claim."""
from pathlib import Path
import gzip,hashlib,json,re,shutil

W=Path(__file__).parent;R=Path('C:/Users/SoftIndVM/Fraktal')
E=R/'Specification/AllenBradley/Evidence'
name='AB_S6_CLASSIFICATION_S9_OFFLINE_2026-11-02';P=E/name
load=lambda p:json.loads(Path(p).read_bytes())
labels=['targeted_python_01','s9_canonical_contract_01','s9_contract_pair_03',
    'hmi_locked_01','hmi_analyze_01','full_hmi_01','full_ab_01',
    'root_tests_01','strict_consistency_01','ab_spec_01','ab_contracts_01',
    'regenerate_build_01','regenerate_s5_01',
    *[kind+'_'+target+'_01' for target in ('EchoController','PhysicalController') for kind in ('build','readback','audit')]]
for label in labels:assert load(W/(label+'_exit.json'))['exitCode']==0,label
counts=re.findall(rb'Ran (\d+) tests in',(W/'full_ab_01.log').read_bytes())
assert counts;ab=max(map(int,counts));assert ab==2370,ab
classification=load(R/'Specification/AllenBradley/AB_S6_CONSUMER_CLASSIFICATION_2026-11-02.json')
assert classification['summary']['unclassified']==0
replay=load(W/'s9_contract_verdict_equivalence_03.json')
assert replay['passed'] and replay['unchangedCaseSetAndVerdicts']
assert all(r['tests']==124 for r in replay['runs'].values())
build=load(W/'regeneration_and_build_result_01.json');assert build['passed'] and not build['controllerAccess']
assert not P.exists() and not (E/(name+'.md')).exists()
pins=[u['pin'].encode() for u in load('C:/work/fraktal_echo38_access_fixture.json')['users']]
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest().upper()
P.mkdir();hashes={}
def archive(source,relative):
    source=Path(source);data=source.read_bytes()
    assert source.suffix.lower() not in {'.acd','.l5x','.exe','.dll','.pdb','.pyc','.bak'}
    assert 'credential' not in source.name.lower()
    assert not any(pin in data for pin in pins),'credential data refused'
    if data.startswith(b'\x1f\x8b'):assert not any(pin in gzip.decompress(data) for pin in pins)
    target=P/relative;target.parent.mkdir(parents=True,exist_ok=True)
    assert not target.exists();shutil.copyfile(source,target);hashes[Path(relative).as_posix()]=sha(target)
sources=[
 'FraktalCore/PLC/Allen-Bradley/tools/fraktal_ab_legacy_consumers.py',
 'FraktalCore/PLC/Allen-Bradley/tools/test_fraktal_ab_legacy_consumers.py',
 'FraktalCore/PLC/Allen-Bradley/tools/fraktal_ab_s9_contract.py',
 'FraktalCore/PLC/Allen-Bradley/tools/test_fraktal_ab_s9_contract.py',
 'FraktalCore/HMI/test/repository_contract_test.dart',
 'Specification/AllenBradley/AB_S6_CONSUMER_CLASSIFICATION_2026-11-02.json',
 'Specification/AllenBradley/AB_CANONICAL_PUBLICATION_S6_CONSUMER_REVIEW_2026-11-02.md']
for source in sources:archive(R/source,Path('Source')/source)
for label in labels:
    for suffix in ('.log','_exit.json'):archive(W/(label+suffix),Path('Gates')/(label+suffix))
for source in W.iterdir():
    if source.is_file() and (source.suffix in ('.py','.json','.log') or source.name.endswith('.json.gz')):
        if source.name in {label+suffix for label in labels for suffix in ('.log','_exit.json')}:continue
        archive(source,Path('Investigation')/source.name)
for source in ('C:/work/ab_s6_classification_preview_20261102_01.json','C:/work/ab_s6_classification_preview_20261102_02.json'):
    archive(source,Path('Investigation')/Path(source).name)
with (P/'payload_hashes.json').open('x',encoding='utf-8') as f:json.dump(hashes,f,indent=2,sort_keys=True)
report=f'''# S6 classification and first canonical harness replay

Offline progress, 2026-11-02 (America/Mexico_City). Entry commit `8cd2060f1`.
This record completes WP6.1 and the first offline WP6.2 harness migration.
S6 has not exited. There is no controller access, new download, schema/layout
change, retirement, baseline switch or V2 activation.

The [consumer review](../AB_CANONICAL_PUBLICATION_S6_CONSUMER_REVIEW_2026-11-02.md)
and [classification](../AB_S6_CONSUMER_CLASSIFICATION_2026-11-02.json) describe
the first-match inventory: 383 Python modules surveyed, 307 classified plus three
explicit non-Python retirement artifacts, 76 unaffected and zero unclassified.
The initial preview has 107 direct references/291 import dependents. After S9's
direct projection dependency is removed, there are 106 direct references and 292
conservative import dependents, including new tests and lazy engineering
imports. A fresh-process replay proves the migrated harness loads none of the
declaration/generator/station/projection/gateway modules. Nine standalone HX
probes retain their specific ABI guards for review. No files are deleted.

S9 now uses the S1 canonical decoder on sealed native captures. Its default
replay matches all 5,264 values/types of the accepted S5 document; three other
accepted captures also match their frozen expected values/types. Invalid
manifests still refuse. The same shared Dart contract passes all 124 cases on
both the historical adapter fixture and canonical capture with identical
case sets/verdicts. These are offline contract replays, not a claim that two
different station states have equal values.

The old instant-RPC fake wrongly replayed a saved responseProcessingMs larger
than its observed RPC duration. The production guard correctly refused all
seven AB contract setups; their errors and an early result-parser failure are
retained. The fake now waits the declared duration, rounded up to timer
resolution. Source ages, values, quality, assertions and production freshness
rules are unchanged. Both historical and canonical fixtures then pass.

Passed gates: 13 focused Python tests; 124 canonical Dart cases; 124 historical
and 124 canonical cases with identical verdicts; 802 full HMI tests with 12
existing skips; analyzer; locked dependencies; {ab:,} full AB tests by discovery;
74 root tests; AB specification/contracts; strict consistency. Flutter 3.47.5 /
Dart 3.13.4 at C:/work/fraktal-toolchains/flutter-3.47.5.

Accepted S5 source regenerates byte-identically, SHA-256
979DD73CDFC0C0CBCD3348915CB6D804FCF2736DC780AEA196963E2F2105A162.
Both v38 targets pass fresh offline builds/readbacks and SDK-log audits.
No controller is accessed and the original genealogy ACD is never opened.
The exact-image Capacity measurement remains 66% on the unchanged image; no
new capacity or native-runtime result is inferred. This verifies the current
S5 source pin, not WP6.3's remaining final replay of all historical pins/oracles.

Next: live harness discovery selection and coherent canonical readers, then
the remaining HX/helper/test migrations and final sealed MO replay before
generator changes. Host services, storage collapse, retirement and activation
remain open; the inherited baseline START refusal remains a readiness follow-up.
O1 permits one commit/push per stage exit; S6 work stays uncommitted. S7 remains
deferred under O2.

Payload manifest SHA-256: {sha(P/'payload_hashes.json')}.
No credentials, ACD/L5X, binaries or caches are archived. Failed investigations
remain preserved. No acceptance assertion, type, value or limit is weakened.
'''
with (E/(name+'.md')).open('x',encoding='utf-8') as f:f.write(report)
print(json.dumps(dict(sealed=name,artifacts=len(hashes),ABTests=ab,HMITests=802,HmiSkips=12,
    controllerAccess=False,S6Exit=False)))
