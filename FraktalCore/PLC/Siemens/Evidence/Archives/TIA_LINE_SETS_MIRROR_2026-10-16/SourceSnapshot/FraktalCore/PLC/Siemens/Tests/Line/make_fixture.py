"""Native P1 kernel bench: two independent line copies, no equipment commands."""
import argparse
import importlib.util
import json
from pathlib import Path
import re
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / 'tools'))
from fraktal_tia_binding import Catalog, PRIVATE, READONLY, type_source
from fraktal_tia_line import Engine, Line
import fraktal_tia_generate as GEN

spec = importlib.util.spec_from_file_location('config_fixture', HERE.parent/'Config/make_fixture.py')
CONFIG = importlib.util.module_from_spec(spec)
spec.loader.exec_module(CONFIG)

RECORD = ('ST_LineProbeConfig', "STRUCT SchemaVersion : UINT := 1; TaktMs : UDINT := 1000; "
          "Gain : LREAL := 1.25; Grade : E_Mode := E_Mode.MANUAL; Enabled : BOOL := TRUE; "
          "HostName : STRING(40) := 'press-line'; Offsets : ARRAY[0..1] OF INT; Small : USINT := 7; END_STRUCT")


def declaration():
    values = []
    for member, key in (('TaktMs', 'taktMs'), ('Gain', 'gain'), ('Grade', 'grade'),
                        ('Enabled', 'enabled'), ('HostName', 'hostName'),
                        ('Offsets[0]', 'offset.0'), ('Offsets[1]', 'offset.1'), ('Small', 'small')):
        field = dict(member='Line.'+member, key='line.'+key, revision=1,
                     label='test.config.preset', requires_ready=False, min_read=1, min_write=2)
        if member == 'TaktMs': field.update(minimum=1, maximum=100000, requires_ready=True)
        if member == 'Gain': field.update(minimum=-100, maximum=100)
        values.append(field)
    return dict(id='PRESS-LINE-1', owner='BenchLineOwner', role='OWNER', roots=['StationA', 'StationB'],
                record=RECORD[0], values=values, stale_after_ms=500)


def build():
    value = CONFIG.declaration()
    value.pop('event_sink', None)
    sources, _ = GEN.build(GEN.DECL.validate(value), True)
    catalog = Catalog.read([RECORD])
    engine = Engine(Line.read(declaration(), ['StationA', 'StationB']), catalog)
    for index, (name, fields) in enumerate(catalog.resolve([RECORD[0], 'ST_LineStatus', 'ST_LineImage']).items()):
        sources['00_line_%02d_%s.udt' % (index, name)] = type_source(name, fields)
    sources.update(engine.sources())
    # The ordinary config scratch owns the enum array used by the one validator.
    scratch = sources['05_FRK_ConfigScratch.db']
    scratch, count = re.subn(r'EnumValues(.*?)Array\[1\.\.\d+\]',
                            lambda m: 'EnumValues'+m[1]+'Array[1..%d]' % max(len(f.enum_values) for f in engine.fields), scratch)
    assert count == 1
    sources['05_FRK_ConfigScratch.db'] = scratch
    statements, labels = [], []

    def emit(*lines): statements.extend('    '+line for line in lines)

    def check(condition, label):
        labels.append(label)
        emit('"F_LineAssert"(Condition := '+condition+', Code := '+str(len(labels))+
             ', Checks := #CheckCount, Failures := #FailureCount, FirstFailure := #FailedCode);')

    def write(key, text, *, ready=True):
        emit("#Request.NameValue := 'line."+key+"';", "#Request.TextValue := WSTRING#'"+text+"';",
             '#Matched := FALSE;', '#Ok := "FRK_LineWrite"(Request := #Request, Access := #Access, Ready := '+
             str(ready).upper()+', State := #OwnerState, Matched := #Matched);')

    def apply(*, restore=False):
        emit('#Ok := "FRK_LineApply"(Image := #Incoming, Restore := '+str(restore).upper()+
             ', NowMs := #NowMs, Stamp := LDT#2026-10-15-12:00:00, TimeSynchronized := #Synchronized, State := #MirrorState);')

    def reject(label, error=2):
        apply()
        check('NOT #Ok AND #MirrorState.Status.SourceError = '+str(error)+
              ' AND #MirrorState.Values.TaktMs = 2500 AND #MirrorState.Values.Gain = 2.5 AND #MirrorState.Status.Revision = #PreviousRevision', label)

    emit('"FRK_LineBoot"(OwnerRole := TRUE, NowMs := 0, State := #OwnerState);',
         '"FRK_LineBoot"(OwnerRole := FALSE, NowMs := 0, State := #MirrorState);',
         '#Access.CurrentLevel := 2;', '#Request.Kind := %d;' % catalog.enums['E_HmiRequestKind']['WRITE_CONFIG'],
         '#Request.IntValue := 1;')
    check('#OwnerState.Status.Revision = 1 AND #OwnerState.Image.Count = 8 AND #OwnerState.Image.Revision = 1', 'owner initial complete image')
    check('#OwnerState.Values.TaktMs = 1000 AND #OwnerState.Values.Gain = 1.25 AND #OwnerState.Values.Small = 7', 'declared typed defaults')
    write('taktMs', '2500')
    check('#Ok AND #Matched AND #OwnerState.Values.TaktMs = 2500 AND #OwnerState.Status.Revision = 2', 'owner accepted write raises revision')
    write('gain', '2.5', ready=False)
    check('#Ok AND #OwnerState.Values.Gain = 2.5 AND #OwnerState.Status.Revision = 3', 'non readiness gated LREAL write')
    emit('#OwnerState.Applied := FALSE;', '#OwnerState.BuiltRevision := 0;', '"FRK_LineBuild"(State := #OwnerState);')
    check('#OwnerState.Applied AND #OwnerState.Image.Revision = 3', 'successful owner image rebuild establishes applied values')
    emit('#PreviousRevision := #OwnerState.Status.Revision;')
    for key, text, ready, label in (
        ('taktMs', '3000', False, 'ready gate'), ('taktMs', '0', True, 'declared bound'),
        ('small', '256', True, 'native USINT bound'), ('grade', '99', True, 'enum domain'),
        ('gain', 'garbage', True, 'malformed decimal'), ('hostName', 'x'*41, True, 'string width')):
        write(key, text, ready=ready)
        check('NOT #Ok AND #OwnerState.Status.Revision = #PreviousRevision', 'refuse '+label)
    emit('#Access.CurrentLevel := 1;')
    write('taktMs', '3000')
    check('NOT #Ok AND #OwnerState.Status.Revision = #PreviousRevision', 'field write access minimum')
    emit('#Access.CurrentLevel := 2;', '#Request.IntValue := 2;')
    write('taktMs', '3000')
    check('NOT #Ok', 'capability revision mismatch')
    emit('#Request.IntValue := 1;', '#Request.DurationMs := 1;')
    write('taktMs', '3000')
    check('NOT #Ok', 'line is never model scoped')
    emit('#Request.DurationMs := 0;')
    write('missing', '3000')
    check('NOT #Ok AND NOT #Matched', 'unknown key is unclaimed')
    emit('#NowMs := 100;', '#Ok := "FRK_LineLocalRead"(OwnerState := #OwnerState, Image := #Incoming);')
    check('#Ok AND #Incoming.Revision = 3', 'local source reads complete owner image')
    apply()
    check('#Ok AND #MirrorState.Status.Revision = 3 AND #MirrorState.Values.TaktMs = 2500 AND #MirrorState.Values.Gain = 2.5', 'mirror whole revision through typed handlers')
    emit("#Incoming.Records[1].ValueText := '+0002500';")
    apply()
    check('#Ok AND #MirrorState.Values.TaktMs = 2500', 'equivalent numeric text is a valid same revision heartbeat')
    check('#MirrorState.Status.Owner = \'BenchLineOwner\' AND NOT #MirrorState.Status.TimeSynchronized AND NOT #MirrorState.Status.Stale', 'owner identity and explicit clock quality')
    emit('#PreviousRevision := #MirrorState.Status.Revision;', '#Matched := FALSE;',
         '#Request.NameValue := \'line.taktMs\';', '#Request.TextValue := WSTRING#\'999\';',
         '#Ok := "FRK_LineWrite"(Request := #Request, Access := #Access, Ready := TRUE, State := #MirrorState, Matched := #Matched);')
    check('NOT #Ok AND #Matched AND #MirrorState.Values.TaktMs = 2500', 'mirror direct write refused')
    emit('#Incoming := #OwnerState.Image;', '#Incoming.LineId := \'wrong\';')
    reject('wrong line refuses whole image', 1)
    for change, label in (
        ("#Incoming.Owner := 'wrong';", 'wrong owner'),
        ('#Incoming.Count := 7;', 'partial count'), ('#Incoming.Count := 33;', 'oversized count'),
        ('#Incoming.Revision := 0;', 'zero revision'), ('#Incoming.Revision := 2;', 'older revision'),
        ("#Incoming.Records[8].WriteKey := 'unknown';", 'unknown key'),
        ('#Incoming.Records[8].WriteKey := #Incoming.Records[1].WriteKey;', 'duplicate key'),
        ('#Incoming.Records[8].Revision := 2;', 'field revision'),
        ("#Incoming.Records[8].ValueText := '256';", 'invalid last record leaves first untouched'),
        ("#Incoming.Records[3].ValueText := '99';", 'source enum domain'),
        ("#Incoming.Records[1].ValueText := '3000';", 'same revision changed content')):
        emit('#Incoming := #OwnerState.Image;', change)
        # Invalid last record also proposes a valid first edit in a NEW revision.
        if 'last record' in label:
            emit('#Incoming.Revision := 4;', "#Incoming.Records[1].ValueText := '3000';")
        reject(label)
    emit('#NowMs := 599;')
    emit('"FRK_LineTick"(NowMs := #NowMs, SourceError := 17, State := #MirrorState);')
    check('NOT #MirrorState.Status.Stale AND #MirrorState.Status.SourceError = 17', 'source failure before stale window')
    emit('#NowMs := 600;', '"FRK_LineTick"(NowMs := #NowMs, SourceError := 17, State := #MirrorState);')
    check('#MirrorState.Status.Stale AND #MirrorState.Values.TaktMs = 2500', 'stale at exact boundary keeps values')
    emit('"FRK_AlarmBegin"(AlarmLog := #AlarmLog, Startup := TRUE);',
         '"FRK_LineAnnounce"(Scope := \'StationA\', State := #MirrorState, AlarmLog := #AlarmLog);')
    check('#AlarmLog.NActive = 1 AND NOT #AlarmLog.Blocking AND #MirrorState.StaleSlot > 0', 'stale event is nonblocking')
    check('#AlarmLog.Active[#MirrorState.StaleSlot].Description = WSTRING#\'std.error.lineDataStale\' AND '+
          '#AlarmLog.Active[#MirrorState.StaleSlot].Severity = %d AND ' % catalog.enums['E_Severity']['LOW']+
          '#AlarmLog.Active[#MirrorState.StaleSlot].Category = %d AND ' % catalog.enums['E_Category']['SYSTEM']+
          '#AlarmLog.Active[#MirrorState.StaleSlot].ResetClass = %d' % catalog.enums['E_ResetClass']['AUTO_RESET'], 'LOW SYSTEM AUTO_RESET event')
    emit('"FRK_LineAnnounce"(Scope := \'StationA\', State := #MirrorState, AlarmLog := #AlarmLog);')
    check('#AlarmLog.NActive = 1', 'stale event deduplicated')
    emit('#Incoming := #OwnerState.Image;', '#Synchronized := TRUE;')
    apply()
    check('#Ok AND NOT #MirrorState.Status.Stale AND #MirrorState.Status.SourceError = 0 AND #MirrorState.Status.TimeSynchronized', 'same revision heartbeat clears stale and updates quality')
    emit('"FRK_LineAnnounce"(Scope := \'StationA\', State := #MirrorState, AlarmLog := #AlarmLog);')
    check('#AlarmLog.NActive = 0 AND #AlarmLog.RingUsed = 1 AND #MirrorState.StaleSlot = 0', 'stale event automatically closes on recovery')
    emit('#Position := 0;', '#NativeResult := Serialize(SRC_VARIABLE := #MirrorState.Image, DEST_ARRAY => #SavedBytes, POS := #Position);',
         '#SavedLength := #Position;')
    check('#NativeResult = 0 AND #SavedLength > 0', 'native image serialization')
    emit('"FRK_LineBoot"(OwnerRole := FALSE, NowMs := 700, State := #MirrorState);',
         '#Position := 0;', '#NativeResult := Deserialize(SRC_ARRAY := #SavedBytes, DEST_VARIABLE => #Incoming, POS := #Position);')
    check('#NativeResult = 0 AND #Position = #SavedLength AND #MirrorState.Values.TaktMs = 1000', 'restart clears working values before restore')
    apply(restore=True)
    check('#Ok AND #MirrorState.Values.TaktMs = 2500 AND #MirrorState.Status.Revision = 3 AND NOT #MirrorState.HaveSuccess', 'restore re applies persisted revision without source heartbeat')
    check('NOT #MirrorState.Status.TimeSynchronized AND #MirrorState.Status.LastUpdate = LDT#1970-01-01-00:00:00', 'restore does not invent timestamp quality')
    emit('"FRK_LineTick"(NowMs := 1200, SourceError := 17, State := #MirrorState);')
    check('#MirrorState.Status.Stale AND #MirrorState.Values.Gain = 2.5', 'offline restored copy eventually stale and keeps values')
    # An equal-revision live poll must repair defaults after every boot too.
    emit('"FRK_LineBoot"(OwnerRole := FALSE, NowMs := 0, State := #MirrorState);',
         '#MirrorState.Status.Revision := #Incoming.Revision;')
    apply()
    check('#Ok AND #MirrorState.Values.TaktMs = 2500', 'boot applies source even when it is same persisted revision')
    emit('#OwnerState.Status.Revision := UDINT#4294967295;')
    write('taktMs', '2600')
    check('#Ok AND #OwnerState.Status.Revision = 1', 'owner revision wraps without zero')
    emit('#MirrorState.Status.Revision := UDINT#4294967295;', '#Incoming := #OwnerState.Image;')
    apply()
    check('#Ok AND #MirrorState.Status.Revision = 1 AND #MirrorState.Values.TaktMs = 2600', 'mirror accepts forward wrap')
    emit('"FRK_ConfigBegin"(Cursor := #Cursor, Page := #Page, PageIndex := 0, Revision := 1);',
         '"FRK_LineManifest"(Scope := \'StationB\', Access := #Access, State := #MirrorState, Cursor := #Cursor, Page := #Page);',
         '"FRK_ConfigFinish"(Cursor := #Cursor, Page := #Page);')
    check('#Page.EntryCount = 8 AND #Page.Entries[1].Scope = WSTRING#\'StationB\' AND #Page.Entries[1].Item = WSTRING#\'Line/TaktMs\'', 'manifest root scope and generic Line group')
    check('NOT #Page.Entries[1].Writable AND #Page.Entries[1].Readable AND #Page.Entries[1].ConfigKind = 2', 'mirror read only manifest')
    emit('#Access.CurrentLevel := 0;', '"FRK_ConfigBegin"(Cursor := #Cursor, Page := #Page, PageIndex := 0, Revision := 1);',
         '"FRK_LineManifest"(Scope := \'StationA\', Access := #Access, State := #OwnerState, Cursor := #Cursor, Page := #Page);',
         '"FRK_ConfigFinish"(Cursor := #Cursor, Page := #Page);')
    check('NOT #Page.Entries[1].Readable AND #Page.Entries[1].ValueText = WSTRING#\'\' AND #Page.Entries[1].Writable', 'line read access conceals value')
    emit('"FRK_LineBoot"(OwnerRole := FALSE, NowMs := UDINT#4294967200, State := #MirrorState);',
         '"FRK_LineTick"(NowMs := 404, SourceError := 0, State := #MirrorState);')
    check('#MirrorState.Status.Stale', 'staleness clock wrap')

    source = '''FUNCTION "F_LineAssert" : Void
{ S7_Optimized_Access := 'TRUE' }
VERSION : 0.1
VAR_INPUT
    Condition : Bool;
    Code : DInt;
END_VAR
VAR_IN_OUT
    Checks : UDInt;
    Failures : UDInt;
    FirstFailure : DInt;
END_VAR
BEGIN
    #Checks := #Checks + 1;
    IF NOT #Condition THEN
        #Failures := #Failures + 1;
        IF #FirstFailure = 0 THEN #FirstFailure := #Code; END_IF;
    END_IF;
END_FUNCTION

FUNCTION_BLOCK "FB_LineTest"
{ S7_Optimized_Access := 'TRUE' }
VERSION : 0.1
VAR_OUTPUT
    Done @READONLY@ : Bool;
    Checks @READONLY@ : UDInt;
    Failures @READONLY@ : UDInt;
    FirstFailure @READONLY@ : DInt;
END_VAR
VAR
    Ran @PRIVATE@ : Bool;
    OwnerState @PRIVATE@ : "FRK_LineState";
    MirrorState @PRIVATE@ : "FRK_LineState";
    Incoming @PRIVATE@ : "ST_LineImage";
    Request @PRIVATE@ : "ST_HmiRequest";
    Access @PRIVATE@ : "FRK_Access";
    Cursor @PRIVATE@ : "FRK_ConfigCursor";
    Page @PRIVATE@ : "ST_ConfigPage";
    AlarmLog @PRIVATE@ : "FRK_AlarmLog";
    SavedBytes @PRIVATE@ : Array[0..20000] of Byte;
    CheckCount @PRIVATE@ : UDInt;
    FailureCount @PRIVATE@ : UDInt;
    FailedCode @PRIVATE@ : DInt;
END_VAR
VAR_TEMP
    NowMs : UDInt;
    PreviousRevision : UDInt;
    Synchronized : Bool;
    Matched : Bool;
    Ok : Bool;
    Position : DInt;
    SavedLength : DInt;
    NativeResult : Int;
END_VAR
BEGIN
    IF NOT #Ran THEN
        #NowMs := 0;
        #Synchronized := FALSE;
@STATEMENTS@
        #Ran := TRUE;
    END_IF;
    #Done := #Ran;
    #Checks := #CheckCount;
    #Failures := #FailureCount;
    #FirstFailure := #FailedCode;
END_FUNCTION_BLOCK
'''.replace('@READONLY@', READONLY.strip()).replace('@PRIVATE@', PRIVATE.strip()).replace('@STATEMENTS@', '\n'.join(statements))
    sources['37_LineTest.scl'] = source
    sources['39_GDB_LineTest.db'] = '\n'.join(['DATA_BLOCK "GDB_LineTest"', "{ S7_Optimized_Access := 'TRUE' }",
        'VERSION : 0.1', 'NON_RETAIN', '"FB_LineTest"', 'BEGIN', 'END_DATA_BLOCK', ''])
    sources['40_Main.scl'] = '\n'.join(['ORGANIZATION_BLOCK "Main"', "{ S7_Optimized_Access := 'TRUE' }",
        'VERSION : 0.1', 'VAR_INPUT', '    Initial_Call : Bool;', '    Remanence : Bool;', 'END_VAR',
        'BEGIN', '    "GDB_LineTest"();', 'END_ORGANIZATION_BLOCK', ''])
    return sources, labels


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('out', type=Path)
    args = parser.parse_args()
    sources, labels = build()
    args.out.mkdir(parents=True, exist_ok=False)
    for name, text in sources.items(): (args.out/name).write_bytes(text.encode('ascii'))
    (args.out/'assertions.json').write_bytes((json.dumps(dict(enumerate(labels, 1)), indent=2)+'\n').encode('ascii'))
    print(json.dumps(dict(sources=len(sources), checks=len(labels))))
