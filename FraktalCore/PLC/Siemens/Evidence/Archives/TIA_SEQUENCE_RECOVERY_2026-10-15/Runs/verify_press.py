import importlib.util, json, shutil, sys
from pathlib import Path
repo = Path('C:/Projects/Fraktal')
plc = repo/'FraktalCore/PLC/Siemens'
sys.path.insert(0, str(plc/'tools'))
import fraktal_tia_examples as EX
spec = importlib.util.spec_from_file_location('exports', plc/'Tests/Generator/verify_exports.py')
exports = importlib.util.module_from_spec(spec); spec.loader.exec_module(exports)
work = Path(__file__).resolve().parent/'press05'
witness = work/'witness'; witness.mkdir()
for path in (work/'sources').iterdir():
    if path.suffix in ('.scl', '.udt') and not path.name.startswith(('23_', '28_')):
        shutil.copy2(path, witness/path.name)
result = exports.verify(witness, work/'native')
result['graphs'] = EX.verify(work/'sources', work/'native')
with (work/'native_readback.json').open('x', encoding='ascii') as stream:
    json.dump(result, stream, indent=2); stream.write('\n')
print(json.dumps({'sources': len(result['sources']), 'interfaces': len(result['interfaces']), 'graphs': result['graphs']}))
