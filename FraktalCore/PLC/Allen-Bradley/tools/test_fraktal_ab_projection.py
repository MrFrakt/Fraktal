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



class TypeKeyTests(unittest.TestCase):
    """LOCALIZATION §7.1: one faceplate per type, across bindings.

    The keys are the ones the TwinCAT press publishes for the same types, so a
    layout authored on either press applies to the other.
    """

    def published(self):
        values = build()["values"]
        return {path.rsplit("/Status/TypeKey", 1)[0]: value
                for path, value in values.items()
                if path.endswith("/Status/TypeKey")}

    def test_every_cylinder_publishes_the_tc3_cylinder_key(self):
        keys = self.published()
        cylinders = [m.name for m in APP.modules]
        self.assertTrue(cylinders)
        for name in cylinders:
            matches = [k for path, k in keys.items() if path.endswith("/" + name)]
            self.assertEqual(matches, ["std.moduleType.cylinder"], name)

    def test_the_root_unit_publishes_the_press_key(self):
        root = [k for path, k in self.published().items() if "/" not in path]
        self.assertEqual(root, ["project.moduleType.pneumaticPress"])

    def test_a_type_key_is_not_part_of_the_controller_manifest(self):
        # Presentation vocabulary: changing it must never ask for a download.
        renamed = replace(APP, type_key="project.moduleType.other", modules=tuple(
            replace(m, type_key="project.moduleType.other") for m in APP.modules))
        self.assertEqual(manifest.content_hash(renamed),
                         manifest.content_hash(APP))

    def test_a_malformed_type_key_is_refused(self):
        for bad in ("cylinder", "std.moduleType.cylinder.name",
                    "project.module.PressRam.name", "std.moduleType.a b"):
            app = replace(APP, modules=(replace(APP.modules[0], type_key=bad),)
                          + APP.modules[1:])
            self.assertTrue(
                any("type key" in f for f in decl.validate(app)), bad)


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


class ChangeoverTests(unittest.TestCase):
    """Core §3.8 changeover: prepare may fail, commit may not.

    The split is the whole design, so the tests are about WHERE a failure can
    happen. Everything that can reject - is this a model this station has? -
    happens before the commit; the commit is a bounded copy of declared
    numbers and has no branch that can leave the press configured as neither
    model.
    """

    def setUp(self):
        self.app = projection.APP

    def test_a_model_changes_what_the_press_does_not_just_its_label(self):
        # A "changeover" that only renames the screen is not one.
        dwells = {m.values["PressDwellMs"] for m in self.app.models}
        self.assertEqual(len(dwells), len(self.app.models))

    def test_the_committed_model_is_published_and_zero_means_none(self):
        values = build(unit=unit_values(ModelOrdinal=0))["values"]
        self.assertEqual(values["Press/Model/ModelCode"], "")
        values = build(unit=unit_values(ModelOrdinal=2))["values"]
        self.assertEqual(values["Press/Model/ModelCode"],
                         self.app.models[1].code)

    def test_the_catalogue_comes_from_the_declaration(self):
        values = build()["values"]
        self.assertEqual(values["Press/AvailableModelCount"],
                         len(self.app.models))
        published = [values[f"Press/AvailableModels[{i}]/ModelCode"]
                     for i in range(1, len(self.app.models) + 1)]
        self.assertEqual(published, [m.code for m in self.app.models])

    def test_an_ordinal_the_station_does_not_have_publishes_no_code(self):
        # Never the nearest model: a wrong code on a changeover screen is how
        # a press runs one product's dwell against another's tooling.
        values = build(unit=unit_values(ModelOrdinal=99))["values"]
        self.assertEqual(values["Press/Model/ModelCode"], "")

    def test_a_model_code_resolves_to_its_ordinal_and_nothing_else_does(self):
        self.assertEqual(mailbox.model_ordinal(self.app, "M-200"), 2)
        self.assertEqual(mailbox.model_ordinal(self.app, "M-999"), 0)
        self.assertEqual(mailbox.model_ordinal(self.app, ""), 0)

    def test_set_model_resolves_the_code_the_hmi_sends(self):
        # opcua_repository sends the code in TextValue; v33 cannot compare
        # strings, so the gateway is what turns it into the ordinal.
        root = "Press/HmiRequest/"
        batch = [
            (root + "Kind", "int32", mailbox.SET_MODEL),
            (root + "TextValue", "string", "M-050"),
            (root + "Sequence", "uint32", 4),
        ]
        out = mailbox.resolve_batch(self.app, batch)
        values = {p.rsplit("/", 1)[-1]: v for p, _t, v in out}
        self.assertEqual(values["IntValue"], 3)
        self.assertTrue(out[-1][0].endswith("/Sequence"))

    def test_an_unknown_code_resolves_to_zero_for_the_controller_to_refuse(self):
        root = "Press/HmiRequest/"
        out = mailbox.resolve_batch(self.app, [
            (root + "Kind", "int32", mailbox.SET_MODEL),
            (root + "TextValue", "string", "NOPE"),
            (root + "Sequence", "uint32", 5),
        ])
        values = {p.rsplit("/", 1)[-1]: v for p, _t, v in out}
        self.assertEqual(values["IntValue"], 0)

    def test_set_model_is_routed_not_refused(self):
        self.assertIn(mailbox.SET_MODEL, mailbox.SUPPORTED)
        self.assertNotIn(mailbox.SET_MODEL, mailbox.REFUSED)

    def test_the_handler_refuses_an_ordinal_the_station_does_not_declare(self):
        body = "\n".join(mailbox.handler_logic(self.app))
        self.assertIn(f"{mailbox.SET_MODEL}: (* SET_MODEL *)", body)
        self.assertIn(f"<= {len(self.app.models)}", body)
        self.assertIn("model_not_declared", body)

    def test_the_commit_writes_every_declared_value_and_nothing_else(self):
        chain = next(c for c in self.app.chains if c.name == "CHANGEOVER")
        commit = next(s for s in chain.steps if s.name == "changeoverCommit")
        text = " ".join(commit.marks)
        for model in self.app.models:
            for member, value in model.values.items():
                self.assertIn(f"Cfg.{member} := {value};", text)
        # and it records WHICH model it committed, or the published code would
        # keep naming the previous one
        self.assertIn("Ctx.ModelOrdinal :=", text)

    def test_the_commit_step_has_no_branch(self):
        # §3.8: the commit is infallible. A MARK step cannot fail or wait; if
        # this ever became an AWAIT or an ISSUE the guarantee would be gone.
        chain = next(c for c in self.app.chains if c.name == "CHANGEOVER")
        commit = next(s for s in chain.steps if s.name == "changeoverCommit")
        self.assertEqual(commit.action, decl.MARK)
        self.assertEqual(commit.on_jump, -1)

    def test_the_confirmation_can_send_the_operator_back_to_the_position(self):
        # The TC3 oracle's shape: answering "repeat" re-drives the guided
        # position rather than simply asking again.
        chain = next(c for c in self.app.chains if c.name == "CHANGEOVER")
        confirm = next(s for s in chain.steps if s.name == "changeoverConfirm")
        self.assertEqual(confirm.action, decl.DECISION)
        positions = [s.number for s in chain.steps
                     if s.name == "changeoverRamUp"]
        self.assertEqual(confirm.on_jump, positions[0])

    def test_a_model_naming_an_unknown_member_is_refused(self):
        bad = replace(self.app, models=(
            decl.Model(code="X", description_key="k",
                       values={"NotAMember": 1}),))
        self.assertTrue(
            any("not a member" in f for f in decl.validate(bad)))

    def test_a_model_may_not_rewrite_the_schema_version(self):
        bad = replace(self.app, models=(
            decl.Model(code="X", description_key="k",
                       values={decl.SCHEMA_VERSION_MEMBER: 2}),))
        self.assertTrue(
            any("SchemaVersion" in f for f in decl.validate(bad)))

    def test_a_model_that_changes_nothing_is_refused(self):
        bad = replace(self.app, models=(
            decl.Model(code="X", description_key="k", values={}),))
        self.assertTrue(any("label, not a changeover" in f
                            for f in decl.validate(bad)))

    def test_the_running_step_is_published_by_name(self):
        # Without this the operator sees a blank where the guidance goes, and
        # a chain waiting for a decision looks exactly like one that hung.
        values = build(unit=unit_values(Mode=3, Step=700))["values"]
        self.assertEqual(values["Press/CurrentStep/StepName"],
                         "project.step.changeoverValidateModel")

    def test_the_step_name_follows_the_running_chain_not_just_the_number(self):
        # Step numbers are per-chain, so resolving without the mode would name
        # whichever chain happened to declare that number first.
        auto = build(unit=unit_values(Mode=0, Step=0))["values"]
        manual = build(unit=unit_values(Mode=1, Step=0))["values"]
        self.assertNotEqual(auto["Press/CurrentStep/StepName"],
                            manual["Press/CurrentStep/StepName"])

    def test_a_step_the_chain_does_not_have_publishes_an_empty_name(self):
        # Present and empty, not absent: the key has to exist in every state
        # or the path set moves. See the path-set invariant below.
        values = build(unit=unit_values(Mode=3, Step=54321))["values"]
        self.assertEqual(values["Press/CurrentStep/StepName"], "")

    def test_a_fresh_station_publishes_the_model_it_is_configured_as(self):
        # ModelOrdinal starts at the default, so a downloaded station says
        # which product it is set up for instead of reporting none.
        self.assertEqual(gen.default_model_ordinal(self.app), 1)
        member = next(m for m in gen.unit_context_members(self.app)
                      if m.name == "ModelOrdinal")
        self.assertEqual(member.initial, gen.default_model_ordinal(self.app))

    def test_a_default_model_that_disagrees_with_the_initials_is_refused(self):
        # The station would boot claiming one model while running another's
        # numbers, which is worse than claiming nothing.
        bad = replace(self.app, default_model="M-200")
        findings = decl.validate(bad)
        self.assertTrue(any("claiming a model it is not configured as" in f
                            for f in findings), findings)

    def test_an_undeclared_default_model_is_refused(self):
        bad = replace(self.app, default_model="M-999")
        self.assertTrue(any("is not declared" in f for f in decl.validate(bad)))

    def test_models_without_a_default_are_refused(self):
        bad = replace(self.app, default_model="")
        self.assertTrue(any("none is the default" in f
                            for f in decl.validate(bad)))

    def test_the_station_publishes_a_policy_rather_than_silence(self):
        # The mapper fails closed on a missing policy, so publishing nothing
        # hid every operational section - including the prompt a changeover
        # shows while it waits for a model. A station that enforces no levels
        # has to SAY so.
        values = build()["values"]
        required = [values[f"Press/Access/Policy/Required[{i}]"]
                    for i in range(1, projection.GATED_ACTION_COUNT + 1)]
        self.assertEqual(required,
                         [projection.ACCESS_NONE] * projection.GATED_ACTION_COUNT)

    def test_the_policy_covers_every_gated_action(self):
        # A short array is the fail-closed case: the mapper refuses any action
        # whose index it cannot find, so a missing entry silently disables it.
        values = build()["values"]
        published = [k for k in values if "Access/Policy/Required[" in k]
        self.assertEqual(len(published), projection.GATED_ACTION_COUNT)

    def test_the_current_level_is_operator_not_admin(self):
        # The transport authenticated somebody, which is the ordinary
        # operating surface. It is not evidence of an engineer.
        values = build()["values"]
        self.assertEqual(values["Press/Access/CurrentLevel"],
                         projection.ACCESS_OPERATOR)

    def test_a_waiting_decision_publishes_its_question(self):
        # The HMI shows a decision card only when a prompt is present, so a
        # chain parked on a decision with nothing published looks exactly
        # like one that stopped. That is how the changeover presented.
        values = build(unit=unit_values(Mode=3, Step=780, DecisionId=2))["values"]
        self.assertEqual(values["Press/Decision/Prompt"],
                         "project.decision.changeoverConfirm")
        self.assertEqual(values["Press/Decision/Options[1]"],
                         "project.decision.confirmChangeover")

    def test_no_decision_publishes_an_empty_prompt(self):
        # The HMI draws a decision card only when the prompt is non-empty, so
        # empty is the "nothing pending" signal - and keeping the key present
        # is what stops the path set moving under a client's targeted reads.
        values = build(unit=unit_values(DecisionId=0))["values"]
        self.assertEqual(values["Press/Decision/Prompt"], "")
        self.assertEqual(values["Press/Decision/Options[1]"], "")

    def test_the_first_option_is_the_one_that_continues(self):
        # The emitted DECISION logic advances on answer 1 and jumps on
        # anything else, so declaring them the other way round would put
        # "scrap the part" under the button meaning "carry on".
        for decision in self.app.decisions:
            self.assertGreaterEqual(len(decision.option_keys), 2)
        confirm = next(d for d in self.app.decisions if d.identifier == 2)
        self.assertEqual(confirm.option_keys[0],
                         "project.decision.confirmChangeover")

    def test_a_step_waiting_on_an_undeclared_decision_is_refused(self):
        # A chain that waits on a question nobody can read waits forever.
        bad = replace(self.app, decisions=())
        findings = decl.validate(bad)
        self.assertTrue(any("not declared" in f and "waits on decision" in f
                            for f in findings), findings)

    def test_the_published_path_set_does_not_depend_on_machine_state(self):
        """The invariant a conditional surface breaks.

        The gateway raises its discovery revision whenever the set of
        published paths changes, and a client's targeted reads are keyed on
        that revision. So a path that appears only while a decision is
        pending invalidates every read in flight the moment the decision
        starts or ends - and the HMI polls HmiResponse/AckSequence that way.
        A decision ending mid-request made it miss the acknowledgement and
        report a command that had already succeeded as blocked.

        Values may change freely. The KEYS may not.
        """
        states = [
            unit_values(),
            unit_values(Mode=3, Step=780, DecisionId=2),
            unit_values(Mode=0, Step=100, DecisionId=1),
            unit_values(Mode=1, Step=0, ModelOrdinal=3),
            unit_values(Mode=2, Step=54321, DecisionId=999),
            unit_values(Mode=7, Step=0),
        ]
        reference = set(build(unit=states[0])["values"])
        for state in states[1:]:
            paths = set(build(unit=state)["values"])
            self.assertEqual(
                paths, reference,
                f"path set moved: {sorted(paths ^ reference)}")

    def test_an_application_without_models_publishes_no_changeover(self):
        bare = replace(self.app, models=())
        self.assertEqual(projection.model_status(bare, {"ModelOrdinal": 0}), {})


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
