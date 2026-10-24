"""Replay recorded S0 bytes through the repaired reader; no controller access."""
import hashlib
import json
from pathlib import Path
import struct
import sys
from types import SimpleNamespace

sys.path.insert(0, 'C:/Users/SoftIndVM/Fraktal/FraktalCore/PLC/Allen-Bradley/tools')
import fraktal_ab_s0_canonical_measure as measure

capture_path, generation_path, output = map(Path, sys.argv[1:])
if output.exists():
    raise SystemExit('refusing existing replay report')
capture = json.loads(capture_path.read_text(encoding='utf-8'))
generation = json.loads(generation_path.read_text(encoding='utf-8'))
by_handle = {}
for name, template in capture['templates'].items():
    fields = []
    for row in template['members']:
        definition = struct.pack('<HHI', row['info'], row['code'], row['offset'])
        assert definition.hex() in template['rawMemberDefinitions']
        fields.append(SimpleNamespace(TagName=row['name'], DataType=row['typeName'], Bytes=definition))
    by_handle[template['handle']] = SimpleNamespace(Type=template['handle'], Name=name, Fields=fields)
root = next(u for u in by_handle.values() if u.Name == measure.RECORD)
rows = measure.member_table(root)
raw = bytes.fromhex(capture['rawHex'])
assert len(raw) == capture['recordBytes']
decoded = measure.decode(raw, 0, rows, by_handle, len(raw))
checks = measure.compare(generation['Cases'][0]['Expected'], decoded, rows)
report = dict(schema='fraktal.ab.s0-canonical-measurement-replay', schemaVersion=1,
              sourceCapture=str(capture_path), sourceCaptureSha256=hashlib.sha256(capture_path.read_bytes()).hexdigest().upper(),
              readOnly=True, recordBytes=len(raw), template=rows, decoded=decoded, checks=checks,
              allEqual=all(c['equal'] for c in checks), findings=[c for c in checks if not c['equal']])
with output.open('x', encoding='utf-8') as stream:
    json.dump(report, stream, indent=2)
    stream.write('\n')
print(json.dumps(dict(checks=len(checks), equal=sum(c['equal'] for c in checks), findings=report['findings'])))
