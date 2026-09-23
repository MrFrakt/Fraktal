"""Tests for the emitted command mailbox.

The mailbox is the first and only writable surface this binding publishes, so
the tests that matter are the ones about what a client can reach: the request
is writable, the response is not, and the handler's own memory is reachable by
nobody. A mailbox whose response a client could write is not a mailbox, it is a
place to forge an acknowledgement.
"""

import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

import fraktal_ab_generate as gen
import fraktal_ab_mailbox as mailbox
import fraktal_ab_press_demo as demo
from test_fraktal_ab_generate import SEED

APP = demo.application()


def emit():
    """The parsed project and its raw text.

    Both, because CDATA does not survive a reparse: ElementTree hands back the
    text content, so a test that re-serialises cannot tell a quoted Logix string
    from a bare one - which is the exact defect the manifest hit.
    """
    with tempfile.TemporaryDirectory() as directory:
        source = Path(directory) / "seed.L5X"
        source.write_text(SEED, encoding="utf-8")
        output = Path(directory) / "app.L5X"
        gen.generate(APP, source, output)
        text = output.read_text(encoding="utf-8")
        return ET.fromstring(text), text


class TypeEmissionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root, cls.text = emit()
        cls.types = {t.get("Name"): t for t in cls.root.iter("DataType")}

    def test_both_contract_records_are_emitted(self):
        self.assertIn(mailbox.request_type_name(APP), self.types)
        self.assertIn(mailbox.response_type_name(APP), self.types)

    def test_a_string_type_exists_for_every_declared_width(self):
        for length in mailbox.string_lengths():
            self.assertIn(mailbox.string_type_name(APP, length), self.types)

    def test_the_widths_are_the_oracle_widths(self):
        self.assertEqual(set(mailbox.string_lengths()), {255, 160, 32})

    def test_every_string_type_is_the_logix_string_layout(self):
        for length in mailbox.string_lengths():
            members = list(self.types[mailbox.string_type_name(APP, length)]
                           .iter("Member"))
            self.assertEqual([m.get("Name") for m in members], ["LEN", "DATA"])
            self.assertEqual(members[0].get("DataType"), "DINT")
            self.assertEqual(members[1].get("DataType"), "SINT")
            self.assertEqual(int(members[1].get("Dimension")), length)

    def test_the_request_carries_every_declared_member_in_order(self):
        members = [m.get("Name") for m in
                   self.types[mailbox.request_type_name(APP)].iter("Member")]
        self.assertEqual(members, [n for n, _, _, _ in mailbox.REQUEST_MEMBERS])

    def test_the_response_carries_every_declared_member_in_order(self):
        members = [m.get("Name") for m in
                   self.types[mailbox.response_type_name(APP)].iter("Member")]
        self.assertEqual(members, [n for n, _, _, _ in mailbox.RESPONSE_MEMBERS])

    def test_no_mailbox_member_is_a_bool(self):
        for type_name in (mailbox.request_type_name(APP),
                          mailbox.response_type_name(APP)):
            kinds = {m.get("DataType")
                     for m in self.types[type_name].iter("Member")}
            self.assertNotIn("BOOL", kinds)

    def test_a_string_member_points_at_a_string_type(self):
        request = self.types[mailbox.request_type_name(APP)]
        by_name = {m.get("Name"): m.get("DataType") for m in request.iter("Member")}
        self.assertEqual(by_name["TargetPath"],
                         mailbox.string_type_name(APP, mailbox.TARGET_PATH_LENGTH))
        self.assertEqual(by_name["User"],
                         mailbox.string_type_name(APP, mailbox.USER_LENGTH))

    def test_the_scalar_members_are_dints(self):
        request = self.types[mailbox.request_type_name(APP)]
        by_name = {m.get("Name"): m.get("DataType") for m in request.iter("Member")}
        for name in ("Kind", "IntValue", "BoolValue", "DurationMs", "Sequence"):
            self.assertEqual(by_name[name], "DINT", name)


class AccessTests(unittest.TestCase):
    """Who can write what. This is the whole security surface of the mailbox."""

    @classmethod
    def setUpClass(cls):
        cls.root, cls.text = emit()
        cls.tags = {t.get("Name"): t for t in cls.root.iter("Tag")}

    def test_the_request_is_the_writable_surface(self):
        self.assertEqual(
            self.tags[mailbox.request_tag_name(APP)].get("ExternalAccess"),
            "Read/Write")

    def test_the_response_cannot_be_written_by_a_client(self):
        # Otherwise a client could write its own AckSequence and manufacture an
        # acknowledgement for a command the machine never saw.
        self.assertEqual(
            self.tags[mailbox.response_tag_name(APP)].get("ExternalAccess"),
            "Read Only")

    def test_the_handlers_last_sequence_is_reachable_by_nobody(self):
        # It is the replay guard. Published, it would be the way around itself.
        self.assertEqual(
            self.tags[f"FRK_{APP.name}_HmiLastSequence"].get("ExternalAccess"),
            "None")

    def test_the_mailbox_is_writable_and_its_answer_is_not(self):
        access = {n: t.get("ExternalAccess") for n, t in self.tags.items()}
        self.assertEqual(access[mailbox.request_tag_name(APP)], "Read/Write")
        self.assertEqual(access[mailbox.response_tag_name(APP)], "Read Only")

    def test_a_command_cannot_be_issued_around_the_mailbox(self):
        """AB §11.2.1, the half of it that is about commands.

        This replaces the test that recorded the bypass. Every request tag the
        mailbox routes into is now `None`, so a CIP client cannot set
        `FRK_Press_RunRequest` directly and skip the validation, the refusal and
        the acknowledgement the mailbox performs. The mailbox is the only way to
        issue a command and therefore the only place one is recorded.
        """
        controller = self.root.find("./Controller/Tags")
        access = {t.get("Name"): t.get("ExternalAccess")
                  for t in controller.findall("Tag")}
        self.assertEqual(access[mailbox.request_tag_name(APP)], "Read/Write")
        for name in gen.command_inputs(APP):
            self.assertEqual(
                access[name], "None",
                f"{name} is routed by the mailbox and must not be writable "
                f"around it")

    def test_the_simulated_plant_is_the_remaining_writable_surface(self):
        """The narrowing that is left, asserted rather than described.

        The press demo declares no physical I/O, so the signals a real machine
        would take from a card are tags, and the evidence harnesses drive the
        plant through them. That is a property of this demonstration
        application - a real one has no such tags - and it is pinned here so it
        cannot quietly grow: anything newly writable has to be added to this
        list deliberately.
        """
        controller = self.root.find("./Controller/Tags")
        writable = {t.get("Name") for t in controller.findall("Tag")
                    if t.get("ExternalAccess") == "Read/Write"}
        expected = set(gen.externally_writable(APP)) | {
            mailbox.request_tag_name(APP)}
        self.assertEqual(writable, expected)
        # ...and none of it is a command (the paired negative).
        self.assertFalse(writable & set(gen.command_inputs(APP)))


class OneShotRequestTests(unittest.TestCase):
    """Every request the handler raises comes down again.

    Measured on hardware 2026-09-22: after START, STOP and OPERATOR_RESET the
    bench was left with RunRequest, AbortRequest, ResetRequest and JogCommand
    all latched at 1 and the Unit reporting Aborted. Ten acknowledgements,
    `Accepted` true on every routed kind, and a machine driven into a latched
    abort the whole time - which is why this suite asserts the tag levels and
    not the acks.

    The generated Unit copies each request into its context every scan and
    tests it as a level, so the deassert is the mailbox's job. It was invisible
    while those tags were externally writable, because every client wrote 1 then
    0 and supplied the deassert itself.
    """

    def setUp(self):
        self.lines = list(mailbox.handler_logic(APP))
        self.logic = chr(10).join(self.lines)

    def index_of(self, fragment):
        for i, line in enumerate(self.lines):
            if fragment in line:
                return i
        raise AssertionError(fragment + " is not in the handler")

    def test_every_one_shot_request_is_lowered_again(self):
        for name in mailbox.one_shot_requests():
            self.assertIn("FRK_%s_%s := 0;" % (APP.name, name), self.logic, name)

    def test_the_lowering_runs_before_the_sequence_check(self):
        # It has to happen on EVERY scan, not only on a scan that carries a new
        # command - otherwise a pulse raised by the last command stays high
        # until the next one arrives, which is the latch again with extra steps.
        guard = self.index_of("<> FRK_%s_HmiLastSequence" % APP.name)
        for name in mailbox.one_shot_requests():
            self.assertLess(
                self.index_of("FRK_%s_%s := 0;" % (APP.name, name)), guard, name)

    def test_a_one_shot_is_raised_after_it_is_lowered(self):
        # Same scan: clear at the top, raise in the dispatch below. The Unit AOI
        # runs later in that scan, so it sees the raise.
        for name, kind in (("AbortRequest", "STOP"),
                           ("ResetRequest", "OPERATOR_RESET"),
                           ("JogCommand", "MANUAL_COMMAND")):
            tag = "FRK_%s_%s" % (APP.name, name)
            self.assertLess(self.index_of(tag + " := 0;"),
                            self.index_of(tag + " := 1;"), kind)

    def test_the_mode_request_is_never_cleared(self):
        # ModeRequest is a selection compared against Mode. Clearing it would
        # request ordinal 0 - AUTO - on the very next scan.
        self.assertNotIn("FRK_%s_ModeRequest := 0;" % APP.name, self.logic)

    def test_start_raises_the_run_level_and_stop_lowers_it(self):
        # RunRequest is a level in both directions, so it is not on the one-shot
        # list; STOP lowers it explicitly instead of a scan boundary doing it.
        tag = "FRK_%s_RunRequest" % APP.name
        self.assertIn(tag + " := 1;", self.logic)
        self.assertIn(tag + " := 0;", self.logic)
        self.assertNotIn("RunRequest", mailbox.one_shot_requests())

    def test_stop_both_aborts_and_stops_running(self):
        # A STOP that left the run level high would be a contradiction the Unit
        # has to resolve every scan.
        stop = self.index_of("(* STOP *)")
        window = chr(10).join(self.lines[stop:stop + 6])
        self.assertIn("FRK_%s_AbortRequest := 1;" % APP.name, window)
        self.assertIn("FRK_%s_RunRequest := 0;" % APP.name, window)

    def test_the_one_shot_list_covers_every_pulsed_request(self):
        # A request the dispatch raises but nobody lowers is the original
        # defect. Anything raised must be either a declared level or a declared
        # one-shot.
        prefix = "FRK_%s_" % APP.name
        raised = set()
        for line in self.lines:
            text = line.strip()
            if not (text.startswith(prefix) and text.endswith(":= 1;")):
                continue
            target = text.split(":=")[0].strip()[len(prefix):]
            # Bare tags only. A dotted name is a structure member - the
            # response's own Accepted flag - not a request the Unit samples.
            if "." not in target:
                raised.add(target)
        known = set(mailbox.one_shot_requests()) | set(mailbox.LEVEL_REQUESTS)
        self.assertTrue(raised <= known, raised - known)

    def test_the_command_tags_have_no_other_writer(self):
        """Why it matters: the mailbox is now the only way in."""
        self.assertEqual(
            set(gen.command_inputs(APP)) & set(gen.externally_writable(APP)),
            set(),
            "a command tag is externally writable again, which would let a "
            "client deassert a latched request and hide this defect")


class InitialValueTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root, cls.text = emit()
        cls.tags = {t.get("Name"): t for t in cls.root.iter("Tag")}

    def test_the_mailbox_starts_uncommanded(self):
        # Kind 0 and Sequence 0: a freshly downloaded controller has not been
        # commanded, and must not look as though it has.
        request = self.tags[mailbox.request_tag_name(APP)]
        values = {m.get("Name"): int(m.get("Value"))
                  for m in request.iter("DataValueMember")
                  if m.get("Value") is not None}
        self.assertEqual(values["Kind"], mailbox.UNCOMMANDED)
        self.assertEqual(values["Sequence"], 0)

    def test_the_response_starts_unacknowledged(self):
        response = self.tags[mailbox.response_tag_name(APP)]
        values = {m.get("Name"): int(m.get("Value"))
                  for m in response.iter("DataValueMember")
                  if m.get("Value") is not None}
        self.assertEqual(values["AckSequence"], 0)
        self.assertEqual(values["Accepted"], 0)

    def test_every_string_starts_empty_and_quoted(self):
        # Logix stores an ASCII string only when it is quoted; an empty one is
        # still quoted. This is the defect the manifest hit.
        # Checked against the emitted text, not a reparse.
        self.assertIn("<![CDATA['']]>", self.text)
        for tag_name in (mailbox.request_tag_name(APP),
                         mailbox.response_tag_name(APP)):
            start = self.text.index(f'<Tag Name="{tag_name}"')
            end = self.text.index("</Tag>", start)
            body = self.text[start:end]
            self.assertNotIn("<![CDATA[]]>", body)


if __name__ == "__main__":
    unittest.main()


class HandlerTests(unittest.TestCase):
    """The handshake's ordering is the contract; none of it is incidental."""

    def setUp(self):
        self.lines = list(mailbox.handler_logic(APP))
        self.body = chr(10).join(self.lines)

    def index(self, fragment):
        for i, line in enumerate(self.lines):
            if fragment in line:
                return i
        raise AssertionError(f"{fragment!r} is not in the handler")

    def test_it_consumes_a_request_only_when_the_sequence_changes(self):
        self.assertLess(self.index("IF FRK_Press_HmiRequest.Sequence <>"),
                        self.index("CASE FRK_Press_HmiRequest.Kind"))

    def test_the_retained_sequence_moves_before_dispatch(self):
        # Otherwise a command that faults mid-dispatch would run again next scan.
        self.assertLess(self.index("FRK_Press_HmiLastSequence :="),
                        self.index("CASE FRK_Press_HmiRequest.Kind"))

    def test_the_answer_is_cleared_before_dispatch(self):
        self.assertLess(self.index("Accepted := 0;"),
                        self.index("CASE FRK_Press_HmiRequest.Kind"))
        self.assertLess(self.index("DiagnosticKey := 0;"),
                        self.index("CASE FRK_Press_HmiRequest.Kind"))

    def test_the_acknowledgement_is_written_last(self):
        # A client polls AckSequence to learn the whole answer is present.
        ack = self.index("AckSequence :=")
        for fragment in ("Accepted := 1;", "END_CASE;", "Secret.LEN := 0;"):
            self.assertLess(self.index(fragment), ack, fragment)

    def test_the_secret_is_wiped_by_bytes_not_just_by_length(self):
        self.assertIn("Secret.LEN := 0;", self.body)
        self.assertIn("Secret.DATA[FRK_Press_HmiWipe] := 0;", self.body)

    def test_the_secret_is_wiped_after_it_could_have_been_sampled(self):
        self.assertLess(self.index("END_CASE;"),
                        self.index("Secret.LEN := 0;"))

    def test_no_string_literal_is_assigned(self):
        # Logix v33 ST will not assign a string literal to a StringFamily
        # member: the SDK imported 21 such assignments at 0 errors and Studio
        # Verify then rejected exactly 21. The answer is a numeric key instead.
        self.assertNotIn(":= '", self.body)

    def test_every_routed_kind_has_a_branch(self):
        for kind in mailbox.SUPPORTED:
            self.assertIn(f"{kind}:", self.body)

    def test_every_refused_kind_has_a_branch(self):
        branches = {int(part)
                    for line in self.lines if line.rstrip().endswith(":")
                    for part in line.rstrip()[:-1].split(",")
                    if part.strip().isdigit()}
        self.assertTrue(set(mailbox.REFUSED) <= branches,
                        set(mailbox.REFUSED) - branches)

    def test_a_refusal_names_a_published_key(self):
        import fraktal_ab_manifest as manifest

        published = {row["NumericKey"]
                     for row in manifest.content(APP)["Localization"]}
        for portable in mailbox.localization_keys():
            key = manifest.numeric_key(APP, portable)
            self.assertIn(key, published, portable)
            self.assertNotEqual(key, 0, portable)

    def test_an_unaccepted_request_always_carries_a_reason(self):
        self.assertIn("(Accepted = 0)".replace("Accepted",
                      "FRK_Press_HmiResponse.Accepted"), self.body)

    def test_an_undeclared_mode_is_refused_rather_than_clamped(self):
        declared = sorted({c.mode_ordinal for c in APP.chains})
        for ordinal in declared:
            self.assertIn(f"IntValue = {ordinal})", self.body)
        self.assertIn(str(manifest_key(mailbox.MODE_NOT_DECLARED_KEY)), self.body)

    def test_an_addressed_manual_command_is_refused(self):
        # The declared manual chain jogs one module; honouring an address it
        # cannot target would be worse than refusing.
        self.assertIn("TargetPath.LEN = 0", self.body)
        self.assertIn(str(manifest_key(mailbox.TARGET_KEY)), self.body)


def manifest_key(portable):
    import fraktal_ab_manifest as manifest

    return manifest.numeric_key(APP, portable)


class ManifestPublicationTests(unittest.TestCase):
    """A mailbox a client cannot discover is a tag someone was told about."""

    def setUp(self):
        import fraktal_ab_manifest as manifest

        self.manifest = manifest
        self.content = manifest.content(APP)
        self.keys = {row["NumericKey"]: row["PortableKey"]
                     for row in self.content["Localization"]}

    def test_the_root_publishes_a_non_zero_mailbox_id(self):
        # Zero is how the manifest says a station cannot be commanded at all.
        self.assertEqual(self.content["Roots"][0]["MailboxId"],
                         self.manifest.MAILBOX_ID)
        self.assertNotEqual(self.content["Roots"][0]["MailboxId"], 0)

    def test_every_request_member_is_published_as_writable(self):
        paths = {self.keys[f["PathKey"]]: f for f in self.content["Fields"]}
        for name, _, _, _ in mailbox.REQUEST_MEMBERS:
            path = f"{APP.name}.HmiRequest.{name}"
            self.assertIn(path, paths)
            self.assertEqual(paths[path]["AccessClass"],
                             self.manifest.ACCESS_WRITE, path)

    def test_every_response_member_is_published_read_only(self):
        paths = {self.keys[f["PathKey"]]: f for f in self.content["Fields"]}
        for name, _, _, _ in mailbox.RESPONSE_MEMBERS:
            path = f"{APP.name}.HmiResponse.{name}"
            self.assertIn(path, paths)
            self.assertEqual(paths[path]["AccessClass"],
                             self.manifest.ACCESS_READ, path)

    def test_the_answer_is_live_and_the_request_is_on_demand(self):
        # A client polls the answer until AckSequence matches; nothing polls the
        # request, because the client is the one writing it.
        paths = {self.keys[f["PathKey"]]: f for f in self.content["Fields"]}
        self.assertEqual(paths[f"{APP.name}.HmiResponse.AckSequence"]["ReadTier"],
                         self.manifest.TIER_LIVE)
        self.assertEqual(paths[f"{APP.name}.HmiRequest.Sequence"]["ReadTier"],
                         self.manifest.TIER_ON_DEMAND)

    def test_the_manifest_still_fits(self):
        evidence = self.manifest.evidence(APP)
        self.assertFalse(evidence["Truncated"])
        # S7 measured 43,728 bytes read coherently at a 4002-byte connection.
        self.assertLess(evidence["EstimatedBytes"], 43728)

    def test_the_refusal_keys_are_all_resolvable(self):
        published = set(self.keys.values())
        for portable in mailbox.localization_keys():
            self.assertIn(portable, published, portable)
