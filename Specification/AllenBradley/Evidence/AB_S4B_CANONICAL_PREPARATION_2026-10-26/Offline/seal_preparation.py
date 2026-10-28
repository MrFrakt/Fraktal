"""Append-only offline/qualification seal. Excludes credentials and ACD binaries."""
from pathlib import Path
import datetime,gzip,hashlib,json,re
R=Path('C:/Users/SoftIndVM/Fraktal');W=Path(__file__).parent;D=W.parent/'session_01'
E=R/'Specification/AllenBradley/Evidence';NAME='AB_S4B_CANONICAL_PREPARATION_2026-10-26'
OUT=E/NAME;REPORT=E/(NAME+'.md');T=R/'FraktalCore/PLC/Allen-Bradley/tools';H=R/'FraktalCore/HMI'
load=lambda p:json.loads(p.read_bytes())
sha=lambda b:hashlib.sha256(b).hexdigest()
def save(p,value):
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('x',encoding='utf-8',newline='') as stream:json.dump(value,stream,indent=2,ensure_ascii=False);stream.write('\n')
assert not OUT.exists() and not REPORT.exists() and not (D/'authorization.json').exists()
gates=('ab_suite_02','root_tests_01','final_spec_01','final_contracts_01','final_consistency_01','final_whitespace_03',
    'view_build_EchoController_01','view_build_PhysicalController_01','view_readback_EchoController_01','view_readback_PhysicalController_01',
    'artifact_gates_01','prepared_compare_01','prepare_capacity_01','compatibility_02','qualification_checks_01','session_build_02',
    'lockfile_01','final_analyze_03','final_flutter_03','windows_build_03','echo_readiness_02','readonly_baseline_01','credential_archive_check_01')
for label in gates:assert load(W/(label+'_exit.json'))['exitCode']==0,label
assert re.search(r'Ran 2336 tests', (W/'ab_suite_02.log').read_text())
assert '631 ~12: All tests passed!' in (W/'final_flutter_03.log').read_text()
capacity=load(W/'capacity_auto_01.json');PIN=capacity['CanonicalSha256'];SOURCE=sha((D/'s4b_read_view.L5X').read_bytes()).upper()
assert capacity['VerifiedFit'] and sha((D/'s4b_read_view.ACD').read_bytes()).upper()==PIN
assert PIN=='7D75E86E9315E0383EDE0C4588A6D327848F54C8A6DBB26B987CCB36DEF056BF'
assert SOURCE=='C4D0E14475AADB651A6C7DA23F63ABD6A10F2A11698E629A828CDD67F38C1C6F'
assert load(W/'qualification_checks_01.json')['passed']
latest=E/'AB_S4A_COHERENCE_RUNTIME_2026-10-25/manifest.json';held=load(latest)
prior={row['name']:row.get('manifestSha256') for row in held['priorSeals']}
prior[latest.parent.name]=sha(latest.read_bytes())
seals=[];total=0
for name,pin in sorted(prior.items()):
    path=E/name/'manifest.json';manifest=load(path)
    if pin:assert sha(path.read_bytes())==pin.lower(),name
    for row in manifest['artifacts']:
        raw=(path.parent/row['path']).read_bytes()
        assert sha(raw)==row['sha256'].lower() and len(raw)==row['bytes'],(name,row['path'])
        if row.get('expandedSha256'):assert sha(gzip.decompress(raw))==row['expandedSha256'].lower()
    if manifest.get('reportSha256'):assert sha((E/manifest['report']).read_bytes())==manifest['reportSha256'].lower()
    seals.append(dict(name=name,manifestSha256=sha(path.read_bytes()),artifacts=len(manifest['artifacts'])));total+=len(manifest['artifacts'])
save(W/'prior_seals_01.json',dict(passed=True,records=len(seals),artifacts=total,rows=seals))
print(json.dumps(dict(priorSealsVerified=len(seals),priorArtifacts=total)),flush=True)

# Runtime file identity: code, supporting gates and exact offline artifacts.
files=set(T.glob('*.py'))|set((R/'tools').glob('check_*.py'))|set(H.joinpath('lib').rglob('*.dart'))|set(H.joinpath('packages/fraktal_opcua_client/lib').rglob('*.dart'))
files.update((H/'test').glob('cip_*_test.dart'));files.update(H/'test/fixtures'/n for n in ('cip_publication_goldens.json.gz','cip_template_goldens.json.gz','cip_read_view_goldens.json.gz'))
files.add(H/'tool/qualify_cip_canonical.dart');files.update(H/n for n in ('pubspec.yaml','pubspec.lock','.dart_tool/package_config.json'))
files.update(D.rglob('*.py'));files.update((D/'session').glob('*.cs'));files.update((D/'session').glob('*.csproj'))
files.update((D/'session/bin/Debug/net8.0/win-x86').glob('*.dll'));files.add(D/'session/bin/Debug/net8.0/win-x86/S4bSession.exe')
files.update(D/n for n in ('s4b_read_view.ACD','s4b_read_view.L5X','canonical.sha256','genealogy.sha256','capacity_review.json','canonical_prepared_compare.json','authorization.template.json'))
docs=[R/'AGENTS.md',R/'Specification/AllenBradley/AB_CANONICAL_PUBLICATION_S4B_READONLY_CONFIG_REVIEW_2026-10-25.md',
    R/'Specification/AllenBradley/AB_CANONICAL_PUBLICATION_PLAN_2026-10-20.md',R/'Specification/AllenBradley/AB_CANONICAL_PUBLICATION_DESIGN_2026-10-19.md',
    R/'Specification/AllenBradley/AB_CANONICAL_PUBLICATION_PART_III_AMENDMENT_DRAFT_2026-10-20.md',R/'Specification/AllenBradley/AB_FROZEN_CONTRACTS_V2.json']
files.update(docs)
P=Path('C:/work/fraktal-ab-s3j-20261024/prepare_d93d8292dbb4425d9eba04ba75cd110c')
files.update(P/n for n in ('audit_baseline_access.py','final_checks.py','measure_timing.py'))
files.add(Path('C:/work/fraktal-toolchains/flutter-3.47.5/bin/cache/dart-sdk/bin/dart.exe'))
save(D/'source_bindings.json',dict(schema='fraktal.ab.s4b-source-bindings',gatesPassed=True,currentOwnerApproved=False,
    canonicalSha256=PIN,sourceSha256=SOURCE,sha256={p.as_posix():sha(p.read_bytes()).upper() for p in sorted(files)}))

sdk=load(W/'sdk_version_01.log');compat=load(W/'compatibility_retry_01/accepted_images_01.json')
assert compat['passed'] and compat['images']==15
failures=[]
for p in sorted(W.glob('*_exit.json')):
    row=load(p)
    if row['exitCode']!=0:failures.append(dict(log=p.name.replace('_exit.json','.log'),exitCode=row['exitCode']))
report=f'''# S4b canonical desktop/configuration preparation — 2026-10-26

**Offline gates pass; the exact-image native session is prepared and unapproved.**
V2 and the Part III amendment remain inactive. No controller-changing operation,
commit or push occurred. Echo remains on the genealogy baseline.

## Decision and exact artifacts

The owner answered **“A — publish a read-only configuration view (Recommended)”**
to `call_519504369cbc4895aca3f61ae5696848:0`. This grants the V6.8 contract and
dependent offline work only. [AGENTS.md §3a](../../../AGENTS.md) says:
“Never perform a controller-changing operation … without current explicit
authorization and an exact target check immediately before use.” The new
download/mode/mailbox session still needs that authorization.

- Target: local Echo **601FC87B**, 1756-L81E v38.011, 127.0.0.1 slot 0,
  controller GUID `91dec7d6-8ac3-45c9-ab2e-0d039c7006fd`.
- Prepared ACD: `{PIN}`.
- Generated L5X: `{SOURCE}`; generated from the S4b declaration, never hand-authored.
- Studio offline Capacity: **2,066,100 used / 1,079,628 available / 3,145,728
  total Blocks (65%)**. This is 161,700 more used Blocks than S4a's offline
  estimate. Native fit/scan and initialization/change-scan cost remain unmeasured.
- Pinned rollback original remains
  `D67561C4A30002E89B7D3F2973633D794239C5890221FF02319C5CFB93ED4084`.
  It is never opened; the session downloads a hash-checked copy.

## Implemented and verified offline

The opt-in PLC V6.8 view publishes exact read-service descriptors, configured
definitions and live/occupied-bank value rows. The existing R2 owner supplies
formatting, revisions and access decisions. Full-width wipes cover unreadable
and unused ValueText buffers, including the existing page window. The private
cache remains unexposed. The independent migration reference uses the legacy
capabilities/records/banks/access source, not the new view's values.

The Dart client discovers Symbols/Templates and the hashed manifest, projects
Core values/types, joins fragment members under one row guard, honors logical
bounds/count references, and carries quality and monotonic ages. The transport
exposes bounded reads only; unsecured direct writes return false locally.
The worker isolate, factory, reconnect policy, read tiers, read-only UI and
configuration adapter are implemented. Configuration batches yield to cyclic
reads, and unselected banks supply routing references without ValueText reads.
No observation frame or station declaration is a client dependency.

Golden replay matches the accepted genealogy **4,428** and press **4,058**
paths/types. Generated-ST/interpreter vectors independently match **979** added
view paths and four configuration pages (live plus three banks). Those V6.8
vectors are explicitly synthetic/offline, not native captures. The four old
HMI spike files and 13 one-off probes are preserved in a hashed retirement
archive and removed from the active tree. The legacy Python projection,
contexts, Frame adapter and observation instrument remain for S6.

| Gate | Exact output/result |
|---|---|
| AB discovery suite | `Ran 2336 tests`; `OK` (`ab_suite_02.log`) |
| Root suite | `Ran 74 tests`; `OK` (`root_tests_01.log`) |
| AB spec/contracts/strict consistency | exit 0 (`final_spec_01`, `final_contracts_01`, `final_consistency_01`) |
| Both v38 targets | EchoController and PhysicalController build/read-back pass |
| Access and SDK logs | four access audits; three clean SDK log audits |
| Prior images | 15 byte-identical (`compatibility_retry_01/accepted_images_01.json`) |
| HMI lockfile/analyze | `pub get --enforce-lockfile`; `No issues found!` |
| Full Flutter suite | **631 passed, 12 skipped** (`final_flutter_03.log`) |
| Windows desktop | debug build passes (`windows_build_03.log`); GUI connection/rendering not run |
| Authorization | 16 negative cases; missing-approval CLI and SDK stop before controller access |
| Whitespace | exit 0 with explicit `cr-at-eol` for tracked CRLF assets; default failures retained |

SDK: **Flutter {sdk['frameworkVersion']} / Dart {sdk['dartSdkVersion']}**, revision
`{sdk['frameworkRevision']}`, at `{sdk['flutterRoot']}`. No dependency/lockfile
change was made. Owner changes in facet_cards and Siemens archives remain untouched.

## Read-only native checks and failed runs

On the unchanged genealogy image the new Dart reader pins identity and discovers
**60 Symbols / 50 Templates in 164 ms** (`native_read_wire_04`). Three earlier
read-only probes failed: SendUnitData Sender Context was incorrectly required
to echo; then the Identity ProductName attribute was requested instead of serial.
The corrected code uses session/connection/sequence for connected replies and
Identity attribute 6 for serial. No controller writes occurred. Protocol sources:
[ODVA PUB00123R1 §3.3.11.2.3](https://www.odva.org/wp-content/uploads/2020/06/PUB00123R1_Common-Industrial_Protocol_and_Family_of_CIP_Networks.pdf)
and [Rockwell 1756-PM020I](https://literature.rockwellautomation.com/idc/groups/literature/documents/pm/1756-pm020_-en-p.pdf).

The final Flutter attempt initially caught the existing 80 ms detail-renewal
timer firing at 79.879 ms. The scheduler now rechecks its monotonic deadline
and rounds the remaining timer upward. The unchanged cadence assertion and
all 22 freshness tests pass; both subsequent full suites pass. Other retained
failures include schema/type warnings, early negative tests, a compatibility
wrapper that called a module without a CLI, SDK build before restore, and CRLF
whitespace checks. Their exact logs/exits are retained; none is native acceptance.

Read-only final checks pass: Run/not faulted/Remote, scanning, MANUAL/idle,
logged out, not restoring, policy restored and five saved documents equal to
live (`readonly_baseline_01.json`). No new dump or controller operation is
part of this preparation. Credentials are excluded from the archive.

## Prepared guarded session and acceptance still pending

`C:/work/fraktal-ab-s4b-20261025/session_01/qualification_session.py` refuses
without current exact-image authorization and matching source/gate hashes.
All guard/session/SDK helpers build or compile; the authorization template is
false and no authorization file exists. The single-use session is:

1. Fresh identity/listener/service/dump checks, guarded MANUAL normalization,
   fresh preflight and backup; SDK backup audit requires **Save As**.
2. Program/download/Run of the exact ACD above, read-back and access audit.
3. Read-only Dart worker/tier observer establishes a fresh progressing root
   before candidate fixture writes; it runs alongside the inherited **41**
   fixed candidate cases (31 main, two Access, eight config/set-store), including
   five-document restoration and restoration of changed values. It then reads
   every occupied bank and chart details without mailbox queries. No new typed
   command vectors are added.
4. All-path independent equivalence, generic capture and native scan.
5. Hash-checked genealogy rollback after any download attempt; exact original
   host documents, five-document restore, **31** baseline cases, MANUAL cleanup,
   final checks/preflight. A fault/dump stops further controller operations.

Fault clears, clock changes, power operations, vendor-state edits and Echo hard
kills are excluded. The observer owns a read-only Dart helper only. Failed runs
are kept and candidate work stops at its first failure. **None of this session
has run.** Full S4 acceptance also requires desktop connection/rendering; the
prepared native observer is not that GUI acceptance.

S5 gateway/installer and per-station write posture, S6 consumer census/legacy
retirement/persistence-event ownership/reductions, and S7 physical/CIP Security
acceptance remain. S3 physical real-I/O proof remains open. Persistence medium,
gateway station posture, S7 hardware and commit/push policy remain owner decisions.
'''
with REPORT.open('x',encoding='utf-8',newline='') as stream:stream.write(report)

artifacts=[]
def archive(source,relative):
    raw=source.read_bytes();expanded=None
    if source.suffix.lower()=='.l5x' or len(raw)>262144 and source.suffix.lower()!='.gz':
        expanded=sha(raw);raw=gzip.compress(raw,mtime=0);relative+='.gz'
    target=OUT/relative;target.parent.mkdir(parents=True,exist_ok=True)
    with target.open('xb') as stream:stream.write(raw)
    artifacts.append(dict(path=relative,source=source.as_posix(),sha256=sha(raw),bytes=len(raw),**({'expandedSha256':expanded} if expanded else {})))
for p in sorted(files):
    if p.suffix.lower() in ('.exe','.dll','.acd'):continue
    if p.is_relative_to(R):relative='Sources/'+p.relative_to(R).as_posix()
    elif p.is_relative_to(D):relative='Session/'+p.relative_to(D).as_posix()
    else:relative='Referenced/'+p.name
    archive(p,relative)
archive(D/'source_bindings.json','Session/source_bindings.json')
for p in sorted(W.iterdir()):
    if p.is_file() and p.suffix.lower() in ('.py','.log','.json','.gz'):
        archive(p,'Offline/'+p.name)
for p in sorted((W/'compatibility_retry_01').glob('*.json')):archive(p,'Offline/compatibility_retry_01/'+p.name)
for name in ('canonical_read_view_01.L5X','EchoController_view_readback_01.L5X','PhysicalController_view_readback_01.L5X','prepared_readback_01.L5X'):
    archive(W/name,'Builds/'+name)
retired=E/'AB_S4B_OFFLINE_2026-10-26/retired_spike'
for p in sorted(retired.rglob('*')):
    if p.is_file():archive(p,'RetiredSpike/'+p.relative_to(retired).as_posix())
manifest=dict(schema='fraktal.ab.s4b-preparation-seal',schemaVersion=1,utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    report=REPORT.name,reportSha256=sha(REPORT.read_bytes()),canonicalSha256=PIN,sourceSha256=SOURCE,
    nativeSessionAuthorized=False,nativeAcceptance=False,controllerChanges=0,gatesPassed=True,failedOrExpectedNegativeRuns=failures,
    sourceBindingsSha256=sha((D/'source_bindings.json').read_bytes()),priorSeals=seals,artifacts=artifacts)
save(OUT/'manifest.json',manifest)
save(W/'sealed_preparation_01.json',dict(passed=True,report=REPORT.as_posix(),artifacts=len(artifacts),priorSeals=len(seals),
    manifestSha256=sha((OUT/'manifest.json').read_bytes()),sourceBindings=len(files),nativeSessionAuthorized=False))
print(json.dumps(dict(sealed=True,artifacts=len(artifacts),priorSeals=len(seals),sourceBindings=len(files),nativeSessionAuthorized=False)))
