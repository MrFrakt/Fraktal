"""Typed config and current exports on the qualified LOAD_DB consumer bench."""
import argparse
import importlib.util
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('persist_fixture', HERE.parent/'Persistence/make_fixture.py')
PERSIST = importlib.util.module_from_spec(spec)
spec.loader.exec_module(PERSIST)


def declaration():
    value = PERSIST.RECOVERY.HISTORY.ACCESS.SETS.CONFIG.declaration()
    value['persistence'] = {'medium': 'LOAD_DB', 'minimum_write_ms': 1000, 'queue_capacity': 4}
    value['records']['ST_UnitProbeStationCfg'] = value['records']['ST_UnitProbeStationCfg'].replace(
        'SchemaVersion : UINT := 1', 'SchemaVersion : UINT := 3').replace('END_STRUCT',
        'Ratio : LREAL := 1.25; Gain : REAL := 2.5; Grade : E_Mode := E_Mode.MANUAL; '
        'Offsets : ARRAY[-1..1] OF INT; Small : USINT := 7; END_STRUCT')
    for module in value['types']:
        if 'unit' in module:
            module['config'] += [
                {'member': 'StationCfg.Ratio', 'key': 'ratio', 'revision': 1, 'label': 'test.config.preset', 'minimum': -1000000, 'maximum': 1000000},
                {'member': 'StationCfg.Gain', 'key': 'gain', 'revision': 1, 'label': 'test.config.preset', 'minimum': -1000, 'maximum': 1000},
                {'member': 'StationCfg.Grade', 'key': 'grade', 'revision': 1, 'label': 'test.config.preset'},
                *[{'member': 'StationCfg.Offsets[%d]'%i, 'key': 'offset.%d'%i, 'revision': 1, 'label': 'test.config.preset'} for i in range(-1, 2)],
                {'member': 'StationCfg.Small', 'key': 'small', 'revision': 1, 'label': 'test.config.preset'},
            ]
    return value


def prepare(out, frames):
    PERSIST.RECOVERY.prepare(out, frames, declaration())
    PERSIST.add_controls(out, frames)
    from fraktal_tia_binding import Catalog
    diagnostic = (HERE/'numeric_debug.scl.in').read_text('ascii').replace(
        '@AS_LREAL@', str(Catalog.read().enums['E_ConfigStorage']['AS_LREAL']))
    (out/'37_ConfigNumericTest.scl').write_bytes(diagnostic.encode('ascii'))
    path = out/'38_ConfigBenchRoutines.scl'
    before, after = path.read_text('ascii').rsplit('END_FUNCTION', 1)
    path.write_bytes((before+'    "F_ConfigNumericTest"();\nEND_FUNCTION'+after).encode('ascii'))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('out', type=Path)
    parser.add_argument('frames', type=Path)
    args = parser.parse_args()
    prepare(args.out, args.frames)
