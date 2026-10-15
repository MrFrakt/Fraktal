"""Check native shared-source/access witnesses and the generated GRAPH object."""
import importlib.util
import json
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]/'tools'))
import fraktal_tia_graph as GRAPH


def verify(work):
    spec = importlib.util.spec_from_file_location('native_exports', HERE.parent/'Generator/verify_exports.py')
    exports = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(exports)
    witness = work/'witness'
    witness.mkdir()
    for path in (work/'sources').iterdir():
        if path.suffix in ('.scl', '.udt') or path.name == '08_GDB_RecoveryTest.db':
            shutil.copy2(path, witness/path.name)
    result = exports.verify(witness, work/'native')
    expected = GRAPH.dump((work/'sources/27_FB_GRAPH_RecoveryTest.xml').read_text('ascii'))
    actual = GRAPH.dump((work/'native/xml/FB_GRAPH_RecoveryTest.xml').read_text('utf-8-sig'))
    assert actual == expected, 'native GRAPH object differs'
    result['graph'] = actual
    with (work/'native_readback.json').open('x', encoding='ascii') as stream:
        json.dump(result, stream, indent=2); stream.write('\n')
    print(json.dumps({'sources': len(result['sources']), 'interfaces': len(result['interfaces']),
                      'graph_steps': len(actual['steps']), 'graph_edges': len(actual['edges'])}))


if __name__ == '__main__':
    verify(Path(sys.argv[1]))
