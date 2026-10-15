"""Native authentication bench: private hashed provisioning, no embedded PINs."""
import argparse
import hashlib
import importlib.util
import os
from pathlib import Path
import secrets

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('manifest_fixture', HERE.parent/'Manifest/make_fixture.py')
MANIFEST = importlib.util.module_from_spec(spec)
spec.loader.exec_module(MANIFEST)


def prepare(out, frames):
    MANIFEST.prepare(out, frames)
    import fraktal_tia_generate as GEN
    from fraktal_tia_access import rounds
    from fraktal_tia_binding import READONLY, Catalog
    (out/'05_GDB_AccessTest.db').write_bytes(GEN.db('GDB_AccessTest', [
        'ProviderOff : Bool;',
        'CancelOnLogin : Bool;', 'SupersedeOnLogin : Bool;',
        'InterruptedBusy'+READONLY+' : Bool;', 'SupersededSequence'+READONLY+' : UDInt;',
        'InterruptRequest'+GEN.PRIVATE+' : "ST_HmiRequest";',
        'HashData'+GEN.PRIVATE+' : Array[0..47] of Byte;',
        *['Hash%d'%i+READONLY+' : Array[0..31] of Byte;' for i in range(4)],
        'HashOk'+READONLY+' : Bool;',
    ]).encode('ascii'))
    path = out/'40_Main.scl'
    text = path.read_text(encoding='ascii')
    for line in (
        '    IF "GDB_UnitTest".LockStart THEN "StationA".Access.Policy.Required[5] := 3; ELSE "StationA".Access.Policy.Required[5] := 0; END_IF;\n',
        '    IF "GDB_RoutingTest".ManualAccessLock THEN "StationA".Access.Policy.Required[2] := 3; ELSE "StationA".Access.Policy.Required[2] := 0; END_IF;\n',
        '    IF "GDB_ManifestTest".ReadLock THEN "StationA".Access.Policy.Required[0] := 3; ELSE "StationA".Access.Policy.Required[0] := 0; END_IF;\n',
    ):
        assert text.count(line) == 1
        text = text.replace(line, '')
    anchor = '    IF #Initial_Call THEN\n'
    assert text.count(anchor) == 1
    setup = ['        "FRK_LocalUsers".Count := 2;']
    for slot, (user, role, env) in enumerate((('operator',1,'FRAKTAL_TIA_OPERATOR_PIN'), ('admin',4,'FRAKTAL_TIA_ADMIN_PIN')), 1):
        secret = os.environ[env].encode('ascii')
        if not 1 <= len(secret) <= 32:
            raise ValueError('PIN width outside Core contract')
        salt = secrets.token_bytes(16)
        digest = hashlib.sha256(salt+secret).digest()
        for _ in range(rounds()):
            digest = hashlib.sha256(digest+salt).digest()
        setup += ['        "FRK_LocalUsers".Rows[%d].User := \'%s\';'%(slot,user),
                  '        "FRK_LocalUsers".Rows[%d].Level := %d;'%(slot,role)]
        for field, values in (('Salt',salt), ('PinHash',digest)):
            setup.extend('        "FRK_LocalUsers".Rows[%d].%s[%d] := BYTE#16#%02X;'%(slot,field,i,v) for i,v in enumerate(values))
    for root in ('StationA','StationB'):
        for gate, role in ((2,1),(4,1),(5,1),(8,4)):
            setup.append('        "%s".Access.Policy.Required[%d] := %d;'%(root,gate,role))
        setup.append('        "%s".Access.Policy.SessionTimeout := T#0ms;'%root)
    for size, number in ((0,0),(3,1),(32,2),(48,3)):
        for i in range(48):
            value = b'abc'[i] if size == 3 and i < 3 else i if size != 3 else 0
            setup.append('        "GDB_AccessTest".HashData[%d] := BYTE#16#%02X;'%(i,value))
        setup.append('        "GDB_AccessTest".HashOk := "FRK_Sha256Pin"(Data := "GDB_AccessTest".HashData, Size := %d, Digest := "GDB_AccessTest".Hash%d);'%(size,number))
    text = text.replace(anchor, anchor+'\n'.join(setup)+'\n')
    anchor = '    "GDB_FraktalMain"(Startup := #Initial_Call);'
    assert text.count(anchor) == 1
    text = text.replace(anchor, '\n'.join('    "%s".Access.ProviderEnabled := NOT "GDB_AccessTest".ProviderOff;'%root for root in ('StationA','StationB'))+'\n'+anchor)
    # Add deterministic stimuli after the normal generated cyclic path.
    anchor = 'END_ORGANIZATION_BLOCK'
    assert text.count(anchor) == 1
    text = text.replace(anchor, '''    IF "StationA".Access.LoginBusy AND ("GDB_AccessTest".CancelOnLogin OR "GDB_AccessTest".SupersedeOnLogin) THEN
        "GDB_AccessTest".InterruptedBusy := TRUE;
        IF "GDB_AccessTest".CancelOnLogin THEN
            "GDB_AccessTest".InterruptRequest.Kind := @LOGOUT@;
            "FRK_UnitOperation"(Core := "StationA".Core, Unit := "StationA".Unit, Status := "StationA".Status, Policy := "StationA".ModePolicy, Access := "StationA".Access, Supported := "StationA".SupportedModesPublished, Request := "GDB_AccessTest".InterruptRequest, Response := "FRK_UnitScratch".Response, Trusted := FALSE);
        ELSE
            "GDB_AccessTest".SupersededSequence := "FRK_AccessNext"(Previous := "StationA".Access.LoginSequence);
            "FRK_AccessLogin"(Access := "StationA".Access, User := 'unknown', Secret := 'wrong', Sequence := "GDB_AccessTest".SupersededSequence);
        END_IF;
        "GDB_AccessTest".CancelOnLogin := FALSE;
        "GDB_AccessTest".SupersedeOnLogin := FALSE;
    END_IF;
''' + anchor)
    text = text.replace('@LOGOUT@',str(Catalog.read().enums['E_HmiRequestKind']['LOGOUT']))
    path.write_bytes(text.encode('ascii'))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('out', type=Path)
    parser.add_argument('frames', type=Path)
    args = parser.parse_args()
    prepare(args.out, args.frames)
