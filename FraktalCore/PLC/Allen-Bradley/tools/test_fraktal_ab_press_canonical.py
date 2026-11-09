"""The press S3 exit candidate is the press declaration plus only accepted choices."""
from dataclasses import fields, replace
import re
import sys
import unittest
from unittest.mock import patch

import fraktal_ab_declaration as decl
import fraktal_ab_genealogy_s3k_demo as genealogy
import fraktal_ab_press_canonical_echo38 as candidate
import fraktal_ab_press_demo as press
import fraktal_ab_press_echo38 as echo
import fraktal_ab_press_rendition_echo38 as oracle

CANONICAL = ('canonical_publication_stage', 'canonical_observation_period_ms', 'canonical_table_driven',
             'canonical_type_manifest', 'canonical_io_fixture')


def changed(a, b):
    # Compatibility metadata (compare=False, such as O12's predecessors) is not content.
    return {f.name for f in fields(a) if f.compare and getattr(a, f.name) != getattr(b, f.name)}


# Legacy contract pruned


class DeclarationTests(unittest.TestCase):
    def test_candidate_adds_only_the_accepted_s3k_choices_and_validates(self):
        app, base = candidate.application(), oracle.application()
        self.assertFalse(decl.validate(app))
        self.assertEqual(changed(app, base), {*CANONICAL, 'io_modules'})
        self.assertEqual({n: getattr(app, n) for n in CANONICAL}, {n: getattr(genealogy.application(), n) for n in CANONICAL})
        self.assertEqual([m.sample_tag for m in app.io_modules], ['FRK_Press_SimIo'])

    def test_oracle_changes_only_auto_renditions_and_contains_the_shipped_selection(self):
        app, base = oracle.application(), echo.application()
        self.assertEqual(changed(app, base), {'chains'})
        mine, theirs = ({c.name: c for c in a.chains} for a in (app, base))
        self.assertEqual(mine['AUTO'].renditions, decl.RENDITIONS)
        self.assertEqual(replace(mine['AUTO'], renditions=theirs['AUTO'].renditions), theirs['AUTO'])
        self.assertTrue(all(mine[n] == theirs[n] for n in mine if n != 'AUTO'))
        shipped = next(c for c in press.application().chains if c.name == 'AUTO').renditions
        self.assertTrue(set(shipped) <= set(mine['AUTO'].renditions))



if __name__ == '__main__': unittest.main()
