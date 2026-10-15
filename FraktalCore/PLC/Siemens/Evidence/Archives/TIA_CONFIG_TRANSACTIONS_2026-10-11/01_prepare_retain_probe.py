"""Copy the preserved station and add a separate native retentivity probe."""
import hashlib
import json
from pathlib import Path
import shutil

work = Path(__file__).resolve().parent
previous = work.parent / 'State_Alarm_20261011'
stations = work.parents[1] / 'TiaStations'
source = stations / 'Alarm_Runtime_20261011/FrkS12'
dest = stations / 'Config_Runtime_20261011/FrkS12'
assert source.is_dir() and not dest.exists()
shutil.copytree(source, dest)
rows = []
for path in sorted(source.rglob('*')):
    if not path.is_file():
        continue
    relative = path.relative_to(source)
    checksum = hashlib.sha256(path.read_bytes()).hexdigest()
    assert hashlib.sha256((dest / relative).read_bytes()).hexdigest() == checksum
    rows.append({'path': relative.as_posix(), 'sha256': checksum})
(work / '01_project_copy.json').write_bytes((json.dumps(rows, indent=2) + '\n').encode('ascii'))
package = work / 'retain_probe'
shutil.copytree(previous / 'package_v4', package)
db = '''DATA_BLOCK "GDB_RetainProbe"
{ S7_Optimized_Access := 'TRUE' }
VERSION : 0.1
NON_RETAIN
VAR RETAIN
    Saved { ExternalWritable := 'False' } : DInt;
    Hidden { ExternalAccessible := 'False'; ExternalVisible := 'False'; ExternalWritable := 'False' } : DInt;
END_VAR
VAR
    WritePulse : Bool;
    Proposed : DInt;
    Live { ExternalWritable := 'False' } : DInt;
END_VAR
BEGIN
END_DATA_BLOCK
'''
(package / '05_GDB_RetainProbe.db').write_bytes(db.encode('ascii'))
main = package / '40_Main.scl'
text = main.read_text('ascii')
anchor = '    "GDB_FraktalMain"(Startup := #Initial_Call);'
assert text.count(anchor) == 1
text = text.replace(anchor, '''    IF "GDB_RetainProbe".WritePulse THEN
        "GDB_RetainProbe".Saved := "GDB_RetainProbe".Proposed;
        "GDB_RetainProbe".Hidden := "GDB_RetainProbe".Proposed;
        "GDB_RetainProbe".WritePulse := FALSE;
    END_IF;
    "GDB_RetainProbe".Live := "GDB_RetainProbe".Hidden;
''' + anchor)
main.write_bytes(text.encode('ascii'))
plan = '\n'.join([
    'open-project --path "' + str(dest / 'FrkS12.ap20') + '"',
    'import-sources --plc PLC_1 --dir "' + str(package) + '" --only 05_GDB_RetainProbe,40_',
    'save', 'compile --plc PLC_1', 'compile --plc PLC_1 --hw true',
    'export --plc PLC_1 --out "' + str(work / 'export_retain') + '" --scl true', 'save', '',
])
(work / '02_retain_build.plan').write_bytes(plan.encode('ascii'))
print(json.dumps({'project': str(dest / 'FrkS12.ap20'), 'copied_files': len(rows)}))
