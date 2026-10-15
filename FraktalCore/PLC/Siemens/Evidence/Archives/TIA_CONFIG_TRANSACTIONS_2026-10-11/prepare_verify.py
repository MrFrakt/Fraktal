"""Separate native reimport and production compiler image; no PLC download."""
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import sys

repo = Path('C:/Projects/Fraktal'); work = Path(__file__).resolve().parent
stations = work.parents[1] / 'TiaStations'
source = stations / 'Config_Runtime_20261011/FrkS12'
target = stations / 'Config_Verify_20261011/FrkS12'
assert source.is_dir() and not target.exists()
shutil.copytree(source, target)
checks = {}
for path in source.rglob('*'):
    if not path.is_file(): continue
    relative = path.relative_to(source)
    checksum = hashlib.sha256(path.read_bytes()).hexdigest()
    assert hashlib.sha256((target / relative).read_bytes()).hexdigest() == checksum
    checks[relative.as_posix()] = checksum
(work / '39_verify_project_copy.json').write_bytes((json.dumps(checks, indent=2)+'\n').encode('ascii'))
spec = importlib.util.spec_from_file_location('ordering', repo / 'FraktalCore/PLC/Siemens/Tests/Generator/prepare_roundtrip.py')
order = importlib.util.module_from_spec(spec); spec.loader.exec_module(order)
order.prepare(work/'package_v6', work/'export_v6', work/'native_ordered')
sys.path.insert(0, str(repo/'FraktalCore/PLC/Siemens/tools'))
import fraktal_tia_generate as gen
spec = importlib.util.spec_from_file_location('fixture', repo/'FraktalCore/PLC/Siemens/Tests/Config/make_fixture.py')
fixture = importlib.util.module_from_spec(spec); spec.loader.exec_module(fixture)
value = fixture.declaration(); value.pop('event_sink')
gen.generate(gen.DECL.validate(value), work/'production', True)
for number, package, export in (('40_roundtrip', 'native_ordered', 'export_roundtrip'), ('41_production', 'production', 'export_production')):
    lines = ['open-project --path "'+str(target/'FrkS12.ap20')+'"',
             'delete-blocks --plc PLC_1', 'import-sources --plc PLC_1 --dir "'+str(work/package)+'"',
             'compile --plc PLC_1', 'export --plc PLC_1 --out "'+str(work/export)+'" --scl true', 'save']
    (work/(number+'.plan')).write_bytes(('\n'.join(lines)+'\n').encode('ascii'))
