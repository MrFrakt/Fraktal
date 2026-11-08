"""Increment C7 offline qualification: R5 production single-rendition selection.

Spec Requirement R5: A production declaration selects one AUTO rendition
(ST, SFC or LD). Acceptance declarations keep all three for the parity gate.
"""

from dataclasses import replace
from pathlib import Path
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fraktal_ab_declaration as decl
import fraktal_ab_generate as gen
import fraktal_ab_press_demo as press_demo
import fraktal_ab_press_echo38 as press_echo38
import fraktal_ab_station_template as template
import fraktal_ab_press_s6_collapse_echo38 as press_s6
import fraktal_ab_press_s6_shelving_echo38 as press_shelving
import fraktal_ab_genealogy_s6_collapse_demo as genealogy_s6
from test_fraktal_ab_generate import SEED_38


class CollapseC7RenditionTests(unittest.TestCase):
    def test_production_declarations_select_exactly_one_auto_rendition(self):
        """Production declarations must declare a single rendition per chain."""
        prod_apps = [
            ('press_demo', press_demo.application()),
            ('press_echo38', press_echo38.application()),
            ('station_template', template.application()),
        ]
        for name, app in prod_apps:
            auto = next(c for c in app.chains if c.name == 'AUTO')
            self.assertEqual(len(auto.renditions), 1, f'{name}: AUTO has {auto.renditions}')
            self.assertFalse(auto.multi_rendition, f'{name}: AUTO must not be multi_rendition')
            self.assertNotIn(gen.rendition_tag(app), gen.writable_inputs(app),
                             f'{name}: rendition tag must not be in writable inputs')
            self.assertNotIn(gen.rendition_tag(app), gen.harness_only_tags(app),
                             f'{name}: rendition tag must not be in harness-only tags')

    def test_acceptance_declarations_preserve_all_three_renditions_for_parity(self):
        """Acceptance declarations retain ST, SFC, LD for the parity gate."""
        acc_apps = [
            ('press_s6', press_s6.application()),
            ('press_shelving', press_shelving.application()),
            ('genealogy_s6', genealogy_s6.application()),
        ]
        for name, app in acc_apps:
            auto = next(c for c in app.chains if c.name == 'AUTO')
            self.assertEqual(auto.renditions, decl.RENDITIONS,
                             f'{name}: AUTO must carry all 3 renditions for parity')
            self.assertTrue(auto.multi_rendition, f'{name}: AUTO must be multi_rendition')
            self.assertIn(gen.rendition_tag(app), gen.controller_tags(app),
                          f'{name}: rendition selector must be emitted')

    def test_r5_production_selection_eliminates_routines_and_reduces_size(self):
        """Selecting one rendition on collapsed press saves 4 routines and ~96KB."""
        acc_app = press_s6.application()
        chains_1 = tuple(replace(c, renditions=(decl.LD,)) if c.name == 'AUTO' else c
                         for c in acc_app.chains)
        prod_app = replace(acc_app, chains=chains_1)

        with tempfile.TemporaryDirectory() as td:
            seed = Path(td) / 'seed.L5X'
            seed.write_text(SEED_38, encoding='utf-8')
            out_acc = Path(td) / 'acc.L5X'
            out_prod = Path(td) / 'prod.L5X'

            r_acc = gen.generate(acc_app, seed, out_acc)
            r_prod = gen.generate(prod_app, seed, out_prod)

            root_acc = ET.fromstring(out_acc.read_bytes())
            root_prod = ET.fromstring(out_prod.read_bytes())

            routs_acc = len(root_acc.findall('.//Routine'))
            routs_prod = len(root_prod.findall('.//Routine'))

            # R5 removes 4 routines: SeqAUTO_ST, SeqAUTO_SFC, SeqAUTO_SFC_Run, and selector
            self.assertEqual(routs_acc - routs_prod, 4)
            self.assertEqual(r_acc['Routines'] - r_prod['Routines'], 4)

            # Byte savings in 60-120KB range
            savings = out_acc.stat().st_size - out_prod.stat().st_size
            self.assertGreaterEqual(savings, 60_000)
            self.assertLessEqual(savings, 120_000)

            # ST tokens reduced by > 3,000
            tokens_acc = sum(len(line.text.split())
                             for r in root_acc.findall('.//Routine')
                             for line in r.findall('.//Line') if line.text)
            tokens_prod = sum(len(line.text.split())
                              for r in root_prod.findall('.//Routine')
                              for line in r.findall('.//Line') if line.text)
            token_savings = tokens_acc - tokens_prod
            self.assertGreaterEqual(token_savings, 3000)

    def test_single_rendition_may_be_any_language(self):
        """Any single language (ST, SFC, or LD) validates cleanly."""
        base = press_demo.application()
        for rendition in decl.RENDITIONS:
            chains = tuple(replace(c, renditions=(rendition,)) if c.name == 'AUTO' else c
                           for c in base.chains)
            app = replace(base, chains=chains)
            self.assertEqual(decl.validate(app), [], f'Single rendition {rendition} must validate')


if __name__ == '__main__':
    unittest.main()
