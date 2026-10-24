from pathlib import Path
R=Path(__file__).parent;prior=R.parent/'runtime_fd53835fe9684f598bdd829da6d29c8d'
t=(prior/'package_failed_session.py').read_text()
for old,new in {
 'retry_9d1da9a04d564b03bc2b176f5b17ea42':'retry_fc306d330cc642499a52abbb53bae945',
 "NAME='AB_S3H_CANONICAL_RETRY_ATTEMPT_2026-10-23'":"NAME='AB_S3H_CANONICAL_PACED_RETRY_ATTEMPT_2026-10-23'",
 "len(prior)==30 and sum(r['artifacts'] for r in prior)==7199":"len(prior)==32 and sum(r['artifacts'] for r in prior)==7749",
 'passingPairs=3,failedPairs=1':'passingPairs=39,failedPairs=1',
 'abTests=2148':'abTests=2149',
 'currentRecords=31,currentArtifacts=7199+len(artifacts),predecessorRecords=30,predecessorArtifacts=7199':
 'currentRecords=33,currentArtifacts=7749+len(artifacts),predecessorRecords=32,predecessorArtifacts=7749',
 }.items():
 assert t.count(old)==1,(old,t.count(old));t=t.replace(old,new,1)
with (R/'package_failed_session.py').open('x') as f:f.write(t)
