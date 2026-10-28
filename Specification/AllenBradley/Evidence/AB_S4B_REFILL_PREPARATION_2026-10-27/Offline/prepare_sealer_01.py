"""Adapt the verified preparation sealer with explicit changed-input checks."""
from pathlib import Path

W=Path(__file__).parent
original=Path('C:/work/fraktal-ab-s4b-busy-witness-20261027/offline_01/seal_preparation_01.py')
source=original.read_text(encoding='utf-8')
def change(old,new,count=1):
    global source
    assert source.count(old)==count,(old,source.count(old),count)
    source=source.replace(old,new)
change('apparatus-only retry over hash-identical shipping/PLC inputs','bounded row-refill retry with explicit HMI changes and unchanged PLC')
change("OLD=Path('C:/work/fraktal-ab-s4b-array-tiers-20261027/session_01')","OLD=Path('C:/work/fraktal-ab-s4b-busy-witness-20261027/session_01')")
change("P=E/'AB_S4B_TIER_QUEUE_PREPARATION_2026-10-27'","P=E/'AB_S4B_BUSY_WITNESS_PREPARATION_2026-10-27'")
change("O=E/'AB_S4B_BUSY_WITNESS_PREPARATION_2026-10-27'","O=E/'AB_S4B_REFILL_PREPARATION_2026-10-27'")
change('6acef0cd97d1c7028cb9098928c3b70da0f5cff2b0748d041cf9f2f9b4eea1ca','e1dab7d72500cef058dc876f9167a0a9db6197e7f181ef7b300df90675c62824')
change('AB_S4B_TIER_QUEUE_ATTEMPT_2026-10-27','AB_S4B_BUSY_WITNESS_ATTEMPT_2026-10-27',2)
change('1226d3062c8e8727cca9834a9ed6e3bb96c834a0757589e06845e4b00b75015b','65c4ee211c89311056efcff3060742fa30ea1028d038301ea0b1643a7fc23051')
change('busy_witness_tests_03','busy_witness_tests_01',2)
change("'authorization_checks_02'","'authorization_checks_01'")
change("'update_status_01','spec_01','contracts_01','consistency_01','root_tests_01','whitespace_01'):",
       "'update_status_01','spec_01','contracts_01','consistency_01','root_tests_01','whitespace_01',\n    'refill_after_03','pub_01','flutter_01','analyze_01','windows_01','focused_01','wire_replay_01','refresh_mirror_01'):")
change("assert previous['candidateCases']==0 and previous['observerSamples']==previous['allGoodSamples']==49",
       "assert previous['candidateCases']==41 and previous['observerSamples']==previous['allGoodSamples']==2805")
change("assert previous['pairedCapturesReplayed']==1 and not previous['nativeAccepted']",
       "assert previous['pairedCapturesReplayed']==87 and previous['loginBusyWitness']['passed'] and not previous['nativeAccepted']")
change("files=set();changed=[];plc_count=0", """mirror=load(W/'isolated_hmi_sources_01.json')
hmi={Path(p) for p in mirror['changed']}
assert len(hmi)==2 and not mirror['added']
copies={Path(row['copy']) for row in mirror['files'] if Path(row['source']) in hmi}
package=Path('C:/work/fraktal-ab-s4b-20261025/hmi_verify_01/.dart_tool/package_config.json')
allowed=docs|hmi|copies|{package}
assert b'668 ~12: All tests passed!' in (W/'flutter_01.log').read_bytes()
assert b'No issues found!' in (W/'analyze_01.log').read_bytes()
assert load(W/'refill_before_02_exit.json')['exitCode']==1
assert b'Actual: <4>' in (W/'refill_before_02.log').read_bytes()
replay=load(W/'wire_replay_01.json')
assert replay['wireReads']==810 and replay['groups']==237 and replay['consumedValues']==976
assert replay['hiddenByClassReads']==0 and not replay['nativeTimingClaim']
files=set();changed=[];plc_count=0""")
change("assert path in docs,'unexpected shipping/input change: '+name","assert path in allowed,'unexpected shipping/input change: '+name")
change("assert set(changed)==docs and plc_count==373\nmirror=load(A/'isolated_hmi_sources_01.json')",
       "assert set(changed)-{package}==docs|hmi|copies and plc_count==373")
change("assert len(names)==102","assert len(names)==104")
change("names.update(('AB_S4B_TIER_QUEUE_PREPARATION_2026-10-27'","names.update(('AB_S4B_BUSY_WITNESS_PREPARATION_2026-10-27'")
change('fraktal.ab.s4b-busy-witness-source-bindings','fraktal.ab.s4b-refill-source-bindings')
change('fraktal.ab.s4b-busy-witness-preparation','fraktal.ab.s4b-refill-preparation')
change('changedHmiFiles=[],addedHmiFiles=[],hmiMirrorInputs=319,sessionOnlyLoginBusyWitness=True,',
       'changedHmiFiles=mirror[\'changed\'],addedHmiFiles=[],hmiMirrorInputs=319,sessionOnlyLoginBusyWitness=True,boundedRowRefill=True,')
change("W/'busy_preparation_report_01.md'","W/'refill_preparation_report_01.md'")
change('flutterTests=665,flutterSkipped=12,busyWitnessTests=14,partTraceTests=6,',
       'flutterTests=668,flutterSkipped=12,busyWitnessTests=14,partTraceTests=6,rowRefillTests=3,focusedTests=56,')
change('changedShippingHmiFiles=0','changedShippingHmiFiles=2',2)
change('changedShippingFiles=0','changedShippingFiles=2')
with (W/'seal_preparation_01.py').open('x',encoding='utf-8',newline='') as stream:stream.write(source)
print('Prepared row-refill sealer; all gate/binding/prior-seal checks precede immutable outputs.')
