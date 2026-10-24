from pathlib import Path
import hashlib,json,shutil,sys
W=Path(__file__).parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest().upper()
pin=(W/'canonical.sha256').read_text().strip();assert sha(W/'s3f_canonical.ACD')==pin
assert not (W/'capacity_review.ACD').exists();shutil.copyfile(W/'s3f_canonical.ACD',W/'capacity_review.ACD')
template=dict(CurrentOwnerApproved=False,Serial='601FC87B',CanonicalSha256=pin,FaultClearAuthorized=False,ClockSetAuthorized=False,
 ManualNormalizationAuthorized=False,AccessVectorsAuthorized=False,ConfigurationVectorsAuthorized=False,RevisionVectorsAuthorized=False,RetainedRestartAuthorized=False,
 Scope=['fresh guard/MANUAL preflight/backup; Program/download/Run exact revision-fix image',
 'five-document restore; 31 inherited regressions, two Access and eight configuration cases',
 'two simulated CHANGEOVER runs via SET_MODEL and tooling confirmation, original model/recipe/inputs restored',
 'one retained Program/Run cycle with no download; new revision and unchanged configuration/banks/policy/page required',
 'read-only equivalence/sizes/scan; genealogy rollback, five-document restore and 31 baseline rows; MANUAL cleanup/final checks'])
with (W/'authorization.template.json').open('x') as f:json.dump(template,f,indent=2)
sys.path.insert(0,'C:/Users/SoftIndVM/Fraktal/FraktalCore/PLC/Allen-Bradley/tools')
import fraktal_ab_readback as readback
old=Path('C:/work/fraktal-ab-s3f-20261022/prepare_3816927132f14d4998876bc62e22f342/genealogy_s3f_05.L5X')
delta=readback.compare(old,W/'genealogy_s3f_revision_01.L5X')
assert delta['Inventory']['Equivalent'] and delta['SFC']['Equivalent'] and not delta['InitialValueDifferences']
assert len(delta['ExecutableDifferences'])==1,delta['ExecutableDifferences']
with (W/'source_delta_01.json').open('x') as f:json.dump(dict(expectedDelta=True,explanation='one first-scan initialization assignment; layout, initials and SFC unchanged',comparison=delta),f,indent=2)
print(json.dumps(dict(passed=True,preparedAcdSha256=pin,sourceSha256=sha(W/'genealogy_s3f_revision_01.L5X'),expectedChangedBodies=1)))
