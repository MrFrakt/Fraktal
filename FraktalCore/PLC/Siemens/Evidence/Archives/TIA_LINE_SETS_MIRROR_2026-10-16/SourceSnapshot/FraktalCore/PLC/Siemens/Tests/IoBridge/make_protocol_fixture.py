"""Native protocol tests without physical I/O or TCP dependencies."""
import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tools'))
from fraktal_tia_binding import PRIVATE, READONLY
from fraktal_tia_io_bridge import config_type, template_text


def build():
    statements = []
    number = 0

    def check(condition):
        nonlocal number
        number += 1
        statements.append('    "F_IoBridgeAssert"(Condition := ' + condition + ', Code := ' + str(number) +
                          ', Checks := #CheckCount, Failures := #FailureCount, FirstFailure := #FailedCode);')

    def cycle(count=1, startup=False, signals='DW#16#0', enable='FALSE'):
        statements.extend([
            '    FOR #Visit := 1 TO ' + str(count) + ' DO',
            '        #NowMs := #NowMs + 50;',
            '        #Physical(Startup := ' + ('#Visit = 1' if startup else 'FALSE') + ', Enabled := TRUE, PhysicalRole := TRUE,',
            '            NowMs := #NowMs, WatchdogMs := 500, Received := #Visit > 1 OR NOT ' + ('TRUE' if startup else 'FALSE') + ',',
            '            SendFrame := TRUE, LocalSignals := DW#16#2001, LocalEnable := TRUE,',
            '            BootEpoch := #PhysicalEpoch, ReceiveBytes := #ControllerBytes, SendBytes := #PhysicalBytes);',
            '        #Controller(Startup := ' + ('#Visit = 1' if startup else 'FALSE') + ', Enabled := TRUE, PhysicalRole := FALSE,',
            '            NowMs := #NowMs, WatchdogMs := 500, Received := TRUE, SendFrame := TRUE,',
            '            LocalSignals := ' + signals + ', LocalEnable := ' + enable + ',',
            '            BootEpoch := #ControllerEpoch, ReceiveBytes := #PhysicalBytes, SendBytes := #ControllerBytes);',
            '    END_FOR;'])

    def receive():
        statements.extend([
            '    #Physical(Startup := FALSE, Enabled := TRUE, PhysicalRole := TRUE,',
            '        NowMs := #NowMs, WatchdogMs := 500, Received := TRUE, SendFrame := FALSE,',
            '        LocalSignals := DW#16#2001, LocalEnable := TRUE,',
            '        BootEpoch := #PhysicalEpoch, ReceiveBytes := #ControllerBytes, SendBytes := #PhysicalBytes);'])

    def checksum():
        statements.extend(['    #Checksum := "F_IoBridgeCrc"(Bytes := #ControllerBytes);',
                           '    #ControllerBytes[30] := WORD_TO_BYTE(SHR(IN := #Checksum, N := 8));',
                           '    #ControllerBytes[31] := WORD_TO_BYTE(#Checksum);'])

    cycle(12, startup=True)
    check('#Physical.LinkHealthy AND #Controller.LinkHealthy')
    check('NOT #Physical.PeerEnable AND #Physical.PeerSignals = DW#16#0')
    check('#Controller.PeerSignals = DW#16#2001')
    cycle(3, signals='DW#16#01', enable='TRUE')
    check('#Physical.PeerEnable AND #Physical.PeerSignals = DW#16#01')
    statements += ['    #RejectBefore := #Physical.RejectedFrames;', '    #ControllerBytes[31] := #ControllerBytes[31] XOR B#16#01;']
    receive()
    check('NOT #Physical.LinkHealthy AND NOT #Physical.PeerEnable AND #Physical.PeerSignals = DW#16#0')
    check('#Physical.RejectedFrames = #RejectBefore + 1')
    statements.append('    #ControllerBytes[31] := #ControllerBytes[31] XOR B#16#01;')
    receive()
    # The last controller packet may have been in flight before corruption;
    # once accepted, the exact replay must never renew the watchdog.
    statements.append('    #RejectBefore := #Physical.RejectedFrames;')
    receive()
    check('#Physical.RejectedFrames = #RejectBefore + 1 AND NOT #Physical.PeerEnable')
    cycle(12, startup=True, signals='DW#16#01', enable='TRUE')
    check('#Physical.LinkHealthy AND #Controller.LinkHealthy AND NOT #Physical.PeerEnable')
    check('#Physical.PeerSignals = DW#16#0')
    cycle(3)
    cycle(3, signals='DW#16#01', enable='TRUE')
    check('#Physical.PeerEnable AND #Physical.PeerSignals = DW#16#01')
    statements.append('    #NowMs := #NowMs + 500;')
    statements.extend(['    #Physical(Startup := FALSE, Enabled := TRUE, PhysicalRole := TRUE,',
                       '        NowMs := #NowMs, WatchdogMs := 500, Received := FALSE, SendFrame := FALSE,',
                       '        LocalSignals := DW#16#2001, LocalEnable := TRUE,',
                       '        BootEpoch := #PhysicalEpoch, ReceiveBytes := #ControllerBytes, SendBytes := #PhysicalBytes);'])
    check('NOT #Physical.LinkHealthy AND NOT #Physical.PeerEnable AND #Physical.PeerSignals = DW#16#0')
    check('"F_IoBridgeElapsed"(NowMs := 5, SinceMs := UDINT#4294967290) = 11')
    statements += ['    #RejectBefore := #Physical.RejectedFrames;',
                   '    "F_IoBridgePut32"(Offset := 8, Value := 1, Bytes := #ControllerBytes);']
    checksum(); receive()
    check('#Physical.RejectedFrames = #RejectBefore + 1')
    statements.append('    #RejectBefore := #Physical.RejectedFrames;')
    statements.append('    #ControllerBytes[5] := 1;')
    checksum(); receive()
    check('#Physical.RejectedFrames = #RejectBefore + 1')
    statements += ['    #ControllerBytes[5] := 2;', '    #ControllerBytes[4] := 2;']
    checksum(); receive()
    check('#Physical.RejectedFrames = #RejectBefore + 2')
    statements += ['    #ControllerBytes[4] := 1;',
                   '    "F_IoBridgePut32"(Offset := 8, Value := 3, Bytes := #ControllerBytes);',
                   '    "F_IoBridgePut32"(Offset := 12, Value := UDINT#4294967294, Bytes := #ControllerBytes);',
                   '    #AcceptBefore := #Physical.AcceptedFrames;']
    checksum(); receive()
    statements.append('    "F_IoBridgePut32"(Offset := 12, Value := UDINT#4294967295, Bytes := #ControllerBytes);')
    checksum(); receive()
    statements.append('    "F_IoBridgePut32"(Offset := 12, Value := 1, Bytes := #ControllerBytes);')
    checksum(); receive()
    check('#Physical.AcceptedFrames = #AcceptBefore + 3')
    statements.append('    #RejectBefore := #Physical.RejectedFrames;')
    statements.append('    "F_IoBridgePut32"(Offset := 12, Value := 0, Bytes := #ControllerBytes);')
    checksum(); receive()
    check('#Physical.RejectedFrames = #RejectBefore + 1')
    statements += ['    #PhysicalEpoch := UDINT#4294967295;',
                   '    #Physical(Startup := TRUE, Enabled := TRUE, PhysicalRole := TRUE,',
                   '        NowMs := #NowMs, WatchdogMs := 500, Received := FALSE, SendFrame := FALSE,',
                   '        LocalSignals := DW#16#0, LocalEnable := FALSE,',
                   '        BootEpoch := #PhysicalEpoch, ReceiveBytes := #ControllerBytes, SendBytes := #PhysicalBytes);']
    check('#PhysicalEpoch = 1 AND NOT #Physical.PeerEnable')

    text = '''FUNCTION "F_IoBridgeAssert" : Void
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

FUNCTION_BLOCK "FB_IoBridgeProtocolTest"
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
    Physical @PRIVATE@ : "FB_IoBridgeProtocol";
    Controller @PRIVATE@ : "FB_IoBridgeProtocol";
    PhysicalEpoch @PRIVATE@ : UDInt;
    ControllerEpoch @PRIVATE@ : UDInt;
    PhysicalBytes @PRIVATE@ : Array[0..31] of Byte;
    ControllerBytes @PRIVATE@ : Array[0..31] of Byte;
    NowMs @PRIVATE@ : UDInt;
    CheckCount @PRIVATE@ : UDInt;
    FailureCount @PRIVATE@ : UDInt;
    FailedCode @PRIVATE@ : DInt;
END_VAR
VAR_TEMP
    Visit : Int;
    Checksum : Word;
    RejectBefore : UDInt;
    AcceptBefore : UDInt;
END_VAR
BEGIN
    IF NOT #Ran THEN
@STATEMENTS@
        #Ran := TRUE;
    END_IF;
    #Done := #Ran;
    #Checks := #CheckCount;
    #Failures := #FailureCount;
    #FirstFailure := #FailedCode;
END_FUNCTION_BLOCK

DATA_BLOCK "GDB_IoBridgeProtocolTest"
{ S7_Optimized_Access := 'TRUE' }
VERSION : 0.1
NON_RETAIN
"FB_IoBridgeProtocolTest"
BEGIN
END_DATA_BLOCK

ORGANIZATION_BLOCK "Main"
{ S7_Optimized_Access := 'TRUE' }
VERSION : 0.1
VAR_INPUT
    Initial_Call : Bool;
    Remanence : Bool;
END_VAR
BEGIN
    "GDB_IoBridgeProtocolTest"();
END_ORGANIZATION_BLOCK
'''.replace('@READONLY@', READONLY.strip()).replace('@PRIVATE@', PRIVATE.strip()).replace('@STATEMENTS@', '\n'.join(statements))
    return {'00_ST_IoBridgeConfig.udt': config_type(),
            '01_IoBridge.scl': template_text(),
            '03_ProtocolTest.scl': text}, number


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('out', type=Path)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    sources, count = build()
    for name, text in sources.items(): (args.out / name).write_bytes(text.encode('ascii'))
    print({'sources': len(sources), 'checks': count})
