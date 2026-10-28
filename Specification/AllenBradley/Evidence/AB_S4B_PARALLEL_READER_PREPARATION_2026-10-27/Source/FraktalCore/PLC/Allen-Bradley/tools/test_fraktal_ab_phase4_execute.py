"""Native fixture expectations follow the declared Start permit's mode scope."""
import dataclasses
import unittest

import fraktal_ab_phase4_execute as fixture
import fraktal_ab_press_demo as demo


class StartReportScope(unittest.TestCase):
    def test_current_air_entry_is_auto_home_only(self):
        for mode, expected in ((demo.MODE_MANUAL, []), (demo.MODE_CHANGEOVER, []),
                               (demo.MODE_AUTO, [('project.condition.airPressureOk', 3)]),
                               (demo.MODE_HOME, [('project.condition.airPressureOk', 3)])):
            self.assertEqual(fixture.entry_conditions(mode), expected)

    def test_unscoped_legacy_permit_is_still_exercised_in_manual(self):
        app = dataclasses.replace(fixture.APP, start_permits=tuple(
            dataclasses.replace(permit, modes=()) for permit in fixture.APP.start_permits))
        self.assertEqual(fixture.entry_conditions(demo.MODE_MANUAL, app),
                         [('project.condition.airPressureOk', 3)])


if __name__ == '__main__':
    unittest.main()
