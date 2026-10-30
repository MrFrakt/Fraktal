"""Core §3.8a/§3.8b on the Allen-Bradley binding: restore, and what it publishes.

The restore gate is the whole of what this binding claims so far. Logix has no
PERSISTENT variable class - retention is a property of controller memory and
its nonvolatile medium - so what is testable offline is the MECHANISM: that a
never-written image initializes silently, that a rejected one says so, and that
an intact one is left alone. Whether a written tag actually outlives a power
cycle is the measured retention matrix AB Part III §3.8b still owes, and no
test here claims it.
"""

import unittest

import fraktal_ab_declaration as decl
import fraktal_ab_generate as gen
import fraktal_ab_press_demo as demo
import fraktal_ab_projection as projection
import fraktal_ab_mailbox as mailbox
from test_fraktal_ab_sets import controller


APP = demo.application()


def _station_cfg_of(app):
    return gen.station_cfg_record(app)


class DeclarationRules(unittest.TestCase):
    def test_the_press_declares_deployment_data(self):
        record = _station_cfg_of(APP)
        self.assertIsNotNone(record)
        self.assertTrue(record.station_cfg)
        self.assertFalse(record.par_cfg)

    def test_a_station_cfg_leads_with_schema_version_at_zero(self):
        """Zero is §3.8a's 'never written', and on Logix it is also what a
        download leaves behind. Both cases want the same answer, which is what
        makes one marker enough."""
        record = _station_cfg_of(APP)
        self.assertEqual(record.members[0].name, decl.SCHEMA_VERSION_MEMBER)
        self.assertEqual(record.members[0].initial, 0)

    def test_a_non_zero_initial_is_refused(self):
        bad = decl.Record(
            name="FRK_T_Bad", station_cfg=True, schema_version=1,
            members=(decl.scalar(decl.SCHEMA_VERSION_MEMBER, "", initial=1),))
        findings = decl._validate_record(bad)
        self.assertTrue(any("starts at 0" in f for f in findings), findings)

    def test_a_record_is_recipe_or_deployment_not_both(self):
        bad = decl.Record(
            name="FRK_T_Bad", par_cfg=True, station_cfg=True,
            members=(decl.scalar(decl.SCHEMA_VERSION_MEMBER, "", initial=0),))
        findings = decl._validate_record(bad)
        self.assertTrue(any("not\nboth" in f or "not both" in f.replace("\n", " ")
                            for f in findings), findings)

    def test_schema_version_zero_is_not_a_real_contract(self):
        bad = decl.Record(
            name="FRK_T_Bad", station_cfg=True, schema_version=0,
            members=(decl.scalar(decl.SCHEMA_VERSION_MEMBER, "", initial=0),))
        findings = decl._validate_record(bad)
        self.assertTrue(any("reserved" in f for f in findings), findings)


class RestoreLogic(unittest.TestCase):
    def setUp(self):
        self.lines = gen.config_restore_logic(APP)
        self.text = "\n".join(self.lines)
        self.record = _station_cfg_of(APP)
        self.tag = f"{self.record.name}Tag"
        # Installed values are stamped with the declared version, or left at
        # zero while a live-document restore is still to answer (§3.8b).
        self.stamp = 0 if decl.live_documents(APP) else self.record.schema_version

    def restore(self, version, *, first_scan=True):
        c = controller(APP)
        c.tags['S:FS'] = first_scan
        for bank in c.tags[gen.model_cfg_tag(APP)][:len(APP.models)]:
            bank['SchemaVersion'] = gen.model_cfg_schema_version(APP)
        for member in self.record.members:
            c.tags[self.tag][member.name] = member.initial + 1
        c.tags[self.tag]['SchemaVersion'] = version
        before = dict(c.tags[self.tag])
        persist = c.tags[gen.config_persist_tag(APP)]
        persist.update(RestoreLost=1, RestoreAcknowledged=1, LostModuleId=2)
        c.run(self.text)
        return c.tags[self.tag], persist, before

    def test_it_runs_on_the_first_scan_after_entering_run(self):
        """S:FS, never a scan counter.

        ScanCount is an ordinary controller tag. It is zero after a DOWNLOAD,
        which is why a counter looked correct on the bench, but a POWER CYCLE
        resumes it - so the gate would never have run on the one event it
        exists for. Measured on 7036B510 at ScanCount 16384.
        """
        self.assertIn("IF S:FS THEN", self.text)
        self.assertNotIn("ScanCount = 0", self.text)

    def test_never_written_installs_defaults_and_says_nothing(self):
        image, persist, _ = self.restore(0)
        self.assertEqual(image['SchemaVersion'], self.stamp)
        self.assertEqual((persist['RestoreLost'], persist['LostModuleId']), (0, 0))

    def test_an_unrecognized_version_is_annunciated(self):
        """The difference between an empty machine and one that has just lost
        its commissioning is exactly what an operator needs told."""
        image, persist, _ = self.restore(99)
        self.assertEqual(image['SchemaVersion'], self.stamp)
        self.assertEqual((persist['RestoreLost'], persist['LostModuleId'],
                          persist['RestoreAcknowledged']), (1, 1, 0))

    def test_both_paths_install_every_declared_default(self):
        values = [m for m in self.record.members
                  if m.name != decl.SCHEMA_VERSION_MEMBER]
        self.assertTrue(values)
        for version in (0, 99):
            with self.subTest(version=version):
                image, _, _ = self.restore(version)
                for member in values:
                    self.assertEqual(image[member.name], member.initial, member.name)

    def test_an_intact_image_is_left_alone(self):
        """A matching version preserves every commissioned value."""
        image, persist, before = self.restore(self.record.schema_version)
        self.assertEqual(image, before)
        self.assertEqual(persist['RestoreLost'], 0)

    def test_later_scans_preserve_the_image_and_loss_acknowledgement(self):
        image, persist, before = self.restore(99, first_scan=False)
        self.assertEqual(image, before)
        self.assertEqual((persist['RestoreLost'], persist['LostModuleId'],
                          persist['RestoreAcknowledged']), (1, 2, 1))

    def test_a_station_with_no_deployment_data_still_answers(self):
        """Positively, rather than by leaving the record unwritten - a client
        reads an unwritten record as fine, and it should be right for the right
        reason."""
        bare = decl.Application(
            **{**APP.__dict__,
               "records": tuple(r for r in APP.records if not r.station_cfg)})
        text = "\n".join(gen.config_restore_logic(bare))
        self.assertIn(f"{gen.config_persist_tag(APP)}.RestoreLost := 0;", text)
        self.assertNotIn("ScanCount = 0", text)

    def test_restore_precedes_every_module(self):
        """No module may read a value that is about to be replaced by its
        default, so the gate runs before the first AOI call."""
        routine = list(gen.routine_logic(APP))
        restore = routine.index("IF S:FS THEN")
        increment = routine.index(
            f"FRK_{APP.name}_ScanCount := FRK_{APP.name}_ScanCount + 1;")
        first_module = next(
            i for i, line in enumerate(routine)
            if line.startswith(gen.module_aoi_name(APP, APP.modules[0])))
        self.assertLess(restore, increment)
        self.assertLess(restore, first_module)


class LossIsDecidedOncePerStart(unittest.TestCase):
    def setUp(self):
        self.lines = gen.config_restore_logic(APP)
        self.persist = gen.config_persist_tag(APP)

    def test_the_loss_is_cleared_only_on_first_scan(self):
        """Cleared anywhere else, a later record's verdict overwrites an
        earlier one's. The old no-StationCfg branch wrote 0 every scan and
        would have wiped a model loss the moment it was raised."""
        start = self.lines.index("IF S:FS THEN")
        clears = [i for i, line in enumerate(self.lines)
                  if line == f"{self.persist}.RestoreLost := 0;"]
        self.assertEqual(len(clears), 1)
        self.assertGreater(clears[0], start)
        self.assertEqual(self.lines[-1], "END_IF;")

    def test_a_new_loss_needs_a_new_acknowledgement(self):
        self.assertIn(f"{self.persist}.RestoreAcknowledged := 0;", self.lines)

    def test_the_loss_is_cleared_before_any_restore_can_raise_it(self):
        clear = self.lines.index(f"{self.persist}.RestoreLost := 0;")
        raises = [i for i, line in enumerate(self.lines)
                  if line == f"{self.persist}.RestoreLost := 1;"]
        self.assertTrue(raises)
        self.assertTrue(all(i > clear for i in raises))


class AcknowledgeRestore(unittest.TestCase):
    """D2 of the audit: the banner offered Acknowledge and AB refused it."""

    def setUp(self):
        self.text = chr(10).join(mailbox._dispatch(APP))
        self.persist = gen.config_persist_tag(APP)

    def test_it_is_routed_not_refused(self):
        self.assertNotIn(mailbox.ACK_CONFIG_RESTORE, mailbox.refused_for(APP))
        self.assertIn(f"{mailbox.ACK_CONFIG_RESTORE}: (* ACK_CONFIG_RESTORE *)",
                      self.text)

    def test_nothing_lost_is_refused_with_tc3s_key(self):
        branch = self.text.split("(* ACK_CONFIG_RESTORE *)")[1].split("ELSE")[0]
        self.assertIn(f"IF {self.persist}.RestoreLost = 0 THEN", branch)
        self.assertIn("std.error.configRestoreAckRefused", branch)

    def test_a_loss_is_acknowledged(self):
        branch = self.text.split("(* ACK_CONFIG_RESTORE *)")[1].split("END_IF;")[0]
        self.assertIn(f"{self.persist}.RestoreAcknowledged := 1;", branch)

    def test_the_refusal_key_is_published(self):
        self.assertIn(mailbox.RESTORE_ACK_REFUSED_KEY,
                      mailbox.localization_keys())


class PublishedSurface(unittest.TestCase):
    def test_the_durability_record_is_a_published_tag(self):
        self.assertIn(gen.config_persist_tag(APP), gen.publishable_tags(APP))

    def test_the_contract_type_is_emitted(self):
        self.assertIn(gen.config_persist_name(APP), gen.data_types(APP))

    def test_no_member_is_a_bool(self):
        """S12 froze the v33 type map: a public contract UDT carries no BOOL."""
        for member in gen.config_persist_members():
            self.assertIn(member.kind, ("scalar", "duration_ms"), member.name)

    def test_a_station_that_cannot_answer_publishes_nothing(self):
        """Absent is not the same as healthy. A build emitted before §3.8b has
        no such tag, and inventing zeroes would report a station safe on no
        evidence at all."""
        self.assertEqual(projection.config_persist_status(APP, None), {})

    def test_a_healthy_station_publishes_every_field_anyway(self):
        values = projection.config_persist_status(
            APP, {m.name: 0 for m in gen.config_persist_members()})
        self.assertEqual(values["ConfigPersist/RestoreLost"], False)
        self.assertEqual(values["ConfigPersist/LostPath"], "")
        # "No problem" and "no answer" render identically to a client, so the
        # healthy case is still ten published values.
        self.assertEqual(len(values), 10)

    def test_the_lost_module_ordinal_resolves_to_a_canonical_path(self):
        first = APP.modules[0].name
        self.assertEqual(projection._module_path(APP, 1), APP.name)
        self.assertEqual(projection._module_path(APP, 2), f"{APP.name}.{first}")
        self.assertEqual(projection._module_path(APP, 0), "")
        self.assertEqual(projection._module_path(APP, 999), "")

    def test_the_store_is_absent_and_says_so(self):
        """SAVE/LOAD/LIST_CONFIG_SET are refused by name, so the HMI must not
        offer save/load/list at all."""
        values = projection.config_persist_status(
            APP, {m.name: 0 for m in gen.config_persist_members()})
        self.assertFalse(values["ConfigPersist/StorePresent"])
        for kind in (mailbox.SAVE_CONFIG_SET, mailbox.LOAD_CONFIG_SET):
            self.assertIn(kind, mailbox.REFUSED)


class WriteSurfaceUnchanged(unittest.TestCase):
    """The press now routes WRITE_CONFIG - decided explicitly on 2026-09-29.

    What must NOT follow from that is a wider tag surface. Configuration is
    written through the mailbox, which validates; it is never written by
    addressing the record tag directly, which would skip every bound.
    """

    def test_the_press_routes_configuration_writes(self):
        self.assertNotIn(mailbox.WRITE_CONFIG, mailbox.refused_for(APP))

    def test_a_station_with_no_editable_value_still_refuses_by_name(self):
        """`no_config_manifest`, never `unknown_kind`: the kind is known and it
        is the station that has nothing to configure."""
        import dataclasses
        bare = dataclasses.replace(APP, records=tuple(
            dataclasses.replace(r, members=tuple(
                dataclasses.replace(m, write_key="") for m in r.members))
            for r in APP.records))
        self.assertEqual(mailbox.refused_for(bare)[mailbox.WRITE_CONFIG],
                         "project.mailbox.refused.no_config_manifest")

    def test_the_record_tags_are_still_not_directly_writable(self):
        record = _station_cfg_of(APP)
        writable = gen.externally_writable(APP)
        self.assertNotIn(f"{record.name}Tag", writable)
        self.assertNotIn(f"{APP.records[0].name}Tag", writable)
        self.assertNotIn(gen.config_persist_tag(APP), writable)


if __name__ == "__main__":
    unittest.main()
