import json
from pathlib import Path
import sys
from xml.dom import minidom

sys.path.insert(0, str(Path.cwd()/'FraktalCore/PLC/Allen-Bradley/tools'))
from fraktal_ab_readback import compare

root = Path('C:/work/fraktal-ab-tag-alarm-20261018')
source = root/'probes_01/tag_alarm_st.L5X'
native = root/'compiled_01/tag_alarm_st_EchoController_readback.L5X'
assert compare(source,native)['Equivalent']
results = {}
for field,value in [('Expression','= 0'),('OnDelay','1000'),('OffDelay','1000'),
                    ('AlarmSetOperIncluded','true'),('AssocTag1','FRK_NativeAlarmSource'),
                    ('Severity','900'),('Message','Changed message'),('MessageSpaces',' Fraktal native projection probe')]:
    with minidom.parse(str(native)) as document:
        alarm = document.getElementsByTagName('AlarmCondition')[0]
        if field.startswith('Message'):
            text = alarm.getElementsByTagName('Text')[0]
            next(node for node in text.childNodes if node.nodeType == node.CDATA_SECTION_NODE).data = value
        else:
            alarm.setAttribute(field,value)
        changed = root/('mutated_'+field+'.L5X')
        assert not changed.exists()
        changed.write_text(document.toxml(),encoding='utf-8')
    result=compare(source,changed)
    assert result['Inventory']['Equivalent'] and not result['ExecutableDifferences']
    assert result['AlarmDifferences'] and not result['Equivalent']
    results[field]=dict(MutationRefused=True,AlarmDifferences=result['AlarmDifferences'])
(root/'native_metadata_mutations.json').write_text(json.dumps(results,indent=2)+'\n',encoding='utf-8')
print('Actual native-export metadata mutations refused:',len(results))
