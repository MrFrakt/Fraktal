"""Verify immutable runtime, current code and post-run document gates; append closeout."""
from pathlib import Path
import datetime,gzip,hashlib,json
R=Path('C:/Users/SoftIndVM/Fraktal');W=Path(__file__).parent;S=W.parent/'session_01'
E=R/'Specification/AllenBradley/Evidence';P=E/'AB_S4B_MSP_ATTEMPT_2026-10-27'
O=E/'AB_S4B_MSP_CLOSEOUT_2026-10-27';REPORT=O.with_suffix('.md')
load=lambda p:json.loads(Path(p).read_bytes())
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
receipt=load(W/'sealed_runtime_01.json');m=load(P/'manifest.json')
assert sha(P/'manifest.json')==receipt['manifestSha256']=='8689e850bd230d13dc0089ac6a57d8a102db3e1bf36cc40ba98ffe707ca10316'
assert sha(E/m['report'])==m['reportSha256']
assert not m['nativeAccepted'] and m['genealogyRestored'] and m['baselineCases']==31 and m['authorizationConsumed']
for row in m['artifacts']:
    raw=(P/row['path']).read_bytes()
    assert len(raw)==row['bytes'] and hashlib.sha256(raw).hexdigest()==row['sha256']
    if row.get('expandedSha256'):assert hashlib.sha256(gzip.decompress(raw)).hexdigest()==row['expandedSha256']
docs={R/'Specification/AllenBradley'/name for name in ('AB_CANONICAL_PUBLICATION_PLAN_2026-10-20.md',
    'AB_CANONICAL_PUBLICATION_DESIGN_2026-10-19.md','AB_CANONICAL_PUBLICATION_PART_III_AMENDMENT_DRAFT_2026-10-20.md','AB_FROZEN_CONTRACTS_V2.json')}
changed={Path(p) for p,pin in load(S/'source_bindings.json')['sha256'].items() if sha(p).upper()!=pin}
assert changed==docs|{S/'s4b_read_view.ACD'},changed
for label in ('spec_02','contracts_02','consistency_02','root_tests_02','whitespace_02','update_runtime_status_01'):
    assert load(W/(label+'_exit.json'))['exitCode']==0,label
assert b'Ran 74 tests' in (W/'root_tests_02.log').read_bytes()
q=load(S/'runtime_summary_01.json')
assert q['candidateCases']==41 and q['pairedCapturesReplayed']==87 and q['observerSamples']==q['allGoodSamples']==2851
assert q['genealogyRestored'] and q['baselineCases']==31 and q['finalChecksPassed'] and q['authorizationConsumed']
assert not q['nativeAccepted'] and not q['currentControllerChangesAuthorized']
assert not O.exists() and not REPORT.exists()
text='''# S4b body-packet qualification closeout — 2026-10-27

The [sealed runtime attempt](AB_S4B_MSP_ATTEMPT_2026-10-27.md) is independently
verified: 252 artifacts and expanded payload hashes match. The completed session
passes 41 candidate cases, 87 exact raw-read replays, the separate busy witness
and 2,851 entirely Good Dart samples. Strict desktop fails after overview at
1,051.723 ms against 1,000 ms. Later configuration/idle/acquisition/final timing
remain skipped. TASK maximum 9,002 us/zero overlaps is observational. Genealogy,
five original documents, 31 baseline cases and every final/preflight check pass.
Authorization is consumed; no subsequent controller change is authorized.

All 1,081 current bound inputs verify except the SDK-saved working ACD and the
four explicitly updated status documents. Shipping PLC/HMI code is unchanged.
The plan, design note, Part III draft and inactive V2 status record the actual
failure and next offline acquisition/delivery analysis. Spec/contracts/strict
consistency/whitespace and all 74 root tests pass after those updates. The
unchanged HMI retains 685 passed/12 skipped, 73 focused, analyzer/Windows/locked
dependencies; unchanged PLC retains 2,339 AB tests, both v38 build/read-back and
65% Capacity by verified bindings. No repeat controller session is started.

S4b desktop/configuration/acquisition/final scan remains open. S5 gateway/Web/
installer, S6 retirement/persistence/events/capacity and S7 physical hardware/
CIP Security including real I/O remain. Persistence medium, gateway write posture,
hardware and commit/push policy remain owner decisions. Nothing committed/pushed.
'''
with REPORT.open('x',encoding='utf-8',newline='') as f:f.write(text)
files=set(docs)
for label in ('spec_02','contracts_02','consistency_02','root_tests_02','whitespace_02','update_runtime_status_01'):
    files.update((W/(label+'.log'),W/(label+'_exit.json')))
files.update((W/'update_runtime_status_01.py',Path(__file__),W/'sealed_runtime_01.json',S/'owner_authorization_consumed_01.json'))
artifacts=[]
for path in sorted(files):
    relative=('Status/'+path.name) if path in docs else ('Checks/'+path.name)
    raw=path.read_bytes();expanded=None
    if path.suffix=='.log':expanded=hashlib.sha256(raw).hexdigest();raw=gzip.compress(raw,mtime=0);relative+='.gz'
    target=O/relative;target.parent.mkdir(parents=True,exist_ok=True)
    with target.open('xb') as f:f.write(raw)
    artifacts.append(dict(path=relative,bytes=len(raw),sha256=sha(target),**(dict(expandedSha256=expanded) if expanded else {})))
value=dict(schema='fraktal.ab.s4b-msp-closeout',sealedUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    report=REPORT.name,reportSha256=sha(REPORT),runtimeManifestSha256=sha(P/'manifest.json'),
    runtimeArtifactsVerified=len(m['artifacts']),runtimeInputsVerified=1081,postRunRootTests=74,
    nativeAccepted=False,authorizationConsumed=True,currentControllerChangesAuthorized=False,
    genealogyRestored=True,artifacts=artifacts,committed=False,pushed=False)
with (O/'manifest.json').open('x',encoding='utf-8') as f:json.dump(value,f,indent=2)
for row in artifacts:assert sha(O/row['path'])==row['sha256']
with (W/'sealed_closeout_01.json').open('x',encoding='utf-8') as f:json.dump(dict(passed=True,
    manifestSha256=sha(O/'manifest.json'),artifacts=len(artifacts),runtimeArtifactsVerified=252,
    runtimeInputsVerified=1081,rootTests=74,genealogyRestored=True,nativeAccepted=False),f,indent=2)
print(json.dumps(dict(sealed=True,runtimeArtifactsVerified=252,currentInputsVerified=1081,
    rootTests=74,artifacts=len(artifacts),genealogyRestored=True,nativeAccepted=False)))
