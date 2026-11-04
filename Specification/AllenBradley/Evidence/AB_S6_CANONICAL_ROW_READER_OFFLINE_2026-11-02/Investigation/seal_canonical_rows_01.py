"""Seal the second S6 offline checkpoint without altering earlier evidence."""
from pathlib import Path
import gzip, hashlib, json, re, shutil

W=Path(__file__).parent;R=Path('C:/Users/SoftIndVM/Fraktal')
E=R/'Specification/AllenBradley/Evidence';name='AB_S6_CANONICAL_ROW_READER_OFFLINE_2026-11-02'
P=E/name;report=E/(name+'.md')
load=lambda p:json.loads(Path(p).read_text(encoding='utf-8-sig'))
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest().upper()
labels=['canonical_live_initial_01',*[f'canonical_live_focused_0{i}' for i in range(1,7)],
        'full_ab_rows_01','full_ab_rows_02','final_ab_rows_01','canonical_contract_rows_01','root_rows_01',
        'strict_rows_01','ab_spec_rows_01','ab_contracts_rows_01','regenerate_build_rows_01',
        'strict_rows_final_01','ab_spec_rows_final_01','ab_contracts_rows_final_01',
        'regenerate_s5_02',*[kind+'_'+target+'_02' for target in ('EchoController','PhysicalController')
                             for kind in ('build','readback','audit')]]
for label in labels:
    expected=1 if label=='canonical_live_initial_01' else 0
    assert load(W/(label+'_exit.json'))['exitCode']==expected,label
tests=max(map(int,re.findall(rb'Ran (\d+) tests in',(W/'full_ab_rows_02.log').read_bytes())))
assert tests==2397,tests
assert load(W/'full_ab_rows_source_bindings_result_02.json')['sourcesUnchangedDuringSuite']
assert load(W/'full_ab_rows_source_bindings_before_02.json')['sources']=={
    p.name:sha(p) for p in sorted((R/'FraktalCore/PLC/Allen-Bradley/tools').glob('*.py'))}
build=load(W/'regeneration_and_build_result_02.json')
assert build['passed'] and not build['controllerAccess'] and build['generatedSourceByteIdenticalToS5']
status=load(W/'echo_readonly_host_status_rows_01.json')
assert status['service']=='Stopped' and not status['listeners'] and not status['serviceMutation']
census=load(R/'Specification/AllenBradley/AB_S6_CONSUMER_CLASSIFICATION_2026-11-02_03.json')
assert census['summary']['unclassified']==0
for row in census['consumers']:
    assert sha(R/row['path'])==row['sha256'],row['path']
# The prior 802/12 result is retained only for the unchanged HMI sources.
previous=E/'AB_S6_CLASSIFICATION_S9_OFFLINE_2026-11-02'
hmi='FraktalCore/HMI/test/repository_contract_test.dart'
assert (R/hmi).read_bytes()==(previous/'Source'/hmi).read_bytes()
assert not P.exists() and not report.exists()
pins=[str(u['pin']).encode() for u in load('C:/work/fraktal_echo38_access_fixture.json')['users']]
P.mkdir();hashes={}
def archive(source,relative):
    source=Path(source);data=source.read_bytes()
    assert source.suffix.lower() not in {'.acd','.l5x','.exe','.dll','.pdb','.pyc','.bak'}
    assert 'credential' not in source.name.lower()
    checked=gzip.decompress(data) if data.startswith(b'\x1f\x8b') else data
    assert not any(pin in checked for pin in pins),'private credential data refused'
    target=P/relative;target.parent.mkdir(parents=True,exist_ok=True)
    assert not target.exists();shutil.copyfile(source,target);hashes[Path(relative).as_posix()]=sha(target)
sources=[
 'FraktalCore/PLC/Allen-Bradley/tools/fraktal_ab_canonical_reader.py',
 'FraktalCore/PLC/Allen-Bradley/tools/fraktal_ab_canonical_manifest.py',
 'FraktalCore/PLC/Allen-Bradley/tools/fraktal_ab_canonical_live.py',
 'FraktalCore/PLC/Allen-Bradley/tools/test_fraktal_ab_canonical_live.py',
 'Specification/AllenBradley/AB_S6_CONSUMER_CLASSIFICATION_2026-11-02_03.json',
 'Specification/AllenBradley/AB_CANONICAL_PUBLICATION_S6_HOST_SERVICES_REVIEW_2026-11-02.md',
 'Specification/AllenBradley/AB_CANONICAL_PUBLICATION_S6_LIVE_READER_REVIEW_2026-11-02.md',
 'Specification/AllenBradley/AB_CANONICAL_PUBLICATION_S6_CONSUMER_REVIEW_2026-11-02.md',
 'Specification/AllenBradley/AB_CANONICAL_PUBLICATION_PLAN_2026-10-20.md']
for source in sources:archive(R/source,Path('Source')/source)
for label in labels:
    for suffix in ('.log','_exit.json'):archive(W/(label+suffix),Path('Gates')/(label+suffix))
for source in ('inventory_fixture_reads_01.py','fixture_read_inventory_01.json',
               'echo_readonly_host_status_rows_01.json','regenerate_and_build_rows_01.py',
               'regenerate_and_build.py','regeneration_and_build_result_02.json',
               'run_logged.py','seal_canonical_rows_01.py','run_final_suite_rows_01.py',
               'host_service_inventory_01.py','host_service_inventory_01.json',
               'full_ab_rows_source_bindings_before_02.json','full_ab_rows_source_bindings_result_02.json'):
    archive(W/source,Path('Investigation')/source)
with (P/'payload_hashes.json').open('x',encoding='utf-8') as f:json.dump(hashes,f,indent=2,sort_keys=True)
body=f'''# S6 canonical row reader — offline progress

2026-11-02, America/Mexico_City; entry commit `8cd2060f1`. This is a second
WP6.2 checkpoint, not S6 exit or live harness acceptance. No controller read,
write, download, mode, fault-clear, clock or power operation runs here.

The [reader review](../AB_CANONICAL_PUBLICATION_S6_LIVE_READER_REVIEW_2026-11-02.md)
describes `open_row_reader`, shared manifest-shape discovery and the canonical
row reader. The exact serial precedes discovery. Only an absent manifest
permits legacy selection; present invalid/ambiguous manifests refuse. A strict
S1 bootstrap validates metadata and discards its values. Every returned leaf
and occupancy count comes from fresh read services under its published owner.
Mixed owners, frozen/invalid progress, torn/late reads, invalid types/handles
and out-of-bounds/count selections yield no values. Protocol 1 keeps the strict
scan-period window; protocol 2 uses its own published bound with independent
progress. The 20-attempt/one-second limits and production HMI policies remain.

All 5,264 occupied S5 leaves replay through complete row/count proofs with exact
values/types. Twenty-seven focused tests pass, including wire/serial/manifest
refusals, fresh-value selection, independent progress, odd/torn retries, wrap,
window/deadline boundaries and no legacy imports. The first test run failed on
nonexistent Busy/Done paths and an incomplete Template fake; that tooling
failure is preserved and corrected against actual published paths.

Full AB discovery passes {tests:,} tests; the same 124 canonical Dart contract
cases and all 74 root tests pass. AB spec/contracts and strict consistency pass.
The earlier {tests:,}-test suite also passed. Final review then made indexed
path spelling exact, rejecting aliases such as [00]; focused tests and a new
full suite pass on the final source, whose 385 Python module hashes stay fixed
throughout that run. Both full logs remain archived.
The prior full HMI result remains 802 passed/12 existing skips, with unchanged
Dart production/test sources; it is not a fresh full HMI run. Flutter/Dart:
3.47.5/3.13.4, C:/work/fraktal-toolchains/flutter-3.47.5.

Accepted S5 source regenerates byte-identically, SHA-256
{build['sourceSha256']}. Both v38 targets pass fresh offline builds/readbacks
and SDK-log audits. No original genealogy ACD is opened. The unchanged exact
image retains its earlier 66% Capacity result; no new runtime/Capacity claim.

The refreshed census has 385 surveyed Python modules, 309 classified plus three
additional artifacts, zero unclassified, 106 direct legacy references and 294
conservative import dependents. No extra HX owner is claimed migrated. The
fixture audit records 47 Unit members and three literal root-leaf matches;
that is not a semantic correspondence or a request to publish private fields.
No existing fixture assertion, write surface or cleanup is changed.

The [WP6.4 host-service inventory](../AB_CANONICAL_PUBLICATION_S6_HOST_SERVICES_REVIEW_2026-11-02.md)
records ConfigSets, ConfigProvider, LiveDocuments and HostEvents owners, current
wire/storage limits and durability/access/delivery requirements under approved
O4/O5. Native descriptor/chunk layouts and adapter implementation remain open;
no V6.11 type or host process is emitted by that inventory.

Read-only host inspection at {status['observedUtc']} finds the Echo service
Stopped and no 44818 listener. No service operation is attempted. Native
fallback/discovery, active row performance and workload equivalence are unrun.
The last accepted controller rollback remains the dated S5 record, not a new
observation of the controller's image or mode.

Next is bounded row-body packet batching, then press lifecycle/public-assertion integration with separately accounted
fixture-only observations and unchanged sealed verdicts. Other HX migrations,
WP6.3 replay, host services, collapse, retirement, S6-Q and V2 activation remain.
S6 has not exited; no commit/push under O1. Physical S7 remains deferred.

Payload manifest SHA-256: {sha(P/'payload_hashes.json')}.
No credentials, ACD/L5X, binaries or caches are archived; earlier evidence is
unchanged and the failed run remains preserved.
'''
assert not any(pin in body.encode() for pin in pins)
with report.open('x',encoding='utf-8') as f:f.write(body)
print(json.dumps(dict(sealed=name,artifacts=len(hashes),ABTests=tests,focused=27,
                     canonicalLeaves=5264,controllerAccess=False,S6Exit=False)))
