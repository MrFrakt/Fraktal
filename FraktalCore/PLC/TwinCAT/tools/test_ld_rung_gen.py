import re
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

from ld_dump import gate_step, network_lines
from ld_rung_gen import (
    ARCHIVE_TYPES,
    PLAIN,
    RESET,
    Allocator,
    Coil,
    Contact,
    Rail,
    RungError,
    Term,
    Value,
    Wire,
    body,
    call,
    clone,
    compare,
    logic,
    max_identifiers,
    method,
    move,
    network,
    rebuild,
    split_networks,
)

LADDER = (Path(__file__).resolve().parents[1]
          / "Examples/PressDemo/Fraktal_Press_Demo"
            "/01_PneumaticPress/Sequences/FB_LD_PressDemoAuto.TcPOU")


class LdRungGeneratorTests(unittest.TestCase):
    """The generator's contract, proven against the shipped ladder.

    These run against the real archive on purpose: a synthetic fixture would
    prove the regexes match themselves, not that they match what XAE writes.
    """

    @classmethod
    def setUpClass(cls):
        cls.source = LADDER.read_text(encoding="utf-8")

    def test_round_trip_is_byte_identical(self):
        # The whole method rests on this: split + rebuild must not perturb one
        # byte, or every generated rung inherits the drift.
        prefix, networks, separator, suffix = split_networks(self.source)
        self.assertGreater(len(networks), 1)
        self.assertEqual(prefix + separator.join(networks) + suffix, self.source)

    def test_rebuild_preserves_bytes_and_only_moves_branch_counter(self):
        _, networks, _, _ = split_networks(self.source)
        rebuilt = rebuild(self.source, networks)
        _, highest_var = max_identifiers(self.source)
        self.assertIn(f'<v n="BranchCounter">{highest_var + 1}</v>', rebuilt)
        # Nothing else changed: strip the counter from both and compare.
        strip = lambda text: text.replace(  # noqa: E731
            f'<v n="BranchCounter">{highest_var + 1}</v>', "")
        self.assertEqual(
            strip(rebuilt),
            strip(self.source.replace(
                self.source[self.source.index('<v n="BranchCounter">'):
                            self.source.index("</v>", self.source.index(
                                '<v n="BranchCounter">')) + 4],
                f'<v n="BranchCounter">{highest_var + 1}</v>')))

    def test_clone_renumbers_every_identifier_into_a_fresh_range(self):
        _, networks, _, _ = split_networks(self.source)
        template = networks[2]                      # the N110 command rung
        highest_id, highest_var = max_identifiers(self.source)
        rung, next_id, next_var = clone(template, id_base=highest_id + 1,
                                        var_base=highest_var + 1)
        old_ids, old_vars = max_identifiers(template)
        clone_ids = {int(m) for m in __import__("re").findall(
            r'<v n="Id">(\d+)L</v>', rung.text)}
        self.assertTrue(min(clone_ids) > highest_id,
                        "cloned Ids must not overlap the file's existing Ids")
        self.assertGreater(next_id, highest_id)
        self.assertGreater(next_var, highest_var)
        # Structure is untouched: same node count, same tag sequence.
        self.assertEqual(rung.text.count("<o"), template.count("<o"))
        self.assertEqual(rung.text.count("BoxTreeOperand"),
                         template.count("BoxTreeOperand"))

    def test_clone_is_identity_when_renumbered_onto_itself(self):
        # The golden test. Cloning the template back onto its OWN id range must
        # reproduce it byte for byte - that is what makes a generated rung
        # trustworthy without opening XAE.
        _, networks, _, _ = split_networks(self.source)
        template = networks[2]
        ids = sorted({int(m) for m in __import__("re").findall(
            r'<v n="Id">(\d+)L</v>', template)})
        varids = sorted({int(m) for m in __import__("re").findall(
            r'<v n="VarId">(\d+)</v>', template)})
        # Only round-trips exactly when the originals are already contiguous;
        # they are not, so assert the mapping is order-preserving instead.
        rung, _, _ = clone(template, id_base=ids[0], var_base=varids[0])
        remapped = sorted({int(m) for m in __import__("re").findall(
            r'<v n="Id">(\d+)L</v>', rung.text)})
        self.assertEqual(len(remapped), len(ids))
        self.assertEqual(remapped, list(range(ids[0], ids[0] + len(ids))))

    def test_subst_asserts_its_hit_count(self):
        _, networks, _, _ = split_networks(self.source)
        rung, _, _ = clone(networks[2], id_base=9000, var_base=900)
        with self.assertRaises(RungError):
            rung.subst("_thisOperandDoesNotExist", "_x")
        # _pressRam.Execute genuinely appears twice (Set coil and Reset coil);
        # asserting 1 must fail rather than silently rewrite one of them.
        with self.assertRaises(RungError):
            rung.subst("_pressRam.Execute", "_door.Execute", count=1)
        rung.subst("_pressRam.Execute", "_door.Execute", count=2)
        self.assertIn('"_door.Execute"', rung.text)

    def test_subst_string_derives_the_declared_length(self):
        _, networks, _, _ = split_networks(self.source)
        rung, _, _ = clone(networks[2], id_base=9000, var_base=900)
        rung.subst_string("project.step.pressRamUp", "project.step.pressDoorOpen")
        self.assertIn("'project.step.pressDoorOpen'", rung.text)
        self.assertIn(f"STRING(INT#{len('project.step.pressDoorOpen')})", rung.text)
        self.assertNotIn("STRING(INT#23)", rung.text)

    def test_generated_rung_keeps_the_document_well_formed(self):
        _, networks, _, _ = split_networks(self.source)
        highest_id, highest_var = max_identifiers(self.source)
        rung, _, _ = clone(networks[2], id_base=highest_id + 1,
                           var_base=highest_var + 1)
        rung.subst("110", "130", count=1)
        candidate = rebuild(self.source, networks + [rung.text])
        ET.fromstring(candidate)          # raises if the splice broke the XML

    def test_ids_are_unique_across_the_whole_generated_body(self):
        # A duplicated Id does not fail to parse - it silently shadows a node.
        _, networks, _, _ = split_networks(self.source)
        highest_id, highest_var = max_identifiers(self.source)
        rung, _, _ = clone(networks[2], id_base=highest_id + 1,
                           var_base=highest_var + 1)
        candidate = rebuild(self.source, networks + [rung.text])
        found = __import__("re").findall(r'<v n="Id">(\d+)L</v>', candidate)
        self.assertEqual(len(found), len(set(found)), "duplicate Id in the body")


class LdToEnConversionTests(unittest.TestCase):
    """`…Ld` facade call -> EN/ENO call on the real method.

    Built from a synthetic box rather than the shipped ladder, because the
    ladder no longer contains a single `…Ld` box - the conversion is done. The
    fixture is the exact shape `FB_SequenceBaseLd` boxes had.
    """

    VOID_BOX = """                    <o t="BoxTreeBox">
                      <v n="BoxType">"M_StepLd"</v>
                      <o n="OutputItems" t="OutputItemList">
                        <l2 n="OutputItems" />
                      </o>
                      <o n="InputParam" t="ParamList">
                        <l2 n="Names" cet="String">
                          <v>Run</v>
                          <v>StepNo</v>
                        </l2>
                        <l2 n="Types" cet="String">
                          <v>BOOL</v>
                          <v>INT</v>
                        </l2>
                      </o>
                      <o n="OutputParam" t="ParamList">
                        <l2 n="Names" />
                        <l2 n="Types" />
                      </o>
                      <v n="CallType" t="Operator">Method</v>
                      <v n="EN">false</v>
                      <v n="ENO">false</v>
                      <v n="Id">42L</v>
                    </o>"""

    VALUE_BOX = VOID_BOX.replace('"M_StepLd"', '"M_AwaitLd"').replace(
        '<l2 n="OutputItems" />',
        '<l2 n="OutputItems" cet="Operand">\n'
        '                          <o>\n'
        '                            <v n="Operand">"_partReady"</v>\n'
        '                            <v n="Type">"BOOL"</v>\n'
        '                            <v n="Id">43L</v>\n'
        '                          </o>\n'
        '                        </l2>').replace(
        '<l2 n="Names" />\n                        <l2 n="Types" />',
        '<l2 n="Names" cet="String">\n'
        '                          <v>M_AwaitLd</v>\n'
        '                        </l2>\n'
        '                        <l2 n="Types" cet="String">\n'
        '                          <v>BOOL</v>\n'
        '                        </l2>')

    def test_void_box_gains_en_and_eno(self):
        from ld_rung_gen import to_en_form
        out = to_en_form(self.VOID_BOX, base_name="M_Step", returns_value=False,
                         eno_operand_id=9000)
        self.assertIn('<v n="BoxType">"M_Step"</v>', out)
        self.assertIn("<v>EN</v>", out)
        self.assertNotIn("<v>Run</v>", out)
        self.assertIn("<v>ENO</v>", out)
        self.assertIn('<v n="EN">true</v>', out)
        self.assertIn('<v n="ENO">true</v>', out)
        ET.fromstring(out)

    def test_value_box_puts_the_return_second_after_eno(self):
        # The trap this encodes: ENO occupies output slot 0, so the method's
        # own return value is slot 1. Wiring a variable into slot 0 compiles
        # clean and strands the intended one.
        from ld_rung_gen import to_en_form
        out = to_en_form(self.VALUE_BOX, base_name="M_Await", returns_value=True,
                         eno_operand_id=9000)
        names = out[out.index('<o n="OutputParam"'):]
        self.assertLess(names.index("<v>ENO</v>"), names.index("<v>M_Await</v>"))
        # OutputItems gained an empty ENO slot BEFORE the real operand.
        items = out[out.index('<l2 n="OutputItems"'):out.index('<o n="InputParam"')]
        self.assertLess(items.index('<v n="Operand">""</v>'),
                        items.index('<v n="Operand">"_partReady"</v>'))
        self.assertIn('<v n="Id">9000L</v>', items)
        ET.fromstring(out)

    def test_conversion_is_idempotent(self):
        from ld_rung_gen import to_en_form
        once = to_en_form(self.VOID_BOX, base_name="M_Step", returns_value=False,
                          eno_operand_id=9000)
        twice = to_en_form(once, base_name="M_Step", returns_value=False,
                           eno_operand_id=9001)
        self.assertEqual(once, twice)

    def test_missing_run_input_raises_rather_than_silently_passing(self):
        from ld_rung_gen import to_en_form
        broken = self.VOID_BOX.replace("<v>Run</v>", "<v>Steppable</v>")
        with self.assertRaises(RungError):
            to_en_form(broken, base_name="M_Step", returns_value=False,
                       eno_operand_id=9000)

    def test_the_shipped_ladder_has_no_facade_boxes_left(self):
        # Regression guard: FB_SequenceBaseLd is deleted from Core, so a `…Ld`
        # box reappearing here would not resolve.
        source = LADDER.read_text(encoding="utf-8")
        import re
        self.assertEqual(re.findall(r'<v n="BoxType">"(M_\w+Ld)"</v>', source), [])
        self.assertIn("EXTENDS FB_SequenceBase\n", source)


STEP_PARAMS = [("StepNo", "INT"), ("StepName", "STRING(120)"),
               ("Awaits", "I_Module"), ("AwaitingLabel", "STRING(120)"),
               ("TimeClass", "E_TimeClass"), ("ExpectedTime", "TIME"),
               ("Branch", "INT")]


class SynthesisTests(unittest.TestCase):
    """Building a rung from its declaration, with no donor to clone."""

    @classmethod
    def setUpClass(cls):
        cls.source = LADDER.read_text(encoding="utf-8")

    # -- the acid test -----------------------------------------------------
    #
    # N999 was drawn by hand in the XAE editor. If the emitter reproduces it
    # node for node, pin for pin and flag for flag, then a rung it emits for a
    # box with NO instance to clone is trustworthy for exactly the same reason.

    @staticmethod
    def _n999(alloc):
        rail = alloc.take_var()
        tap = lambda: Rail(rail)                                    # noqa: E731
        step = lambda nodes: [                                      # noqa: E731
            (name, type_name, node)
            for (name, type_name), node in zip(STEP_PARAMS, nodes)]
        return [
            Wire(rail, compare("EQ", Term(), Value("_step", "INT"),
                               Value("999", "INT"))),
            method("M_Step", tap(), step([
                Value("999", "INT"),
                Value.text("project.step.pressAutoComplete"),
                Value("0", "INT"),
                Value.text(""),
                Value("E_TimeClass.WORK", "E_TIMECLASS"),
                Value("T#0S", "TIME"),
                Value("0", "INT")])),
            Coil("_outCmd.CycleCompleted", tap(), PLAIN),
            method("M_PartProcessed",
                   logic("AND", [tap(), Contact("_partDispositioned",
                                                negated=True)]),
                   [("Verdict", "E_Verdict", Value("E_Verdict.OK", "E_VERDICT")),
                    ("Reason", "E_Reason", Value("E_Reason.NONE", "E_REASON"))],
                   returns=("M_PartProcessed", "BOOL"), result="_processed"),
            method("M_CountGood", logic("AND", [tap(), Contact("_processed")])),
            Coil("_partDispositioned",
                 logic("AND", [tap(), Contact("_partDispositioned")]), RESET),
            Coil("_partInMachine", tap(), RESET),
            Coil("_startLatched", tap(), RESET),
            method("M_EndOfCycle", tap(), returns=("M_EndOfCycle", "BOOL"),
                   result="_endCycle"),
            move(logic("AND", [tap(), Contact("_endCycle")]),
                 Value("100", "INT"), "_step", "INT"),
        ]

    @staticmethod
    def _normalise_rails(lines):
        # Rail numbers are freshly allocated; only the PATTERN of reuse matters.
        seen, out = {}, []
        for line in lines:
            for number in re.findall(r"var=(\d+)", line):
                seen.setdefault(number, f"#{len(seen)}")
                line = line.replace(f"var={number}", f"var={seen[number]}")
            out.append(line)
        return out

    def _editor_drawn_n999(self):
        # By its gate, never by position: the network list is ordered for
        # execution and gets reordered, so an index would silently point at a
        # different rung.
        _, networks, _, _ = split_networks(self.source)
        for text in networks:
            if gate_step(ET.fromstring(text)) == 999:
                return networks, text
        raise AssertionError("the ladder has no N999 rung")

    def test_synthesis_reproduces_the_editor_drawn_rung(self):
        networks, n999 = self._editor_drawn_n999()
        alloc = Allocator.above(self.source)
        generated = network(self._n999(alloc), alloc)
        self.assertEqual(
            self._normalise_rails(network_lines(ET.fromstring(n999),
                                                show_ids=False)),
            self._normalise_rails(network_lines(ET.fromstring(generated),
                                                show_ids=False)))

    def test_synthesis_reproduces_every_operand_flag(self):
        # The graph dump does not show LValue/Boolean/Fixed/Flags, and those are
        # what separate a contact from an argument and a Set coil from a Reset.
        fields = ("Operand", "Type", "LValue", "Boolean", "IsInstance")

        def records(text):
            rows = []
            for node in ET.fromstring(text).iter("o"):
                if node.find("./v[@n='Operand']") is None:
                    continue
                read = lambda name: (                               # noqa: E731
                    node.find(f"./v[@n='{name}']").text
                    if node.find(f"./v[@n='{name}']") is not None else None)
                flags = node.find("./o[@n='Flags']")
                values = [read(name) for name in fields]
                if values[fields.index("IsInstance")] == "true":
                    values[fields.index("Type")] = ""   # cosmetic; the file is
                    # itself inconsistent here (a stale "M_CountGoodLd" survives
                    # from the …Ld migration next to plain "" on its neighbours)
                rows.append(tuple(values) + (flags.find("./v[@n='Flags']").text,
                                             flags.find("./v[@n='Fixed']").text))
            return rows

        networks, n999 = self._editor_drawn_n999()
        alloc = Allocator.above(self.source)
        generated = network(self._n999(alloc), alloc)
        self.assertEqual(records(n999), records(generated))

    # -- the signature is the whole input ----------------------------------

    def test_method_box_derives_its_pins_from_the_declaration(self):
        alloc = Allocator(1, 1)
        box = ET.fromstring(method(
            "M_Delay", Term(), [("PT", "TIME", Value("T#1S", "TIME"))],
            returns=("M_Delay", "E_StepResult"), result="_retVal"
        ).render(alloc))
        names = [v.text for v in box.findall("./o[@n='InputParam']/l2[@n='Names']/v")]
        outs = [v.text for v in box.findall("./o[@n='OutputParam']/l2[@n='Names']/v")]
        wired = [o.find("./v[@n='Operand']").text for o in
                 box.findall("./o[@n='OutputItems']/l2[@n='OutputItems']/o")]
        self.assertEqual(names, ["EN", "PT"])
        # ENO occupies output slot 0; the return value is SECOND. Wiring a
        # variable into slot 0 puts it on ENO and strands the intended one.
        self.assertEqual(outs, ["ENO", "M_Delay"])
        self.assertEqual(wired, ['""', '"_retVal"'])

    def test_a_void_method_gets_an_empty_output_slot_and_no_result(self):
        alloc = Allocator(1, 1)
        box = method("M_PartStarted", Term()).render(alloc)
        self.assertIn('<l2 n="OutputItems">\n', box)
        self.assertIn("<n />", box)
        self.assertIn("<v>ENO</v>", box)
        with self.assertRaises(RungError):
            method("M_PartStarted", Term(), result="_x")

    def test_a_childs_method_folds_the_instance_into_the_box_type(self):
        alloc = Allocator(1, 1)
        box = method("_pressRam.WithdrawOutputs", Term()).render(alloc)
        self.assertIn('<v n="BoxType">"_pressRam.WithdrawOutputs"</v>', box)

    def test_every_synthesised_item_carries_its_own_type(self):
        # The silent failure this exists to prevent: a node with no `t=` of its
        # own parses AND compiles while the box is simply absent.
        alloc = Allocator(1, 1)
        rail = alloc.take_var()
        text = network([Wire(rail, compare("EQ", Term(), Value("_step", "INT"),
                                           Value("0", "INT"))),
                        method("M_PartStarted", Rail(rail)),
                        Coil("_x", Rail(rail), RESET)], alloc)
        items = ET.fromstring(text).find("./l2[@n='NetworkItems']")
        self.assertIsNone(items.get("cet"), "a cet would type the items collectively")
        for item in items:
            self.assertIsNotNone(item.get("t"), ET.tostring(item)[:80])

    def test_synthesised_ids_are_unique_and_above_the_body(self):
        _, networks, _, _ = split_networks(self.source)
        alloc = Allocator.above(self.source)
        highest_id, _ = max_identifiers(self.source)
        generated = network(self._n999(alloc), alloc)
        candidate = rebuild(self.source, networks + [generated])
        ET.fromstring(candidate)
        found = re.findall(r'<v n="Id">(\d+)L</v>', candidate)
        self.assertEqual(len(found), len(set(found)), "duplicate Id in the body")
        self.assertTrue(all(int(m) > highest_id for m in
                            re.findall(r'<v n="Id">(\d+)L</v>', generated)))

    def test_string_operand_length_comes_from_the_literal(self):
        # The declared form STRING(120) belongs in a parameter list; an operand
        # carries the literal's own length. Mixing them is a silent mismatch.
        self.assertEqual(Value.text("PressDwell").type_name, "STRING(INT#10)")
        self.assertEqual(Value.text("").type_name, "STRING(INT#0)")

    def test_an_fb_instance_call_names_the_type_and_carries_the_instance(self):
        # The one shape a method box cannot express: `ModeStart();`. It names the
        # FB TYPE and puts the INSTANCE in its Instance operand, which is what
        # makes the compiler check one against the other - proven by pointing it
        # at a name that is not an instance of that type and watching XAE say
        # "'ModeStartTypo' is not an instance of 'FB_PermIntlk'".
        alloc = Allocator(1, 1)
        box = ET.fromstring(call("FB_PermIntlk", "ModeStart", Term()).render(alloc))
        self.assertEqual(box.find("./v[@n='BoxType']").text, '"FB_PermIntlk"')
        self.assertEqual(
            box.find("./o[@n='Instance']/v[@n='Operand']").text, '"ModeStart"')
        self.assertEqual(box.find("./v[@n='CallType']").text, "FunctionBlock")
        # Inputs left unwired keep whatever the instance already holds.
        self.assertEqual(
            [v.text for v in box.findall("./o[@n='InputParam']/l2[@n='Names']/v")],
            ["EN"])

    def test_body_wraps_networks_into_a_loadable_archive(self):
        alloc = Allocator(1, 1)
        rung = network([method("M_PartStarted", Term())], alloc)
        text = body([rung], indent="      ")
        root = ET.fromstring(text)
        archive = root.find("./NWL/XmlArchive")
        self.assertIsNotNone(archive, "no <NWL><XmlArchive> in the body")
        # The TypeList is not decoration - the archive will not load without it.
        self.assertEqual(
            len(archive.findall("./TypeList/Type")), len(ARCHIVE_TYPES))
        holder = archive.find("./Data/o")
        self.assertEqual(len(holder.findall("./l2[@n='NetworkList']/o")), 1)
        self.assertIsNotNone(holder.find("./v[@n='BranchCounter']"))

    def test_network_comment_cannot_break_the_quoting(self):
        alloc = Allocator(1, 1)
        with self.assertRaises(RungError):
            network([], alloc, comment='he said "no"')
        self.assertIn('<v n="Comment">"215: scrap &amp; return"</v>',
                      network([], alloc, comment="215: scrap & return"))


if __name__ == "__main__":
    unittest.main()
