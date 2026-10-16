"""Production line composition over the existing typed LOAD_DB bench."""
import argparse
import importlib.util
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]/'tools'))
spec = importlib.util.spec_from_file_location('line_kernel_fixture', HERE/'make_fixture.py')
LINE = importlib.util.module_from_spec(spec)
spec.loader.exec_module(LINE)

spec = importlib.util.spec_from_file_location('config_types_fixture', HERE.parent/'ConfigTypes/make_fixture.py')
CONFIG = importlib.util.module_from_spec(spec)
spec.loader.exec_module(CONFIG)


def declaration():
    value = CONFIG.declaration()
    value['records'][LINE.RECORD[0]] = LINE.RECORD[1]
    value['line'] = LINE.declaration()
    return value


def prepare(out, frames):
    CONFIG.PERSIST.RECOVERY.prepare(out, frames, declaration())
    CONFIG.PERSIST.add_controls(out, frames)
    from fraktal_tia_binding import READONLY
    from fraktal_tia_config import function
    from fraktal_tia_generate import db
    (out/'06_GDB_LineOwnerTest.db').write_bytes(db('GDB_LineOwnerTest', [
        'PoisonPulse : Bool;', 'Poisoned'+READONLY+' : Bool;',
        'BootDefaultSeen'+READONLY+' : Bool;', 'BootDefaultValue'+READONLY+' : UDInt;',
        'WorkingTaktMs'+READONLY+' : UDInt;',
    ]).encode('ascii'))
    body = ['    IF #Startup THEN "GDB_LineOwnerTest".BootDefaultSeen := FALSE; END_IF;',
            '    IF "FRK_PersistStatus".Restoring AND NOT "GDB_LineOwnerTest".BootDefaultSeen THEN',
            '        "GDB_LineOwnerTest".BootDefaultValue := "FRK_Line".Data.Values.TaktMs;',
            '        "GDB_LineOwnerTest".BootDefaultSeen := TRUE;', '    END_IF;',
            '    IF "GDB_LineOwnerTest".PoisonPulse THEN',
            '        "FRK_Line".Data.Values.TaktMs := 99999;',
            '        "GDB_LineOwnerTest".PoisonPulse := FALSE;',
            '        "GDB_LineOwnerTest".Poisoned := TRUE;', '    END_IF;',
            '    "GDB_LineOwnerTest".WorkingTaktMs := "FRK_Line".Data.Values.TaktMs;']
    (out/'37_LineOwnerObserve.scl').write_bytes(function('F_LineOwnerObserve', ['Startup : Bool;'], [], [], body).encode('ascii'))
    path = out/'38_ConfigBenchRoutines.scl'
    text = path.read_text('ascii')
    anchor = 'FUNCTION "F_ConfigBenchObserve"'
    before, after = text.split(anchor)
    pos = after.index('END_FUNCTION')
    after = after[:pos]+'    "F_LineOwnerObserve"(Startup := #Startup);\n'+after[pos:]
    path.write_bytes((before+anchor+after).encode('ascii'))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('out', type=Path)
    parser.add_argument('frames', type=Path)
    args = parser.parse_args()
    prepare(args.out, args.frames)
