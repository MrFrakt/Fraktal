"""Archive only the measured read-only baseline timing/packet findings."""
from pathlib import Path
import datetime,gzip,hashlib,json
R=Path('C:/Users/SoftIndVM/Fraktal');W=Path(__file__).parent
M=Path('C:/work/fraktal-ab-s4b-msp-20261027/offline_01')
E=R/'Specification/AllenBradley/Evidence';O=E/'AB_S4B_HOST_TIMING_2026-10-27';REPORT=O.with_suffix('.md')
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
load=lambda p:json.loads(Path(p).read_bytes())
assert not O.exists() and not REPORT.exists()
for label in ('guard_cli_01','scalar_cli_01','guard_flutter_01','scalar_flutter_01','guard_msp_01','read_msp_probe_01'):
    assert load(W/(label+'_exit.json'))['exitCode']==0,label
assert load(M/'guard_dart_batch_01_exit.json')['exitCode']==0
assert load(M/'dart_batch_probe_01_exit.json')['exitCode']==0
cli=load(W/'scalar_cli_01.json')['worker'];flutter=load(W/'scalar_flutter_01.json')['rows']
native=load(W/'read_msp_probe_01.json');dart=load(M/'dart_batch_probe_01.json')
assert cli['reads']==160 and cli['plcWrites']==0
assert all(row['worker']['reads']==160 and row['worker']['plcWrites']==0 for row in flutter)
assert native['packets']==dart['packets']==20 and native['plcWrites']==dart['tagWrites']==0
report='''# S4b read-only host timing and packet support — 2026-10-27

**Diagnostic findings only. Canonical/desktop acceptance remains open.**
The [row-refill attempt](AB_S4B_REFILL_ATTEMPT_2026-10-27.md) passes 41 cases,
87 independent exact replays and 3,144 entirely Good observer samples. Desktop
still becomes STALE after overview at 1,428.145 ms. Genealogy, five original
documents, 31 baseline cases and final checks pass. Its authorization is consumed.

These subsequent probes only read the restored baseline on local Echo
601FC87B, 1756-L81E v38.011, 127.0.0.1 slot 0. Fresh service/listener/identity/
fault/keyswitch guards precede each probe; transports pin the serial. No tag
writes, mode changes, downloads, clears, clock/power/vendor-state operations or
Echo hard kills occur. Diagnostic isolate cleanup affects its worker only.

## Scalar/timer control

Each phase reads the public HealthProbe Samples DINT 160 times through four
serial-pinned connections, one outstanding request per socket, in a worker
isolate. Forty one-millisecond timers follow. Flutter uses the same fully-live
binding as qualification: first without widgets, then with the shipped simulator
UI. This simulator phase is rendering load only, not the live station UI.

| Host | Request median /p95 /max (us) | 1 ms timer median /max (us) |
|---|---|---|
'''
for label,data in [('Dart CLI',cli),*[(row['phase'],row['worker']) for row in flutter]]:
    req,timer=data['requestUs'],data['oneMsTimerUs']
    report+=f"| {label} | {req['median']} /{req['p95']} /{req['maximum']} | {timer['median']} /{timer['maximum']} |\n"
report+='''
The observed Flutter request tails (13–16 ms) can exceed the 10 ms canonical
row-proof window. Medians remain near 1 ms. This does not isolate the precise
host/network/PLC cause of prior qualification failures. It does not justify
altering proofs, retry budgets, source timestamps or freshness limits.

## Multiple Service Packet support

[Rockwell's data-access manual](https://literature.rockwellautomation.com/idc/groups/literature/documents/pm/1756-pm020_-en-p.pdf)
documents service 0x0A for grouping requests in one explicit message.
The fixed probes read Samples /TaskLastScanUs /Samples; every embedded operation
is a read. Python sends 20 packets/60 Read Tag services, with native headers,
counts, offsets, type and exact DINT lengths checked. Dart's new read-only
transport sends 20 packets/60 Read Tag Fragmented services with typed replies.
No credential-bearing tag is read. Native raw responses and request bytes are
retained for the Python probe.

'''
report+=f"Python packet time (us): `{native['elapsedUs']}`; equal sample counters **{native['equalSampleCounterPackets']}/20**.\n\n"
report+=f"Dart packet time (us): `{dart['requestUs']}`; equal sample counters **{dart['equalSampleCounterPackets']}/20**.\n\n"
report+='''The changed-counter packet shows that an MSP is not a whole-scan atomic
transaction. The canonical reader must still prove equal-even published
counters and a window below the declared interval. HealthProbe Samples is not
that seqlock; these packets prove protocol support/timing only, not canonical
coherence, desktop acceptance or the performance of a full tree.

Next is offline validation of bounded row packets retaining every original
proof/freshness/read-only gate, then separately authorized canonical-image
qualification. No new controller-changing operation is authorized here.
The canonical image/Capacity and shipping V2 activation remain unchanged.
Nothing is committed or pushed. Credentials and binaries are excluded.
'''
with REPORT.open('x',encoding='utf-8',newline='') as f:f.write(report)
artifacts=[]
def archive(path,relative):
    assert 'credential' not in path.name.lower()
    raw=path.read_bytes();expanded=None
    if path.suffix=='.log':expanded=hashlib.sha256(raw).hexdigest();raw=gzip.compress(raw,mtime=0);relative+='.gz'
    target=O/relative;target.parent.mkdir(parents=True,exist_ok=True)
    with target.open('xb') as f:f.write(raw)
    artifacts.append(dict(path=relative,bytes=len(raw),sha256=sha(target),**(dict(expandedSha256=expanded) if expanded else {})))
for path in sorted(W.iterdir()):
    if path.is_file() and path.name!='seal_timing_01.log' and path.suffix in ('.py','.dart','.json','.log'):
        archive(path,'Control/'+path.name)
for name in ('probe_dart_batch.dart','dart_batch_probe_01.json','dart_batch_probe_01.log','dart_batch_probe_01_exit.json',
    'guard_dart_batch_01.log','guard_dart_batch_01_exit.json'):
    archive(M/name,'DartBatch/'+name)
manifest=dict(schema='fraktal.ab.s4b-readonly-host-timing',schemaVersion=1,
    sealedUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(),report=REPORT.name,reportSha256=sha(REPORT),
    controllerChanges=0,canonicalAccepted=False,desktopAccepted=False,artifacts=artifacts)
with (O/'manifest.json').open('x',encoding='utf-8') as f:json.dump(manifest,f,indent=2);f.write('\n')
for row in artifacts:assert sha(O/row['path'])==row['sha256']
with (W/'sealed_timing_01.json').open('x',encoding='utf-8') as f:
    json.dump(dict(passed=True,report=REPORT.as_posix(),artifacts=len(artifacts),manifestSha256=sha(O/'manifest.json')),f,indent=2)
print(json.dumps(dict(sealed=True,artifacts=len(artifacts),controllerChanges=0)))
