"""One-time hashed provisioning on the config/set/decision simulator bench."""
import argparse
import importlib.util
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('sets_fixture', HERE.parent/'ConfigSets/make_fixture.py')
SETS = importlib.util.module_from_spec(spec)
spec.loader.exec_module(SETS)


def prepare(out, frames, value=None):
    SETS.prepare(out, frames, value)
    from fraktal_tia_generate import db
    from fraktal_tia_binding import PRIVATE, READONLY
    path = out/'38_ConfigBenchRoutines.scl'
    text = path.read_text('ascii')
    start = text.index('        "FRK_LocalUsers".Count := 2;')
    end = text.index('        "StationA".Access.Policy.Required', start)
    provision = text[start:end]
    text = text[:start] + '''        IF NOT "FRK_AccessStorage".UsersCommissioned AND "FRK_LocalUsers".SchemaVersion = 0 AND "FRK_LocalUsers".Generation = 0 AND "FRK_LocalUsers".Checksum = DWORD#0 THEN
            "F_AccessBenchProvision"();
        END_IF;
''' + text[end:]
    anchor = '    "F_ConfigSetBench"();'
    assert text.count(anchor) == 1
    text = text.replace(anchor, anchor+'\n    "F_AccessPersistenceBench"(Startup := #Startup);')
    # An explicit test-only engineering repair restores the known hashed table.
    function = '\n'.join(['FUNCTION "F_AccessBenchProvision" : Void',
        "{ S7_Optimized_Access := 'TRUE' }", 'VERSION : 0.1', 'BEGIN',
        provision, '    "GDB_AccessPersistTest".ProvisionCount := "GDB_AccessPersistTest".ProvisionCount + 1;',
        'END_FUNCTION', ''])
    path.write_bytes((function+text).encode('ascii'))
    (out/'05_GDB_AccessPersistTest.db').write_bytes(db('GDB_AccessPersistTest',[
        'Operation : Int;', 'Value : DInt;', 'Gate : Int;', 'RotateOnLogin : Bool;',
        'Root : String[32];', 'Applied'+READONLY+' : Bool;',
        'UsersReady'+READONLY+' : Bool;', 'UsersLost'+READONLY+' : Bool;',
        'UserGeneration'+READONLY+' : UDInt;',
        'CrcWitness'+READONLY+' : DWord;', 'Record'+PRIVATE+' : "ST_UserRecord";',
        'PolicySlot'+PRIVATE+' : Int;',
    ]).replace('END_VAR\nBEGIN','END_VAR\nVAR RETAIN\n    ProvisionCount'+READONLY+' : UDInt;\n    StartupCount'+READONLY+' : UDInt;\nEND_VAR\nBEGIN').encode('ascii'))
    (out/'39b_AccessPersistenceBench.scl').write_bytes((HERE/'bench.scl.in').read_bytes())


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('out', type=Path)
    parser.add_argument('frames', type=Path)
    args = parser.parse_args()
    prepare(args.out, args.frames)
