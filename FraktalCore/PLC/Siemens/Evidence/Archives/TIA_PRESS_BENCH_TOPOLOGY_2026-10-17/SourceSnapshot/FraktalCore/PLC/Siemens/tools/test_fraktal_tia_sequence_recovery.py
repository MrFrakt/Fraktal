"""Ownership and lifecycle boundaries for the portable recovery helpers."""
import unittest
import fraktal_tia_declaration as DECL
import fraktal_tia_generate as GEN
import fraktal_tia_sequence_recovery as RECOVERY
import fraktal_tia_examples as EX
from test_fraktal_tia_sequence_view import FIXTURE
from fraktal_tia_binding import Catalog


class RecoveryTests(unittest.TestCase):
    def test_only_consumed_unit_owners_are_allocated(self):
        model = DECL.validate(FIXTURE.select(FIXTURE.CONFIG.declaration()))
        sources, _ = RECOVERY.build(model, Catalog.read())
        owned = sources['08_FRK_SequenceOwners.db']
        expected = [i for i in model.instances if next(t for t in model.types if t.name == i.type_name).sequence_view]
        self.assertEqual(owned.count(' : "FRK_SequenceLifecycle";'), len(expected)+1)
        self.assertEqual(owned.count("ExternalWritable := 'False'"), len(expected)+1)
        self.assertNotIn('ST_ModuleStatus', sources['06_FRK_SequenceLifecycle.udt'])

    def test_frame_captures_fault_after_kernel_resolves(self):
        sources, _ = GEN.build(DECL.validate(FIXTURE.select(FIXTURE.CONFIG.declaration())), True)
        frame = next(text for name, text in sources.items() if name.startswith('20_') and 'FRK_SeqLifecycleUpdate' in text)
        final = frame.rindex('"FRK_SeqLifecycleUpdate"')
        self.assertGreater(final, frame.index('"FRK_End"'))
        self.assertLess(frame.index('"FRK_SeqLifecycleUpdate"'), frame.index('// ---- AUTHORED: unconditional sequence policy'))

    def test_native_graph_adapters_share_the_correct_scan_boundary(self):
        sources, _, _ = EX.build()
        owners = [text for name, text in sources.items() if name.startswith('28_')]
        self.assertEqual(len(owners), 4)  # AUTO, HOME, CHANGEOVER and LoadPosition
        for text in owners:
            self.assertIn('"FRK_SeqGraphBegin"', text)
            self.assertNotIn('"FRK_SeqBegin"', text)
            self.assertLess(text.index('IF NOT #Seq.Frozen OR #Seq.RestartPending THEN'), text.index('#Chart('))
        # Each rendition consumes the same computed sub-chain reset operand;
        # a LAD operand must not serialize an SCL expression as a tag name.
        self.assertNotIn('Restart OR #Seq', sources['26_FB_LD_PressDemoAuto.xml'])


if __name__ == '__main__':
    unittest.main()
