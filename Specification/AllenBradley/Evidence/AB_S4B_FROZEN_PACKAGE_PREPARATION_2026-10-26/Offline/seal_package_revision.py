from pathlib import Path
import datetime,gzip,hashlib,json
R=Path('C:/Users/SoftIndVM/Fraktal');W=Path(__file__).parent;D=W.parent/'session_01';E=R/'Specification/AllenBradley/Evidence'
old=E/'AB_S4B_CANONICAL_PREPARATION_2026-10-26';OUT=E/'AB_S4B_FROZEN_PACKAGE_PREPARATION_2026-10-26';REPORT=OUT.with_suffix('.md')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,value):
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('x',encoding='utf-8',newline='') as stream:json.dump(value,stream,indent=2,ensure_ascii=False);stream.write('\n')
assert not OUT.exists() and not REPORT.exists() and not (D/'authorization.json').exists()
prior=json.loads((old/'manifest.json').read_bytes())
assert sha(E/prior['report'])==prior['reportSha256']
for row in prior['artifacts']:
    path=old/row['path'];assert sha(path)==row['sha256'] and path.stat().st_size==row['bytes']
binding=json.loads((D/'source_bindings.json').read_bytes())
original=(R/'FraktalCore/HMI/.dart_tool/package_config.json').as_posix()
assert original in binding['sha256'];binding['sha256'].pop(original)
docs=[R/'Specification/AllenBradley/AB_CANONICAL_PUBLICATION_PLAN_2026-10-20.md',R/'Specification/AllenBradley/AB_FROZEN_CONTRACTS_V2.json']
jsonfile=docs[1];status=json.loads(jsonfile.read_bytes())
status['manifestV68'].update(preparation=REPORT.relative_to(R/'Specification/AllenBradley').as_posix(),
    originalPreparation='Evidence/AB_S4B_CANONICAL_PREPARATION_2026-10-26.md',
    qualificationRunner='C:/work/fraktal-ab-s4b-20261025/session_01/qualification_session_v2.py',
    packageBinding='Private frozen map from the tested Flutter 3.47.5 / Dart 3.13.4 seal; shared generated package map is not a runtime input')
jsonfile.write_bytes((json.dumps(status,indent=2,ensure_ascii=False)+'\n').encode())
for path,pin in binding['sha256'].items():
    if Path(path) not in docs:assert sha(Path(path)).upper()==pin,path
for path in docs:binding['sha256'][path.as_posix()]=sha(path).upper()
new=[D/n for n in ('dart_package_config.json','qualification_session_v2.py','candidate_regressions_v2.py')]
for path in new:binding['sha256'][path.as_posix()]=sha(path).upper()
binding.update(schema='fraktal.ab.s4b-source-bindings.v2',supersedesSha256=sha(D/'source_bindings.json'),mutableGeneratedPackageMapExcluded=True)
save(D/'source_bindings_02.json',binding)
assert json.loads((W/'qualification_checks_03_exit.json').read_bytes())['exitCode']==0
assert json.loads((W/'private_map_cli_refusal_02_exit.json').read_bytes())['exitCode']==255
assert 'Endpoint and new output required' in (W/'private_map_cli_refusal_02.log').read_text()
frozen=json.loads((D/'dart_package_config.json').read_bytes())
assert frozen['flutterVersion']=='3.47.5' and frozen['generatorVersion']=='3.13.4'
assert all(row['rootUri'].startswith('file:') for row in frozen['packages'])
for p,pin in binding['sha256'].items():assert sha(Path(p)).upper()==pin,p
report='''# S4b frozen-package preparation — 2026-10-26

**This supersedes the initial S4b preparation's runnable package binding.**
The PLC image, application behavior, Capacity and authorized scope are unchanged.
No controller change has occurred; the native session is still unapproved.

Read the [initial preparation](AB_S4B_CANONICAL_PREPARATION_2026-10-26.md) for
the implementation, exact image, complete gate outputs, failures and proposed
41-candidate/31-baseline session. Its 808 artifacts and report hash still verify.
It verified 69 earlier seals (19,272 artifacts). Its failed final source check
is preserved rather than editing that evidence.

The check caught the IDE rewriting the shared generated package map with
Flutter 3.47.2 / Dart 3.13.2, after qualification with **Flutter 3.47.5 / Dart
3.13.4**. This was a package-root/SDK change, not merely a timestamp change.
The hash guard refused correctly. The owner/IDE-generated map is left alone.

The revised runner uses `dart_package_config.json`, copied from the tested
3.47.5 seal with every package root resolved to an absolute URI. It is private,
immutable and hash-bound. The mutable `.dart_tool/package_config.json` is not
an input to this runner. The same observer compiles to its expected argument
refusal under the private map, before network I/O. All 16 authorization
refusal cases and both missing-approval refusals pass again.

Runnable entry: `C:/work/fraktal-ab-s4b-20261025/session_01/qualification_session_v2.py`.
It reads `source_bindings_02.json` and invokes `candidate_regressions_v2.py`.
The SDK helper and all identity, active-session, idle, fault, dump, Capacity,
source/image, rollback and restoration guards remain unchanged. No approval
file, backup, session-start or deployment-attempt file exists.

- ACD: `7D75E86E9315E0383EDE0C4588A6D327848F54C8A6DBB26B987CCB36DEF056BF`.
- Source: `C4D0E14475AADB651A6C7DA23F63ABD6A10F2A11698E629A828CDD67F38C1C6F`.
- Offline Capacity: **2,066,100 used / 1,079,628 available / 3,145,728 total
  Blocks (65%)**.
- Current gates: **2,336 AB / 74 root / 631 Flutter tests passed; 12 Flutter
  skips**; no analyzer issues, enforced lockfile, Windows debug build, both v38
  builds/read-backs, four access audits, 15 byte-identical accepted images.

Approval is still required for fresh backup, guarded MANUAL normalization and
Program/download/Run; five-document restore and inherited 41 candidate cases
with the concurrent read-only Dart observer/all-bank/detail reads; read-only
equivalence/capture/scan; pinned genealogy rollback, original documents,
31 baseline cases and final checks/preflight. Candidate work stops on its first
failure. Fault clears, clock changes, power/vendor-state operations and Echo
hard kills remain excluded. [AGENTS.md §3a](../../../AGENTS.md) requires
“current explicit authorization and an exact target check immediately before
use”; the V6.8 contract/offline approval is not that session approval.

Native S4b, GUI connection/rendering, S5–S7 and S3 physical I/O acceptance remain
pending. V2/Part III stay inactive. Nothing is committed or pushed. Credentials
and ACD binaries are excluded from the payload.
'''
with REPORT.open('x',encoding='utf-8',newline='') as stream:stream.write(report)
paths=[*new,*docs,D/'source_bindings_02.json',W/'verify_preparation.py',W/'verify_preparation_01.log',W/'verify_preparation_01_exit.json',
    W/'fix_package_binding.py',W/'fix_package_binding_v2.py',W/'prepare_frozen_map.py',W/'seal_package_revision.py',W/'qualification_checks_v2.py']
for pattern in ('package_binding*','private_map_cli_refusal*','qualification_checks_03*','missing_approval_cli_02*','missing_approval_sdk_02*'):
    paths.extend(p for p in W.glob(pattern) if p.is_file())
artifacts=[]
for i,p in enumerate(sorted(set(paths))):
    relative=('Session/'+p.relative_to(D).as_posix()) if p.is_relative_to(D) else ('Sources/'+p.relative_to(R).as_posix()) if p.is_relative_to(R) else 'Offline/'+p.name
    target=OUT/relative;target.parent.mkdir(parents=True,exist_ok=True);raw=p.read_bytes()
    with target.open('xb') as stream:stream.write(raw)
    artifacts.append(dict(path=relative,source=p.as_posix(),sha256=sha(target),bytes=len(raw)))
manifest=dict(schema='fraktal.ab.s4b-frozen-package-preparation',schemaVersion=1,utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    report=REPORT.name,reportSha256=sha(REPORT),canonicalSha256=prior['canonicalSha256'],sourceSha256=prior['sourceSha256'],
    nativeSessionAuthorized=False,nativeAccepted=False,controllerChanges=0,sourceBindingsSha256=sha(D/'source_bindings_02.json'),
    supersedes=dict(name=old.name,manifestSha256=sha(old/'manifest.json'),verifiedArtifacts=len(prior['artifacts'])),artifacts=artifacts)
save(OUT/'manifest.json',manifest)
save(W/'sealed_package_revision_01.json',dict(passed=True,artifacts=len(artifacts),sourceBindings=len(binding['sha256']),
    manifestSha256=sha(OUT/'manifest.json'),nativeSessionAuthorized=False,controllerChanges=0))
print(json.dumps(dict(sealed=True,artifacts=len(artifacts),sourceBindings=len(binding['sha256']),nativeSessionAuthorized=False)))
