"""Append the WP4b.5 offline record, retaining failures and an unmet native gate."""
from pathlib import Path
import datetime,gzip,hashlib,json,re
R=Path('C:/Users/SoftIndVM/Fraktal');H=R/'FraktalCore/HMI';W=Path(__file__).parent
E=R/'Specification/AllenBradley/Evidence';O=E/'AB_WP4B5_REHEARSAL_2026-10-28';REPORT=O.with_suffix('.md')
load=lambda p:json.loads(Path(p).read_bytes())
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert not O.exists() and not REPORT.exists()
for label in ('pub_01','peer_tests_05','flutter_01','analyze_02','profile_build_01',
    'analyze_rehearsal_01','update_plan_01','spec_01','contracts_01','consistency_01','root_tests_01','whitespace_01'):
    assert load(W/(label+'_exit.json'))['exitCode']==0,label
for label in ('rehearsal_profile_final_01','rehearsal_debug_final_01','apparatus_final_01'):
    assert load(W/(label+'_exit.json'))['exitCode']==1,label
assert b'+697 ~12: All tests passed!' in (W/'flutter_01.log').read_bytes()
assert b'+7: All tests passed!' in (W/'peer_tests_05.log').read_bytes()
assert b'No issues found!' in (W/'analyze_02.log').read_bytes()
assert b'Ran 74 tests' in (W/'root_tests_01.log').read_bytes()
q=load(W/'rehearsal_analysis_01.json');assert not q['prerequisitePassed'] and q['consecutiveQualifyingPasses']==0
package=load(H/'.dart_tool/package_config.json')
assert package['flutterVersion']=='3.47.5' and package['generatorVersion']=='3.13.4'
cap=E/'AB_S4B_READER_RUNTIME_2026-10-26/Runtime/generic_capture.json.gz'
pin='b0ebfbd06853fbaf1262c3b74549f88f99bd9af37e1585844dc5b9a4291afb4a'
assert sha(cap)==pin
for label in ('profile_final_01','debug_final_01','apparatus_final_01'):
    for name,pin_at_run in load(W/label/'sources.json').items():
        assert sha(W/label/'Sources'/name)==pin_at_run
sources=[H/name for name in ('tool/cip_rehearsal_peer.dart','test/cip_rehearsal_peer_test.dart',
    'integration_test/ab_desktop_acceptance_test.dart','test_driver/integration_test.dart',
    'lib/data/opcua_repository.dart','packages/fraktal_opcua_client/lib/src/cip_session_client.dart',
    'packages/fraktal_opcua_client/lib/src/cip_read_plan.dart','pubspec.yaml','pubspec.lock')]
sources += [R/'Specification/AllenBradley'/name for name in ('AB_CANONICAL_PUBLICATION_PLAN_2026-10-20.md',
    'AB_CANONICAL_PUBLICATION_STATUS_LOG_2026-10-27.md')]
report='''# S4b WP4b.5 rehearsal implementation and failed prerequisite — 2026-10-28

**Offline apparatus implemented; rehearsal prerequisite remains open. No native
acceptance is claimed.** This continues commit `883f7d00a` and the handed-over
loopback peer. Echo remains on genealogy throughout; each launch passes the
read-only original preflight before and after. No download, mode/tag write,
fault/counter clear, clock change, power or vendor-state operation occurs.

## Implemented and verified

`HMI/tool/cip_rehearsal_peer.dart` serves Symbol/Template data and native records
from the immutable [generic capture](AB_S4B_READER_RUNTIME_2026-10-26/Runtime/generic_capture.json.gz),
SHA-256 `B0EBFBD06853FBAF1262C3B74549F88F99BD9AF37E1585844DC5B9A4291AFB4A`.
The manifest is re-encoded from its normalized captured form, with exact logical
round-trip tests. The inherited sender-context/template-instance/atomic-type
corrections are retained and exercised through the real client socket stack.
Read Tag Fragmented and read-only MSP are served; unsupported services refuse.
Counters advance by two each 10 ms, odd for the first millisecond. The peer binds
loopback only, refuses port 44818, verifies a supplied capture hash and closes
its sockets on explicit stdin `stop`. No shipped endpoint defaults to it.

Seven tests pass: SHA known/captured vectors, hash-mismatch refusal, invalid
port/delay refusal, golden/sealed manifest round-trips and golden/sealed wire
discovery with exact cyclic values/types. Production read tiers are applied
before the first snapshot; polling every closed history ring was an incorrect
test precondition. A second snapshot retains values/types and omits the path
vector as WP4b.1 requires. PIN/credential data is never supplied to the peer.

Latency uses piecewise interpolation between the host-timing record's measured
minimum 440 us, median 1276.5 us, p95 6974 us and maximum 16290 us. Intermediate
quartiles in the inherited draft were not measured and were removed. This is
an explicitly synthetic quantile model: raw empirical request samples were not
retained by that record. It does not establish equivalence to native Echo timing.
The requested-versus-realized socket delay still needs calibration.

The desktop test accepts a separate, explicitly enabled loopback rehearsal
endpoint. Its result flags cannot claim native desktop/freshness acceptance.
The in-memory acceptance panel is configured through the existing content API
for public read visibility; live mode remains logged out and every original
read-only action refusal remains. PLC permissions and session identity are not
changed. Empty/default local operator/engineer view floors had hidden most tabs
in the original test. The expected seven modules/three bus nodes/31 views stay
required. No view is skipped to pass.

Trace-only repository mapped ages and worker operation start/completion records
supplement WP4b.3. They log counts/timing, never argument values. Normal builds
omit them. No production scheduling, source timestamp, retry/deadline, equality/
even/window proof, Good/expiry budget or write policy changes in this work.

## Rehearsal results

| Run | Recorded outcome |
|---|---|
| Final profile, seed 7, scale 1 | Startup refuses; snapshot await 3,397.686 ms, effective age 1,001.601 ms against 1,000 ms; zero views |
| Final debug, seed 7, scale 1 | Startup refuses; snapshot await 4,135.311 ms, effective age 1,027.650 ms; zero views |
| Final profile apparatus, scale 0 | Seven mapped snapshots, maximum age 261.606 ms; four views (Overview and three root tabs), then STALE after Statistics demand; not a model-gate run |

Final profile/debug `replyWaitUs` is 1076/679 us. The first diagnostic model
profile records 154/239 groups needing more than two attempts and about four
seconds of acquisition. These intervals identify acquisition cost in this
model, not an isolated host/network/controller cause or an actual PLC failure.

The zero-delay operation trace shows Statistics demand reducing excluded leaves
from 3660 to 1380: 2280 detail leaves are promoted into slow snapshots. A new
snapshot starts, then freshness expires before it completes. The retained
finder exception is secondary to a recorded STALE/empty forest; later guards
check LIVE before and after tab selection. This diagnostic does not demonstrate
full 31-view navigation or satisfy the three-run/700 ms prerequisite.

All failures remain: the inherited unprofiled full-tree test, the launcher's
readiness parser (Dart build-hook text prefixes JSON), model profile/debug
refusals, hidden local-policy tabs, and partial zero-delay navigation. Only the
final-source runs have per-launch source snapshots; early drafts are diagnostic
history, not acceptance evidence. No unchanged failing native session is retried.
Every local peer stops gracefully; final peer logs show zero refused services
and no controller writes. Genealogy preflight passes before/after every launch.

## Gates and exact scope

- **697 HMI tests pass /12 intentional skips**, including the seven new peer
  tests; analyzer is clean; `pub get --enforce-lockfile` and Windows profile
  build pass. SDK **Flutter 3.47.5 /Dart 3.13.4**,
  `C:/work/fraktal-toolchains/flutter-3.47.5` (the AGENTS example path is absent).
- Spec/contracts/strict consistency/whitespace and **74 root tests pass** after
  the plan/status update. Build logs retain third-party CMake deprecation output.
- All **373 PLC/gate bindings** verify unchanged; **2,339 AB tests**, both v38
  builds/read-backs and exact-image **65% Capacity** transfer by those hashes.
  They are not rerun here. No PLC source/image is changed or deployed.
- The plan records **zero qualifying profile passes**. Three consecutive passes
  with maximum effective age at most 700 ms are still required before WP4b.6/
  S4b-Q preparation. No native session, physical proof or O7 fallback is claimed.

## Next and remaining work

Calibrate the rehearsal delay at the socket boundary, address initial fast-walk
cost, and test bounded slow-detail scheduling without blocking cyclic samples.
Preserve every demanded value/type, row proof, source age and existing limit.
Then run the unchanged 3-pass/700 ms gate. S4b-Q must still pass E1–E9 together.
S5 gateway/Web/installer and S6 retirement/FileMedium/events/capacity remain.
S7 physical gates remain deferred/excluded under O2. O1–O7 stand; no new owner
decision is requested. No stage exit, commit or push occurs in this continuation.
'''
with REPORT.open('x',encoding='utf-8',newline='') as f:f.write(report)
artifacts=[]
def archive(path,relative):
    assert 'credential' not in path.name.lower(),path
    raw=path.read_bytes();expanded=None
    if path.suffix.lower()=='.log':
        expanded=hashlib.sha256(raw).hexdigest();raw=gzip.compress(raw,mtime=0);relative+='.gz'
    dest=O/relative;dest.parent.mkdir(parents=True,exist_ok=True)
    with dest.open('xb') as f:f.write(raw)
    artifacts.append(dict(path=relative,bytes=len(raw),sha256=sha(dest),
        **(dict(expandedSha256=expanded) if expanded else {})))
for path in sources:archive(path,'Source/'+path.relative_to(R).as_posix())
for path in sorted(W.rglob('*')):
    if not path.is_file() or '__pycache__' in path.parts:continue
    if path.name=='seal_evidence_01.log':continue
    if path.suffix.lower() not in ('.py','.dart','.json','.log','.png','.yaml','.lock'):continue
    archive(path,'Offline/'+path.relative_to(W).as_posix())
for name in ('preflight.py','guard_echo.py'):
    path=Path('C:/work/fraktal-ab-s4b-msp-20261027/session_01/scripts')/name
    archive(path,'BaselineTools/'+name)
manifest=dict(schema='fraktal.ab.wp4b5-rehearsal',schemaVersion=1,
    sealedUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(),report=REPORT.name,reportSha256=sha(REPORT),
    captureSha256=pin,rehearsalPrerequisitePassed=False,qualifyingPasses=0,nativeAcceptanceClaim=False,
    controllerChanges=0,genealogyBeforeAfterVerified=True,hmiTests=697,hmiSkipped=12,peerTests=7,rootTests=74,
    unchangedPlcBindings=373,abTestsTransferred=2339,capacityPercentTransferred=65,
    stageExit=False,committed=False,pushed=False,artifacts=artifacts,
    sourceSha256={p.as_posix():sha(p) for p in sources},credentialsArchived=False,binariesArchived=False)
with (O/'manifest.json').open('x',encoding='utf-8') as f:json.dump(manifest,f,indent=2)
for row in artifacts:assert sha(O/row['path'])==row['sha256']
with (W/'sealed_evidence_01.json').open('x') as f:json.dump(dict(passed=True,
    manifestSha256=sha(O/'manifest.json'),artifacts=len(artifacts),rehearsalPrerequisitePassed=False,
    controllerChanges=0,hmiTests=697,rootTests=74),f,indent=2)
print(json.dumps(dict(sealed=True,artifacts=len(artifacts),hmiTests=697,rootTests=74,
    rehearsalPrerequisitePassed=False,controllerChanges=0)))
