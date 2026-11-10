"""The P9 reusable module types composed under one root Unit, compiled and run.

Every type is bound by the same function the press uses (command labels from
the type's own catalog, band reasons from the TC3 module reason list), and the
typed APIs call the same sequence runtime the press ships. Nothing here is
station logic: the root only owns the three modules so each is instantiated.
The case driver replaces Main and asserts the TC3 suite rows natively.
"""
import argparse
import json
from pathlib import Path
import re
import sys

HERE = Path(__file__).resolve().parent
TIA = HERE.parents[1]
sys.path.insert(0, str(TIA / 'tools'))
import fraktal_tia_declaration as DECL
import fraktal_tia_generate as GEN
from fraktal_tia_binding import Catalog, READONLY, REPO
from fraktal_tia_examples import TC3_MODULE_REASONS, bind, module_type, sequence_sources
from fraktal_tia_test_runtime import build as test_runtime, seal_signature, signature

MODULES = TIA / 'Framework/Modules'
# (directory, stem, api source name or None); the cylinder is the clamp's child.
TYPES = ((MODULES / 'EquipmentModules/Clamp', 'clamp', '22_ClampApi.scl'),
         (MODULES / 'ControlModules/ConfigurableCylinder', 'configurable_cylinder', '22_ConfigurableCylinderApi.scl'),
         (MODULES / 'ControlModules/Separator', 'separator', '22_SeparatorApi.scl'),
         (MODULES / 'ControlModules/Cylinder', 'cylinder', '22_CylinderApi.scl'))
LEASE = ('STRUCT OwnerIndex : DINT; ChainIndex : DINT; BranchIndex : DINT; '
         'Step : DINT; Raised : BOOL; AbortIssued : BOOL; ReleasedScan : UDINT; END_STRUCT')


def declaration(catalog):
    records = {'ST_SequenceCommandLease': LEASE,
               'ST_BenchUnitParCfg': 'STRUCT SchemaVersion : UINT := 1; Timeout : TIME := T#10s; END_STRUCT',
               'ST_BenchUnitParCmd': 'STRUCT Reserved : BOOL; END_STRUCT',
               'ST_BenchUnitOutCmd': 'STRUCT Done : BOOL; END_STRUCT',
               'ST_BenchUnitOutImm': 'STRUCT Ready : BOOL; END_STRUCT'}
    types = []
    for directory, stem, _ in TYPES:
        module, module_records = module_type(directory, stem, catalog)
        records.update(module_records)
        types.append(module)
    unit = {'name': 'FB_BenchUnit', 'tier': 'UNIT', 'type_key': 'bench.reusableModulesUnit',
            'children': [{'name': 'Clamp', 'type': 'FB_ClampEM'},
                         {'name': 'ConfigCyl', 'type': 'FB_ConfigurableCylinderCM'},
                         {'name': 'Separator', 'type': 'FB_SeparatorCM'}],
            'contract': {k: 'ST_BenchUnit' + k for k in ('ParCfg', 'ParCmd', 'OutCmd', 'OutImm')},
            'commands': [{'id': 1, 'label': 'Run'}], 'timeout': 'Timeout',
            'unit': {'modes': ['AUTO', 'MANUAL'], 'initial': 'MANUAL', 'run_command': 1},
            # The typed module APIs are called from chains; a sequence view is
            # what brings the chain runtime they bind against into the program.
            'sequence_view': {'capacity': 8, 'branches': 2, 'annotations': 4},
            'logic': {'cyclic': '    #OutImm.Ready := TRUE;'}}
    return {'schema_version': 1, 'target_family': 'S7-1500', 'registry_capacity': 16,
            'types': [unit, *types], 'roots': [{'name': 'BenchUnit', 'type': 'FB_BenchUnit'}],
            'records': records}


ROOT, HAL = '"BenchUnit"', '"GDB_FraktalHal".Data.BenchUnit'


class Cases:
    """One case per scan with an injected clock: writes, then one scan of the
    root exactly as the composition runs it, then assertions (Lifecycle form)."""

    def __init__(self, catalog):
        self.catalog, self.rows, self.labels = catalog, [], []

    def scan(self, now, writes=(), checks=()):
        code = ['        %d:' % len(self.rows), *['            ' + w for w in writes],
                '            "FRK_Clock".NowMs := UDINT#%d;' % now,
                '            "FRK_AccessStoreBoot"(Startup := #Startup);',
                '            %s(ParentIndex := 0, Startup := #Startup, Hal := %s);' % (ROOT, HAL)]
        for condition, label in checks:
            self.labels.append(label)
            code.append('            "FRK_TestAssert"(Condition := %s, Code := %d, Result := "GDB_ModulesTest".Result);' % (condition, len(self.labels)))
        self.rows.append('\n'.join(code))


def cases(catalog):
    """TC3 suite rows (FB_ConfigurableCylinderCM/Separator/ClampEM_Tests) on the
    TIA types, plus the configured abort/timeout reactions TC3 implements."""
    run = Cases(catalog)
    state = catalog.enums['E_ExecState']
    cc, hc = ROOT + '.ConfigCyl', HAL + '.ConfigCyl'
    sp, hs = ROOT + '.Separator', HAL + '.Separator'
    cl, ca, cb = ROOT + '.Clamp', ROOT + '.Clamp.CylA', ROOT + '.Clamp.CylB'
    ha, hb = HAL + '.Clamp.CylA', HAL + '.Clamp.CylB'

    def diag(prefix, reason, path, text):
        return ['%s.ReasonCode := %d;' % (prefix, reason), "%s.SourcePath := WSTRING#'%s';" % (prefix, path),
                "%s.Description := WSTRING#'%s';" % (prefix, text)]

    def error(module, reason, path):
        return ("%s.Error AND %s.ErrorID = DWORD#%d AND %s.Status.Diagnostic.ReasonCode = %d AND %s.Status.Diagnostic.SourcePath = WSTRING#'%s'"
                % (module, module, reason, module, reason, module, path))
    interlock = catalog.enums['E_Reason']['INTERLOCK_DROPPED']
    timeout = catalog.enums['E_Reason']['TIMEOUT']
    unsupported = catalog.enums['E_Reason']['UNSUPPORTED_COMMAND']
    reasons = dict(re.findall(r'\b(\w+)\s*:\s*DINT\s*:=\s*(\d+)', (REPO / TC3_MODULE_REASONS).read_text('utf-8-sig')))
    r = {k: int(v) for k, v in reasons.items()}

    # Startup: every permit up, the duplex cylinder at home, the clamp open.
    run.scan(1000, ['%s.ToHomePermit := TRUE; %s.ToWorkPermit := TRUE;' % (hc, hc),
                    '%s.HomeFb[1] := TRUE; %s.HomeFb[2] := TRUE;' % (hc, hc),
                    '%s.ParCfg.HomeSensorCount := 2; %s.ParCfg.WorkSensorCount := 2;' % (cc, cc),
                    '%s.Permit := TRUE;' % hs,
                    *['%s.ExtendPermit := TRUE; %s.RetractPermit := TRUE; %s.FeedbackRetracted := TRUE;' % (h, h, h) for h in (ha, hb)]],
             [('%s.Status.State = %d AND %s.OutImm.AtHome AND %s.OutImm.Position = 1' % (cc, state['READY'], cc, cc), 'duplex cylinder starts READY at home'),
              ('%s.Status.State = %d AND %s.Status.State = %d AND %s.OutImm.Unclamped' % (sp, state['READY'], cl, state['READY'], cl), 'separator and clamp start READY, clamp open')])
    # ---- Configurable cylinder: duplex agreement, settle, discrepancy.
    run.scan(1010, ['%s.Command := 2; %s.Execute := TRUE;' % (cc, cc)],
             [('%s.Busy AND %s.ToWorkOut AND NOT %s.ToHomeOut' % (cc, hc, hc), 'TO_WORK energizes only the work output')])
    run.scan(1020, ['%s.HomeFb[1] := FALSE; %s.HomeFb[2] := FALSE; %s.WorkFb[1] := TRUE;' % (hc, hc, hc)],
             [('%s.Busy AND NOT %s.OutImm.AtWork' % (cc, cc), 'one of two work sensors is not arrival')])
    run.scan(1030, ['%s.WorkFb[2] := TRUE;' % hc], [('%s.Busy' % cc, 'all sensors agree, settle starts')])
    run.scan(1079, checks=[('%s.Busy' % cc, 'settle time not yet elapsed')])
    run.scan(1080, checks=[('%s.Done AND %s.OutCmd.ReachedPosition = 2 AND %s.ToWorkOut' % (cc, cc, hc), 'duplex all agree completes at WORK and holds the output')])
    run.scan(1090, ['%s.Execute := FALSE;' % cc], [('%s.Status.State = %d' % (cc, state['READY']), 'Execute drop returns READY')])
    run.scan(1100, ['%s.WorkFb[2] := FALSE;' % hc], [('NOT %s.Error' % cc, 'a sensor split is not yet a discrepancy')])
    run.scan(1299, checks=[('NOT %s.Error' % cc, 'discrepancy waits DiscrepancyTime')])
    run.scan(1300, checks=[(error(cc, r['CYL_DISCREPANCY'], 'BenchUnit.ConfigCyl'), 'persistent split faults CYL_DISCREPANCY with the module path')])
    # ---- HELD (Core 6.1): a lost permit holds, withholds the output, and a hold
    # longer than MoveTimeout must not turn into a timeout on release.
    run.scan(1310, ['%s.WorkFb[2] := TRUE; %s.Command := 1; %s.Execute := TRUE;' % (hc, cc, cc)],
             [('%s.Busy AND %s.ErrorID = DWORD#0 AND %s.ToHomeOut' % (cc, cc, hc), 'new command after a background fault drives TO_HOME')])
    run.scan(1320, ['%s.ToHomePermit := FALSE;' % hc, *diag(hc + '.ToHomePermitDiag', interlock, 'BenchUnit.Area', 'test.areaUnsafe')],
             [("%s.Busy AND %s.Held AND NOT %s.Error AND NOT %s.ToHomeOut AND %s.Status.Diagnostic.ReasonCode = %d AND %s.Status.Diagnostic.SourcePath = WSTRING#'BenchUnit.Area'"
               % (cc, cc, cc, hc, cc, interlock, cc), 'T3: lost permit holds and withholds the output')])
    run.scan(10320, checks=[('%s.Held AND NOT %s.Error' % (cc, cc), 'a hold beyond MoveTimeout stays HELD')])
    run.scan(10330, ['%s.ToHomePermit := TRUE;' % hc],
             [('%s.Busy AND NOT %s.Held AND NOT %s.Error AND %s.ToHomeOut' % (cc, cc, cc, hc), 'permit return resumes without consuming MoveTimeout')])
    run.scan(10340, ['%s.HomeFb[1] := TRUE; %s.HomeFb[2] := TRUE; %s.WorkFb[1] := FALSE; %s.WorkFb[2] := FALSE;' % (hc, hc, hc, hc)])
    run.scan(10400, checks=[('%s.Done AND %s.OutCmd.ReachedPosition = 1' % (cc, cc), 'resumed move completes at HOME')])
    run.scan(10410, ['%s.Execute := FALSE;' % cc])
    # ---- Timeout: ResetOnTimeout withdraws, and FALSE keeps the coil (TC3).
    run.scan(10420, ['%s.Command := 2; %s.Execute := TRUE;' % (cc, cc)], [('%s.Busy AND %s.ToWorkOut' % (cc, hc), 'TO_WORK started')])
    run.scan(18400, checks=[('%s.Busy' % cc, 'MoveTimeout not yet elapsed')])
    run.scan(18440, checks=[(error(cc, r['CYL_WORK_NOT_REACHED'], 'BenchUnit.ConfigCyl') + ' AND NOT %s.ToWorkOut' % hc, 'timeout faults CYL_WORK_NOT_REACHED and ResetOnTimeout withdraws')])
    run.scan(18450, ['%s.Execute := FALSE; %s.ParCfg.ResetOnTimeout := FALSE;' % (cc, cc)])
    run.scan(18460, ['%s.Execute := TRUE;' % cc], [('%s.Busy' % cc, 'TO_WORK with ResetOnTimeout FALSE')])
    run.scan(26480, checks=[(error(cc, r['CYL_WORK_NOT_REACHED'], 'BenchUnit.ConfigCyl') + ' AND %s.ToWorkOut' % hc, 'ResetOnTimeout FALSE keeps the coil after the timeout fault')])
    run.scan(26490, ['%s.Execute := FALSE; %s.ParCfg.ResetOnTimeout := TRUE;' % (cc, cc)])
    # ---- Abort: the configured safe position, or de-energized by default.
    run.scan(26500, ['%s.ParCfg.DeenergizeOnAbort := FALSE; %s.ParCfg.SafePosOnAbort := 2; %s.Command := 1; %s.Execute := TRUE;' % (cc, cc, cc, cc)],
             [('%s.Busy' % cc, 'TO_HOME before abort')])
    run.scan(26510, ['%s.Abort := TRUE;' % cc], [('%s.Aborted AND %s.ToWorkOut AND NOT %s.ToHomeOut' % (cc, hc, hc), 'abort drives the configured safe position WORK')])
    run.scan(26520, checks=[('%s.Aborted AND %s.ToWorkOut' % (cc, hc), 'the safe position is held while ABORTED')])
    run.scan(26530, ['%s.Abort := FALSE; %s.Execute := FALSE; %s.ParCfg.DeenergizeOnAbort := TRUE; %s.ParCfg.SafePosOnAbort := 0;' % (cc, cc, cc, cc)])
    run.scan(26540, ['%s.Command := 1; %s.Execute := TRUE;' % (cc, cc)])
    run.scan(26550, ['%s.Abort := TRUE;' % cc], [('%s.Aborted AND NOT %s.ToWorkOut AND NOT %s.ToHomeOut' % (cc, hc, hc), 'DeenergizeOnAbort releases both outputs')])
    run.scan(26560, ['%s.Abort := FALSE; %s.Execute := FALSE;' % (cc, cc)])
    run.scan(26570, ['%s.ParCfg.TravelTime := T#9s; %s.Command := 2; %s.Execute := TRUE;' % (cc, cc, cc)],
             [(error(cc, r['CYL_CFG_INVALID'], 'BenchUnit.ConfigCyl'), 'TravelTime the MoveTimeout cannot contain is CYL_CFG_INVALID')])
    run.scan(26580, ['%s.Execute := FALSE; %s.ParCfg.TravelTime := T#0ms;' % (cc, cc)])
    # ---- Separator: interlock holds, one carrier released, close delay.
    run.scan(30000, ['%s.Permit := FALSE;' % hs, *diag(hs + '.PermitDiagnostic', interlock, 'BenchUnit.Feed', 'test.feedUnsafe')],
             [('%s.Status.State = %d AND NOT %s.ValveOpen' % (sp, state['READY'], hs), 'a missing permit while idle is not a fault')])
    run.scan(30010, ['%s.Command := 1; %s.Execute := TRUE;' % (sp, sp)])
    run.scan(30020, checks=[('%s.Busy AND %s.Held AND NOT %s.Error AND NOT %s.ValveOpen AND %s.Status.Diagnostic.ReasonCode = %d' % (sp, sp, sp, hs, sp, interlock),
                             'T3: interlock withholds the valve and holds rather than faults')])
    run.scan(30030, ['%s.Permit := TRUE;' % hs], [('%s.Busy AND NOT %s.Held AND %s.ValveOpen' % (sp, sp, hs), 'permit return opens the valve')])
    run.scan(30040, ['%s.CarrierAt := TRUE;' % hs])
    run.scan(30050, ['%s.CarrierAt := FALSE;' % hs])
    run.scan(30060, ['%s.CarrierAfter := TRUE;' % hs], [('%s.Busy AND %s.ValveOpen' % (sp, hs), 'carrier arrived after the separator')])
    run.scan(30559, checks=[('%s.ValveOpen' % hs, 'close delay not yet elapsed')])
    run.scan(30560, checks=[('%s.Busy AND NOT %s.ValveOpen' % (sp, hs), 'valve closes after CloseDelay')])
    run.scan(30570, ['%s.CarrierAfter := FALSE;' % hs], [('%s.Done AND %s.OutCmd.SeparateOk' % (sp, sp), 'separate releases one carrier and completes')])
    run.scan(30580, ['%s.Execute := FALSE; %s.ParCfg.CheckAfter := FALSE;' % (sp, sp)])
    run.scan(30590, ['%s.Execute := TRUE;' % sp])
    run.scan(30600, checks=[('%s.Busy AND %s.ValveOpen' % (sp, hs), 'CheckAfter FALSE separate opens')])
    run.scan(30610, ['%s.CarrierAt := TRUE;' % hs])
    run.scan(30620, ['%s.CarrierAt := FALSE;' % hs])
    run.scan(30630, checks=[('%s.Busy AND %s.ValveOpen' % (sp, hs), 'without CheckAfter the close delay still starts at release')])
    run.scan(31120, checks=[('%s.Done AND NOT %s.ValveOpen AND %s.OutCmd.SeparateOk' % (sp, hs, sp), 'without CheckAfter the valve closes after CloseDelay and completes')])
    run.scan(31130, ['%s.Execute := FALSE; %s.ParCfg.CheckAfter := TRUE;' % (sp, sp)])
    run.scan(31140, ['%s.Execute := TRUE;' % sp])
    run.scan(32140, checks=[('%s.Busy' % sp, 'waiting for a carrier within MaxOpenTime')])
    run.scan(34240, checks=[(error(sp, r['SEP_NO_CARRIER_AT'], 'BenchUnit.Separator') + ' AND NOT %s.ValveOpen' % hs, 'no carrier at the separator faults 10001 and closes')])
    run.scan(34250, ['%s.Execute := FALSE;' % sp])
    run.scan(34260, ['%s.Command := 9; %s.Execute := TRUE;' % (sp, sp)],
             [('%s.Error AND %s.ErrorID = DWORD#%d' % (sp, sp, unsupported), 'unsupported command is rejected')])
    run.scan(34270, ['%s.Execute := FALSE; %s.Command := 1;' % (sp, sp)])
    # ---- Clamp EM: both children, T3 through the EM, child first-out rollup.
    run.scan(40000, ['%s.Command := 1; %s.Execute := TRUE;' % (cl, cl)], [('%s.Busy' % cl, 'CLAMP started')])
    run.scan(40010, checks=[('%s.Busy AND %s.Busy AND %s.CoilExtend AND %s.CoilExtend' % (ca, cb, ha, hb), 'EM commands both children in parallel')])
    run.scan(40020, ['%s.FeedbackRetracted := FALSE; %s.FeedbackExtended := TRUE; %s.FeedbackRetracted := FALSE; %s.FeedbackExtended := TRUE;' % (ha, ha, hb, hb)])
    run.scan(40030)
    run.scan(40250, checks=[('%s.Done AND %s.OutCmd.Confirmed AND %s.OutImm.Clamped' % (cl, cl, cl), 'clamp confirms both children after SettleTime')])
    run.scan(40260, ['%s.Execute := FALSE;' % cl])
    run.scan(40270, ['%s.RetractPermit := FALSE;' % ha, *diag(ha + '.RetractDiagnostic', interlock, 'BenchUnit.Clamp.CylA', 'test.clampAreaUnsafe'),
                     '%s.Command := 2; %s.Execute := TRUE;' % (cl, cl)])
    run.scan(40280)
    run.scan(40290, checks=[("%s.Held AND %s.Busy AND NOT %s.Error AND %s.Status.Diagnostic.ReasonCode = %d AND %s.Status.Diagnostic.SourcePath = WSTRING#'BenchUnit.Clamp.CylA'"
                              % (cl, cl, cl, cl, interlock, cl), 'T3 through the EM names the blocked child'),
                             ('NOT %s.CoilRetract AND NOT %s.Error' % (ha, cb), 'interlocked child withholds its output, partner keeps its command')])
    run.scan(40300, ['%s.RetractPermit := TRUE;' % ha])
    run.scan(40310, ['%s.FeedbackExtended := FALSE; %s.FeedbackRetracted := TRUE; %s.FeedbackExtended := FALSE; %s.FeedbackRetracted := TRUE;' % (ha, ha, hb, hb)])
    run.scan(40320)
    run.scan(40550, checks=[('%s.Done AND NOT %s.Held AND %s.OutCmd.Confirmed AND %s.OutImm.Unclamped' % (cl, cl, cl, cl), 'the held unclamp completes when the permit returns')])
    run.scan(40560, ['%s.Execute := FALSE; %s.ParCfg.Timeout := T#1s;' % (cl, cb)])
    run.scan(40570, ['%s.Command := 1; %s.Execute := TRUE;' % (cl, cl)])
    run.scan(40580, ['%s.FeedbackRetracted := FALSE; %s.FeedbackExtended := TRUE;' % (ha, ha)])
    run.scan(42080, checks=[(error(cl, timeout, 'BenchUnit.Clamp.CylB'), 'EM adopts the CylB first-out verbatim, naming CylB')])
    run.scan(42090, ['%s.Execute := FALSE;' % cl])
    return run


def build():
    catalog = Catalog.read()
    sources, manifest = GEN.build(DECL.validate(declaration(catalog)), True)
    sources.update(sequence_sources(catalog))
    for directory, stem, api in TYPES:
        commands = {c['label']: c['id'] for c in json.loads((directory / (stem + '.json')).read_bytes())['commands']}
        sources[api] = bind((directory / (stem + '_api.scl.in')).read_text('ascii'), catalog, commands)
    sim = MODULES / 'ControlModules/ConfigurableCylinder/configurable_cylinder_sim.scl.in'
    sources['38_ConfigurableCylinderSim.scl'] = bind(sim.read_text('ascii'), catalog)
    # Native behaviour: the case driver replaces the composition's Main.
    run = cases(catalog)
    results = json.loads((HERE / 'bench.json').read_bytes())['results']
    sources.update(test_runtime())
    sources['39_GDB_ModulesTest.db'] = GEN.db('GDB_ModulesTest', ['CaseNo : DInt;', 'Result : "FRK_TestResult";'])
    sources['39_GDB_ModulesResultTest.db'] = GEN.db(results, ['Status' + READONLY + ' : "FRK_TestStatus";'])
    sources['38_ModulesCases.scl'] = '\n'.join([
        'FUNCTION "FRK_ModulesCases" : Void', "{ S7_Optimized_Access := 'TRUE' }", 'VERSION : 0.1',
        'VAR_TEMP', '    Startup : Bool;', 'END_VAR', 'BEGIN',
        '    #Startup := "GDB_ModulesTest".CaseNo = 0;',
        '    IF #Startup THEN "FRK_Registry".Count := 0; "FRK_Registry".Fault := FALSE; END_IF;',
        '    CASE "GDB_ModulesTest".CaseNo OF', *run.rows, '        ELSE', '            ;', '    END_CASE;',
        '    IF "GDB_ModulesTest".CaseNo < %d THEN "GDB_ModulesTest".CaseNo := "GDB_ModulesTest".CaseNo + 1; END_IF;' % len(run.rows),
        'END_FUNCTION', ''])
    sources['40_Main.scl'] = '\n'.join([
        'ORGANIZATION_BLOCK "Main"', "{ S7_Optimized_Access := 'TRUE' }", 'VERSION : 0.1', 'BEGIN',
        '    "FRK_ModulesCases"();',
        '    "FRK_TestPublish"(Complete := "GDB_ModulesTest".CaseNo >= %d, ' % len(run.rows)
        + ', '.join('Image%d := DWORD#@IMAGE_HASH_%d@' % (i, i) for i in range(8))
        + ', Result := "GDB_ModulesTest".Result, Status := "%s".Status);' % results,
        'END_ORGANIZATION_BLOCK', ''])
    return seal_signature(sources, run.labels), manifest, run.labels


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('out', type=Path)
    a = p.parse_args()
    sources, _, labels = build()
    a.out.mkdir(parents=True, exist_ok=False)
    for name, text in sources.items():
        (a.out / name).write_bytes(text.encode('ascii'))
    (a.out / 'image_hash.json').write_text(json.dumps(dict(sha256=signature(sources, labels)), indent=2) + '\n', encoding='ascii')
    (a.out / 'assertions.json').write_text(json.dumps(dict(enumerate(labels, 1)), indent=2) + '\n', encoding='ascii')
    print(json.dumps(dict(sources=len(sources), checks=len(labels))))
