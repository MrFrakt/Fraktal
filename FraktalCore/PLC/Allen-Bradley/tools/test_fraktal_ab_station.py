"""A new station is selected in one place, and the template has everything on.

Two promises the AB new-project guide makes, held here:

* **The tools are not the press's.** One variable, FRAKTAL_AB_DECLARATION,
  selects the declaration the generator, the projection, the manifest reader
  and the gateway serve; unset, it is the press, which is what the bench
  evidence is written against. Each test that selects another station runs in
  a fresh interpreter, because every one of those tools binds its station at
  import - exactly as a gateway does at start.
* **The template is a working station with every Phase 0-5 feature on**, not
  documentation that drifts: it validates, emits, fits the manifest budget and
  projects as the HMI reads it.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock

import fraktal_ab_declaration as decl
import fraktal_ab_generate as gen
import fraktal_ab_library as library
import fraktal_ab_manifest as manifest
import fraktal_ab_press_demo as press
import fraktal_ab_station as station
import fraktal_ab_station_template as template
from test_fraktal_ab_generate import emit

HERE = Path(__file__).resolve().parent
TEMPLATE = "fraktal_ab_station_template"


def selected(code: str, declaration: str | None) -> str:
    """Run `code` in a fresh interpreter with the station selected; its stdout."""
    env = {k: v for k, v in os.environ.items() if k != station.ENV}
    if declaration is not None:
        env[station.ENV] = declaration
    done = subprocess.run([sys.executable, "-B", "-c", code], cwd=HERE, env=env,
                          capture_output=True, text=True, timeout=120)
    if done.returncode:
        raise AssertionError(done.stderr)
    return done.stdout.strip()


class SelectorTests(unittest.TestCase):

    def test_unset_is_the_press(self):
        with mock.patch.dict(os.environ, {station.ENV: ""}):
            self.assertEqual(station.module_name(), "fraktal_ab_press_demo")
            self.assertEqual(station.application(), press.application())

    def test_the_variable_selects_the_declaration(self):
        with mock.patch.dict(os.environ, {station.ENV: TEMPLATE}):
            self.assertEqual(station.application(), template.application())

    def test_every_reader_serves_the_selected_station(self):
        code = ("import json, fraktal_ab_projection as p, fraktal_ab_manifest_read as r,"
                " fraktal_ab_press_execute as x;"
                "print(json.dumps([p.APP.name, r.APP.name, x.APP.name, x.UNIT]))")
        self.assertEqual(json.loads(selected(code, TEMPLATE)),
                         ["Cell", "Cell", "Cell", "FRK_Cell_Unit"])
        self.assertEqual(json.loads(selected(code, None)),
                         ["Press", "Press", "Press", "FRK_Press_Unit"])

    def test_the_gateway_checks_the_selected_stations_hash(self):
        """The gateway's on-disk hash is what tells a stale controller from a
        stale gateway; computed for the press while serving the cell, it would
        refuse every healthy cell as a build mismatch."""
        import fraktal_ab_gateway as gateway

        with mock.patch.dict(os.environ, {station.ENV: TEMPLATE}):
            self.assertEqual(gateway.declared_on_disk(),
                             manifest.content_hash(template.application()))

    def test_the_generator_takes_a_declaration(self):
        import tempfile
        from test_fraktal_ab_generate import SEED

        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "seed.L5X"
            source.write_text(SEED, encoding="utf-8")
            output = Path(directory) / "cell.L5X"
            env = {k: v for k, v in os.environ.items() if k != station.ENV}
            done = subprocess.run(
                [sys.executable, "-B", "fraktal_ab_generate.py", str(source),
                 str(output), "--declaration", TEMPLATE],
                cwd=HERE, env=env, capture_output=True, text=True, timeout=300)
            self.assertEqual(done.returncode, 0, done.stderr)
            self.assertEqual(json.loads(done.stdout)["Application"], "Cell")


class TemplateTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = template.application()
        cls.root, cls.text, cls.evidence = emit(cls.app)

    def test_it_is_a_valid_declaration(self):
        self.assertEqual(decl.validate(self.app), [])
        self.assertEqual(library.validate(self.app), [])

    def test_every_opt_in_feature_is_on(self):
        """What a station has to ask for, the template asks for, so a project
        copied from it starts with all of it and removes what it does not want."""
        app = self.app
        self.assertEqual(app.run_styles, decl.RUN_STYLES)
        self.assertTrue(app.ideal_cycle_member)
        self.assertTrue(app.baseline_work_member)
        self.assertTrue(app.state_flags)
        self.assertEqual(app.system_health, decl.SystemHealth.for_task(app.task_period_ms))
        self.assertTrue(app.start_permits)
        self.assertTrue(any(m.permits for m in app.modules))
        self.assertIsNotNone(app.manual_mode)
        self.assertTrue(app.models and app.default_model)
        self.assertTrue(any(r.par_cfg for r in app.records))
        self.assertTrue(any(r.station_cfg for r in app.records))

    def test_it_emits_every_facet(self):
        published = set(self.evidence["PublishableTags"])
        for facet in ("Oee", "Profiler", "StateFlags", "SystemHealth", "HealthProbe",
                      "AlarmActive", "AlarmRing", "ConfigPersist", "ModelCfg"):
            self.assertIn(f"FRK_Cell_{facet}", published)

    def test_it_fits_the_manifest_budget(self):
        m = self.evidence["Manifest"]
        self.assertFalse(m["Truncated"])
        self.assertLessEqual(m["EstimatedBytes"], manifest.MANIFEST_BUDGET_BYTES)
        for name, table in m["Tables"].items():
            self.assertLessEqual(table["rows"], table["capacity"], name)

    def test_it_projects_as_the_hmi_reads_it(self):
        code = (
            "import json, test_fraktal_ab_projection as t\n"
            "doc = t.build(oee_state=t.oee_values(), profiler_state=t.profiler_values(),"
            " flags_state=t.flag_values(), health_state=t.health_values(),"
            " alarm_state=t.alarm_values(), persist=t.persist_values(),"
            " record_values=t.record_values())\n"
            "v = doc['values']\n"
            "print(json.dumps({'names': sorted(x for x in v if x.endswith('/Status/Name')),"
            " 'flag': v.get('Cell/StateFlags[1]/Key'),"
            " 'health': v.get('Cell/SystemHealth/Present'),"
            " 'oee': 'Cell/Oee/Performance' in v}))\n")
        doc = json.loads(selected(code, TEMPLATE))
        self.assertEqual(doc["names"], ["Cell/Clamp/Status/Name",
                                        "Cell/PartSensor/Status/Name",
                                        "Cell/Status/Name"])
        self.assertEqual(doc["flag"], "project.state.cellAtLoadPosition")
        self.assertTrue(doc["health"])
        self.assertTrue(doc["oee"])


class DefaultHelperTests(unittest.TestCase):
    """The helpers are TC3's values, so a station using them says what TC3 says."""

    def test_system_health_for_a_task(self):
        h = decl.SystemHealth.for_task(10)
        self.assertEqual((h.max_task_cycle_us, h.max_task_jitter_us), (20000, 2000))
        self.assertFalse(h.require_time_sync or h.require_fieldbus or h.require_dc_sync)
        self.assertTrue(decl.SystemHealth.for_task(10, require_time_sync=True)
                        .require_time_sync)

    def test_the_press_uses_them(self):
        app = press.application()
        self.assertEqual(app.system_health, decl.SystemHealth.for_task(10))
        members = {m.name: m for r in app.records if r.par_cfg for m in r.members}
        self.assertEqual(members["IdealCycleMs"],
                         decl.ideal_cycle_ms(950, "press.recipe.idealCycleMs"))
        self.assertEqual(members["BaselineWorkMs"],
                     decl.capture(decl.baseline_work_ms(950, "press.recipe.baselineWorkMs"),
                                  "Profiler.LastWork"))

    def test_a_delay_without_conditions_needs_no_wait_condition_reason(self):
        """reasons.validate requires WAIT_CONDITION only of a DELAY that a
        condition can pause; the emitter used to look it up for every DELAY,
        so a station without it validated and then could not be generated."""
        import dataclasses

        self.assertNotIn("WAIT_CONDITION", template.REASONS)
        app = template.application()
        three = dataclasses.replace(app, chains=tuple(
            dataclasses.replace(c, renditions=(decl.ST, decl.SFC, decl.LD))
            if c.loops else c for c in app.chains))
        for station_app in (app, three):       # the ST emitter, and the chart's
            self.assertTrue(gen.all_generated_logic(station_app))
            emit(station_app)


if __name__ == "__main__":
    unittest.main()
