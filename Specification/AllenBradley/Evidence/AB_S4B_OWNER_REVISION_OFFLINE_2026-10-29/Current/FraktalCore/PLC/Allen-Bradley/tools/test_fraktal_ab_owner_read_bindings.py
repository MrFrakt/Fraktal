"""Contract, wire integrity and executable owner transactions for V6.10."""
from copy import deepcopy
from dataclasses import replace
import json
import unittest

import fraktal_ab_canonical_manifest as wire
import fraktal_ab_canonical_publication as pub
import fraktal_ab_config_read_view as view
import fraktal_ab_genealogy_s4b_demo as previous
import fraktal_ab_genealogy_s4b_owner_demo as profile
import fraktal_ab_owner_read_bindings as owner
import fraktal_ab_st_model as st
from test_fraktal_ab_read_coherence import physical


class OwnerReadBindingsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = profile.application()
        cls.schema = pub.schema(cls.app)
        cls.rows = owner.rows(cls.app, cls.schema)

    def test_scope_is_derived_without_inventing_child_config_revisions(self):
        self.assertEqual(len(self.rows), 8)
        self.assertEqual(sum(len(json.loads(r['MembersJson'])) for r in self.rows), 29)
        self.assertEqual(json.loads(self.rows[0]['MembersJson']), list(owner.HEADER_MEMBERS))
        self.assertTrue(all('ConfigRev' not in json.loads(r['MembersJson']) for r in self.rows[1:-1]))
        self.assertEqual(self.rows[-1]['CanonicalPrefix'], view.canonical_root(self.app))
        self.assertTrue(all(r['ProgressSymbol'] == pub.generation_tag(self.app)
                            and r['RevisionSymbol'] != r['ProgressSymbol'] for r in self.rows))

    def test_core_path_and_type_inventory_does_not_change(self):
        old = previous.application()
        self.assertEqual(pub.field_rows(old, pub.schema(old)), pub.field_rows(self.app, self.schema))
        self.assertEqual(owner.validate(self.app), [])
        self.assertTrue(owner.validate(replace(self.app, canonical_owner_revisions='yes')))
        self.assertTrue(owner.validate(replace(self.app, canonical_config_read_view=False)))

    def test_new_table_is_hash_covered_and_old_minor_remains_eight(self):
        header = pub.manifest_values(self.app, self.schema)
        normalized = wire.normalize(physical(header))
        self.assertEqual(normalized['schemaMinor'], 10)
        self.assertEqual(normalized['ownerReadBindings'], self.rows)
        damaged = deepcopy(header)
        damaged['OwnerReadBindings'][0]['MaximumProofWindowUs'] = 999999
        with self.assertRaisesRegex(ValueError, 'hash/revision'):
            wire.normalize(physical(damaged))
        self.assertEqual(pub.manifest_values(previous.application())['SchemaMinor'], 8)

    def test_invalid_owner_scope_and_bounds_refuse(self):
        vectors = [('Protocol', 1), ('Protocol', True), ('MinimumUpdateIntervalUs', 0),
                   ('MaximumProofWindowUs', 1000001), ('MaximumProofWindowUs', True),
                   ('ProgressSymbol', self.rows[0]['RevisionSymbol']),
                   ('MembersJson', '["Name","Name","ModuleType","State"]'),
                   ('MembersJson', '["Name","ModuleType","State","Secret"]'),
                   ('MembersJson', '[]'), ('CanonicalPrefix', 'Other/NotStatus')]
        for key, value in vectors:
            rows = deepcopy(self.rows); rows[0][key] = value
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                owner.validate_rows(rows, read_services=view.descriptors(self.app))
        with self.assertRaises(ValueError):
            owner.validate_rows(self.rows + [self.rows[0]], read_services=view.descriptors(self.app))

    def controller(self, revision=0, state=0, config=0):
        app = self.app
        counter = owner.header_revision(app, 0)
        protected = {app.name + '.Status.State', app.name + '.Status.ConfigRev'}
        class GuardedController(st.Controller):
            def write(controller, ref, value):
                if controller.describe(ref) in protected:
                    self.assertEqual(controller.tags[counter] % 2, 1,
                                     'protected bytes written outside owner transaction')
                super().write(ref, value)
        tags = {app.name:dict(Status=dict(State=state, ConfigRev=config)), 'S:FS':False}
        tags.update({owner.header_revision(app, i):0 for i in range(len(owner.module_paths(app)))})
        tags[counter] = revision
        return GuardedController(tags)

    def test_write_guard_refuses_an_unowned_header_assignment(self):
        with self.assertRaisesRegex(AssertionError, 'outside owner'):
            self.controller().run(self.app.name + '.Status.State := 1;')

    def test_two_header_changes_share_one_transaction_and_unchanged_scan_is_stable(self):
        controller = self.controller()
        lines = owner.write_header(self.app, 0, 'State', '1')
        controller.run('\n'.join(lines))
        counter = owner.header_revision(self.app, 0)
        self.assertEqual(controller.tags[counter], 1)
        cfg = owner.write_header(self.app, 0, 'ConfigRev', '23')
        controller.run('\n'.join(cfg)); self.assertEqual(controller.tags[counter], 1)
        controller.run('\n'.join(owner.close_headers(self.app)))
        self.assertEqual(controller.tags[counter], 2)
        controller.run('\n'.join(lines + cfg + owner.close_headers(self.app)))
        self.assertEqual(controller.tags[counter], 2)
        self.assertEqual(controller.tags[self.app.name]['Status'], dict(State=1, ConfigRev=23))

    def test_wrap_and_odd_recovery_never_publish_even_during_writes(self):
        for before, after in [(2147483646, 2), (3, 4)]:
            with self.subTest(before=before):
                controller = self.controller(revision=before)
                controller.run('\n'.join(owner.write_header(self.app, 0, 'State', '1')
                    + owner.close_headers(self.app)))
                self.assertEqual(controller.tags[owner.header_revision(self.app, 0)], after)


if __name__ == '__main__':
    unittest.main()
