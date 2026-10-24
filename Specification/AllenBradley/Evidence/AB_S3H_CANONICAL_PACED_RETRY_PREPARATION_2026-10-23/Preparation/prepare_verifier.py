from pathlib import Path
P=Path(__file__).parent;OLD=P.parent/'retry_9d1da9a04d564b03bc2b176f5b17ea42'
t=(OLD/'verify_retry.py').read_text()
replacements={
 "transport_2eff7b66442a4322a987fb2f7812268b":"transport_ae4489870e334fefaf4d7d28580708cc",
 "(W,('ab_suite_02','observer_tests_01','integration_tests_02','scan_start_tests_01','multiplex_transport_01'))":"(W,('ab_suite_01','paced_tests_01','four_paced_proxy_01'))",
 "'helper_build_01','source_binding_03'":"'helper_build_02','source_bindings_01'",
 "'final_readonly_02'":"'final_readonly_01'",
 "'shipping_transport_01','scan_start_proxy_01'":"'scan_start_proxy_01'",
 "W/'ab_suite_02.log'":"W/'ab_suite_01.log'",
 "int(found[1])==2148":"int(found[1])==2149",
 "P/'source_bindings_02.json'":"P/'source_bindings_01.json'",
 "s3h_regenerated_retry_02.L5X":"s3h_regenerated_paced_01.L5X",
 "len(proxy['samples'])==20":"len(proxy['samples'])==1000",
 "len(seals)==29 and sum(r['artifacts'] for r in seals)==6885":"len(seals)==31 and sum(r['artifacts'] for r in seals)==7480",
 "abTests=2148":"abTests=2149",
 "qualifiedBaselineProxyCaptures=20":"qualifiedBaselineProxyCaptures=1000",
 "predecessorRecords=29,predecessorArtifacts=6885":"predecessorRecords=31,predecessorArtifacts=7480",
 }
for old,new in replacements.items():
 assert t.count(old)==1,(old,t.count(old))
 t=t.replace(old,new,1)
t=t.replace("imageAndNativeBuildAndCapacityUnchanged=True,", "imageAndNativeBuildAndCapacityUnchanged=True,unchangedEvenWaitSeconds=.001,")
with (P/'verify_retry.py').open('x') as f:f.write(t)
