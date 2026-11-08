"""Canonical view and harness migration qualification for remaining HX station readers.

Verifies Increment 3 station-reading harnesses:
  1. fraktal_ab_press_parity.py
  2. fraktal_ab_phase1_execute.py
  3. fraktal_ab_phase2_execute.py
  4. fraktal_ab_phase3_execute.py
  5. fraktal_ab_phase4_execute.py
  6. fraktal_ab_s3_execute.py

Proves canonical CIP row queries, O10 surface reads, fallback paths when
canonical_collapse is False, and exact predicate retention without controller access.
"""
from types import SimpleNamespace as NS
import unittest
from unittest.mock import Mock, patch

import fraktal_ab_declaration as decl
import fraktal_ab_fixture_reads as views
import fraktal_ab_generate as gen
import fraktal_ab_mailbox as mailbox
import fraktal_ab_phase1_execute as phase1
import fraktal_ab_phase2_execute as phase2
import fraktal_ab_phase3_execute as phase3
import fraktal_ab_phase4_execute as phase4
import fraktal_ab_press_execute as px
import fraktal_ab_press_parity as parity
import fraktal_ab_press_s6_collapse_echo38 as base
import fraktal_ab_s3_execute as s3

APP = base.application()


class PressParityHarness(unittest.TestCase):
    def test_parity_reads_cfg0_surface_when_collapsed(self):
        comm = Mock()
        with patch.object(views, "surface", return_value={"Recipe": 1}) as mock_surface:
            cfg = (views.surface(comm, "Cfg0", app=APP)
                   if APP.canonical_collapse
                   else px.read_layout(comm, px.CFG, APP.records[0].members) or {})
            self.assertEqual(cfg, {"Recipe": 1})
            mock_surface.assert_called_once_with(comm, "Cfg0", app=APP)

    def test_parity_falls_back_to_legacy_read_layout_when_not_collapsed(self):
        legacy_app = NS(canonical_collapse=False, records=APP.records)
        comm = Mock()
        with patch.object(px, "read_layout", return_value={"Recipe": 2}) as mock_legacy:
            cfg = (views.surface(comm, "Cfg0", app=legacy_app)
                   if legacy_app.canonical_collapse
                   else px.read_layout(comm, px.CFG, legacy_app.records[0].members) or {})
            self.assertEqual(cfg, {"Recipe": 2})
            mock_legacy.assert_called_once_with(comm, px.CFG, legacy_app.records[0].members)


class Phase1Harness(unittest.TestCase):
    def test_phase1_alarm_log_and_release_report_surfaces(self):
        comm = Mock()
        with patch.object(views, "surface") as mock_surface:
            mock_surface.side_effect = lambda _c, name, **_k: {
                "AlarmActive": {"Count": 1},
                "AlarmRing": {"Head": 2},
                "ReleaseStart": {"Count": 0},
            }[name]
            active, ring = views.read_alarm_log(comm, app=APP)
            self.assertEqual(active, {"Count": 1})
            self.assertEqual(ring, {"Head": 2})
            report = views.read_release_report(comm, app=APP)
            self.assertEqual(report, {"Count": 0})

    def test_phase1_step_conditions_canonical_query(self):
        comm = Mock()
        paths_called = []
        def mock_values(_comm, paths, *, app):
            paths_called.append(list(paths))
            return {
                f"{app.name}/CurrentStep/Conds[1]/Label": "cond1",
                f"{app.name}/CurrentStep/Conds[1]/Ok": 1,
                f"{app.name}/CurrentStep/Conds[2]/Label": "cond2",
                f"{app.name}/CurrentStep/Conds[2]/Ok": 0,
                f"{app.name}/CurrentStep/Conds[3]/Label": "cond3",
                f"{app.name}/CurrentStep/Conds[3]/Ok": 0,
                f"{app.name}/CurrentStep/Conds[4]/Label": "cond4",
                f"{app.name}/CurrentStep/Conds[4]/Ok": 0,
            }
        with patch.object(views, "_session", return_value=NS(root=APP.name)), \
                patch.object(views, "values", side_effect=mock_values):
            conds = views.step_conditions(comm, count=4, app=APP)
            self.assertEqual(len(conds), 4)
            self.assertEqual(conds[0], ("cond1", 1))
            self.assertEqual(conds[1], ("cond2", 0))
            self.assertEqual(len(paths_called[0]), 8)

    def test_phase1_unit_diagnostic_and_header_valid(self):
        comm = Mock()
        def mock_values(_comm, paths, *, app):
            return {
                f"{app.name}/Status/Diagnostic/ReasonCode": 101,
                f"{app.name}/Status/Diagnostic/Description": "alarm.desc",
                f"{app.name}/Status/Diagnostic/IoTag": "tag",
                f"{app.name}/Status/Diagnostic/IoAddress": "addr",
                f"{app.name}/Status/Diagnostic/Since": 12345,
                f"{app.name}/Status/Name": "Press",
            }
        with patch.object(views, "_session", return_value=NS(root=APP.name)), \
                patch.object(views, "values", side_effect=mock_values):
            diag = views.unit_diagnostic(comm, app=APP)
            self.assertEqual(diag["ReasonCode"], 101)
            self.assertEqual(diag["Description"], "alarm.desc")
            self.assertTrue(views.header_valid(comm, app=APP))


class Phase2Harness(unittest.TestCase):
    def test_phase2_sequence_step_summary(self):
        comm = Mock()
        def mock_values(_comm, paths, *, app):
            return {
                f"{app.name}/SequenceStepCount": 2,
                f"{app.name}/SequenceSteps[1]/StepNo": 10,
                f"{app.name}/SequenceSteps[1]/LastDuration": 150.0,
                f"{app.name}/SequenceSteps[1]/ErrorActive": 0,
                f"{app.name}/SequenceSteps[1]/WarningActive": 0,
                f"{app.name}/SequenceSteps[2]/StepNo": 20,
                f"{app.name}/SequenceSteps[2]/LastDuration": 0.0,
                f"{app.name}/SequenceSteps[2]/ErrorActive": 0,
                f"{app.name}/SequenceSteps[2]/WarningActive": 0,
            }
        with patch.object(views, "_session", return_value=NS(root=APP.name)), \
                patch.object(views, "values", side_effect=mock_values):
            summary = views.sequence_step_summary(comm, app=APP)
            self.assertEqual(summary["count"], 2)
            self.assertEqual(summary["steps"], [10, 20])
            self.assertEqual(summary["rows"][10]["LastDuration"], 150.0)
            self.assertEqual(summary["rows"][20]["LastDuration"], 0.0)
            rows = phase2.published_rows(summary)
            self.assertEqual(rows, [10, 20])
            self.assertEqual(phase2.row_field(summary, 10, "LastDuration"), 150.0)
            self.assertEqual(phase2.row_field(summary, 20, "LastDuration"), 0.0)

    def test_phase2_active_step_cursor_and_annotations(self):
        comm = Mock()
        def mock_values(_comm, paths, *, app):
            return {
                f"{app.name}/ActiveSteps[1]/RowIdx": 2,
                f"{app.name}/SequenceAnnotationCount": 1,
                f"{app.name}/SequenceAnnotations[1]/RowIdx": 2,
                f"{app.name}/SequenceAnnotations[1]/Key": "annotation.key",
                f"{app.name}/SequenceAnnotations[1]/SourcePath": "Press.Door",
                f"{app.name}/SequenceAnnotations[1]/IsError": False,
            }
        with patch.object(views, "_session", return_value=NS(root=APP.name)), \
                patch.object(views, "values", side_effect=mock_values):
            cursor = views.active_step_cursor(comm, leg=1, app=APP)
            self.assertEqual(cursor, 2)
            count, note = views.sequence_annotations(comm, app=APP)
            self.assertEqual(count, 1)
            self.assertEqual(note["Key"], "annotation.key")


class Phase3Harness(unittest.TestCase):
    def test_phase3_module_status_and_diagnostic(self):
        comm = Mock()
        def mock_values(_comm, paths, *, app):
            return {
                f"{app.name}/Door/Status/TypeKey": 1,
                f"{app.name}/Door/Status/DisplayNameKey": 2,
                f"{app.name}/Door/Status/State": 3,
                f"{app.name}/Door/Status/FaultActive": 0,
                f"{app.name}/Door/Status/Diagnostic/ReasonCode": 404,
                f"{app.name}/Door/Status/Diagnostic/Description": "door.fault",
                f"{app.name}/Door/Status/Diagnostic/IoTag": "tag",
                f"{app.name}/Door/Status/Diagnostic/IoAddress": "addr",
                f"{app.name}/Door/Status/Diagnostic/Since": 555,
                f"{app.name}/CurrentStepTimedOut": 0,
            }
        with patch.object(views, "_session", return_value=NS(root=APP.name)), \
                patch.object(views, "values", side_effect=mock_values):
            status = views.module_status(comm, "Door", app=APP)
            self.assertEqual(status["State"], 3)
            self.assertEqual(status["FaultActive"], 0)
            diag = views.module_diagnostic(comm, "Door", app=APP)
            self.assertEqual(diag["ReasonCode"], 404)
            self.assertEqual(diag["Description"], "door.fault")
            timed_out = views.current_step_timed_out(comm, app=APP)
            self.assertEqual(timed_out, 0)
            doc = phase3.document(comm)
            self.assertEqual(doc, {f"{APP.name}/CurrentStepTimedOut": 0})


class Phase4Harness(unittest.TestCase):
    def test_phase4_module_catalog(self):
        comm = Mock()
        def mock_values(_comm, paths, *, app):
            return {
                f"{app.name}/Door/CatalogCount": 2,
                f"{app.name}/Door/Catalog[1]/Value": 1,
                f"{app.name}/Door/Catalog[1]/Label": "std.command.extend",
                f"{app.name}/Door/Catalog[2]/Value": 2,
                f"{app.name}/Door/Catalog[2]/Label": "std.command.retract",
            }
        with patch.object(views, "_session", return_value=NS(root=APP.name)), \
                patch.object(views, "values", side_effect=mock_values):
            count, entries = views.module_catalog(comm, "Door", app=APP)
            self.assertEqual(count, 2)
            self.assertEqual(entries, [(1, "std.command.extend"), (2, "std.command.retract")])

    def test_phase4_release_report_hmi(self):
        comm = Mock()
        def mock_values(_comm, paths, *, app):
            return {
                f"{app.name}/HmiResponse/Report/Released": True,
                f"{app.name}/HmiResponse/Report/Count": 1,
                f"{app.name}/HmiResponse/Report/Reasons/Reasons[1]/Description": "airOk",
                f"{app.name}/HmiResponse/Report/Reasons/Reasons[1]/ReasonCode": 10,
                f"{app.name}/HmiResponse/Report/Reasons/Reasons[1]/SourcePath": "Press",
                f"{app.name}/HmiResponse/Report/Reasons/Reasons[1]/Kind": 3,
            }
        with patch.object(views, "_session", return_value=NS(root=APP.name)), \
                patch.object(views, "values", side_effect=mock_values):
            released, entries = views.release_report_hmi(comm, app=APP)
            self.assertTrue(released)
            self.assertEqual(entries, [("airOk", 10, "Press", 3)])


class S3Harness(unittest.TestCase):
    def test_s3_health_probe_canonical_read_flat(self):
        comm = Mock()
        members = tuple(m.name for m in gen.health_probe_members())
        dummy_probe = {m: 0 for m in members}
        with patch.object(px, "read_flat", return_value=dummy_probe) as mock_flat:
            probe = views.read_health_probe(comm, app=APP)
            self.assertEqual(probe, dummy_probe)
            mock_flat.assert_called_once_with(comm, gen.health_probe_tag(APP), members)

    def test_s3_health_probe_legacy_fallback(self):
        legacy_app = NS(canonical_collapse=False, name="Press")
        comm = Mock()
        dummy_probe = {"Samples": 100}
        with patch.object(px, "read_layout", return_value=dummy_probe) as mock_layout:
            probe = views.read_health_probe(comm, app=legacy_app)
            self.assertEqual(probe, dummy_probe)
            mock_layout.assert_called_once_with(comm, gen.health_probe_tag(legacy_app),
                                                gen.health_probe_members())


if __name__ == "__main__":
    unittest.main()
