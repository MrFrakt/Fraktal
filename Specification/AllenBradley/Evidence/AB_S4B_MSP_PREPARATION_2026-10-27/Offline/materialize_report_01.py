from pathlib import Path
import json
W=Path(__file__).parent
q=json.loads((W/'wire_replay_01.json').read_bytes())
assert q['passed'] and q['packetRequests']==711 and q['wireReads']==810 and q['consumedValues']==976
assert q['groups']==237 and not q['nativeTimingClaim']
text=(W/'msp_preparation_report_01.template.md').read_text(encoding='utf-8')
for marker,value in {'@PACKETS@':q['packetRequests'],'@READS@':q['wireReads']}.items():
    assert text.count(marker)==1
    text=text.replace(marker,str(value))
with (W/'msp_preparation_report_01.md').open('x',encoding='utf-8',newline='') as stream:stream.write(text)
print('Final preparation report materialized from verified replay counts.')
