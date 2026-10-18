import json
from pathlib import Path
import subprocess
import sys

sys.path.insert(0,str(Path.cwd()/'FraktalCore/PLC/Allen-Bradley/tools'))
import fraktal_ab_native_alarm_probe as probe
from fraktal_ab_readback import compare
from fraktal_ab_sdk_log_gate import audit_log

root=Path('C:/work/fraktal-ab-tag-alarm-20261018')
generation=json.loads((root/'probes_qualified/generation.json').read_text())
reproduced=probe.generate_all(Path('C:/work/echo38_5580_seed.L5X'),root/'reproduced')
assert {r['Case']:r['OutputSha256'] for r in generation['Cases']} == {r['Case']:r['OutputSha256'] for r in reproduced['Cases']}
directories={'almd_st':'compiled_01','invalid_alarm_attribute':'compiled_01',
 'tag_alarm_st':'compiled_final','invalid_tag_alarm_attribute':'compiled_final',
 'invalid_tag_alarm_status_write':'compiled_access',
 'tag_alarm_operator_write_discriminator':'compiled_discriminator'}
rows=[]
for case in generation['Cases']:
    directory=root/directories[case['Case']]
    result=json.loads((directory/'result.json').read_text())
    row=next(r for r in result['Cases'] if r['Case']==case['Case'])
    assert row['ConformsToExpectation'] and row['Imported'] and row['ReadbackEqual']
    assert case['OutputSha256']==row['SourceSha256'] and case['ExpectedBuild']==row['ExpectedBuild']
    for target, build in row['Builds'].items():
        exported=directory/(case['Case']+'_'+target+'_readback.L5X')
        readback=compare(Path(case['Output']),exported)
        assert readback['Equivalent']
        rows.append(dict(Case=case['Case'],Target=target,Expected=case['ExpectedBuild'],
                         Accepted=build['Accepted'],CompilerRejected=build['CompilerRejected'],
                         SourceSha256=case['OutputSha256'],ExportSha256=probe.sha256(exported),
                         Readback=readback))
canonical_source=root/'compiled_final/tag_alarm_st_EchoController_readback.L5X'
canonical=compare(canonical_source,root/'canonical_tag_readback.L5X')
assert canonical['Equivalent']
raw=(root/'canonical_tag.log').read_bytes()
log=raw.decode('utf-16' if raw.startswith(b'\xff\xfe') else 'utf-8-sig')
assert audit_log(log,('Open project','Build','Save As'),require_clean_import=True)['Clean']
assert all(r['MutationRefused'] for r in json.loads((root/'native_metadata_mutations.json').read_text()).values())
assert probe.sha256(root/'probes_qualified/almd_st.L5X')=='223490BCD183AF1D1DCC9F2D4B020A6200B727719EA54EB17199ACB753A7DC6B'
assert probe.sha256(root/'probes_qualified/invalid_alarm_attribute.L5X')=='32FC4DCE2EB6A276C5CD6EE3DBA39A554B057A427303AC70264B68B976A6D48E'
results=dict(Schema='fraktal.ab.tag-alarm-closure',SchemaVersion=1,Complete=True,
             ControllerWrites=0,RuntimeAccepted=False,ProductionAlarmOwnerChanged=False,
             ReproductionEqual=True,OriginalAlmdUnchanged=True,Cases=rows,CanonicalReadback=canonical)
(root/'closure.json').write_text(json.dumps(results,indent=2)+'\n',encoding='utf-8')
print('Expected outcomes and read-back verified:',len(rows),'builds; canonical round trip equal.')
