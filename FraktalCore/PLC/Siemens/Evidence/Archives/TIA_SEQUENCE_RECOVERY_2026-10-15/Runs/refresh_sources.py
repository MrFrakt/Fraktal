import json
import shutil
import sys
from pathlib import Path

repo = Path('C:/Projects/Fraktal')
plc = repo/'FraktalCore/PLC/Siemens'
sys.path.insert(0, str(plc/'tools'))
import fraktal_tia_generate as GEN
import fraktal_tia_declaration as DECL
import fraktal_tia_examples as EX
from fraktal_tia_program_layout import group

work = Path(__file__).resolve().parent
old = plc/'Tests/Generator/generated'
metadata = json.loads((old/'manifest.json').read_bytes())
fresh = work/'shipped/default05'
GEN.generate(DECL.validate(metadata['declaration']), fresh, metadata['shared_runtime'])
for path in fresh.iterdir():
    shutil.copy2(path, old/path.name)
target = plc/'Examples/PressDemo/generated'
source = work/'press05/sources'
sources, _, _ = EX.build()
for name, text in sources.items():
    hits = list(target.rglob(name))
    location = target/group(name, text)/name
    assert not hits or hits == [location], (name, hits, location)
    assert (source/name).read_bytes() == text.encode('ascii'), name
    location.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source/name, location)
shutil.copy2(source/'manifest.json', target/'manifest.json')
shutil.copy2(work/'press05/grouped/layout.json', target/'layout.json')
plan = (work/'press05/grouped/import.plan').read_text('ascii')
plan = plan.replace(str(work/'press05/grouped'), str(target))
(target/'import.plan').write_bytes(plan.encode('ascii'))
print(json.dumps({'default': GEN.verify(old), 'press': EX.verify(target)}))
