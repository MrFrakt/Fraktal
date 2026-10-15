"""Native load-memory instruction gate on a copy of the qualified runtime."""
import argparse
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / 'tools'))
from fraktal_tia_generate import db
from fraktal_tia_binding import PRIVATE, READONLY


def prepare(out, baseline):
    out.mkdir(parents=True, exist_ok=False)
    for p in sorted(baseline.iterdir()):
        if p.suffix in ('.scl', '.udt', '.db'):
            (out / p.name).write_bytes(p.read_bytes())
    for name in ('GDB_LoadSource', 'GDB_LoadBankA', 'GDB_LoadBankB', 'GDB_LoadRead'):
        (out / ('06_' + name + '.db')).write_bytes(db(name, [
            'Payload' + PRIVATE + ' : Array[0..63] of Byte;'
        ]).encode('ascii'))
    (out / '06_GDB_LoadMemoryTest.db').write_bytes(db('GDB_LoadMemoryTest', [
        'Kind : Int;', 'Seed : Byte;', 'Sequence : UDInt;',
        'AckSequence' + READONLY + ' : UDInt;', 'Accepted' + READONLY + ' : Bool;',
        'Busy' + READONLY + ' : Bool;', 'NativeStatus' + READONLY + ' : Word;',
        'BusyScans' + READONLY + ' : UDInt;',
        'FirstByte' + READONLY + ' : Byte;', 'LastByte' + READONLY + ' : Byte;',
        'ReadCrc' + READONLY + ' : DWord;',
        'BankAWorkByte' + READONLY + ' : Byte;', 'BankBWorkByte' + READONLY + ' : Byte;',
        'PendingKind' + PRIVATE + ' : Int;', 'RequestPulse' + PRIVATE + ' : Bool;',
        'SeenSequence' + PRIVATE + ' : UDInt;',
    ]).replace('END_VAR\nBEGIN', 'END_VAR\nVAR RETAIN\n    StartupCount' + READONLY + ' : UDInt;\nEND_VAR\nBEGIN').encode('ascii'))
    (out / '39f_LoadMemoryBench.scl').write_bytes((HERE / 'bench.scl.in').read_bytes())
    p = out / '38_ConfigBenchRoutines.scl'
    text = p.read_text('ascii')
    anchor = '    "F_ConfigSetBench"();'
    assert text.count(anchor) == 1
    text = text.replace(anchor, '    "F_LoadMemoryBench"(Startup := #Startup);\n' + anchor)
    p.write_bytes(text.encode('ascii'))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('out', type=Path)
    parser.add_argument('baseline', type=Path)
    args = parser.parse_args()
    prepare(args.out, args.baseline)
