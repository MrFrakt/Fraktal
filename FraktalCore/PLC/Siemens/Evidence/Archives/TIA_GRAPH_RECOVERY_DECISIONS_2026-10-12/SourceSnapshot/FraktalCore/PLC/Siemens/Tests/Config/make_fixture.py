"""Editable station/model config with the measured local-retain provider."""
import argparse
import importlib.util
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('state_fixture', HERE.parent / 'StateAlarm/make_fixture.py')
STATE = importlib.util.module_from_spec(spec)
spec.loader.exec_module(STATE)


def declaration():
    value = STATE.declaration()
    value['model_config'] = {'models': ['MODEL_A', 'MODEL_B'], 'initial': 'MODEL_A'}
    value['records']['ST_DeclarationParCfg'] = 'STRUCT SchemaVersion : UINT := 4; Timeout : TIME := T#8s; Preset : DINT := 10; END_STRUCT'
    value['records']['ST_UnitProbeStationCfg'] = "STRUCT SchemaVersion : UINT := 1; SiteLabel : STRING(80) := 'bench'; Enabled : BOOL := TRUE; END_STRUCT"
    for t in value['types']:
        t['config'] = [
            {'member': 'ParCfg.Timeout', 'key': 'timeout', 'revision': 1, 'label': 'test.config.timeout', 'minimum': 1, 'maximum': 60000},
            {'member': 'ParCfg.Preset', 'key': 'preset', 'revision': 2, 'label': 'test.config.preset', 'minimum': 0, 'maximum': 1000, 'min_write': 1},
        ]
        if 'unit' in t:
            t['station_config'] = 'ST_UnitProbeStationCfg'
            t['config'] += [
                {'member': 'StationCfg.SiteLabel', 'key': 'siteLabel', 'revision': 1, 'label': 'test.config.siteLabel', 'requires_ready': False, 'min_write': 1},
                {'member': 'StationCfg.Enabled', 'key': 'enabled', 'revision': 1, 'label': 'test.config.enabled', 'requires_ready': False},
            ]
    return value


def prepare(out, frames):
    STATE.prepare(out, frames, declaration())
    import fraktal_tia_generate as GEN
    from fraktal_tia_binding import READONLY, PRIVATE
    # Test-only retained-image corruption and store availability switches.
    (out / '05_GDB_ConfigTest.db').write_bytes(GEN.db('GDB_ConfigTest', [
        'Unavailable : Bool;', 'CorruptPulse : Bool;',
        'CorruptScope : String[80];', 'CorruptKey : String[160];', 'CorruptModel : String[64];',
        'CorruptText : String[80];', 'CorruptSchema : UInt;',
        'CorruptSlot'+READONLY+' : Int;', 'ConfiguredPulse : Bool;',
    ]).replace('END_VAR\nBEGIN', 'END_VAR\nVAR RETAIN\n    BlockRestore : Bool;\nEND_VAR\nBEGIN').encode('ascii'))
    path = out / '40_Main.scl'
    text = path.read_text('ascii')
    # The old control bench adjusts a timeout cyclically. This config bench uses
    # its declared config/defaults and the acknowledged owner handler only.
    text, removed = re.subn(r'^.*\.ParCfg\.Timeout\s*:=.*\n', '', text, flags=re.M)
    assert removed == 1
    anchor = '    "GDB_FraktalMain"(Startup := #Initial_Call);'
    assert text.count(anchor) == 1
    wiring = '''    "FRK_ConfigRuntime".Unavailable := "GDB_ConfigTest".Unavailable;
    IF "GDB_ConfigTest".BlockRestore THEN "StationA".ConfigPersist.RestorePolicy := 1;
    ELSE "StationA".ConfigPersist.RestorePolicy := 0; END_IF;
    IF "GDB_ConfigTest".CorruptPulse THEN
        "GDB_ConfigTest".CorruptSlot := "FRK_ConfigFind"(Scope := "GDB_ConfigTest".CorruptScope, Key := "GDB_ConfigTest".CorruptKey, ModelCode := "GDB_ConfigTest".CorruptModel);
        IF "GDB_ConfigTest".CorruptSlot > 0 THEN
            "FRK_ConfigStore".Rows["GDB_ConfigTest".CorruptSlot].SchemaVersion := "GDB_ConfigTest".CorruptSchema;
            "FRK_ConfigStore".Rows["GDB_ConfigTest".CorruptSlot].Record.ValueText := "GDB_ConfigTest".CorruptText;
        END_IF;
        "GDB_ConfigTest".CorruptPulse := FALSE;
    END_IF;
'''
    text = text.replace(anchor, wiring + anchor)
    from fraktal_tia_program_layout import split_main
    main, routines = split_main(text)
    path.write_bytes(main.encode('ascii'))
    (out / '38_ConfigBenchRoutines.scl').write_bytes(routines.encode('ascii'))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('out', type=Path); parser.add_argument('frames', type=Path)
    args = parser.parse_args(); prepare(args.out, args.frames)
