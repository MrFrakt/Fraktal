"""Seal the reviewed inventory and approval before dependent implementation."""
from pathlib import Path
import datetime,gzip,hashlib,json
R=Path(__file__).parent;ROOT=Path('C:/Users/SoftIndVM/Fraktal');AB=ROOT/'Specification/AllenBradley';E=AB/'Evidence'
NAME='AB_S3I_CANONICAL_INVENTORY_2026-10-24';DEST=E/NAME;REPORT=E/(NAME+'.md')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
d=json.loads((R/'inventory_01.json').read_text());v=json.loads((R/'validation_01.json').read_text())
approval=json.loads((R/'owner_contract_approval_01.json').read_text())
assert v['passed'] and approval['OwnerApproved'] and not approval['ControllerChangesAuthorized']
for label in ('inventory_01','contract_review_01','validation_01','plan_update_01','ab_remaining_s3_01',
              'root_remaining_s3_01','spec_remaining_s3_01','contracts_remaining_s3_01',
              'consistency_remaining_s3_01','whitespace_remaining_s3_01'):
    assert json.loads((R/(label+'_exit.json')).read_text())['exitCode']==0,label
assert 'Ran 2158 tests in 268.052s' in (R/'ab_remaining_s3_01.log').read_text()
assert 'Ran 74 tests' in (R/'root_remaining_s3_01.log').read_text()
for name,bound in d['sourceBindings'].items():assert sha(ROOT/name)==bound['sha256'],name
review=AB/'AB_CANONICAL_PUBLICATION_REMAINING_S3_CONTRACT_REVIEW_2026-10-24.md'
inventory=AB/'AB_CANONICAL_PUBLICATION_REMAINING_S3_INVENTORY_2026-10-24.json'
binding=dict(approvalQuestion=approval['ApprovalQuestion'],approvalAnswer=approval['ApprovalAnswer'],
    reviewSha256=sha(review),inventorySha256=sha(inventory),controllerChangesAuthorized=False,
    reviewedDraftArchivedAs='Reviewed/AB_CANONICAL_PUBLICATION_REMAINING_S3_CONTRACT_REVIEW_2026-10-24.md')
with (R/'owner_contract_binding_01.json').open('x') as out:json.dump(binding,out,indent=2)
report=f'''# Remaining S3 inventory and approved finite contract — 2026-10-24

**The owner approved the finite remaining-S3 contract and dependent offline
work. No controller operation or dependent implementation ran in this record.**
Approval: `{approval['ApprovalQuestion']}`, “{approval['ApprovalAnswer']}”.
The payload binds the exact reviewed proposal and inventory by SHA-256. Its
prepared working-document snapshots retain their review-pending wording;
the later approval record governs the decision. Applying the V2 allowance
and implementing S3i are subsequent work, not acceptance claimed here.

The frozen 4,437-path genealogy oracle remains unchanged. Prior stage inventory
keys are already in D2 canonical coordinates. Normalizing the frozen keys once
and subtracting proves **149** gaps, rather than the raw difference of 157.
The eight apparent array endpoints, including Access/Policy.Required[12], are
already represented under their approved indices. There is no new D2 exception.

| Finding | Exact count |
|---|---:|
| Existing covered frozen paths after D2 | 4,288 |
| Remaining mailbox/report | 126 |
| Remaining Line/current-shift | 16 |
| Remaining production / Features | 5 / 2 |
| Total remaining | 149 |
| Proposed finite Core path spellings | 122: 120 reason fields and two Line names |
| Proposed frozen type corrections | 13: seven UInt32, three Int16, three DateTime |
| Additional static command/status paths | 11: nine request arguments and two missing Core Line status fields |
| Occupied eight-row history schema | 21 fields/row, at most 168 paths; frozen history count is zero |
| Dynamic history corrections | 112 type paths plus 32 explicitly enumerated dependent validity values; eight added SchemaVersion fields |

The proposal follows Core ST_HmiRequest/ST_HmiResponse/ST_ReleaseReport,
ST_LineStatus/ST_ShiftRecordV3 and actual Unit declarations. It explicitly
normalizes timestamps, preserves UInt32 bits and Core Float32 operation order,
retains binding-owned metadata, rejects over-width LineId, and requires
versioned released layouts. The public report has 24 slots over an eight-row
legacy producer; the approved canonical target uses a versioned complete
24-reason owner. Secret command values stay outside snapshots/frame evidence.
The JSON enumerates every finite path and its source; no implementation may
replace it with blanket coercion, path omission, tolerance or truncation.

The newer S3h observation-frame runtime is accepted: 41 candidate /31 baseline
checks, all 88 native pairs exact. Capacity is measured at 2,680,132 used /
465,596 available /3,145,728 Blocks (85%) for that candidate; genealogy was
restored afterward. The planning forecast warns, but no new image's fit is
claimed. Exact-image automatic Studio Capacity and scan remain mandatory.
The frame is migration-only and removed at S6. Part III §3.13 shipping
coherence is per row/group and read tier, not a coherent live document.

S3i Line/shift is the next implementation slice. S3j's separate fieldbus
product has zero frozen genealogy paths and still needs its own proof. The
actual press declaration must pass ST/SFC/ladder; genealogy's rendition runs
do not accept another declaration. S4–S7, persistence-medium selection after
the probe, per-station write posture and physical/CIP Security stay open.

Validation: the independent set/type/rename/source checks pass, and all 162
accepted implementation source bindings are unchanged. A fresh full AB suite
passes **2,158 tests in 268.052 s**; all 74 root tests, specification, contracts,
strict consistency (0 errors/warnings) and whitespace gates pass. There is no
new PLC/ST/L5X or HMI implementation here, so no new native build/download,
Capacity/scan or Flutter gate is applicable. Existing v38/Capacity/runtime
evidence stays at its exact-image scope. All 41 predecessor records /9,345
artifacts are verified unchanged by the seal. The owner's unrelated Siemens
archive edits are untouched. No credential, ACD, state file or memory dump is
archived. No commit or push.

Work folder: `{R.as_posix()}`. Append-only
[payload manifest]({NAME}/manifest.json). Current contract/next-stage working
documents may subsequently record approval and implementation progress; their
reviewed bytes remain preserved here.
'''
with REPORT.open('x',encoding='utf-8',newline='\n') as out:out.write(report)
prior=[]
prefixes=('AB_S0_CANONICAL','AB_S0_SUPPLEMENTARY','AB_S1_CANONICAL','AB_S2_CANONICAL',
          'AB_S3A_CANONICAL','AB_S3B_CANONICAL','AB_S3C_CANONICAL','AB_S3D_CANONICAL',
          'AB_S3E_CANONICAL','AB_S3F_CANONICAL','AB_S3G_CANONICAL','AB_S3H_CANONICAL')
for path in sorted(E.glob('AB_*/manifest.json')):
    if not any(prefix in path.parent.name for prefix in prefixes):continue
    m=json.loads(path.read_text())
    for row in m['artifacts']:
        p=path.parent/row['path'];assert p.stat().st_size==row['bytes'] and sha(p)==row['sha256'].lower(),p
        if row.get('expandedSha256'):assert hashlib.sha256(gzip.decompress(p.read_bytes())).hexdigest()==row['expandedSha256'].lower(),p
    if m.get('report'):assert sha(E/m['report'])==m['reportSha256'].lower()
    prior.append(dict(name=path.parent.name,artifacts=len(m['artifacts']),manifestSha256=sha(path)))
assert len(prior)==41 and sum(row['artifacts'] for row in prior)==9345
assert not DEST.exists();DEST.mkdir()
def copy(path,name):
    assert path.suffix.lower() not in ('.acd','.dmp','.sqlite','.exe','.dll') and 'credential' not in path.name.lower()
    target=DEST/name;target.parent.mkdir(parents=True,exist_ok=True)
    with target.open('xb') as out:out.write(path.read_bytes())
for path in sorted(R.iterdir()):
    if not path.is_file() or path.name.startswith(('seal_inventory_01','inventory_seal_')):continue
    copy(path,'Work/'+path.name)
for name in ('AB_CANONICAL_PUBLICATION_REMAINING_S3_CONTRACT_REVIEW_2026-10-24.md',
             'AB_CANONICAL_PUBLICATION_REMAINING_S3_INVENTORY_2026-10-24.json',
             'AB_CANONICAL_PUBLICATION_REMAINING_S3_NOTES_2026-10-24.md',
             'AB_CANONICAL_PUBLICATION_PLAN_2026-10-20.md','AB_CANONICAL_PUBLICATION_HANDOVER_2026-10-20.md'):
    copy(AB/name,'Reviewed/'+name)
for name in d['sourceBindings']:copy(ROOT/name,'Source/'+name)
rows=[dict(path=path.relative_to(DEST).as_posix(),bytes=path.stat().st_size,sha256=sha(path)) for path in sorted(DEST.rglob('*')) if path.is_file()]
m=dict(schema='fraktal.ab.remaining-s3-inventory-review-evidence',schemaVersion=1,date='2026-10-24',
    sealedUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(),report=REPORT.name,reportSha256=sha(REPORT),
    ownerContractApproved=True,approval=binding,implementationChanged=False,controllerAccess=False,controllerWrites=0,
    approvedAllowListNotYetChanged=True,remainingPaths=149,rawUnmatchedKeys=157,d2EndpointsAlreadyCovered=8,
    proposedRenames=122,proposedFrozenTypeCorrections=13,dynamicHistoryTypeCorrections=112,
    dynamicHistoryDependentValidityPaths=32,sourceBindingsUnchanged=162,abTests=2158,rootTests=74,
    priorSeals=prior,artifacts=rows,artifactCount=len(rows),totalBytes=sum(row['bytes'] for row in rows))
with (DEST/'manifest.json').open('x') as out:json.dump(m,out,indent=2)
for row in rows:assert sha(DEST/row['path'])==row['sha256']
result=dict(passed=True,artifactCount=len(rows),manifestSha256=sha(DEST/'manifest.json'),reportSha256=sha(REPORT),
    predecessorRecords=41,predecessorArtifacts=9345,currentRecords=42,currentArtifacts=9345+len(rows),
    ownerApprovedOffline=True,controllerChangesAuthorized=False)
with (R/'inventory_seal_01.json').open('x') as out:json.dump(result,out,indent=2)
print(json.dumps(result))
