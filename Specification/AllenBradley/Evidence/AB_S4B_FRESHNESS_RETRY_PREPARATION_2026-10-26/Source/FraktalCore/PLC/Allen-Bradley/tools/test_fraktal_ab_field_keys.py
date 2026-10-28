"""Fields.PathKey is relative to its module: what that changed, and what it didn't.

Audit 2026-09-29 §5 / Q2. Field keys were absolute and interned once per module
instance, so three identical cylinders cost 96 Localization rows for 32 names,
and the four missing press modules would have taken the table past what S7
measured. They are now relative to the canonical path of the row's ModuleId.

The promise was that no published path moves. These tests hold it to that by
composing paths the way a READER must - through the Modules table, from the
manifest as delivered - and comparing against the absolute form the old
contract used. A test that compared the emitter's own strings would prove only
that the emitter agrees with itself.
"""

import dataclasses
import unittest

import fraktal_ab_generate as gen
import fraktal_ab_manifest as manifest
import fraktal_ab_press_demo as demo


APP = demo.application()
CONTENT = manifest.content(APP)
PATHS = manifest.field_paths(CONTENT)


def _old_absolute_paths(app) -> set[str]:
    """The absolute keys the major-1 manifest published, rebuilt from scratch."""
    import fraktal_ab_mailbox as mailbox

    n = app.name
    out = {f"{n}.Unit.{m.name}" for m in gen.unit_context_members(app)}
    out |= {f"{n}.Chart.{m.name}" for m in gen.chart_members(app)}
    # Added after the rule changed (Core §8.3), and held to the same test: the
    # absolute form the old rule WOULD have produced is what the relative
    # composition must reproduce. An addition that composed to anything else
    # would be a field no reader could find.
    out |= {f"{n}.AlarmActive.{m.name}" for m in gen.alarm_active_members()}
    out |= {f"{n}.AlarmRing.{m.name}" for m in gen.alarm_ring_members()}
    # Added with Core §8.5.1 (audit Phase 5c): the OEE accounting and ring.
    out |= {f"{n}.Oee.{m.name}" for m in gen.oee_members()}
    # Added with Core §8.11.4 (audit Phase 5e): the cycle-time profile.
    out |= {f"{n}.Profiler.{m.name}" for m in gen.profiler_members(app)}
    if gen.editable_values(app):
        import fraktal_ab_config as config
        out |= {f"{n}.ConfigAudit.{m.name}" for m in config.audit_members()}
    if app.config_sets:
        import fraktal_ab_sets as sets
        out |= {f'{n}.ConfigSetState.{m.name}' for m in sets.state_members(app)}
    if app.line is not None:
        import fraktal_ab_line as line
        out |= {f'{n}.LineState.{m.name}' for m in line.state_members()}
        out |= {f'{n}.LineShift.{m.name}' for m in line.shift_members()}
    if app.access_users is not None:
        import fraktal_ab_access as access
        for prefix, members in (('AccessState', access.state_members(app)), ('AccessAudit', access.audit_members())):
            out |= {f'{n}.{prefix}.{m.name}' for m in members}
        import fraktal_ab_data_access as data
        for prefix, members in (('DataPolicy', data.policy_members(app)), ('DataLevels', data.levels_members(app))):
            out |= {f'{n}.{prefix}.{m.name}' for m in members}
    # Added with Core §8.12's input (AB S3): the controller health probe.
    out |= {f"{n}.HealthProbe.{m.name}" for m in gen.health_probe_members()}
    # Added with Core §8.12 (audit Phase 5h): the thresholds and the status.
    if app.system_health is not None:
        out |= {f"{n}.HealthCfg.{m.name}" for m in gen.health_cfg_members(app)}
        out |= {f"{n}.SystemHealth.{m.name}" for m in gen.system_health_members()}
    # Added with Core §3.12 (audit Phase 5g): the derived state flags.
    if app.state_flags:
        out |= {f"{n}.StateFlags.{m.name}" for m in gen.state_flags_members(app)}
    for record in app.records:
        out |= {f"{n}.{record.name}.{m.name}" for m in record.members}
    for module in app.modules:
        out |= {f"{n}.{module.name}.{m.name}"
                for m in gen.module_members(module)}
    out |= {f"{n}.HmiRequest.{name}" for name, *_ in mailbox.REQUEST_MEMBERS}
    out |= {f"{n}.HmiResponse.{name}" for name, *_ in mailbox.RESPONSE_MEMBERS}
    # Added with Core §7.8 (audit Phase 4b): TC3's HmiResponse.Report.
    out |= {f"{n}.HmiResponse.Report.{m.name}" for m in gen.release_report_members()}
    return out


def _sim_input_rows() -> set[str]:
    commanded = set(gen.command_inputs(APP))
    publishable = set(gen.publishable_tags(APP))
    return {tag for tag in APP.sim_inputs
            if tag in publishable and tag not in commanded}


class NoPublishedPathMoved(unittest.TestCase):
    def test_every_structured_path_is_byte_identical(self):
        """Every path the HMI can read composes to exactly what it was."""
        expected = _old_absolute_paths(APP)
        composed = {p for p in PATHS
                    if p.split(".", 1)[-1] not in _sim_input_rows()}
        self.assertEqual(composed, expected)

    def test_the_one_path_that_changed_is_the_simulated_stimulus(self):
        """Stated, not hidden. A simulated plant input was published as a bare
        tag name among browse paths - the only row that was never a path. Under
        one composition rule it becomes a path under the root. Nothing in the
        HMI reads these; they are what the parity harness writes, and Phase 3
        of the plan replaces them with real modules."""
        for tag in _sim_input_rows():
            self.assertIn(f"{APP.name}.{tag}", PATHS)
            self.assertNotIn(tag, PATHS)


class KeysAreShared(unittest.TestCase):
    def test_every_module_of_a_type_uses_the_same_member_keys(self):
        """The line the change exists for: one set of names per type, and the
        common base's names shared by every type."""
        import fraktal_ab_library as library

        keys = {r["NumericKey"]: r["PortableKey"] for r in CONTENT["Localization"]}
        ids = {keys[row["CanonicalPathKey"]].rsplit(".", 1)[-1]: row["ModuleId"]
               for row in CONTENT["Modules"] if row["ParentModuleId"] != 0}
        per_module: dict[str, set[int]] = {}
        for row in CONTENT["Fields"]:
            for name, module_id in ids.items():
                if row["ModuleId"] == module_id:
                    per_module.setdefault(name, set()).add(row["PathKey"])
        by_type: dict[str, list[set[int]]] = {}
        for module in APP.modules:
            by_type.setdefault(module.type_key, []).append(per_module[module.name])
        self.assertGreater(len(by_type[library.CYLINDER.type_key]), 1)
        for sets in by_type.values():
            for keyset in sets:
                self.assertEqual(keyset, sets[0])
        common = {k for k, v in keys.items()
                  if v in {m.name for m in gen.common_context_members()}}
        for sets in by_type.values():
            self.assertTrue(common <= sets[0])

    def test_another_module_adds_no_field_keys(self):
        """What makes Phase 3 fit: a fifth cylinder costs Fields rows, but not
        one Localization row for its fields."""
        extra = dataclasses.replace(
            APP.modules[0], name="ExtraCylinder")
        bigger = dataclasses.replace(APP, modules=APP.modules + (extra,))
        before = len(CONTENT["Localization"])
        after = len(manifest.content(bigger)["Localization"])
        # the new module's own identity keys, and nothing for its 32 fields
        self.assertLessEqual(after - before, 3)
        self.assertEqual(
            len(manifest.content(bigger)["Fields"]) - len(CONTENT["Fields"]),
            len(gen.module_members(extra)))

    def test_the_press_fits_the_declared_total(self):
        """The whole manifest, not any one table, is the limit."""
        self.assertLessEqual(manifest.estimated_bytes(APP), manifest.MANIFEST_BUDGET_BYTES)


class ReadersRefuseTheOldContract(unittest.TestCase):
    def test_the_major_moved(self):
        """A major-1 reader would compose wrong paths, so it must refuse."""
        self.assertGreaterEqual(manifest.MANIFEST_SCHEMA_MAJOR, 2)

    def test_the_projection_refuses_a_major_1_manifest(self):
        import fraktal_ab_projection as projection
        import test_fraktal_ab_projection as fixture

        header = dict(fixture.good_header(), SchemaMajor=1)
        with self.assertRaises(projection.ProjectionRefused):
            projection.validate(header)


class WriteCapabilitiesAgree(unittest.TestCase):
    def test_a_capability_names_its_field_the_same_way(self):
        """A capability points at a field; if the two used different forms,
        the page would name a field no reader can find."""
        keys = {r["NumericKey"]: r["PortableKey"]
                for r in CONTENT["Localization"]}
        field_keys = {r["PathKey"] for r in CONTENT["Fields"]}
        for cap in CONTENT["WriteCapabilities"]:
            self.assertIn(cap["PathKey"], field_keys, keys[cap["PathKey"]])

    def test_the_configuration_page_still_has_every_entry(self):
        """The failure this change nearly shipped: config_page required three
        dotted parts, relative keys have two, and every entry vanished."""
        import fraktal_ab_projection as projection

        values = {r.name: {m.name: m.initial for m in r.members}
                  for r in APP.records}
        page = projection.config_page(APP, CONTENT, values)
        self.assertEqual(page["HmiResponse/ConfigPage/EntryCount"],
                         len(gen.editable_values(APP)))


if __name__ == "__main__":
    unittest.main()
