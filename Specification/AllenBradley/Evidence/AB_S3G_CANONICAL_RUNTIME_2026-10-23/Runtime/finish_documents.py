"""Record the completed Echo gate and add its accepted Capacity observation."""
from pathlib import Path
import hashlib,json
ROOT=Path('C:/Users/SoftIndVM/Fraktal');R=Path(__file__).parent;AB=ROOT/'Specification/AllenBradley'
v=json.loads((R/'runtime_verification_01.json').read_text());assert v['passed'] and v['acceptedTotalChecks']==83 and v['allPreparedSourcesUnchanged']
summary='''**Latest, 2026-10-23: S3g exit passes on Echo.** All 83 planned checks
pass on their first runs: 41 candidate cases, nine OEE boundary vectors, two
profiler high-bit vectors and 31 restored-genealogy regressions. All 88 paired
captures replay exactly from native bytes and independent provider/metric
references, at 3,672 / 3,622 / 3,272 paths/types. The unchanged whole-scan proof
accepts in 1–75 attempts within 100 attempts/five seconds. All 151 prepared
sources, including the PLC/image and generic reader, are unchanged; their
2,127 AB and 74 root tests remain bound to the preparation seal.

Automatic Capacity is 76%: 2,407,200 used / 738,528 available / 3,145,728 total
Blocks, +108,752 over accepted S3f. Native root/definitions/alarm metadata total
145,084 bytes (121,160 / 7,308 / 16,616). Candidate scan median/max is
868 / 5,273 µs; restored genealogy 99 / 1,168 µs; zero overlaps. These are Echo
observations under different workloads, not isolated publication costs.

Genealogy is restored: Run/not faulted/Remote/scanning, MANUAL=1/idle/logout,
not restoring, all five saved/live documents and policy/preflight equal. No
fault clear or clock change occurred. This exact session authorization is
consumed. V2 remains inactive; no commit or push. Read
[S3g runtime evidence](Evidence/AB_S3G_CANONICAL_RUNTIME_2026-10-23.md).
S3h inventory is next; further controller changes need separate current approval.

'''
for name,anchor in (
    ('AB_CANONICAL_PUBLICATION_PLAN_2026-10-20.md','## 2. State at hand-over (2026-10-20)\n\n'),
    ('AB_CANONICAL_PUBLICATION_HANDOVER_2026-10-20.md','## Current continuation state (2026-10-20)\n\n')):
    path=AB/name;text=path.read_text(encoding='utf-8');assert text.count(anchor)==1
    text=text.replace(anchor,anchor+summary,1)
    text=text.replace('**S3g complete offline preparation, 2026-10-23:**','**Earlier S3g offline preparation, 2026-10-23 (session completed above):**',1)
    path.write_text(text,encoding='utf-8')
notes=AB/'AB_CANONICAL_PUBLICATION_S3G_NOTES_2026-10-23.md'
notes.write_text('# S3g OEE/profiler/health publication\n\n'+summary+
    'The finite 200 numeric / 224 dependent value amendments are accepted at\n'
    'this genealogy/Echo scope; 631 other added paths stay exact. All 1,055\n'
    'added paths are PLC-owned. Physical/CIP Security, other declarations and\n'
    'S3h–S7 acceptance remain separate. No shipping contract activation.\n\n'
    'Preparation and its six historical failed schema/probe/test runs stay\n'
    'sealed unchanged. This native session has no failed or extra runs.\n',encoding='utf-8')
design=AB/'AB_CANONICAL_PUBLICATION_DESIGN_2026-10-19.md'
text=design.read_text(encoding='utf-8');text+='\n\n## S3g Echo acceptance (2026-10-23)\n\n'+summary
design.write_text(text,encoding='utf-8')
v2=AB/'AB_FROZEN_CONTRACTS_V2.json';data=json.loads(v2.read_text());assert not data['active']
m=data['approvedMetricsCorrection'];m.update(runtimeAccepted=True,runtimeAcceptedAtRecordedScope=True,
    runtimeEvidence='Evidence/AB_S3G_CANONICAL_RUNTIME_2026-10-23.md',remainingNativeGates=[],
    runtimeScope='Local Echo 601FC87B genealogy fixture; physical/CIP Security and later stages remain open',
    sessionAuthorizationConsumed=True,controllerChangesAuthorized=False,
    runtimeChecks=dict(candidate=41,nativeVectors=11,baseline=31,total=83),pairedCaptures=88,
    nativePayloadBytes=145084,nativeRecordBytes=[121160,7308,16616],timingUs=v['timing'])
v2.write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')
obs=AB/'AB_CAPACITY_OBSERVATIONS_2026-10-21.json';data=json.loads(obs.read_text());assert len(data['samples'])==8
source='Evidence/AB_S3G_CANONICAL_PREPARATION_2026-10-23/Preparation/s3g_native_candidate_01.L5X.gz'
capacity='Evidence/AB_S3G_CANONICAL_PREPARATION_2026-10-23/Preparation/capacity_review.json'
data['samples'].append(dict(label='S3g',source=source,sourceSha256=v['sourceSha256'],capacity=capacity,
    capacitySha256=hashlib.sha256((AB/capacity).read_bytes()).hexdigest(),acdSha256=v['preparedAcdSha256'],
    runtimeEvidence='Evidence/AB_S3G_CANONICAL_RUNTIME_2026-10-23.md'))
obs.write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')
print(json.dumps(dict(passed=True,s3gStageComplete=True,acceptedChecks=83,capacityCalibrationSamples=9,v2Active=False,authorizationConsumed=True)))
