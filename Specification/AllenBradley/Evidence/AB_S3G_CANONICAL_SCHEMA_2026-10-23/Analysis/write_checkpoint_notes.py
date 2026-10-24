from pathlib import Path
import json
ROOT=Path('C:/Users/SoftIndVM/Fraktal');P=Path(__file__).parent;AB=ROOT/'Specification/AllenBradley'
proposal=json.loads((P/'boundary_implications_01.json').read_text())
proposal['qualityTotalWrapCounterexample']=dict(nativeGood=-1,nativeNok=1,coreUnsignedGood=4294967295,coreUnsignedNok=1,coreTotal=(4294967295+1)&0xffffffff,legacyQualValid=True,coreQualValid=False)
with (P/'boundary_implications_02.json').open('x') as f:json.dump(proposal,f,indent=2)
p=AB/'AB_CANONICAL_PUBLICATION_S3G_DEPENDENT_VALUES_REVIEW_2026-10-23.md'
text=p.read_text(encoding='utf-8').replace('boundary_implications_01.json','boundary_implications_02.json')
needle='- A native profiler count with bits `0x80000000`'
assert needle in text
text=text.replace(needle,'- Good/NOK bit patterns `0xffffffff` / `1` produce a Core UDINT total of 0,\n  so QualValid becomes FALSE; the legacy signed/clamped calculation makes it TRUE.\n'+needle,1)
p.write_text(text,encoding='utf-8')
p=AB/'AB_FROZEN_CONTRACTS_V2.json';data=json.loads(p.read_text());m=data['approvedMetricsCorrection'];m.update(dependentValuesReview='AB_CANONICAL_PUBLICATION_S3G_DEPENDENT_VALUES_REVIEW_2026-10-23.md',dependentValuesApproved=False,pendingDependentValuePaths=224,schemaQualifiedOffline=True,fullCandidatePrepared=False);p.write_text(json.dumps(data,indent=2)+'\n')
summary='''**S3g offline checkpoint, 2026-10-23:** owner approval records the 200 numeric
corrections. The schema covers all 1,055 paths; native REAL/INT and the existing
UInt32 bit representation need no generic decoder changes. The schema and health
mapper pass both v38 compiler/read-back/access gates in an explicitly offline,
uncalled type/health probe. Four focused tests and 2,118 full AB tests pass;
S3f source still regenerates exactly B71E30AB...0AE7CF3.

Boundary analysis found 224 dependent value paths omitted by the type-only
allow-list: 64 OEE validity flags and 160 profiler row values. Their exact Core
counterexamples and [review draft](AB_CANONICAL_PUBLICATION_S3G_DEPENDENT_VALUES_REVIEW_2026-10-23.md)
are pending the owner's decision. The default generator refuses stage 9 until
that contract and the complete algorithms pass. No complete S3g deployment image,
exact-image Capacity, native equivalence/scan or session is prepared. The layout
forecast is advisory only. No controller access or changing operation occurred;
the last verified live image is restored genealogy from the S3f session.
Read [checkpoint evidence](Evidence/AB_S3G_CANONICAL_SCHEMA_2026-10-23.md).

'''
for name,marker in [('AB_CANONICAL_PUBLICATION_PLAN_2026-10-20.md','**Latest, 2026-10-23: S3f exit passes on Echo.**'),('AB_CANONICAL_PUBLICATION_HANDOVER_2026-10-20.md','**Latest, 2026-10-23: S3f exit passes on Echo.**')]:
 p=AB/name;text=p.read_text(encoding='utf-8');assert marker in text;text=text.replace(marker,summary+marker,1);p.write_text(text,encoding='utf-8')
p=AB/'AB_CANONICAL_PUBLICATION_S3G_NOTES_2026-10-23.md'
with p.open('x',encoding='utf-8') as f:f.write('# S3g offline schema and numeric contract checkpoint\n\n'+summary+'Work: `'+P.as_posix()+'`.\n\nThe 200 type paths are approved. The 224 dependent value paths remain pending;\nthe deployed/shipping contracts and the frozen oracle are unchanged. The\nprobe retains the S3f executable graph and adds one uncalled health mapper;\nit is never a qualified S3g runtime candidate.\n')
print(json.dumps(dict(passed=True,numericTypeApprovalRecorded=True,dependentValuesApproved=False,fullCandidatePrepared=False,controllerAccess=False)))
