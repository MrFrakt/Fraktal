"""Manifest bench: existing nested forest with one test-only data-read gate."""
import argparse
import importlib.util
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('routing_fixture', HERE.parent/'UnitRouting/make_fixture.py')
ROUTING = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ROUTING)


def prepare(out, frames, declaration=None):
    ROUTING.prepare(out, frames, declaration)
    import fraktal_tia_generate as GEN
    (out/'05_GDB_ManifestTest.db').write_bytes(GEN.db('GDB_ManifestTest', ['ReadLock : Bool;']).encode('ascii'))
    path = out/'40_Main.scl'
    text = path.read_text(encoding='ascii')
    anchor = '    "GDB_FraktalMain"(Startup := #Initial_Call);'
    assert text.count(anchor) == 1
    text = text.replace(anchor, '''    IF "GDB_ManifestTest".ReadLock THEN "StationA".Access.Policy.Required[0] := 3; ELSE "StationA".Access.Policy.Required[0] := 0; END_IF;
''' + anchor)
    path.write_bytes(text.encode('ascii'))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('out', type=Path)
    parser.add_argument('frames', type=Path)
    args = parser.parse_args()
    prepare(args.out, args.frames)
