"""Source-bound mirror; the synthetic provider lends only an untrusted image."""
import argparse
from pathlib import Path

import make_owner_fixture as OWNER


def declaration():
    value = OWNER.declaration()
    value['line'].update(role='MIRROR', source='F_LineMirrorSource', stale_after_ms=3000)
    return value


def prepare(out, frames):
    OWNER.CONFIG.PERSIST.RECOVERY.prepare(out, frames, declaration())
    OWNER.CONFIG.PERSIST.add_controls(out, frames)
    from fraktal_tia_binding import PRIVATE, READONLY
    from fraktal_tia_config import function
    from fraktal_tia_generate import db
    fields = ['PublishPulse : Bool;', 'IncomingRevision : UDInt := 10;', 'TaktMs : UDInt := 1500;',
              'ImageMode : Int;', 'SourceError : DInt;', 'Synchronized : Bool;',
              *[name+READONLY+' : '+kind+';' for name,kind in (
                  ('SourceCalls','UDInt'),('ReadyScans','UDInt'),('SourceOncePerScan','Bool'),
                  ('WorkingTaktMs','UDInt'),('BootDefaultSeen','Bool'),('BootDefaultValue','UDInt'))],
              'PoisonPulse : Bool;',
              'Available'+PRIVATE+' : Bool;', 'Incoming'+PRIVATE+' : "ST_LineImage";',
              'SourceOwner'+PRIVATE+' : "FRK_LineState";']
    text = db('GDB_LineMirrorTest', fields).replace('END_VAR\nBEGIN', 'END_VAR\nVAR RETAIN\n    Enabled : Bool;\nEND_VAR\nBEGIN')
    (out/'06_GDB_LineMirrorTest.db').write_bytes(text.encode('ascii'))
    body = ['    "GDB_LineMirrorTest".SourceCalls := "GDB_LineMirrorTest".SourceCalls + 1;',
            '    #SourceError := "GDB_LineMirrorTest".SourceError;',
            '    #Stamp := LDT#2026-10-16-12:00:00; #TimeSynchronized := "GDB_LineMirrorTest".Synchronized;',
            '    #F_LineMirrorSource := "GDB_LineMirrorTest".Enabled AND "GDB_LineMirrorTest".Available;',
            '    IF #F_LineMirrorSource THEN',
            '        #Image := "GDB_LineMirrorTest".Incoming; "GDB_LineMirrorTest".Available := FALSE;', '    END_IF;']
    provider = ('FUNCTION "F_LineMirrorSource" : Bool\n{ S7_Optimized_Access := \'TRUE\' }\nVERSION : 0.1\n'
                'VAR_OUTPUT SourceError : DInt; Stamp : LDT; TimeSynchronized : Bool; END_VAR\n'
                'VAR_IN_OUT Image : "ST_LineImage"; END_VAR\nBEGIN\n'+'\n'.join(body)+'\nEND_FUNCTION\n')
    (out/'06a_LineMirrorSource.scl').write_bytes(provider.encode('ascii'))
    body = ['    IF #Startup THEN "GDB_LineMirrorTest".BootDefaultSeen := FALSE; END_IF;',
            '    IF "FRK_PersistStatus".Restoring AND NOT "GDB_LineMirrorTest".BootDefaultSeen THEN',
            '        "GDB_LineMirrorTest".BootDefaultValue := "FRK_Line".Data.Values.TaktMs;',
            '        "GDB_LineMirrorTest".BootDefaultSeen := TRUE;', '    END_IF;',
            '    IF NOT "FRK_PersistStatus".Restoring THEN',
            '        "GDB_LineMirrorTest".ReadyScans := "GDB_LineMirrorTest".ReadyScans + 1;',
            '        "GDB_LineMirrorTest".SourceOncePerScan := "GDB_LineMirrorTest".SourceCalls = "GDB_LineMirrorTest".ReadyScans;', '    END_IF;',
            '    IF "GDB_LineMirrorTest".PublishPulse THEN',
            '        "FRK_LineBoot"(OwnerRole := TRUE, NowMs := 0, State := "GDB_LineMirrorTest".SourceOwner);',
            '        "GDB_LineMirrorTest".SourceOwner.Values.TaktMs := "GDB_LineMirrorTest".TaktMs;',
            '        "GDB_LineMirrorTest".SourceOwner.Status.Revision := "GDB_LineMirrorTest".IncomingRevision;',
            '        "GDB_LineMirrorTest".SourceOwner.BuiltRevision := 0;',
            '        "FRK_LineBuild"(State := "GDB_LineMirrorTest".SourceOwner);',
            '        "GDB_LineMirrorTest".Incoming := "GDB_LineMirrorTest".SourceOwner.Image;',
            '        "GDB_LineMirrorTest".Incoming.Revision := "GDB_LineMirrorTest".IncomingRevision;',
            '        CASE "GDB_LineMirrorTest".ImageMode OF',
            '            1: "GDB_LineMirrorTest".Incoming.LineId := \'WRONG-LINE\';',
            '            2: "GDB_LineMirrorTest".Incoming.Count := "GDB_LineMirrorTest".Incoming.Count - 1;',
            '            3: "GDB_LineMirrorTest".Incoming.Records[%d].ValueText := \'999\';'%len(OWNER.LINE.declaration()['values']),
            '            ELSE "GDB_LineMirrorTest".Incoming.Owner := \'BenchLineOwner\';', '        END_CASE;',
            '        "GDB_LineMirrorTest".PublishPulse := FALSE; "GDB_LineMirrorTest".Available := TRUE;', '    END_IF;',
            '    IF "GDB_LineMirrorTest".PoisonPulse THEN',
            '        "FRK_Line".Data.Values.TaktMs := 99999; "GDB_LineMirrorTest".PoisonPulse := FALSE;', '    END_IF;',
            '    "GDB_LineMirrorTest".WorkingTaktMs := "FRK_Line".Data.Values.TaktMs;']
    (out/'37_LineMirrorObserve.scl').write_bytes(function('F_LineMirrorObserve',['Startup : Bool;'],[],[],body).encode('ascii'))
    OWNER.append_observer(out,'F_LineMirrorObserve')


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('out',type=Path);parser.add_argument('frames',type=Path)
    args=parser.parse_args();prepare(args.out,args.frames)
