"""Publish the reviewable offline state and finite approved rule, without activation."""
from pathlib import Path
import json
P=Path(__file__).parent;AB=Path('C:/Users/SoftIndVM/Fraktal/Specification/AllenBradley')
cap=json.loads((P/'capacity_review.json').read_text());assert cap['VerifiedFit']
assert cap['UsedStandardBlocks']==2407200 and cap['AvailableBlocks']==738528
pin=(P/'canonical.sha256').read_text().strip()
with (P/'canonical_prepared_compare.json').open('x') as f:f.write((P/'prepared_readback_01.log').read_text())
review=AB/'AB_CANONICAL_PUBLICATION_S3G_CONTRACT_REVIEW_2026-10-23.md'
text=review.read_text(encoding='utf-8')
text=text.replace('No S3g PLC image or native session is prepared.',
    'A complete S3g image is now prepared behind its separate native-session approval gate.')
text=text.replace('All other paths retain exact values and types. The 855 other added S3g paths,',
    'The owner separately approved the [224 dependent value paths](AB_CANONICAL_PUBLICATION_S3G_DEPENDENT_VALUES_REVIEW_2026-10-23.md).\nTheir types stay unchanged. The 631 remaining added S3g paths,')
review.write_text(text,encoding='utf-8')
status='''**S3g complete offline preparation, 2026-10-23:** both approved amendments
are implemented: 200 Core numeric types and 224 dependent values, with exactly
1,055 additional consumed paths. The independent Core Float32/UInt32 reference
and actual emitted ST pass 13 focused tests, 2,127 full AB tests (291.415 s),
74 root tests, specification/contracts/strict-consistency and whitespace gates.
The complete image passes both v38 builds, exact read-back and access audits;
all seven accepted prior stage images and sealed capture replays remain exact.
The generic reader is unchanged.

Prepared ACD `CCE00F97...B4A6331` has measured automatic Studio Capacity of
2,407,200 used / 738,528 available / 3,145,728 total Blocks (76%), +108,752
over accepted S3f. Source `50E0F897...104DAE91` includes a separately generated
bench routine: nine first-scan OEE boundary vectors and two high-bit profiler
rows. The latter save/restore six fixed DINT owner cells in that same scan,
before normal publication. Results are read-only and outside the canonical tree.
No controller-changing operation is authorized or performed. Fresh read-only
checks pass on restored genealogy: Run/not faulted/Remote/scanning,
MANUAL=1/idle/logout/not-restoring, five documents and policy equal.

Next is current authorization for this exact image and the guarded S3g native
session: backup, Program/download/Run, 41 candidate regressions plus 11 native
boundary results, read-only 3,672 / 3,622 / 3,272-path equivalence/size/scan,
genealogy rollback and 31 baseline regressions/final checks. Native equivalence,
scan, hardware and CIP Security acceptance remain open. No commit or push.
Read [complete preparation evidence](Evidence/AB_S3G_CANONICAL_PREPARATION_2026-10-23.md).

'''
for name,anchor in (
    ('AB_CANONICAL_PUBLICATION_PLAN_2026-10-20.md','## 2. State at hand-over (2026-10-20)\n\n'),
    ('AB_CANONICAL_PUBLICATION_HANDOVER_2026-10-20.md','## Current continuation state (2026-10-20)\n\n')):
    path=AB/name;text=path.read_text(encoding='utf-8');assert text.count(anchor)==1
    text=text.replace(anchor,anchor+status,1)
    text=text.replace('**S3g offline checkpoint, 2026-10-23:**','**Earlier S3g schema checkpoint, 2026-10-23 (superseded above):**',1)
    text=text.replace('S3g inventory/review is next; further native changes need their own current approval.',
        'S3g offline preparation is described above; further native changes need their own current approval.')
    path.write_text(text,encoding='utf-8')
(AB/'AB_CANONICAL_PUBLICATION_S3G_NOTES_2026-10-23.md').write_text(
    '# S3g OEE/profiler/health publication\n\n'+status+
    'Work: `'+P.as_posix()+'`.\n\n'
    'The shipped Part III and V1 contract remain authoritative until the final\n'
    'activation gate; V2 remains inactive. The original schema-only probe is\n'
    'sealed separately and its historical findings are unchanged. The 2,125-test\n'
    'attempt retained one obsolete stage-rejection test failure; the corrected\n'
    'full suite passes 2,127 tests. No validation or feature was removed.\n',encoding='utf-8')
design=AB/'AB_CANONICAL_PUBLICATION_DESIGN_2026-10-19.md';text=design.read_text(encoding='utf-8')
text=text.replace('type. The only differences allowed are the D2 bound corrections, listed one\n  by one.',
    'type. Allowed differences are the five D2 bound corrections plus the finite\n  owner-approved S3f corrections and S3g 200 numeric / 224 dependent value paths\n  enumerated in the plan §1. No general coercion, tolerance or ignored path applies.',1)
text+='\n\n## Current S3g preparation (2026-10-23)\n\n'+status
design.write_text(text,encoding='utf-8')
amendment=AB/'AB_CANONICAL_PUBLICATION_PART_III_AMENDMENT_DRAFT_2026-10-20.md'
text=amendment.read_text(encoding='utf-8');needle='## AB §1, §2.1 and §4.1 — reference profile'
assert text.count(needle)==1
text=text.replace(needle,
    'The owner-approved S3f and S3g finite corrections extend this target draft.\n'
    'S3g binds the 64 consumed OEE values to exact Core REAL arithmetic, 101\n'
    'numeric paths to the full UInt32 domain and 35 to Int16. Its separately\n'
    'approved 224 dependent values follow those Core arithmetic/count semantics;\n'
    'all 631 other S3g values/types stay exact. The [plan §1](AB_CANONICAL_PUBLICATION_PLAN_2026-10-20.md)\n'
    'links the enumerations. This records the approved target, without activating\n'
    'Part III/V2 or establishing runtime acceptance.\n\n'+needle,1)
amendment.write_text(text,encoding='utf-8')
v2=AB/'AB_FROZEN_CONTRACTS_V2.json';data=json.loads(v2.read_text());assert not data['active']
m=data['approvedMetricsCorrection'];m.update(fullCandidatePrepared=True,
    preparationEvidence='Evidence/AB_S3G_CANONICAL_PREPARATION_2026-10-23.md',
    sourceBindings=151,abTests=2127,rootTests=74,preparedAcdSha256=pin,
    sourceSha256='50E0F8977D975A14C5CD6F86A42AE56B8D4F995CD6A2AA52E071C252104DAE91',
    measuredCapacityBlocks=dict(used=2407200,available=738528,total=3145728,percent=76,deltaFromAcceptedS3f=108752),
    nativeChecksPrepared=dict(oeeVectors=9,profilerHighBitVectors=2,fixedProfilerCellsSavedRestored=6),
    remainingNativeGates=['current exact-image authorization','11 fixed native boundary results','41 candidate and 31 restored-baseline regressions',
        'whole-scan path/type/value equivalence','native record sizes and scan'],runtimeAccepted=False,controllerChangesAuthorized=False)
paths=json.loads((P/'boundary_implications_02.json').read_text())['paths'];assert len(set(paths))==224
m['dependentValueInventory']=paths
v2.write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')
print(json.dumps(dict(passed=True,preparedAcdSha256=pin,controllerChangesAuthorized=False,capacityBlocks=2407200)))
