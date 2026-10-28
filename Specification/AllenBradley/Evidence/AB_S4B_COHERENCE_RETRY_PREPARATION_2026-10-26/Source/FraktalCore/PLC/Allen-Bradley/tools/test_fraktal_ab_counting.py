from dataclasses import replace
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

import fraktal_ab_counting as counting
import fraktal_ab_declaration as decl
import fraktal_ab_generate as gen
import fraktal_ab_host_demo as host_demo
import fraktal_ab_part_demo as part_demo
import fraktal_ab_st_model as st
import test_fraktal_ab_rendition_cycle as cycle
from test_fraktal_ab_two_hand import aoi_scope


class VerdictOwnership(unittest.TestCase):
    def test_nok_then_good_cycle_counts_exactly_once_in_every_language(self):
        for language in decl.RENDITIONS:
            with self.subTest(language=language):
                bench = cycle.Press(language)
                unit = bench.plc.tags[cycle.UNIT]
                seen_finish = False
                for _ in range(1000):
                    bench.ctx('PressRam')['FaultRequest'] = int(bench.step() == 200)
                    if bench.step() == 210:
                        unit['DecisionAnswer'] = 1
                    seen_finish |= bench.step() == 999
                    bench.scan()
                    if seen_finish and bench.step() == 100:
                        break
                else:
                    self.fail('NOK cycle did not finish')
                self.assertEqual((unit['CycleCount'], unit['GoodCount'], unit['ScrapCount']), (1,0,1))
                self.assertEqual(bench.plc.tags[counting.tag(cycle.APP)]['Nok'], 0)
                bench.ctx('PressRam')['FaultRequest'] = 0
                unit['StartLatched'] = 1
                bench.plc.tags[cycle.TWO_HAND] = 0
                for _ in range(3):
                    bench.scan()
                bench.plc.tags[cycle.TWO_HAND] = 1
                bench.one_cycle()
                self.assertEqual((unit['CycleCount'], unit['GoodCount'], unit['ScrapCount']), (2,1,1))

    def test_reset_abort_and_mode_change_clear_only_the_cycle_latch(self):
        app = cycle.APP
        for trigger in ('ResetRequest','AbortRequest','ModeRequest'):
            with self.subTest(trigger=trigger):
                tags = aoi_scope()
                u = tags['Ctx']
                u.update(ScrapCount=5, GoodCount=3)
                u[trigger] = 1
                held = tags['CycleVerdict']
                held['Nok'] = 1
                st.Controller(tags).run('\n'.join(gen.unit_logic(app)))
                self.assertEqual(held['Nok'], 0)
                self.assertEqual((u['ScrapCount'],u['GoodCount']), (5,3))

    def test_carrier_owner_is_not_duplicated_and_private_layout_is_versioned(self):
        self.assertTrue(counting.enabled(host_demo.application()))
        app = part_demo.application()
        self.assertFalse(counting.enabled(app))
        self.assertNotIn('CycleVerdict', gen.controller_tags(app))
        tags = ET.fromstring(gen.controller_tags(cycle.APP))
        self.assertEqual(tags.find(f"Tag[@Name='{counting.tag(cycle.APP)}']").get('ExternalAccess'), 'None')
        self.assertIn('_CountV1', gen.unit_aoi_name(cycle.APP))
        self.assertNotIn('_CountV1', gen.unit_aoi_name(app))


if __name__ == '__main__':
    unittest.main()
