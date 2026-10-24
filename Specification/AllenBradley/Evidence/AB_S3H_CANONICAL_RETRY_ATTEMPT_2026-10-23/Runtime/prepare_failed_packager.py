from pathlib import Path
R=Path(__file__).parent;prior=R.parent/'runtime_6cf76ecb8785463ab372c202e79f03f2'
t=(prior/'package_failed_session.py').read_text()
changes={
 'prepare_5822102a73e348ec95ff7082959ef940':'retry_9d1da9a04d564b03bc2b176f5b17ea42',
 "NAME='AB_S3H_CANONICAL_ATTEMPT_2026-10-23'":"NAME='AB_S3H_CANONICAL_RETRY_ATTEMPT_2026-10-23'",
 'len(prior)==28 and sum(r[\'artifacts\'] for r in prior)==6589':"len(prior)==30 and sum(r['artifacts'] for r in prior)==7199",
 "passingPairs=10,failedPairs=1":"passingPairs=3,failedPairs=1",
 "sourceBindings=157,abTests=2140,rootTests=74,focusedTests=13":"sourceBindings=159,abTests=2148,rootTests=74",
 "currentRecords=29,currentArtifacts=6589+len(artifacts),predecessorRecords=28,predecessorArtifacts=6589":
 "currentRecords=31,currentArtifacts=7199+len(artifacts),predecessorRecords=30,predecessorArtifacts=7199",
 "schema='fraktal.ab.s3h-canonical-attempt-evidence'":"schema='fraktal.ab.s3h-canonical-retry-attempt-evidence'",
}
for old,new in changes.items():
 assert t.count(old)==1,(old,t.count(old))
 t=t.replace(old,new,1)
with (R/'package_failed_session.py').open('x',encoding='utf-8') as f:f.write(t)
