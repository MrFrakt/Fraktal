"""C4 storage narrowing: private state stays native; externally needed facts stay addressable."""
from collections import Counter
from dataclasses import replace
import unittest
import xml.etree.ElementTree as ET

import fraktal_ab_collapse as collapse
import fraktal_ab_generate as gen
import fraktal_ab_library as library
import fraktal_ab_manifest as manifest
import fraktal_ab_module_storage as storage
import fraktal_ab_press_s6_collapse_echo38 as press
import fraktal_ab_genealogy_s6_collapse_demo as genealogy


class Classification(unittest.TestCase):
    def layout(self, body, external='', *, speed=25):
        app = press.application()
        app = replace(app, modules=(replace(app.modules[0], speed_per_scan=speed),))
        module, = app.modules
        aoi = gen.module_aoi_name(app, module)
        text = (f'<AddOnInstructionDefinitions><AddOnInstructionDefinition Name="{aoi}">'
                f'<Parameters/><Routines><Routine><STContent><Line>{body}</Line></STContent></Routine></Routines>'
                '</AddOnInstructionDefinition></AddOnInstructionDefinitions>'
                f'<Programs><Program><Routine><STContent><Line>{external}</Line></STContent></Routine></Program></Programs>')
        return dict(storage.derive(app, text)[0][1])

    def test_private_read_write_state_becomes_local_and_unused_disappears(self):
        roles = self.layout('ExecutePrev := Execute; RunCount := RunCount + 1;')
        self.assertEqual(roles['ExecutePrev'], 'Local')
        self.assertEqual(roles['RunCount'], 'Local')
        self.assertEqual(roles['SchemaVersion'], 'Unused')

    def test_observed_output_and_externally_written_input_keep_parameters(self):
        roles = self.layout('OutImm_Pos := OutImm_Pos + Par_Speed;',
                            'x := FRK_Press_InstPressRam.OutImm_Pos; FRK_Press_InstPressRam.HoldRequest := 1;')
        self.assertEqual(roles['OutImm_Pos'], 'Output')
        self.assertEqual(roles['HoldRequest'], 'Input')

    def test_instance_specific_initial_value_cannot_become_a_type_default(self):
        self.assertEqual(self.layout('x := Par_Speed;', speed=17)['Par_Speed'], 'Input')
        self.assertEqual(self.layout('x := Par_Speed;', speed=25)['Par_Speed'], 'Local')

    def test_comments_and_strings_cannot_keep_a_dead_field(self):
        roles = self.layout("(* SchemaVersion := 1; *) s := 'ErrorCount';")
        self.assertEqual(roles['SchemaVersion'], 'Unused')
        self.assertEqual(roles['ErrorCount'], 'Unused')

    def test_whole_instance_copy_is_refused_instead_of_hiding_its_members(self):
        for code in ('CPS(FRK_Press_InstPressRam, Snapshot, 1);',
                     'UnknownOwner(FRK_Press_InstPressRam);'):
            with self.subTest(code=code), self.assertRaisesRegex(ValueError, 'whole module instance'):
                self.layout('', code)


class Owners(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = (press.application(), genealogy.application())
        cls.apps = tuple(storage.application(app) for app in cls.raw)

    def test_one_immutable_plan_does_not_mutate_the_declaration(self):
        for raw, app in zip(self.raw, self.apps):
            self.assertFalse(storage.planned(raw))
            self.assertIs(storage.application(app), app)
            self.assertEqual(raw.modules, app.modules)
            self.assertEqual(raw.fixture_observation, app.fixture_observation)

    def test_fixture_and_cross_owner_facts_remain_parameters(self):
        for app in self.apps:
            for surface, names in app.fixture_observation:
                if surface in ('Unit', 'Chart'):
                    continue
                module = next(m for m in app.modules if m.name == surface)
                roles = storage.roles(app, library.type_of(module))
                self.assertTrue(all(roles[name] in ('Input', 'Output') for name in names))
            counts = Counter(role for layout in storage.report(app).values() for role in layout.values())
            self.assertGreater(counts['Local'], 10)
            self.assertGreater(counts['Unused'], 0)
            self.assertGreater(counts['Output'], 0)

    def test_all_instance_initial_values_and_local_defaults_have_one_home(self):
        for raw, app in zip(self.raw, self.apps):
            definitions = {a.get('Name'): a for a in ET.fromstring('<A>' + gen.aoi_definitions(app) + '</A>').iter('AddOnInstructionDefinition')}
            for module in app.modules:
                mtype = library.type_of(module)
                roles = storage.roles(app, mtype)
                aoi = definitions[gen.module_aoi_name(app, module)]
                locals = {n.get('Name'): n for n in aoi.findall('./LocalTags/LocalTag')}
                parameters = {n.get('Name'): n for n in aoi.findall('./Parameters/Parameter')}
                tag = ET.fromstring(collapse.instance_data(gen.module_aoi_name(app,module), gen.module_initial_members(app,module)))
                values = {n.get('Name'): int(n.get('Value')) for n in tag.iter('DataValueMember')}
                for member in gen.module_initial_members(raw, module):
                    role = roles[member.name]
                    if role == 'Unused':
                        self.assertNotIn(member.name, parameters)
                        self.assertNotIn(member.name, locals)
                    elif role == 'Local':
                        self.assertNotIn(member.name, values)
                        self.assertNotIn(member.name, parameters)
                        self.assertEqual(int(locals[member.name].find('./DefaultData/DataValue').get('Value')), member.initial)
                    else:
                        self.assertNotIn(member.name, locals)
                        self.assertEqual(values[member.name], member.initial)
                        self.assertEqual(parameters[member.name].get('Usage'), role)

    def test_v5_metadata_does_not_point_at_hidden_or_removed_fields(self):
        for app in self.apps:
            for module in app.modules:
                roles = storage.roles(app, library.type_of(module))
                self.assertEqual({m.name for m in gen.module_members(module,app)},
                                 {name for name, role in roles.items() if role in ('Input','Output')})
            # This is the same member function manifest model calls for each
            # module; building it also catches capacity/count/key disagreements.
            self.assertTrue(manifest.evidence(app))

    def test_changed_aoi_signatures_have_new_names(self):
        for raw, app in zip(self.raw, self.apps):
            self.assertNotEqual(gen.unit_aoi_name(raw), gen.unit_aoi_name(app))
            for module in app.modules:
                self.assertNotEqual(gen.module_aoi_name(raw,module), gen.module_aoi_name(app,module))
                self.assertLessEqual(len(gen.module_aoi_name(app,module)),40)
            self.assertLessEqual(len(gen.unit_aoi_name(app)),40)
        # Same type, different externally required facts: a different signature
        # must have a different name even across applications.
        signatures = {}
        for app in self.apps:
            for module in app.modules:
                name = gen.module_aoi_name(app,module)
                signature = storage.roles(app,library.type_of(module))
                if name in signatures:
                    self.assertEqual(signatures[name],signature)
                signatures[name] = signature


if __name__ == '__main__':
    unittest.main()
