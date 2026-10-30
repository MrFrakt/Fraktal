"""Execute owner-versioned view publication against the existing page oracle."""
import unittest
from unittest.mock import patch

import fraktal_ab_canonical_publication as pub
import fraktal_ab_config_read_view as view
import fraktal_ab_genealogy_s4b_owner_demo as profile
import fraktal_ab_models as models
import fraktal_ab_owner_read_bindings as owner
import test_fraktal_ab_config_read_view as previous


class OwnerReadViewTests(unittest.TestCase):
    def setUp(self):
        app = profile.application()
        self.app = app
        self.case = case = previous.ReadViewTests()
        with patch.object(previous.profile, 'application', lambda: app):
            case.setUp()
        tags = case.controller.tags
        tags.update({owner.header_revision(app, i): 0 for i in range(len(owner.module_paths(app)))})
        tags[owner.view_revision(app)] = 0
        tags[owner.work_tag(app)] = case.value(owner.WORK)
        original_write = case.controller.write
        original_copy = case.controller.calls['CPS']
        counter = owner.view_revision(app)

        def guard(ref):
            name = case.controller.describe(ref)
            if name.startswith(view.tag(app) + '.'):
                self.assertEqual(tags[counter] % 2, 1, 'unowned view write: ' + name)

        def write(ref, value):
            guard(ref)
            original_write(ref, value)

        def copy(controller, arguments):
            guard(arguments[1])
            original_copy(controller, arguments)

        case.controller.write = write
        case.controller.calls['CPS'] = copy
        original_scan = case.scan

        def scan():
            original_scan()
            case.execute(owner.close_headers(app))
        case.scan = scan

    def revision(self):
        return self.case.controller.tags[owner.view_revision(self.app)]

    def test_all_pages_equal_oracle_and_unchanged_scans_keep_the_version(self):
        self.case.test_every_live_and_model_row_equals_the_existing_independent_page_oracle()
        first = self.revision()
        self.assertEqual(first, 2)
        self.case.scan()
        self.assertEqual(self.revision(), first)
        self.case.test_changed_values_and_banks_refresh_once_with_clean_string_tails()
        self.assertEqual(self.revision(), first + 2)

    def test_access_masking_and_retained_first_scan_remain_inside_the_owner(self):
        self.case.test_access_drop_wipes_full_value_buffers_and_does_not_publish_a_private_cache()
        self.assertEqual(self.revision(), 4)
        self.case.test_retained_first_scan_applies_access_drop_without_deferral()
        self.assertEqual(self.revision() % 2, 0)

    def test_cold_clear_invalid_count_and_recovery_are_change_owned(self):
        self.case.test_cold_first_scan_withholds_publication_and_wipes_until_next_scan()
        tags = self.case.controller.tags
        count = tags[models.tag(self.app)]['Count']
        tags[models.tag(self.app)]['Count'] = (self.app.model_capacity or len(self.app.models)) + 1
        self.case.scan()
        invalid = self.revision()
        self.assertEqual(self.case.read['ValueCount'], 0)
        self.case.scan()
        self.assertEqual(self.revision(), invalid)
        tags[models.tag(self.app)]['Count'] = count
        tags[pub.header_tag(self.app)]['Valid'] = 1
        self.case.test_every_live_and_model_row_equals_the_existing_independent_page_oracle()
        self.assertEqual(self.revision(), invalid + 2)


if __name__ == '__main__':
    unittest.main()
