"""Unit assembly, mutation surface and model authority before the TIA gate."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

import fraktal_tia_declaration as DECL
import fraktal_tia_generate as GEN
import tia_lint

spec=importlib.util.spec_from_file_location('unit_fixture',Path(__file__).resolve().parents[1]/'Tests/Unit/make_fixture.py')
FIXTURE=importlib.util.module_from_spec(spec);spec.loader.exec_module(FIXTURE)


class UnitTests(unittest.TestCase):
    def test_unit_profile_is_tier_and_catalog_checked(self):
        for change in ('tier','initial','command','duplicate','unknown'):
            value=FIXTURE.declaration(); unit=value['types'][0]['unit']
            if change=='tier':value['types'][1]['unit']=unit
            elif change=='initial':unit['initial']='CALIBRATION'
            elif change=='command':unit['run_command']=99
            elif change=='duplicate':unit['modes'].append('AUTO')
            else:unit['modes'].append('PRIVATE_MODE')
            with self.assertRaises(DECL.DeclarationError):DECL.validate(value)

    def test_unit_mailbox_is_writable_static_and_other_facets_read_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/'frames';GEN.generate(DECL.validate(FIXTURE.declaration()),out,True)
            self.assertEqual(tia_lint.lint([out]),[])
            block=next(b for p in out.glob('*.scl') for b in tia_lint.parse_blocks(p.read_text()) if b.name=='FB_DeclarationUnit')
            fields={d.name:d for d in block.decls}
            self.assertEqual(fields['HmiRequest'].section,'VAR')
            self.assertEqual(fields['HmiRequest'].attrs,'')
            for name in ('HmiResponse','Part','History','Access','ModeActivePublished'):
                self.assertIn("ExternalWritable := 'False'",fields[name].attrs)
            for name in ('Unit','ModePolicy','Device'):
                self.assertIn("ExternalAccessible := 'False'",fields[name].attrs)
            self.assertEqual(GEN.verify(out),len(list(p for p in out.iterdir() if p.suffix in ('.scl','.udt','.db'))))

    def test_management_precedes_consumption_and_reset_release_is_generated(self):
        sources,_=GEN.build(DECL.validate(FIXTURE.declaration()),True)
        frame=next(v for k,v in sources.items() if k.endswith('FB_DeclarationUnit.scl'))
        self.assertLess(frame.index('// ---- AUTHORED: cyclic management'),frame.index('"FRK_UnitConsume"'))
        self.assertLess(frame.index('"FRK_UnitConsume"'),frame.index('"FRK_RouteAbort"'))
        self.assertIn('"FRK_ReleaseCommand"(Core := #Cell.Core, Execute := #Cell.Execute);',frame)
        self.assertIn('"FRK_PartAborted"',frame)
        cell=next(v for k,v in sources.items() if k.endswith('FB_DeclarationCell.scl'))
        self.assertIn('"FRK_ReleaseCommand"(Core := #Clamp.Core',cell)

    def test_unit_state_and_assembly_cannot_be_written_in_authored_regions(self):
        for body in ('#Unit.RunReq := TRUE;','"FRK_UnitConsume"(Unit := #Unit);'):
            value=FIXTURE.declaration();value['types'][0]['logic']['Cyclic']=body
            with self.assertRaises(DECL.DeclarationError):GEN.build(DECL.validate(value),True)

    def test_nested_unit_requires_a_profile_and_manual_reaction_cannot_mutate(self):
        value=FIXTURE.declaration()
        value['types'][0]['children'].append({'name':'Subunit','type':'FB_Subunit'})
        import copy
        nested=copy.deepcopy(value['types'][0]);nested['name']='FB_Subunit'
        nested['children']=nested['children'][:1];del nested['unit']
        value['types'].append(nested);value['registry_capacity']=32
        with self.assertRaises(DECL.DeclarationError):GEN.build(DECL.validate(value),True)
        for body in ('#Device.CyclicCount := 0;', '"FRK_Fault"(Core := #Core);'):
            value=FIXTURE.declaration();value['types'][2]['logic']['ManRelease']=body
            with self.assertRaises(DECL.DeclarationError):GEN.build(DECL.validate(value),True)

    def test_catalog_and_typed_manual_route_are_derived_from_commands_and_tree(self):
        sources,_=GEN.build(DECL.validate(FIXTURE.declaration()),True)
        cylinder=next(v for k,v in sources.items() if k.endswith('FB_DeclarationCylinder.scl'))
        self.assertIn('CatalogCount',cylinder)
        self.assertIn('#Catalog[6].Value := 6;',cylinder)
        self.assertIn('#Catalog[6].Label := \'Instant\';',cylinder)
        self.assertIn('"FRK_ManualApply"',cylinder)
        unit=next(v for k,v in sources.items() if k.endswith('FB_DeclarationUnit.scl'))
        self.assertIn('"FRK_Route_DeclarationCell"(Module := #Cell',unit)
        self.assertIn('#Unit.Request.TargetPath',unit)

    def test_missing_or_overwritten_manual_condition_is_rejected_before_generation(self):
        for slots in ((0,), (17,), (1,1)):
            value=FIXTURE.declaration()
            value['types'][2]['logic']['ManRelease']='\n'.join(
                '    "FRK_ManualCondition"(Conditions := #ManConditions, Slot := %d, Value := 2, Ok := #Hal.Permit, Diag := #Hal.Diag, Bypassable := FALSE);' % slot for slot in slots)
            with self.assertRaises(DECL.DeclarationError):GEN.build(DECL.validate(value),True)

    def test_manifest_static_facets_are_private_and_generated_names_cannot_collide(self):
        sources,_=GEN.build(DECL.validate(FIXTURE.declaration()),True)
        block=next(b for text in sources.values() for b in tia_lint.parse_blocks(text) if b.name=='FB_DeclarationCylinder')
        for member in ('Catalog','CatalogCount'):
            declaration=next(d for d in block.decls if d.name==member)
            self.assertIn("ExternalAccessible := 'False'",declaration.attrs)
        for child in ('ConfigCursor','ConfigRev'):
            value=FIXTURE.declaration()
            value['types'][0]['children'][0]['name']=child
            with self.assertRaises(DECL.DeclarationError):GEN.build(DECL.validate(value),True)
        for body in ('#ConfigRev := 1;', '#Catalog[1].Value := 77;', '"FRK_ConfigFinish"(Page := #HmiResponse.ConfigPage);'):
            value=FIXTURE.declaration();value['types'][0]['logic']['Cyclic']=body
            with self.assertRaises(DECL.DeclarationError):GEN.build(DECL.validate(value),True)


if __name__=='__main__':unittest.main()
