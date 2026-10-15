"""Selected document medium on the existing isolated config/access bench."""
import argparse
import importlib.util,json
from pathlib import Path

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('recovery',HERE.parent/'AlarmRecovery/make_fixture.py')
RECOVERY=importlib.util.module_from_spec(spec);spec.loader.exec_module(RECOVERY)


def prepare(out,frames):
    value=RECOVERY.HISTORY.ACCESS.SETS.CONFIG.declaration()
    value['persistence']={'medium':'LOAD_DB','minimum_write_ms':1000,'queue_capacity':4}
    RECOVERY.prepare(out,frames,value)
    add_controls(out,frames)


def add_controls(out,frames):
    from fraktal_tia_generate import db
    from fraktal_tia_binding import PRIVATE,READONLY
    from fraktal_tia_config import function
    info=json.loads((frames/'manifest.json').read_bytes())['runtime']['persistence']
    documents=info['documents']
    fields=['Operation : Int;','Slot : Int;','Bank : Int;','Offset : Int;','ByteValue : Byte;','Unavailable : Bool;',
            'Applied'+READONLY+' : Bool;','Done'+READONLY+' : Bool;','NativeStatus'+READONLY+' : Word;',
            'Step'+PRIVATE+' : Int;','Busy'+PRIVATE+' : Bool;','Pulse'+PRIVATE+' : Bool;',
            'Generation'+READONLY+' : Array[1..%d] of UDInt;'%len(documents),
            'CurrentBank'+READONLY+' : Array[1..%d] of Int;'%len(documents)]
    control=db('GDB_PersistenceTest',fields)
    control=control.replace('    Unavailable : Bool;\n','')
    control=control.replace('END_VAR\nBEGIN','END_VAR\nVAR RETAIN\n    Unavailable : Bool;\nEND_VAR\nBEGIN')
    (out/'06_GDB_PersistenceTest.db').write_bytes(control.encode('ascii'))
    import re
    capacity=int(re.search(r'Rows.*?Array\[1\.\.(\d+)\]',(out/'05_FRK_ConfigStore.db').read_text('ascii'))[1])
    mirrors=[]
    for d in documents:
        tag='D%03d'%d['index'];slot=d['index']
        mirrors+=['    "GDB_PersistenceTest".Generation[%d] := "FRK_PersistRuntime".Anchor[%d].Generation;'%(slot,slot),
                  '    IF "FRK_PersistNumber"(Bytes := "FRK_PersistBuffers".'+tag+'A, Offset := 8) = UDINT_TO_DWORD("FRK_PersistRuntime".Anchor[%d].Generation) THEN "GDB_PersistenceTest".CurrentBank[%d] := 1; ELSE "GDB_PersistenceTest".CurrentBank[%d] := 2; END_IF;'%(slot,slot,slot)]
    body=['    "FRK_PersistRuntime".Unavailable := "GDB_PersistenceTest".Unavailable;',*mirrors,
          '    IF "GDB_PersistenceTest".Operation <> 0 AND "GDB_PersistenceTest".Step = 0 THEN',
          '        "GDB_PersistenceTest".Applied := FALSE; "GDB_PersistenceTest".Done := FALSE;',
          '        #Slot := "GDB_PersistenceTest".Slot;',
          '        IF #Slot < 1 OR #Slot > %d THEN "GDB_PersistenceTest".Operation := 0; RETURN; END_IF;'%len(documents),
          '        IF "FRK_PersistRuntime".Leased[#Slot] THEN RETURN; END_IF;',
          '        CASE "GDB_PersistenceTest".Operation OF',
          '            1:', '                IF "GDB_PersistenceTest".Offset < 0 OR "GDB_PersistenceTest".Offset >= "FRK_PersistRuntime".Capacity[#Slot] + %d THEN "GDB_PersistenceTest".Operation := 0; RETURN; END_IF;'%info['header_bytes'],
          '                IF "GDB_PersistenceTest".Bank <> 1 AND "GDB_PersistenceTest".Bank <> 2 THEN "GDB_PersistenceTest".Operation := 0; RETURN; END_IF;',
          '                "GDB_PersistenceTest".Step := 1; "GDB_PersistenceTest".Pulse := TRUE;',
          '            2:',
          '                IF "FRK_PersistAnchors".SelectedB[#Slot] THEN "FRK_PersistAnchors".RowsB[#Slot].Checksum := "FRK_PersistAnchors".RowsB[#Slot].Checksum XOR DWORD#1;',
          '                ELSE "FRK_PersistAnchors".RowsA[#Slot].Checksum := "FRK_PersistAnchors".RowsA[#Slot].Checksum XOR DWORD#1; END_IF;',
          '                "GDB_PersistenceTest".Applied := TRUE; "GDB_PersistenceTest".Done := TRUE; "GDB_PersistenceTest".Operation := 0;',
          '            3:',
          '                // Deliberately poison retained caches: subsequent boot must read the selected medium.',
          '                FOR #Index := 1 TO %d DO "FRK_ConfigStore".Rows[#Index].Record.ValueText := \'poison-cache\'; END_FOR;'%capacity,
          '                "FRK_LocalUsers".Checksum := DWORD#0;',
          '                "GDB_PersistenceTest".Applied := TRUE; "GDB_PersistenceTest".Done := TRUE; "GDB_PersistenceTest".Operation := 0;',
          '            ELSE "GDB_PersistenceTest".Operation := 0;', '        END_CASE;', '    END_IF;',
          '    IF "GDB_PersistenceTest".Step = 0 THEN RETURN; END_IF;',
          '    #Slot := "GDB_PersistenceTest".Slot;',
          '    CASE #Slot OF']
    # Native operands use the actual per-document extent; no oversized VARIANT copy.
    for d in documents:
        tag='D%03d'%d['index'];buffer='"FRK_PersistBuffers".'+tag+'A'
        body+=['        %d:'%d['index'],'            IF "GDB_PersistenceTest".Step = 1 THEN']
        for bank_number,bank in ((1,'A'),(2,'B')):
            body+=['                '+('IF' if bank_number==1 else 'ELSE')+' "GDB_PersistenceTest".Bank = %d THEN'%bank_number if bank_number==1 else '                ELSE',
                   '                    #Result := READ_DBL(REQ := "GDB_PersistenceTest".Pulse, SRCBLK := "FRK_Load_'+tag+bank+'".Bytes, BUSY => "GDB_PersistenceTest".Busy, DSTBLK => '+buffer+');']
        body+=['                END_IF;', '            ELSE']
        for bank_number,bank in ((1,'A'),(2,'B')):
            body+=['                IF "GDB_PersistenceTest".Bank = 1 THEN' if bank_number==1 else '                ELSE',
                   '                    #Result := WRIT_DBL(REQ := "GDB_PersistenceTest".Pulse, SRCBLK := '+buffer+', BUSY => "GDB_PersistenceTest".Busy, DSTBLK => "FRK_Load_'+tag+bank+'".Bytes);']
        body+=['                END_IF;', '            END_IF;',
               '            IF "GDB_PersistenceTest".Step = 1 AND NOT "GDB_PersistenceTest".Busy AND #Result = 0 THEN '+buffer+'["GDB_PersistenceTest".Offset] := "GDB_PersistenceTest".ByteValue; END_IF;']
    body+=['        ELSE "GDB_PersistenceTest".Step := 0; RETURN;', '    END_CASE;',
           '    "GDB_PersistenceTest".Pulse := FALSE;', '    "GDB_PersistenceTest".NativeStatus := INT_TO_WORD(#Result);',
           '    IF "GDB_PersistenceTest".Busy THEN RETURN; END_IF;',
           '    IF #Result <> 0 THEN "GDB_PersistenceTest".Step := 0; "GDB_PersistenceTest".Done := TRUE; "GDB_PersistenceTest".Operation := 0; RETURN; END_IF;',
           '    IF "GDB_PersistenceTest".Step = 1 THEN "GDB_PersistenceTest".Step := 2; "GDB_PersistenceTest".Pulse := TRUE;',
           '    ELSE "GDB_PersistenceTest".Step := 0; "GDB_PersistenceTest".Applied := TRUE; "GDB_PersistenceTest".Done := TRUE; "GDB_PersistenceTest".Operation := 0; END_IF;']
    # The pool's actual declared size is authoritative, rather than a test-side maximum.
    (out/'39f_PersistenceBench.scl').write_bytes(function('F_PersistenceBench',[],[],['Slot : Int;','Index : Int;','Result : Int;'],body).encode('ascii'))
    p=out/'30_FB_FraktalMain.scl';text=p.read_text('ascii')
    marker='    "FRK_PersistEnter"(Startup := #Startup);'
    assert text.count(marker)==1
    text=text.replace(marker,'    "F_PersistenceBench"();\n'+marker)
    p.write_bytes(text.encode('ascii'))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('out',type=Path);p.add_argument('frames',type=Path)
    a=p.parse_args();prepare(a.out,a.frames)
