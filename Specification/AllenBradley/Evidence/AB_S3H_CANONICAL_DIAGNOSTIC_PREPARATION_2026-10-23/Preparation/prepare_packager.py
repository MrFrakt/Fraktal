from pathlib import Path
P=Path(__file__).parent;OLD=P.parent/'retry_fc306d330cc642499a52abbb53bae945'
t=(OLD/'package_retry.py').read_text()
for old,new in {
 'transport_ae4489870e334fefaf4d7d28580708cc':'transport_bd2c073c468c443eb19ca12f85d90eda',
 "NAME='AB_S3H_CANONICAL_PACED_RETRY_PREPARATION_2026-10-23'":"NAME='AB_S3H_CANONICAL_DIAGNOSTIC_PREPARATION_2026-10-23'",
 "P/'retry_verification_01.json'":"P/'diagnostic_verification_01.json'",
 "P/'retry_verification_01_exit.json'":"P/'diagnostic_verification_02_exit.json'",
 'predecessorRecords=31,predecessorArtifacts=7480':'predecessorRecords=33,predecessorArtifacts=8072',
 'currentRecords=32,currentArtifacts=7480+len(artifacts)':'currentRecords=34,currentArtifacts=8072+len(artifacts)',
 'qualifiedBaselineProxyCaptures=1000,unchangedEvenWaitSeconds=.001':'diagnosticWrapperTests=4,unchangedEvenWaitSeconds=.001',
 "schema='fraktal.ab.s3h-canonical-retry-preparation-evidence'":"schema='fraktal.ab.s3h-canonical-diagnostic-preparation-evidence'",
 "status='retry-offline-gates-passed-current-native-authorization-pending'":"status='diagnostic-offline-gates-passed-current-native-authorization-pending'",
 }.items():
 assert t.count(old)==1,(old,t.count(old));t=t.replace(old,new,1)
t=t.replace('retryReady','diagnosticReady').replace('retry_seal_verification_','diagnostic_seal_verification_')
with (P/'package_diagnostic.py').open('x') as f:f.write(t)
