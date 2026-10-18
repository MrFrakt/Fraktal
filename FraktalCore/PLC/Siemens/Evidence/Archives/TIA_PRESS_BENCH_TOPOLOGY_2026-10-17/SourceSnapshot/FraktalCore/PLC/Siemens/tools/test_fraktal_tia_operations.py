"""Production selection/ownership and native-runner result admission."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET

from fraktal_tia_binding import Catalog
from fraktal_tia_declaration import DeclarationError
import fraktal_tia_generate as gen
from fraktal_tia_operations import build
from fraktal_tia_test import junit

TIA=Path(__file__).resolve().parents[1]


def declaration():
    path=TIA/'Tests/Operations/make_frame_fixture.py'
    spec=importlib.util.spec_from_file_location('production_fixture',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module.declaration(calendar=False)


class ProductionTests(unittest.TestCase):
    def test_health_thresholds_cannot_bind_model_or_unregistered_storage(self):
        for source in ('ParCfg.Timeout','StationCfg.Missing','StationCfg.Grade'):
            value=declaration();unit=next(t for t in value['types'] if 'production' in t)
            unit['health']={'max_task_cycle':source}
            with self.subTest(source=source),self.assertRaises(DeclarationError):gen.build(gen.DECL.validate(value),True)

    def test_asset_identity_unique_and_bounded(self):
        value=declaration();value['nameplates']['StationB']=dict(value['nameplates']['StationA'])
        with self.assertRaises(DeclarationError):gen.DECL.validate(value)
        value=declaration();value['nameplates']['StationA']['SerialNumber']='s'*41
        with self.assertRaises(DeclarationError):gen.DECL.validate(value)

    def test_commissioning_gate_activity_is_a_build_fact(self):
        value=declaration();value['engineering_gates'][0]['active']='Hal.Switch'
        with self.assertRaises(DeclarationError):gen.DECL.validate(value)

    def test_capture_cannot_read_private_or_missing_or_wrongly_typed_source(self):
        for source in ('Device.Cycles','OutImm.Missing','OutImm.Resets'):
            value=declaration();unit=next(t for t in value['types'] if 'production' in t)
            field=next(f for f in unit['config'] if f['member']=='StationCfg.Gain')
            field['capture']=source
            with self.subTest(source=source),self.assertRaises(DeclarationError):gen.build(gen.DECL.validate(value),True)

    def test_services_derive_types_and_capacities(self):
        sources,_=build();facts=Catalog.read()
        self.assertIn('Array[1..%d]'%facts.capacities['MAX_OEE_SAMPLES'],sources['16a_ProductionServices.scl'])
        self.assertNotIn('@',''.join(sources.values()))
        self.assertIn(str(facts.defaults['OEE_SAMPLE_MS']),sources['16a_ProductionServices.scl'])

    def test_profile_replay_and_frame_ownership(self):
        value=declaration();model=gen.DECL.validate(value)
        sources,metadata=gen.build(model,True)
        frame=next(s for n,s in sources.items() if 'FB_DeclarationUnit.scl' in n)
        self.assertIn('"FRK_OeeTick"(',frame)
        self.assertIn('IdealCycleMs := #ParCfg.IdealCycleMs',frame)
        self.assertIn('BaselineMs := #ParCfg.BaselineMs',frame)
        self.assertIn('"FRK_ProductionRequest"(',frame)
        self.assertIn('ProductionBook {ExternalAccessible',frame)
        with tempfile.TemporaryDirectory() as folder:
            out=Path(folder)/'frames';gen.generate(model,out,True)
            self.assertEqual(gen.verify(out),len(sources))

    def test_profile_requires_registered_typed_config(self):
        for member in ('ParCfg.Missing','Hal.Signal','ParCfg.SchemaVersion'):
            value=declaration();unit=next(t for t in value['types'] if 'production' in t)
            unit['production']['ideal_cycle']=member
            with self.subTest(member=member),self.assertRaises(DeclarationError):gen.build(gen.DECL.validate(value),True)

    def test_calendar_is_validated_before_individual_or_whole_commits(self):
        path=TIA/'Tests/Operations/make_frame_fixture.py'
        spec=importlib.util.spec_from_file_location('calendar_fixture',path)
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        sources,_=gen.build(gen.DECL.validate(module.declaration()),True,line_workbench=True)
        line=sources['17_Line.scl'];sets=sources['18_LineSets.scl']
        self.assertIn('Values := #Stage',line)
        self.assertIn('NOT "FRK_LineValid"(Values := #Stage)',line)
        self.assertIn('#Phase = 1 OR #Phase = 4',sets)
        self.assertIn('"FRK_LineValid"',sets)
        self.assertIn('Values.ShiftStartMin[1] := -1',sources['05_FRK_LineDefaults.db'])
        self.assertIn('Values.ShiftDurationMin[1] := 1440',sources['05_FRK_LineDefaults.db'])

    def test_authored_logic_cannot_reimplement_accounting(self):
        for text in ('#Oee.RunMs := 1;','"FRK_OeeReset"();','#ProductionBook.GoodBase := 1;'):
            value=declaration();unit=next(t for t in value['types'] if 'production' in t)
            unit['logic']['cyclic']=text
            with self.subTest(text=text),self.assertRaises(DeclarationError):gen.build(gen.DECL.validate(value),True)

    def test_application_cannot_replace_identity_events_or_pacing_authority(self):
        for text in ('#HostEvents.Count := 0;','#HostSeenSequence := 5;','#RunStyle := 1;',
                     '"FRK_HostMirror"();','"FRK_RunStylePrepare"();'):
            value=declaration();unit=next(t for t in value['types'] if 'production' in t)
            unit['logic']['Cyclic']=text
            with self.subTest(text=text),self.assertRaises(DeclarationError):gen.build(gen.DECL.validate(value),True)

    def test_runtime_service_names_cannot_be_deployed_as_roots(self):
        for name in ('FRK_HostStore','FRK_HostEmit','FRK_EngineeringManifest'):
            value=declaration();value['registry_capacity']=64
            value['roots'].append(dict(name=name,type=value['roots'][0]['type']))
            with self.subTest(name=name),self.assertRaisesRegex(DeclarationError,'reserved block names collide'):gen.build(gen.DECL.validate(value),True)

    def test_junit_never_turns_missing_results_into_pass(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'result.xml'
            self.assertFalse(junit(p,'bench',{'1':'first'},{}))
            self.assertEqual(ET.parse(p).getroot().attrib['failures'],'1')

    def test_junit_records_the_native_assertion_count(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'result.xml'
            self.assertTrue(junit(p,'bench',{'1':'first'},dict(Done=True,Checks=1,Failures=0,FirstFailure=0)))
            self.assertEqual(ET.parse(p).getroot().attrib['failures'],'0')


if __name__=='__main__':unittest.main()
