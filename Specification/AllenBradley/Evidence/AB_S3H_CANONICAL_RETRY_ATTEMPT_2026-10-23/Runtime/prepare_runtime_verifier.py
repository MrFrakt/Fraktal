from pathlib import Path
R=Path(__file__).parent
prior=R.parent/'runtime_6cf76ecb8785463ab372c202e79f03f2'
t=(prior/'verify_runtime.py').read_text()
def replace(old,new):
    global t
    assert t.count(old)==1,(old,t.count(old))
    t=t.replace(old,new,1)
replace('prepare_5822102a73e348ec95ff7082959ef940','retry_9d1da9a04d564b03bc2b176f5b17ea42')
replace("    'focused_tool_fix_01','ab_tool_fix_01','root_tool_fix_01','spec_tool_fix_01','contracts_tool_fix_01','consistency_tool_fix_01',\n    'whitespace_tool_fix_01','tooling_validation_01','prepare_offline_audits_01','preflight_before_download_01',",
        "    'prepare_offline_audits_01','preflight_before_download_01',")
replace("R/'tooling_validation_01.json'","R/'initial_source_verification.json'")
t=t.replace('157','159').replace('2140','2148').replace('inputs[\'preparedSourceSha256\']',"prepared['sourceSha256']")
replace("inputs=json.loads((R/'initial_source_verification.json').read_text());assert inputs['passed'] and inputs['sourceBindings']==159",
        "inputs=json.loads((R/'initial_source_verification.json').read_text());assert inputs['passed'] and inputs['sourceBindings']==159\nprepared=json.loads((P/'retry_verification_01.json').read_text())")
replace("        correctedBeforeDownload=inputs['changedFromPreparation'],sha256=inputs['sha256']),f,indent=2)",
        "        observerChangesQualifiedBeforeRetry=True,sha256=inputs['sha256']),f,indent=2)")
replace("assert len(seals)==28 and sum(row['artifacts'] for row in seals)==6589",
        "assert len(seals)==30 and sum(row['artifacts'] for row in seals)==7199")
replace("allNativeSessionSourcesUnchanged=True,correctedBeforeDownload=inputs['changedFromPreparation'],",
        "allNativeSessionSourcesUnchanged=True,observerChangesQualifiedBeforeRetry=True,")
replace("priorSeals=seals,predecessorRecords=28,predecessorArtifacts=6589)",
        "priorSeals=seals,predecessorRecords=30,predecessorArtifacts=7199)")
replace("rootTests=74,focusedTests=13,","rootTests=74,")
with (R/'verify_runtime.py').open('x',encoding='utf-8') as f:f.write(t)
