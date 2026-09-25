"""Tests for the AB projection into the HMI's snapshot document.

Two properties carry the weight.

The first is that the document satisfies the rules the Dart mapper actually
applies - a module is found by ``Status/Name`` plus ``Status/ModuleType``,
parentage comes from the dotted identity, and a node whose browse name differs
from the last segment of its identity is *discarded* as an alias. Those rules
are re-stated here as assertions because no Dart SDK is installed on this
workstation, so the mapper itself cannot be run against this output. That is a
narrowing, and it is written down rather than glossed: these tests check the
document against the contract as read from the mapper's source, and they are
not a substitute for executing it.

The second is refusal. Core §3.10 makes discovery all or nothing, so every way
a manifest can be untrustworthy is paired here with the refusal it must cause.
A projection that renders half a plant is worse than one that renders none.
"""

import unittest
from dataclasses import replace

import fraktal_ab_declaration as decl
import fraktal_ab_generate as gen
import fraktal_ab_mailbox as mailbox
import fraktal_ab_manifest as manifest
import fraktal_ab_projection as projection

APP = projection.APP


def good_header(**overrides):
    rows = manifest.content(APP)
    header = {
        "Magic": manifest.MANIFEST_MAGIC,
        "SchemaMajor": manifest.MANIFEST_SCHEMA_MAJOR,
        "SchemaMinor": manifest.MANIFEST_SCHEMA_MINOR,
        "ConfigRevision": manifest.config_revision(APP),
        "ContentHash": manifest.content_hash(APP),
        "Valid": 1,
        "Truncated": 0,
        "KeyLength": manifest.key_string_length(APP),
    }
    for table in manifest.tables(APP):
        header[f"{table.name}Count"] = len(rows[table.name])
        header[f"{table.name}Capacity"] = table.capacity
    header.update(overrides)
    return header


def unit_values(**overrides):
    values = {m.name: 0 for m in gen.unit_context_members(APP)}
    values.update(overrides)
    return values


def module_values(**overrides):
    values = {m.name: 0 for m in gen.module_context_members()}
    values.update(overrides)
    return values


def contexts(**overrides):
    out = {m.name: module_values() for m in APP.modules}
    for name, values in overrides.items():
        out[name] = values
    return out


def chart_values(**overrides):
    values = {}
    for member in gen.chart_members(APP):
        values[member.name] = [0] * member.dimension if member.dimension else 0
    values.update(overrides)
    return values


def build(**kwargs):
    known = {"header", "rows", "unit", "contexts", "chart", "mailbox_state",
             "io_state"}
    unknown = set(kwargs) - known
    if unknown:
        raise TypeError(f"build() got unexpected {sorted(unknown)}; a dropped "
                        "keyword makes a test assert against a default")
    return projection.project(
        kwargs.pop("header", good_header()),
        kwargs.pop("rows", manifest.content(APP)),
        kwargs.pop("unit", unit_values()),
        kwargs.pop("contexts", contexts()),
        kwargs.pop("chart", chart_values()),
        kwargs.pop("mailbox_state", None),
        kwargs.pop("io_state", None),
    )



class TopologyTests(unittest.TestCase):
    """The fieldbus view: declared identity, live state, and the seam between.

    The press's channels are transcribed from the TC3 cabinet mapping, so the
    tests that matter are the ones that would catch a transcription drifting -
    a tag localized by accident, a bit shared by two channels, control power
    creeping back in.
    """

    ROOT = "PressFieldbus/Topology"

    def values(self, **io):
        return build(io_state={"Local:1": io} if io else None)["values"]

    def test_the_fieldbus_is_not_published_under_a_module(self):
        # A bus node is not a Fraktal module; giving it a module's browse path
        # would make the generic HMI treat it as one.
        for key in build()["values"]:
            if "/Topology/" in key:
                self.assertFalse(key.startswith("Press/"), key)

    def test_one_node_carries_every_declared_channel(self):
        values = self.values(input=0, output=0, fault=0)
        self.assertEqual(values[f"{self.ROOT}/NodeCount"], 1)
        self.assertEqual(values[f"{self.ROOT}/Nodes[1]/ChannelCount"], 20)
        self.assertEqual(values[f"{self.ROOT}/Nodes[1]/Address"], "Local:1")

    def test_the_electrical_tag_is_published_verbatim(self):
        values = self.values(input=0, output=0, fault=0)
        names = {values[f"{self.ROOT}/Nodes[1]/Channels[{i}]/Name"]
                 for i in range(1, 21)}
        self.assertIn("_101B201A", names)   # door closed
        self.assertIn("_101K202B", names)   # press upward
        # Localized text is a separate member; the tag is never it.
        self.assertEqual(
            values[f"{self.ROOT}/Nodes[1]/Channels[3]/DescriptionKey"],
            "project.io.door_closed")

    def test_control_power_is_absent_not_renumbered(self):
        values = self.values(input=0, output=0, fault=0)
        names = {values[f"{self.ROOT}/Nodes[1]/Channels[{i}]/Name"]
                 for i in range(1, 21)}
        for tag in ("_000K951_A1", "_000K911_A1", "_000K911_Y32"):
            self.assertNotIn(tag, names)
        # and the channels that remain keep their TC3 bit positions
        self.assertEqual(values[f"{self.ROOT}/Nodes[1]/Channels[12]/Address"],
                         "Local:1:I.14")   # _000K910A, TC3 input channel 15

    def test_a_live_module_publishes_its_bits(self):
        values = self.values(input=0b101, output=0b10, fault=0)
        node = f"{self.ROOT}/Nodes[1]"
        self.assertEqual(values[f"{node}/State"], projection.NODE_OPERATIONAL)
        self.assertIs(values[f"{node}/LinkOk"], True)
        self.assertIs(values[f"{node}/Channels[1]/BoolValue"], True)   # in b0
        self.assertIs(values[f"{node}/Channels[2]/BoolValue"], False)  # in b1
        self.assertIs(values[f"{node}/Channels[14]/BoolValue"], True)  # out b1

    def test_an_inhibited_module_is_offline_not_sixteen_broken_channels(self):
        # Every fault bit set is exactly what an inhibited module reports, and
        # it is the bench's state today.
        values = self.values(input=0, output=0, fault=0xFFFF)
        node = f"{self.ROOT}/Nodes[1]"
        self.assertEqual(values[f"{node}/State"], projection.NODE_OFFLINE)
        self.assertIs(values[f"{node}/LinkOk"], False)
        self.assertIs(values[f"{node}/Channels[1]/Quality"], False)

    def test_a_partial_fault_is_a_fault_not_an_offline_module(self):
        values = self.values(input=0, output=0, fault=0b10)
        node = f"{self.ROOT}/Nodes[1]"
        self.assertEqual(values[f"{node}/State"], projection.NODE_FAULT)
        self.assertIs(values[f"{node}/Channels[2]/FaultActive"], True)
        self.assertIs(values[f"{node}/Channels[1]/FaultActive"], False)

    def test_unread_words_publish_identity_with_bad_quality(self):
        # Never a confident zero: the HMI renders Bad quality as unavailable.
        values = self.values()
        node = f"{self.ROOT}/Nodes[1]"
        self.assertEqual(values[f"{node}/Channels[1]/Name"], "_101B301A")
        self.assertIs(values[f"{node}/Channels[1]/Quality"], False)
        self.assertEqual(values[f"{node}/State"], projection.NODE_OFFLINE)

    def test_no_channel_offers_forcing(self):
        # §10.5.1 forcing is a write, and AB §11.2.1 makes the mailbox the only
        # command surface, so a force affordance could not be honoured.
        values = self.values(input=0, output=0, fault=0)
        for i in range(1, 21):
            self.assertIs(
                values[f"{self.ROOT}/Nodes[1]/Channels[{i}]/Forceable"], False)

    def test_a_channel_cross_links_to_the_module_that_owns_it(self):
        values = self.values(input=0, output=0, fault=0)
        self.assertEqual(
            values[f"{self.ROOT}/Nodes[1]/Channels[3]/ModulePath"],
            "Press.Door")

    def test_a_station_signal_cross_links_to_the_root_unit(self):
        # A lamp belongs to the station, not to a device module. Publishing an
        # empty owner would cost it its alarm cross-link, and the HMI resolves
        # a channel's owning root from this same path.
        values = self.values(input=0, output=0, fault=0)
        self.assertEqual(
            values[f"{self.ROOT}/Nodes[1]/Channels[19]/Name"], "_101P101")
        self.assertEqual(
            values[f"{self.ROOT}/Nodes[1]/Channels[19]/ModulePath"], "Press")

    def test_an_application_without_io_publishes_no_fieldbus_root(self):
        bare = replace(projection.APP, io_modules=())
        self.assertEqual(projection.topology(bare, None), {})


class IoDeclarationTests(unittest.TestCase):
    """What the declaration refuses before anything reaches a chassis."""

    def _app(self, *channels):
        module = decl.IoModule(
            name="M", type_id="T", address="Local:1",
            description_key="k", data_width=16, channels=channels)
        return replace(projection.APP, io_modules=(module,))

    def test_two_channels_cannot_share_a_bit(self):
        findings = decl.validate(self._app(
            decl.IoChannel("_A", "k", 3, decl.DIR_INPUT),
            decl.IoChannel("_B", "k", 3, decl.DIR_INPUT)))
        self.assertTrue(any("both claim bit 3" in f for f in findings))

    def test_the_same_bit_in_each_direction_is_fine(self):
        self.assertEqual(decl.validate(self._app(
            decl.IoChannel("_A", "k", 3, decl.DIR_INPUT),
            decl.IoChannel("_B", "k", 3, decl.DIR_OUTPUT))), [])

    def test_a_duplicate_electrical_tag_is_refused(self):
        findings = decl.validate(self._app(
            decl.IoChannel("_A", "k", 1, decl.DIR_INPUT),
            decl.IoChannel("_A", "k", 2, decl.DIR_INPUT)))
        self.assertTrue(any("duplicate electrical tags" in f for f in findings))

    def test_a_bit_outside_the_data_word_is_refused(self):
        findings = decl.validate(self._app(
            decl.IoChannel("_A", "k", 16, decl.DIR_INPUT)))
        self.assertTrue(any("outside" in f for f in findings))

    def test_a_channel_cannot_name_a_module_that_does_not_exist(self):
        findings = decl.validate(self._app(
            decl.IoChannel("_A", "k", 1, decl.DIR_INPUT, module_path="Nope")))
        self.assertTrue(any("not a declared module" in f for f in findings))

    def test_the_shipped_press_declaration_is_valid(self):
        self.assertEqual(decl.validate(projection.APP), [])


class ForceResolutionTests(unittest.TestCase):
    """The seam where a browse path becomes a DINT the controller can read.

    The oracle names a channel with a string and TC3 resolves it in the PLC.
    This binding cannot, so the resolution moved to the gateway - and a
    resolution that fired on the wrong command, or guessed at an unknown
    channel, would force a terminal nobody named.
    """

    ROOT = "Press/HmiRequest/"

    def batch(self, kind, **members):
        writes = [(self.ROOT + "Kind", "int32", kind)]
        writes += [(self.ROOT + k, "string" if isinstance(v, str) else "int32", v)
                   for k, v in members.items()]
        return writes + [(self.ROOT + "Sequence", "uint32", 7)]

    def resolved(self, writes):
        out = mailbox.resolve_force_batch(projection.APP, writes)
        return {p.rsplit("/", 1)[-1]: v for p, _t, v in out}

    def test_a_channel_path_becomes_its_bit_mask(self):
        # _101K202A is press-downward, TC3 output channel 5, so bit 4.
        values = self.resolved(self.batch(
            mailbox.FORCE_CHANNEL, TargetPath="Discrete_IO._101K202A",
            TextValue="true"))
        self.assertEqual(values["IntValue"], 1 << 4)
        self.assertEqual(values[mailbox.FORCE_LEVEL_MEMBER], 1)

    def test_the_level_follows_the_oracle_text_argument(self):
        values = self.resolved(self.batch(
            mailbox.FORCE_CHANNEL, TargetPath="Discrete_IO._101K202A",
            TextValue="false"))
        self.assertEqual(values[mailbox.FORCE_LEVEL_MEMBER], 0)

    def test_the_commit_marker_stays_last(self):
        out = mailbox.resolve_force_batch(projection.APP, self.batch(
            mailbox.FORCE_CHANNEL, TargetPath="Discrete_IO._101K301A",
            TextValue="true"))
        self.assertTrue(out[-1][0].endswith("/Sequence"))

    def test_an_unknown_channel_is_left_for_the_controller_to_refuse(self):
        writes = self.batch(mailbox.FORCE_CHANNEL,
                            TargetPath="Discrete_IO._not_a_channel",
                            TextValue="true")
        self.assertEqual(mailbox.resolve_force_batch(projection.APP, writes),
                         writes)

    def test_another_command_carrying_a_path_is_untouched(self):
        # UNSHELVE_ALARM also sends a TargetPath, and IntValue means something
        # else entirely to DECISION_ANSWER. Resolution must see Kind.
        writes = self.batch(mailbox.UNSHELVE_ALARM,
                            TargetPath="Discrete_IO._101K202A")
        self.assertEqual(mailbox.resolve_force_batch(projection.APP, writes),
                         writes)

    def test_only_one_bit_is_ever_set(self):
        for module in projection.APP.io_modules:
            for channel in module.channels:
                if channel.direction != decl.DIR_OUTPUT:
                    continue
                mask = mailbox.force_argument(0, channel.bit)
                self.assertEqual(bin(mask).count("1"), 1)

    def test_a_second_io_module_is_refused_rather_than_folded_in(self):
        with self.assertRaises(ValueError):
            mailbox.force_argument(1, 0)

    def test_every_declared_channel_resolves_from_its_published_path(self):
        # The path the gateway resolves is the one the projection publishes;
        # if those two ever disagree, forcing silently stops working.
        for module in projection.APP.io_modules:
            for channel in module.channels:
                path = f"{module.name}.{channel.name}"
                resolved = mailbox.force_target(projection.APP, path)
                if channel.direction == decl.DIR_OUTPUT:
                    self.assertIsNotNone(resolved, path)
                else:
                    self.assertIsNone(resolved, path)


class ForcePermissionTests(unittest.TestCase):
    """§10.5.1: the controller decides, and a force never outlives it."""

    def test_the_mask_carries_exactly_the_declared_output_bits(self):
        mask = gen.force_output_mask(projection.APP)
        module = projection.APP.io_modules[0]
        outputs = [c for c in module.channels
                   if c.direction == decl.DIR_OUTPUT]
        self.assertEqual(bin(mask).count("1"), len(outputs))
        for channel in outputs:
            self.assertTrue(mask >> channel.bit & 1, channel.name)

    def test_an_input_is_not_forceable_even_sharing_an_output_bit(self):
        # _101B301A is input bit 0 and _101K301A is output bit 0. Resolving
        # the input would produce the output's mask and energize a valve from
        # a request that named a sensor.
        self.assertIsNone(
            mailbox.force_target(projection.APP, "Discrete_IO._101B301A"))
        self.assertIsNotNone(
            mailbox.force_target(projection.APP, "Discrete_IO._101K301A"))

    def test_the_emitted_logic_withdraws_before_it_applies(self):
        # Ordering is the guarantee: clearing after applying would leave a
        # held bit on the terminal for the scan the permission was lost.
        lines = gen.force_logic(projection.APP)
        body = "\n".join(lines)
        withdraw = body.index("ForceMask := 0;")
        apply_at = body.index(":O.Data :=")
        self.assertLess(withdraw, apply_at)

    def test_forcing_is_permitted_only_in_idle_manual(self):
        body = "\n".join(gen.force_logic(projection.APP))
        self.assertIn("Unit.Mode = 1", body)      # E_Mode.MANUAL
        self.assertIn("Unit.Running = 0", body)
        self.assertIn("Unit.Error = 0", body)

    def test_an_application_without_io_emits_no_force_logic(self):
        bare = replace(projection.APP, io_modules=())
        self.assertEqual(gen.force_logic(bare), [])
        self.assertEqual(gen.force_tags(bare), ())

    def test_the_force_words_are_read_only_to_a_client(self):
        # A writable ForceMask would let a client hold an output without ever
        # passing the permission test - the bypass §11.2.1 exists to prevent.
        tags = gen.controller_tags(projection.APP)
        for name in gen.force_tags(projection.APP):
            index = tags.index(f'Name="{name}"')
            self.assertIn('ExternalAccess="Read Only"',
                          tags[index:index + 240], name)


class RefusalTests(unittest.TestCase):
    """Every way a manifest can be untrustworthy, paired with its refusal."""

    def test_a_faithful_manifest_projects(self):
        self.assertTrue(build()["values"])

    def test_an_invalid_manifest_is_refused(self):
        with self.assertRaises(projection.ProjectionRefused):
            build(header=good_header(Valid=0))

    def test_a_truncated_manifest_is_refused(self):
        with self.assertRaises(projection.ProjectionRefused):
            build(header=good_header(Truncated=1))

    def test_a_disagreeing_content_hash_is_refused(self):
        with self.assertRaises(projection.ProjectionRefused):
            build(header=good_header(ContentHash="0000000000000000"))

    def test_a_foreign_manifest_is_refused(self):
        with self.assertRaises(projection.ProjectionRefused):
            build(header=good_header(Magic=1))

    def test_a_future_schema_major_is_refused(self):
        with self.assertRaises(projection.ProjectionRefused):
            build(header=good_header(SchemaMajor=99))

    def test_the_refusal_says_which_check_failed(self):
        with self.assertRaises(projection.ProjectionRefused) as caught:
            build(header=good_header(Truncated=1))
        self.assertIn("truncated", str(caught.exception))

    def test_every_reason_is_reported_not_just_the_first(self):
        with self.assertRaises(projection.ProjectionRefused) as caught:
            build(header=good_header(Valid=0, Truncated=1))
        message = str(caught.exception)
        self.assertIn("not valid", message)
        self.assertIn("truncated", message)

    def test_a_module_without_live_state_is_refused(self):
        # A published module whose context did not read must not appear as a
        # module in the default state: that would render a device as Ready.
        partial = contexts()
        partial.pop(APP.modules[0].name)
        with self.assertRaises(projection.ProjectionRefused):
            build(contexts=partial)


class MapperContractTests(unittest.TestCase):
    """The rules the Dart mapper applies, restated as assertions."""

    def setUp(self):
        self.document = build()
        self.values = self.document["values"]

    def test_every_module_publishes_a_name_and_a_type(self):
        names = [k for k in self.values if k.endswith("/Status/Name")]
        self.assertEqual(len(names), len(APP.modules) + 1)
        for key in names:
            base = key[: -len("/Status/Name")]
            self.assertIn(f"{base}/Status/ModuleType", self.values)

    def test_a_name_is_a_string_and_a_type_is_an_integer(self):
        for key, value in self.values.items():
            if key.endswith("/Status/Name"):
                self.assertIsInstance(value, str, key)
            if key.endswith("/Status/ModuleType"):
                self.assertIsInstance(value, int, key)

    def test_no_module_would_be_discarded_as_an_alias(self):
        # The mapper drops a node whose browse name differs from the last
        # segment of its identity. Every node here must survive that.
        for key, identity in self.values.items():
            if not key.endswith("/Status/Name"):
                continue
            base = key[: -len("/Status/Name")]
            browse_name = base.rsplit("/", 1)[-1]
            local_name = identity.rsplit(".", 1)[-1]
            self.assertEqual(browse_name, local_name, base)

    def test_the_module_type_is_inside_the_enum(self):
        for key, value in self.values.items():
            if key.endswith("/Status/ModuleType"):
                # none(0) is excluded by the mapper, controlModule(3) is last.
                self.assertGreater(value, 0, key)
                self.assertLessEqual(value, 3, key)

    def test_exactly_one_module_is_the_unit(self):
        types = [v for k, v in self.values.items()
                 if k.endswith("/Status/ModuleType")]
        self.assertEqual(types.count(projection.MODULE_TYPE_UNIT), 1)

    def test_every_child_identity_resolves_to_a_published_parent(self):
        identities = {v for k, v in self.values.items()
                      if k.endswith("/Status/Name")}
        for identity in identities:
            if "." not in identity:
                continue
            self.assertIn(identity.rsplit(".", 1)[0], identities)

    def test_the_truncation_flag_matches_the_manifest(self):
        self.assertFalse(self.document["truncated"])

    def test_the_node_count_matches_the_values(self):
        self.assertEqual(self.document["nodeCount"], len(self.values))


class StateTests(unittest.TestCase):
    def test_a_module_reports_its_exec_state(self):
        values = build(contexts=contexts(
            PressRam=module_values(OutImm_ExecState=gen.STATE_BUSY))
        )["values"]
        self.assertEqual(values["Press/PressRam/Status/State"], gen.STATE_BUSY)

    def test_a_module_error_raises_fault_active(self):
        values = build(contexts=contexts(
            Door=module_values(Error=1)))["values"]
        self.assertTrue(values["Press/Door/Status/FaultActive"])

    def test_a_module_reports_its_reason(self):
        values = build(contexts=contexts(
            Door=module_values(OutImm_Reason=6130)))["values"]
        self.assertEqual(values["Press/Door/Status/Diagnostic/ReasonCode"], 6130)

    def test_the_unit_publishes_the_core_mode_ordinal_verbatim(self):
        import fraktal_ab_press_demo as demo

        values = build(unit=unit_values(Mode=demo.MODE_AUTO))["values"]
        self.assertEqual(values["Press/ModeActivePublished"], demo.MODE_AUTO)

    def test_a_running_unit_is_busy(self):
        values = build(unit=unit_values(Running=1))["values"]
        self.assertEqual(values["Press/Status/State"], gen.STATE_BUSY)

    def test_a_faulted_unit_is_error_whatever_else_it_is(self):
        values = build(unit=unit_values(Running=1, Error=1))["values"]
        self.assertEqual(values["Press/Status/State"], gen.STATE_ERROR)
        self.assertTrue(values["Press/Status/FaultActive"])

    def test_a_completed_unit_is_done(self):
        values = build(unit=unit_values(Complete=1))["values"]
        self.assertEqual(values["Press/Status/State"], gen.STATE_DONE)

    def test_an_idle_unit_is_ready(self):
        self.assertEqual(build()["values"]["Press/Status/State"], gen.STATE_READY)

    def test_the_unit_reports_counts_and_the_step(self):
        values = build(unit=unit_values(
            GoodCount=7, ScrapCount=2, Step=130))["values"]
        self.assertEqual(values["Press/GoodCount"], 7)
        self.assertEqual(values["Press/NokCount"], 2)
        self.assertEqual(values["Press/CurrentStep/StepNo"], 130)

    def test_a_stalled_chart_marks_the_step_timed_out(self):
        values = build(chart=chart_values(StallReason=6130))["values"]
        self.assertTrue(values["Press/CurrentStepTimedOut"])


class AbsenceTests(unittest.TestCase):
    """What the binding cannot publish is data, because silence would render."""

    def setUp(self):
        self.document = build()

    def test_absence_is_declared_with_a_reason(self):
        self.assertTrue(self.document["absent"])
        for entry in self.document["absent"]:
            self.assertTrue(entry["path"])
            self.assertTrue(entry["reason"])

    def test_nothing_declared_absent_is_also_published(self):
        # The list would be a lie the moment a path appeared in both.
        published = set(self.document["values"])
        for entry in self.document["absent"]:
            path = entry["path"]
            if path.endswith("/*"):
                prefix = path[:-1]
                self.assertFalse(
                    any(f"/{prefix}" in key for key in published), path)
            else:
                self.assertFalse(
                    any(key.endswith(f"/{path}") for key in published), path)

    def test_the_unpublished_io_surface_is_named(self):
        paths = {entry["path"] for entry in self.document["absent"]}
        self.assertIn("Status/Diagnostic/IoTag", paths)
        self.assertIn("AlarmLog/*", paths)
        self.assertIn("ControlPower/*", paths)


if __name__ == "__main__":
    unittest.main()


class MailboxProjectionTests(unittest.TestCase):
    """What the HMI's repository polls after it commits a command."""

    def setUp(self):
        import fraktal_ab_manifest as manifest

        self.manifest = manifest
        self.rows = manifest.content(APP)

    def values(self, **response):
        state = {"AckSequence": 0, "Accepted": 0, "DiagnosticKey": 0}
        state.update(response)
        return projection.mailbox_values(
            self.rows, state, state["AckSequence"])

    def test_it_publishes_the_paths_the_repository_reads(self):
        values = self.values()
        for path in ("HmiResponse/AckSequence", "HmiResponse/Accepted",
                     "HmiResponse/Diagnostic", "HmiRequest/Sequence"):
            self.assertIn(path, values)

    def test_accepted_is_a_boolean_for_the_client(self):
        self.assertIs(self.values(Accepted=1)["HmiResponse/Accepted"], True)
        self.assertIs(self.values(Accepted=0)["HmiResponse/Accepted"], False)

    def test_a_refusal_key_resolves_to_its_portable_name(self):
        key = self.manifest.numeric_key(
            APP, "project.mailbox.refused.no_control_power")
        self.assertEqual(self.values(DiagnosticKey=key)["HmiResponse/Diagnostic"],
                         "project.mailbox.refused.no_control_power")

    def test_an_accepted_command_carries_no_reason(self):
        self.assertEqual(self.values(Accepted=1)["HmiResponse/Diagnostic"], "")

    def test_an_unresolvable_key_is_reported_rather_than_blanked(self):
        # Blank would read as "accepted without comment", which is the one thing
        # a refusal must never look like.
        text = self.values(DiagnosticKey=999999)["HmiResponse/Diagnostic"]
        self.assertNotEqual(text, "")
        self.assertIn("999999", text)

    def test_every_refusal_the_handler_can_write_resolves(self):
        import fraktal_ab_mailbox as mailbox

        for portable in mailbox.localization_keys():
            key = self.manifest.numeric_key(APP, portable)
            self.assertEqual(
                self.values(DiagnosticKey=key)["HmiResponse/Diagnostic"],
                portable)

    def test_the_mailbox_reaches_the_document_under_the_root(self):
        document = build(mailbox_state={
            "response": {"AckSequence": 4, "Accepted": 1, "DiagnosticKey": 0},
            "requestSequence": 4,
        })
        self.assertEqual(document["values"]["Press/HmiResponse/AckSequence"], 4)
        self.assertIs(document["values"]["Press/HmiResponse/Accepted"], True)

    def test_a_document_without_mailbox_state_omits_it_rather_than_faking_it(self):
        values = build()["values"]
        self.assertNotIn("Press/HmiResponse/AckSequence", values)
