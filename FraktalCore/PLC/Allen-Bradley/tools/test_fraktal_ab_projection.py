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

import fraktal_ab_generate as gen
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
    return projection.project(
        kwargs.pop("header", good_header()),
        kwargs.pop("rows", manifest.content(APP)),
        kwargs.pop("unit", unit_values()),
        kwargs.pop("contexts", contexts()),
        kwargs.pop("chart", chart_values()),
    )


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
