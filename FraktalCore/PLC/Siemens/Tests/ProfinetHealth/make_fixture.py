"""PROFINET node health against the CPU's own device view (Part IV 10.5).

The fixture project carries one PROFINET IO system with an ET 200SP head
(IM_1) with a DQ module (PnDQ, slot 1) and a central DQ module (DQ_1, the forceable
address for the force-job spike). The suite runs across scans: the device and
its module the simulator presents are operational; D_ACT_DP disables the device
from the program, the next sample takes it, its input and its module offline;
re-enabling returns them. A non-asserting probe
records the CPU's LED states for the force-job spike.
"""
import argparse
import importlib.util
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
TIA = HERE.parents[1]
sys.path.insert(0, str(TIA/'tools'))
from fraktal_tia_binding import Catalog, READONLY, PRIVATE
from fraktal_tia_generate import db
from fraktal_tia_test_runtime import build as test_runtime, signature, seal_signature

IO_SYSTEM, DEVICE, MODULE = 'Local~PROFINET_IO-System', 'IM_1~IODevice', 'IM_1~PnDQ'
# Fixture hardware, created by the approved driver after the CPU (compile_fresh).
HARDWARE = ['io-system --plc PLC_1 --name "PROFINET IO-System" --item "PROFINET interface_1"',
            'add-device --order "OrderNumber:6ES7 155-6AU01-0BN0/V4.2" --name IM_1 --station PnIo1',
            'connect-io --plc PLC_1 --station PnIo1 --ip 169.254.213.58 --pn-name pnio1',
            # Slot 1: the ET 200SP server module is added after it and nothing may follow that.
            'add-module --station PnIo1 --order "OrderNumber:6ES7 132-6BF01-0BA0/V0.0" --name PnDQ --slot 1',
            'add-module --station TiaGate --order "OrderNumber:6ES7 522-1BH01-0AB0/V1.0" --name DQ_1 --slot 2']
WAIT_SCANS = 5000
# D_ACT_DP modes (S7-1500): 1 activate, 2 deactivate.
ACTIVATE, DEACTIVATE = 1, 2


def build():
    spec = importlib.util.spec_from_file_location('line_fixture', HERE.parent/'Line/make_fixture.py')
    line = importlib.util.module_from_spec(spec); spec.loader.exec_module(line)
    sources, _ = line.build()
    for name in ('37_LineTest.scl', '39_GDB_LineTest.db'): sources.pop(name)
    sources.update(test_runtime())
    facts = Catalog.read(); states = facts.enums['E_NodeState']
    from fraktal_tia_topology import sources as topology
    pn_spec = dict(block='GDB_PnTestFieldbus', publisher='F_PnTestPublish', image='GDB_PnTestIO', healthy='Healthy',
        nodes=[dict(name='PnIo1', description_key='project.hardware.pnio1', type_id='IM 155-6 PN ST', address='pnio1',
                    profinet=dict(io_system=IO_SYSTEM, device=DEVICE),
                    channels=[dict(tag='I1', description_key='project.io.I1', address='%I0.0', dir='INPUT', source='In1', module='PnTest')]),
               dict(name='PnDQ', parent=1, description_key='project.hardware.pnio1Dq', type_id='DQ 8x24VDC/0.5A ST', address='slot 1',
                    profinet=dict(io_system=IO_SYSTEM, device=DEVICE, module=MODULE))])
    image = {'Healthy', 'In1'}
    sources.update(topology(facts, pn_spec, image, 'PnTest', set()))
    sources['38_GDB_PnTestIO.db'] = '\n'.join(['DATA_BLOCK "GDB_PnTestIO"', "{ S7_Optimized_Access := 'TRUE' }", 'VERSION : 0.1', 'NON_RETAIN',
        'VAR', *['    ' + n + PRIVATE + ' : Bool;' for n in sorted(image)], 'END_VAR', 'BEGIN', 'END_DATA_BLOCK', ''])
    node, module = '"GDB_PnTestFieldbus".Topology.Nodes[1]', '"GDB_PnTestFieldbus".Topology.Nodes[2]'
    labels, cases = [], []

    def check(condition, label):
        labels.append(label)
        return '"FRK_TestAssert"(Condition := %s, Code := %d, Result := #Result);' % (condition, len(labels))

    def sample():
        return ['"FRK_Clock".NowMs := "FRK_Clock".NowMs + UDINT#300;', '"F_PnTestPublish"();']

    def actuate(mode, label):
        # Asynchronous: called each scan with the same request until it completes.
        return ['#Ret := D_ACT_DP(REQ := TRUE, MODE := BYTE#%d, LADDR := "%s", BUSY => #Busy);' % (mode, DEVICE),
                '#Scans := #Scans + 1;',
                'IF NOT #Busy OR #Scans > %d THEN' % WAIT_SCANS,
                '    ' + check('NOT #Busy AND #Ret = 0', label),
                '    #Step := #Step + 1; #Scans := 0;', 'END_IF;']

    up = '%s.LinkOk AND %s.State = %d AND %s.Channels[1].Quality' % (node, node, states['OPERATIONAL'], node)
    module_up = '%s.LinkOk AND %s.State = %d' % (module, module, states['OPERATIONAL'])
    module_down = 'NOT %s.LinkOk AND %s.State = %d' % (module, module, states['OFFLINE'])
    cases.append(['"FRK_Clock".NowMs := UDINT#1000;', '"F_PnTestPublish"();',
                  check(up, 'the device the CPU reports present makes its node operational and its input good'),
                  check(module_up, 'its present module (ModuleStates, slot from LOG2GEO) is operational'),
                  '#Step := 1;'])
    cases.append(actuate(DEACTIVATE, 'D_ACT_DP disables the device from the program'))
    cases.append([*sample(), check('NOT %s.LinkOk AND %s.State = %d AND NOT %s.Channels[1].Quality' % (node, node, states['OFFLINE'], node),
                                   'the next sample takes a disabled device, its node and its input offline'),
                  check(module_down, 'a module of a disabled device is offline with it'), '#Step := 3;'])
    cases.append(actuate(ACTIVATE, 'D_ACT_DP re-enables the device'))
    cases.append([*sample(), '#Scans := #Scans + 1;',
                  'IF %s.LinkOk OR #Scans > %d THEN' % (node, WAIT_SCANS),
                  '    ' + check(up, 'a re-enabled device returns its node to operational'),
                  '    ' + check(module_up, 'and its module with it'),
                  '    #Step := 5;', 'END_IF;'])
    body = ['    CASE #Step OF']
    for number, lines in enumerate(cases):
        body += ['        %d:' % number, *['            ' + line for line in lines]]
    body += ['        ELSE', '            #Scans := 0;', '    END_CASE;']
    # Force-job spike probe (no assertion): what the program can see of the CPU's LEDs.
    probe = ['    #LedReturn[%d] := LED(LADDR := "Local~Common", LED := %d);' % (led, led) for led in (1, 2, 3)]
    sources['37_ProfinetTest.scl'] = '\n'.join(['FUNCTION_BLOCK "FB_ProfinetTest"', "{ S7_Optimized_Access := 'TRUE' }", 'VERSION : 0.1',
        'VAR_OUTPUT', *['    ' + n + READONLY + ' : ' + t + ';' for n, t in [('Done', 'Bool'), ('Checks', 'Int'), ('Failures', 'Int'), ('FirstFailure', 'Int')]],
        '    LedReturn' + READONLY + ' : Array[1..3] of Int;  // STOP/RUN, ERROR, MAINT', 'END_VAR',
        'VAR', '    Result' + READONLY + ' : "FRK_TestResult";',
        *['    ' + n + PRIVATE + ' : ' + t + ';' for n, t in [('Step', 'Int'), ('Scans', 'Int'), ('Ret', 'Int'), ('Busy', 'Bool')]],
        'END_VAR', 'BEGIN', *body, *probe,
        '    #Done := #Step >= %d AND NOT #Result.ProtocolError; #Checks := #Result.Checks; #Failures := #Result.Failures; #FirstFailure := #Result.FirstFailure;' % len(cases),
        'END_FUNCTION_BLOCK', ''])
    sources['39_GDB_ProfinetTest.db'] = '\n'.join(['DATA_BLOCK "GDB_ProfinetTest"', "{ S7_Optimized_Access := 'TRUE' }", 'VERSION : 0.1', 'NON_RETAIN', '"FB_ProfinetTest"', 'BEGIN', 'END_DATA_BLOCK', ''])
    results = json.loads((HERE/'bench.json').read_bytes())['results']
    sources['39_%s.db' % results] = db(results, ['Status' + READONLY + ' : "FRK_TestStatus";'])
    sources['40_Main.scl'] = '\n'.join(['ORGANIZATION_BLOCK "Main"', "{ S7_Optimized_Access := 'TRUE' }", 'VERSION : 0.1', 'BEGIN', '    "GDB_ProfinetTest"();',
        '    "FRK_TestPublish"(Complete := "GDB_ProfinetTest".Done, ' + ', '.join('Image%d := DWORD#@IMAGE_HASH_%d@' % (i, i) for i in range(8))
        + ', Result := "GDB_ProfinetTest".Result, Status := "' + results + '".Status);', 'END_ORGANIZATION_BLOCK', ''])
    return seal_signature(sources, labels), labels


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('out', type=Path); a = p.parse_args()
    sources, labels = build(); a.out.mkdir(parents=True, exist_ok=False)
    for name, text in sources.items(): (a.out/name).write_bytes(text.encode('ascii'))
    (a.out/'image_hash.json').write_text(json.dumps(dict(sha256=signature(sources, labels)), indent=2) + '\n', encoding='ascii')
    (a.out/'assertions.json').write_text(json.dumps(dict(enumerate(labels, 1)), indent=2) + '\n', encoding='ascii')
    print(json.dumps(dict(sources=len(sources), checks=len(labels))))
