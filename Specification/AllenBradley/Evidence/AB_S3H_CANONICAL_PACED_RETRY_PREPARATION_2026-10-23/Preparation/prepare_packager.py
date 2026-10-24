from pathlib import Path
P=Path(__file__).parent;OLD=P.parent/'retry_9d1da9a04d564b03bc2b176f5b17ea42'
t=(OLD/'package_retry.py').read_text()
for old,new in {
 'transport_2eff7b66442a4322a987fb2f7812268b':'transport_ae4489870e334fefaf4d7d28580708cc',
 "NAME='AB_S3H_CANONICAL_RETRY_PREPARATION_2026-10-23'":"NAME='AB_S3H_CANONICAL_PACED_RETRY_PREPARATION_2026-10-23'",
 'abTests=2148':'abTests=2149',
 'predecessorRecords=29,predecessorArtifacts=6885':'predecessorRecords=31,predecessorArtifacts=7480',
 'currentRecords=30,currentArtifacts=6885+len(artifacts)':'currentRecords=32,currentArtifacts=7480+len(artifacts)',
 "baselineTransportProxyOnly=True,":"baselineTransportProxyOnly=True,qualifiedBaselineProxyCaptures=1000,unchangedEvenWaitSeconds=.001,",
 }.items():
 assert t.count(old)==1,(old,t.count(old));t=t.replace(old,new,1)
with (P/'package_retry.py').open('x') as f:f.write(t)
R=P.parent/'runtime_6cf76ecb8785463ab372c202e79f03f2'
t=(R/'trace_observations.py').read_text()
old="    assert pair['projection']['values']==v and pair['projection']['types']==types"
assert t.count(old)==1
t=t.replace(old,"    from fraktal_ab_canonical_equivalence import compare_documents\n    comparison=compare_documents(pair['projection'],c)\n    assert comparison['equal'] and comparison['typeAcceptance']")
with (P/'trace_observations.py').open('x') as f:f.write(t)
