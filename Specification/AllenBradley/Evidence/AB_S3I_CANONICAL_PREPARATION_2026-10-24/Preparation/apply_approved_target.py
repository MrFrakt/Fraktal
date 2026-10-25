from pathlib import Path
import hashlib,json
ROOT=Path('C:/Users/SoftIndVM/Fraktal');AB=ROOT/'Specification/AllenBradley';R=Path(__file__).parent
SEALED=AB/'Evidence/AB_S3I_CANONICAL_INVENTORY_2026-10-24'
approval=json.loads((SEALED/'Work/owner_contract_approval_01.json').read_text())
binding=json.loads((SEALED/'Work/owner_contract_binding_01.json').read_text())
assert approval['OwnerApproved'] and not approval['ControllerChangesAuthorized']
name='AB_CANONICAL_PUBLICATION_REMAINING_S3_INVENTORY_2026-10-24.json';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(AB/name)==binding['inventorySha256']
path=AB/'AB_FROZEN_CONTRACTS_V2.json';d=json.loads(path.read_text());assert not d['active']
assert 'approvedRemainingSurfaceCorrection' not in d
d['approvedRemainingSurfaceCorrection']=dict(ownerApproved=True,status='approved-for-offline-implementation',
    approvalQuestion=approval['ApprovalQuestion'],approvalAnswer=approval['ApprovalAnswer'],
    approvalEvidence='Evidence/AB_S3I_CANONICAL_INVENTORY_2026-10-24.md',
    reviewedContractSha256=binding['reviewSha256'],inventory=name,inventorySha256=binding['inventorySha256'],
    frozenPaths=149,pathSpellings=122,frozenTypeCorrections=13,additionalStaticCorePaths=11,
    dynamicShiftHistoryCapacity=8,dynamicShiftTypeCorrections=112,dynamicShiftDependentValidityPaths=32,
    releaseReasonCapacity=24,controllerChangesAuthorized=False,runtimeAccepted=False,
    stageStatus=dict(S3i='offline-in-progress',S3j='pending',S3k='pending'))
path.write_bytes((json.dumps(d,indent=2)+'\n').encode())
review=AB/'AB_CANONICAL_PUBLICATION_REMAINING_S3_CONTRACT_REVIEW_2026-10-24.md'
text=review.read_text(encoding='utf-8')
old='**Proposal awaiting owner approval. No dependent PLC/client implementation or\nnew controller operation is authorized by this document.**'
assert text.count(old)==1
text=text.replace(old,'**Owner-approved for dependent offline work on 2026-10-24**\n(question `'+approval['ApprovalQuestion']+'`). The exact reviewed bytes and approval\nare preserved in [inventory evidence](Evidence/AB_S3I_CANONICAL_INVENTORY_2026-10-24.md).\nNo controller operation is authorized by this approval.',1)
review.write_bytes(text.encode())
for filename in ('AB_CANONICAL_PUBLICATION_PLAN_2026-10-20.md','AB_CANONICAL_PUBLICATION_HANDOVER_2026-10-20.md'):
    p=AB/filename;text=p.read_text(encoding='utf-8')
    if filename.startswith('AB_CANONICAL_PUBLICATION_PLAN'):
        old='awaits owner approval before implementation.**';assert text.count(old)==1
        text=text.replace(old,'is owner-approved for offline implementation.**',1)
        old='obligations absent from the frozen sample. No allowance is activated yet.';assert text.count(old)==1
        text=text.replace(old,'obligations absent from the frozen sample. The finite target allowance is recorded; V2 remains inactive.',1)
        old='retain exact values and types. The frozen genealogy';assert text.count(old)==1
        text=text.replace(old,'retain exact values and types. The owner also approved the finite\n   [remaining-S3 corrections](AB_CANONICAL_PUBLICATION_REMAINING_S3_CONTRACT_REVIEW_2026-10-24.md)\n   on 2026-10-24: 122 path spellings, 13 frozen type corrections and the\n   enumerated command/status/history schema and arithmetic consequences.\n   The exact inventory and approval are bound in S3i inventory evidence. The frozen genealogy',1)
    else:
        old='decision; dependent implementation has not begun.**';assert text.count(old)==1
        text=text.replace(old,'decision, now approved for offline work; S3i implementation is starting.**',1)
        old='No new runtime scope, V2 allowance, write posture, commit or push is granted.';assert text.count(old)==1
        text=text.replace(old,'The finite V2 target allowance is recorded; no new runtime scope, deployment write posture, commit or push is granted.',1)
    p.write_bytes(text.encode())
notes=AB/'AB_CANONICAL_PUBLICATION_REMAINING_S3_NOTES_2026-10-24.md';text=notes.read_text(encoding='utf-8')
old='is awaiting approval. The approved V2 allow-list\nis unchanged. No controller, PLC generator or HMI source is changed here.';assert text.count(old)==1
text=text.replace(old,'was owner-approved for offline work (question `'+approval['ApprovalQuestion']+'`).\nThe finite target allowance is recorded, with V2 inactive and S3i offline work\nstarting. The inventory itself changed no controller or production source.',1)
notes.write_bytes(text.encode())
with (R/'approved_target_application_01.json').open('x') as out:
    json.dump(dict(applied=True,approval=approval,inventorySha256=binding['inventorySha256'],
                   v2Active=False,controllerChangesAuthorized=False),out,indent=2)
print(json.dumps(dict(applied=True,offlineImplementationApproved=True,controllerChangesAuthorized=False)))
