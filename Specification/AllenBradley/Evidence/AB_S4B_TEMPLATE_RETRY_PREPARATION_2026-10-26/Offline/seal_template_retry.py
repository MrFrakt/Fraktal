"""Seal unchanged-image retry and the complete pinned-SDK regression proof."""
from pathlib import Path
import datetime,gzip,hashlib,json
R=Path('C:/Users/SoftIndVM/Fraktal');W=Path(__file__).parent;OLD=W.parent/'session_01';D=W.parent/'retry_template_01'
E=R/'Specification/AllenBradley/Evidence';OUT=E/'AB_S4B_TEMPLATE_RETRY_PREPARATION_2026-10-26';REPORT=OUT.with_suffix('.md')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();load=lambda p:json.loads(p.read_bytes())
def save(p,value):
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('x',encoding='utf-8',newline='') as stream:json.dump(value,stream,indent=2,ensure_ascii=False);stream.write('\n')
assert not OUT.exists() and not REPORT.exists() and not (D/'authorization.json').exists()
for label in ('seal_attempt_03','namespace_goldens_01','namespace_tests_01','native_read_wire_05','isolated_lockfile_01',
    'isolated_flutter_serial_02','isolated_windows_01','retry_analyze_01','retry_sdk_build_01','retry_authorization_checks_01',
    'retry_status_01','retry_root_tests_01','retry_spec_01','retry_contracts_01','retry_consistency_01','retry_whitespace_01'):
    assert load(W/(label+'_exit.json'))['exitCode']==0,label
assert '635 ~12: All tests passed!' in (W/'isolated_flutter_serial_02.log').read_text(encoding='utf-8')
assert 'No issues found!' in (W/'retry_analyze_01.log').read_text(encoding='utf-8')
assert load(OLD/'session_result.json')['genealogyRestored'] and load(OLD/'session_result.json')['authorizationConsumed']
assert all(load(OLD/'final_checks.json')['checks'].values())
capacity=load(D/'capacity_review.json');PIN=capacity['CanonicalSha256'];SOURCE=sha(D/'s4b_read_view.L5X').upper()
assert sha(D/'s4b_read_view.ACD').upper()==PIN=='7D75E86E9315E0383EDE0C4588A6D327848F54C8A6DBB26B987CCB36DEF056BF'
assert SOURCE=='C4D0E14475AADB651A6C7DA23F63ABD6A10F2A11698E629A828CDD67F38C1C6F'
original=load(OLD/'source_bindings_02.json')['sha256'];unchanged_plc=0;files=set()
for name,pin in original.items():
    p=Path(name)
    if 'FraktalCore/PLC/Allen-Bradley/tools/' in name:
        assert sha(p).upper()==pin,name;unchanged_plc+=1
    if p.is_relative_to(OLD):
        p=D/p.relative_to(OLD)
        if not p.is_file():continue
    files.add(p)
H=R/'FraktalCore/HMI';copy=W.parent/'hmi_verify_01'
mirror=load(W/'isolated_hmi_sources_02.json')
for row in mirror['files']:
    assert Path(row['source']).read_bytes()==Path(row['copy']).read_bytes()
    assert sha(Path(row['source']))==row['sha256']
    files.add(Path(row['source']))
assert load(copy/'.dart_tool/package_config.json')['flutterVersion']=='3.47.5'
assert (copy/'pubspec.lock').read_bytes()==(H/'pubspec.lock').read_bytes()
files.update((D/'session/bin/Debug/net8.0/win-x86').glob('*.dll'));files.update((D/'session/bin/Debug/net8.0/win-x86').glob('*.json'))
files.add(D/'session/bin/Debug/net8.0/win-x86/S4bSession.exe')
files.update(D.glob('*.py'));files.update((D/'scripts').glob('*.py'));files.update((D/'session').glob('*.cs'));files.update((D/'session').glob('*.csproj'))
files.update(D/n for n in ('s4b_read_view.ACD','s4b_read_view.L5X','authorization.template.json','dart_package_config.json',
    'canonical.sha256','genealogy.sha256','capacity_review.json','canonical_prepared_compare.json'))
files.discard(H/'.dart_tool/package_config.json')
save(D/'source_bindings.json',dict(schema='fraktal.ab.s4b-template-retry-source-bindings',gatesPassed=True,currentOwnerApproved=False,
    canonicalSha256=PIN,sourceSha256=SOURCE,unchangedPlcBoundFiles=unchanged_plc,
    privatePinnedPackageMap=True,sha256={p.as_posix():sha(p).upper() for p in sorted(files)}))
base=E/'AB_S4B_CANONICAL_PREPARATION_2026-10-26';prior={row['name'] for row in load(base/'manifest.json')['priorSeals']}
prior.update((base.name,'AB_S4B_FROZEN_PACKAGE_PREPARATION_2026-10-26','AB_S4B_CANONICAL_ATTEMPT_2026-10-26'))
seals=[];total=0
for name in sorted(prior):
    p=E/name/'manifest.json';m=load(p)
    assert sha(E/m['report'])==m['reportSha256']
    for row in m['artifacts']:
        a=p.parent/row['path'];assert sha(a)==row['sha256'] and a.stat().st_size==row['bytes'],(name,row['path'])
        if row.get('expandedSha256'):assert hashlib.sha256(gzip.decompress(a.read_bytes())).hexdigest()==row['expandedSha256']
    seals.append(dict(name=name,manifestSha256=sha(p),artifacts=len(m['artifacts'])));total+=len(m['artifacts'])
save(W/'retry_prior_seals_01.json',dict(passed=True,records=len(seals),artifacts=total,rows=seals))
report=f'''# S4b Template retry preparation — 2026-10-26

**The unchanged-image retry is ready offline and is not authorized.** Genealogy
was restored and verified after the [failed attempt](AB_S4B_CANONICAL_ATTEMPT_2026-10-26.md).
That session's approval is consumed. No further controller-changing operation
occurred. Native S4b and desktop acceptance remain pending; V2 stays inactive.

## Exact image and preserved scope

- Target: Echo **601FC87B**, 1756-L81E v38.011, 127.0.0.1 slot 0.
- ACD: `{PIN}`.
- Generated source: `{SOURCE}`.
- Measured offline Capacity: **2,066,100 used / 1,079,628 available /
  3,145,728 total Blocks (65%)**. Both v38 builds/read-backs, four access audits
  and SDK build-log proof transfer by unchanged image/source hashes.
- **{unchanged_plc} bound PLC/gate files are unchanged**; the existing 2,336 AB
  test result transfers by those exact bindings. The 74 root tests pass again.
- Pinned rollback original:
  `D67561C4A30002E89B7D3F2973633D794239C5890221FF02319C5CFB93ED4084`.

The scope remains fresh guards/backup; guarded MANUAL normalization and
Program/download/Run; five-document restore and the inherited **41 candidate
cases** with concurrent read-only Dart observation; all-bank configuration and
chart-detail reads; read-only equivalence/capture/scan; then pinned genealogy
rollback, exact original host documents, **31 baseline cases** and final checks.
Candidate work stops at its first failure. Fault clears, clock changes,
power/vendor-state operations and Echo hard kills remain excluded.

Runnable entry:
`C:/work/fraktal-ab-s4b-20261025/retry_template_01/qualification_session_v2.py`.
It uses a fresh workspace, the original prepared ACD copy, a frozen private
3.47.5 package map, new source/gate bindings and an all-false authorization
template. No backup, start marker, deployment attempt or authorization file
exists in that workspace. The SDK helper builds with zero warnings/errors;
all 16 negative authorization cases and missing-approval CLI/SDK refusals pass.

## Corrected discovery and evidence limits

The old reader requested `(attribute4 * 4) - 23` bytes and accepted service
success, then required every member name's NUL to exist in that span. The
recorded S0 supplementary definitions show two native types, Page and Block,
whose last NUL is at byte 33, outside a 33-byte request. Their complete DINT
allocation is 36 bytes. Fetching the entire allocation fixes this reproducible
truncation without accepting incomplete names or unbounded data.

The fixture preserves **10 native definitions** and independently decoded
member tables from the hash-verified
[S0 record](AB_S0_SUPPLEMENTARY_RUNTIME_2026-10-21.md). Four new tests check
complete names/offsets, fragmentation, missing terminators and empty/oversized
fragments. Bounds, explicit type/CRC checks, identity and per-row coherence are
unchanged. Missing names now report a bounded handle/offset/metadata-tail
diagnostic. This reproduces the failure mechanism; the exact failing S4b
Template handle was not captured, so the retry must confirm it on that image.

[Rockwell 1756-PM020I, pp. 53–57](https://literature.rockwellautomation.com/idc/groups/literature/documents/pm/1756-pm020_-en-p.pdf)
defines the formula, member records and terminated names. The allocation-tail
finding is measured in the captured Echo bytes. It is not a claim that the
manual explicitly requires the extra bytes. No names or station facts are
invented. Read-only baseline discovery still passes: **60 Symbols /50 Templates
in 118 ms**, with no value, mode or tag write.

## Gates

The isolated HMI copy is byte-identical to all **315** tracked/untracked active
source inputs, with the unchanged sibling PLC type inventory available to the
semantic icon gate. It uses **Flutter 3.47.5 / Dart 3.13.4**, independent of the
IDE's mutable 3.47.2 package map. Lockfile enforcement passes; no dependency
or production timeout is changed. Full suite with concurrency 1: **635 passed,
12 skipped**; analyzer and Windows debug build pass. The login fixture now
asserts observation of the completed expired result rather than an incidental
poll count; the production result/timeout rule remains unchanged.

Failed isolated attempts are retained: missing sibling PLC test-input folders,
timing-sensitive runs under concurrent compilation, and the poll-count fixture.
The complete final run passes with every original assertion on production
freshness/timeout behavior intact. These are offline test outcomes, not native
S4b acceptance. GUI connection/rendering, S5–S7 and S3 physical I/O proof remain.

The initial and failed-session evidence is immutable: **{len(seals)} prior seals /
{total} artifacts** verify again. This preparation archives no credential files
or ACD binaries. No commit or push occurred.

[AGENTS.md §3a](../../../AGENTS.md) requires “current explicit authorization and
an exact target check immediately before use.” A fresh exact-image session
approval is required because the previous run completed with rollback and its
approval is consumed. Contract/offline approval does not authorize this retry.
'''
with REPORT.open('x',encoding='utf-8',newline='') as stream:stream.write(report)
artifacts=[]
def archive(p,relative):
    data=p.read_bytes();expanded=None
    if p.suffix.lower() in ('.log','.l5x'):
        expanded=hashlib.sha256(data).hexdigest();data=gzip.compress(data,mtime=0);relative+='.gz'
    target=OUT/relative;target.parent.mkdir(parents=True,exist_ok=True)
    with target.open('xb') as stream:stream.write(data)
    artifacts.append(dict(path=relative,source=p.as_posix(),bytes=len(data),sha256=sha(target),**({'expandedSha256':expanded} if expanded else {})))
for p in sorted(files):
    if p.suffix.lower() in ('.exe','.dll','.acd'):continue
    if p.is_relative_to(D):relative='Preparation/'+p.relative_to(D).as_posix()
    elif p.is_relative_to(R):relative='Source/'+p.relative_to(R).as_posix()
    else:continue
    archive(p,relative)
archive(D/'source_bindings.json','Preparation/source_bindings.json')
for p in sorted(W.iterdir()):
    if not p.is_file() or p.suffix.lower() not in ('.py','.log','.json','.gz'):continue
    if p.name.startswith(('isolated_','namespace_','native_read_wire_05','retry_','template_lengths_','copy_','prepare_template','update_retry','seal_template')):
        archive(p,'Offline/'+p.name)
manifest=dict(schema='fraktal.ab.s4b-template-retry-preparation',schemaVersion=1,sealedUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    report=REPORT.name,reportSha256=sha(REPORT),canonicalSha256=PIN,sourceSha256=SOURCE,
    sourceBindingsSha256=sha(D/'source_bindings.json'),nativeSessionAuthorized=False,nativeAccepted=False,
    abTests=2336,unchangedPlcBoundFiles=unchanged_plc,rootTests=74,flutterTests=635,flutterSkipped=12,
    priorSeals=seals,artifacts=artifacts,credentialFilesArchived=False,acdBinariesArchived=False,controllerChanges=0)
save(OUT/'manifest.json',manifest)
for row in artifacts:assert sha(OUT/row['path'])==row['sha256']
save(W/'sealed_template_retry_01.json',dict(passed=True,manifestSha256=sha(OUT/'manifest.json'),artifacts=len(artifacts),
    sourceBindings=len(files),priorSeals=len(seals),unchangedPlcBoundFiles=unchanged_plc,nativeSessionAuthorized=False))
print(json.dumps(dict(sealed=True,artifacts=len(artifacts),sourceBindings=len(files),priorSeals=len(seals),nativeSessionAuthorized=False)))
