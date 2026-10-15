"""Generator boundaries for state freshness, owning logs and sink dependencies."""
import importlib.util
from pathlib import Path
import unittest

from fraktal_tia_binding import Catalog,REPO
import fraktal_tia_declaration as DECL
import fraktal_tia_generate as GEN
from fraktal_tia_alarms import ALARM,STATE

spec=importlib.util.spec_from_file_location('unit_alarm_fixture',REPO/'FraktalCore/PLC/Siemens/Tests/Unit/make_fixture.py')
FIX=importlib.util.module_from_spec(spec);spec.loader.exec_module(FIX)


class AlarmTests(unittest.TestCase):
    def state_model(self,body=None):
        v=FIX.declaration()
        v['types'][0]['logic']['cyclic']=body or '#OutImm.Cycles := BOOL_TO_UDINT("FRK_State"(Idx := 1, Key := \'project.state.atHome\', Ok := #Hal.Cell.Clamp.Permit));'
        return v

    def test_state_context_and_freshness_are_generated_only_for_consumers(self):
        s,m=GEN.build(DECL.validate(self.state_model()),True)
        root=next(v for k,v in s.items() if k.endswith('FB_DeclarationUnit.scl'))
        leaf=next(v for k,v in s.items() if k.endswith('FB_DeclarationCylinder.scl'))
        self.assertIn('Flags := #StateFlags, Count := #StateFlagCount, Touched := #StateTouched',root)
        self.assertLess(root.index('"FRK_StateSweep"'),root.index('"FRK_Begin"'))
        self.assertNotIn('StateFlags',leaf)
        self.assertIn(STATE.relative_to(REPO).as_posix(),m['runtime']['authority_inputs'])

    def test_conditional_and_duplicate_publishers_are_rejected(self):
        call='"FRK_State"(Idx := 1, Key := \'project.state.atHome\', Ok := TRUE)'
        for body in ('IF #Hal.Cell.Clamp.Permit THEN #OutImm.Cycles := BOOL_TO_UDINT('+call+'); END_IF;',
                     '#OutImm.Cycles := BOOL_TO_UDINT('+call+');\n#OutImm.Changes := BOOL_TO_UDINT('+call+');'):
            with self.assertRaises(DECL.DeclarationError):GEN.build(DECL.validate(self.state_model(body)),True)

    def test_state_bounds_and_frame_storage_cannot_be_bypassed(self):
        for body in ('"FRK_State"(Idx := 0, Key := \'x\', Ok := TRUE);',
                     '"FRK_State"(Idx := 13, Key := \'x\', Ok := TRUE);',
                     '"FRK_State"(Idx := 1, Key := \''+'x'*121+'\', Ok := TRUE);',
                     '#StateFlagCount := 1;', '"FRK_StateSweep"(Startup := FALSE);'):
            with self.assertRaises(DECL.DeclarationError):GEN.build(DECL.validate(self.state_model(body)),True)

    def test_assembly_cannot_be_invoked_from_project_modules(self):
        for body in ('#AlarmLog.Blocking := FALSE;','"FRK_AlarmClose"(Slot := 1);',
                     '"FRK_AlarmOperatorReset"(AlarmLog := #AlarmLog);'):
            v=FIX.declaration();v['types'][0]['logic']['Cyclic']=body
            with self.assertRaises(DECL.DeclarationError):GEN.build(DECL.validate(v),True)

    def test_event_capacities_and_sink_dependency_are_owned_by_authorities(self):
        v=FIX.declaration();v['event_sink']='F_SiteEventSink'
        s,m=GEN.build(DECL.validate(v),True)
        self.assertIn('F_SiteEventSink',m['runtime_dependencies'])
        self.assertIn('"F_SiteEventSink"(Ev := #Ev)',s['13_UnitServices.scl'])
        self.assertIn('Array[1..%d]'%Catalog.read().capacities['MAX_ALARM_RING'],s['02_FRK_AlarmLog.udt'])
        self.assertIn(ALARM.relative_to(REPO).as_posix(),m['runtime']['authority_inputs'])
        v.pop('event_sink');s,m=GEN.build(DECL.validate(v),True)
        self.assertNotIn('SinkEnabled',s['02_FRK_AlarmLog.udt'])

    def test_reset_and_fault_capture_follow_the_existing_lifecycle(self):
        s,m=GEN.build(DECL.validate(FIX.declaration()),True)
        root=next(v for k,v in s.items() if k.endswith('FB_DeclarationUnit.scl'))
        self.assertLess(root.index('"FRK_UnitConsume"'),root.index('"FRK_AlarmOperatorReset"'))
        self.assertLess(root.index('"FRK_AlarmOperatorReset"'),root.index('// ---- GENERATED: child call'))
        self.assertLess(root.index('"FRK_End"'),root.index('"FRK_AlarmCapture"'))
        self.assertIn('IF NOT #Unit.EvReset THEN',root)

    def test_retained_history_is_keyed_by_consumed_units_and_private(self):
        value=FIX.declaration();value['alarm_history']={'scopes':['StationA','StationB']}
        s,m=GEN.build(DECL.validate(value),True)
        from fraktal_tia_alarms import HISTORY
        count=sum(i['module_type']==1 for i in m['inventory']['instances'])
        storage=s['05_FRK_AlarmHistory.db']
        self.assertIn('VAR RETAIN',storage)
        self.assertIn('Array[1..%d]'%count,storage)
        self.assertNotIn("ExternalAccessible := 'True'",storage)
        self.assertIn(HISTORY.relative_to(REPO).as_posix(),m['runtime']['authority_inputs'])
        root=next(v for k,v in s.items() if k.endswith('FB_DeclarationUnit.scl'))
        self.assertLess(root.index('"FRK_AlarmBegin"'),root.index('"FRK_AlarmHistoryBoot"'))
        self.assertLess(root.index('"FRK_AlarmHistoryBoot"'),root.index('"FRK_AccessCyclic"'))
        self.assertNotIn('AlarmHistoryBoot',next(v for k,v in s.items() if k.endswith('FB_DeclarationCylinder.scl')))

    def test_history_checksums_follow_all_core_event_fields(self):
        from fraktal_tia_alarms import history_sources
        _,text=history_sources(Catalog.read())
        checksum=text[text.index('FUNCTION "FRK_AlarmEventCrc"'):text.index('FUNCTION "FRK_AlarmHistoryHeaderCrc"')]
        for field in Catalog.read().resolve(['ST_AlarmEvent'])['ST_AlarmEvent']:
            self.assertIn('#Ev.'+field['member'],checksum)
        self.assertIn('FRK_CrcByte',checksum)
        self.assertNotIn('CRC_POLYNOMIAL',text)
        self.assertIn('#AlarmLog.Truncated := TRUE;',text)
        self.assertNotIn('FRK_AlarmNotify',text)

    def test_retention_is_optional_and_only_deployed_units_are_selectable(self):
        value=FIX.declaration()
        s,m=GEN.build(DECL.validate(value),True)
        self.assertNotIn('05_FRK_AlarmHistory.db',s)
        self.assertNotIn('FRK_AlarmHistoryBoot',s['13_UnitServices.scl'])
        for scopes in (['missing'], ['StationA.Cell'], ['StationA','StationA'], ['stationa'], 'StationA'):
            value['alarm_history']={'scopes':scopes}
            with self.assertRaises(DECL.DeclarationError):DECL.validate(value)

    def test_project_cannot_clear_or_replace_retained_history(self):
        for body in ('"FRK_AlarmHistoryBoot"(Startup := TRUE);',
                     '"FRK_AlarmHistoryClear"(AlarmLog := #AlarmLog);',
                     '"FRK_AlarmHistoryHeaderSave"(AlarmLog := #AlarmLog);',
                     '"FRK_AlarmHistory".Rows[1].SchemaVersion := 0;'):
            value=FIX.declaration();value['types'][0]['logic']['Cyclic']=body
            with self.assertRaises(DECL.DeclarationError):GEN.build(DECL.validate(value),True)


if __name__=='__main__':unittest.main()
