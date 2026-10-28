"""Core 3.10.2 on Allen-Bradley: the configuration page a client reads.

The page is assembled from the controller's OWN WriteCapabilities and
Localization tables plus the live record values - never from the local
declaration. A numeric key means something only within the revision that
published it, so resolving one from anywhere else reads this controller's
answer through another build's catalogue. That is the property most of these
tests are about.
"""

import unittest

import fraktal_ab_generate as gen
import fraktal_ab_mailbox as mailbox
import fraktal_ab_manifest as manifest
import fraktal_ab_press_demo as demo
import fraktal_ab_projection as projection
from test_fraktal_ab_data_access import effective_levels


APP = demo.application()
ROWS = manifest.content(APP)
BASE = "HmiResponse/ConfigPage"


def _values(**overrides):
    held = {r.name: {m.name: m.initial for m in r.members} for r in APP.records}
    for record, members in overrides.items():
        held.setdefault(record, {}).update(members)
    return held


def _page(rows=None, values=None):
    return projection.config_page(APP, rows or ROWS,
                                  values if values is not None else _values(), data_levels=effective_levels(APP))


def _entries(page):
    out = []
    for index in range(1, page[f"{BASE}/EntryCount"] + 1):
        prefix = f"{BASE}/Entries[{index}]"
        out.append({k[len(prefix) + 1:]: v
                    for k, v in page.items() if k.startswith(prefix + "/")})
    return out


class PageShape(unittest.TestCase):
    def test_every_editable_value_appears_once(self):
        page = _page()
        self.assertEqual(page[f"{BASE}/EntryCount"],
                         len(gen.editable_values(APP)))
        keys = [e["WriteKey"] for e in _entries(page)]
        self.assertEqual(sorted(keys), sorted(set(keys)))

    def test_it_answers_one_page(self):
        """The contract carries a PageCount so a client loops; this station
        fits in one, and a station that outgrows it pages here with no client
        change."""
        self.assertEqual(_page()[f"{BASE}/PageCount"], 1)

    def test_a_station_with_nothing_editable_publishes_no_page(self):
        rows = dict(ROWS, WriteCapabilities=[])
        self.assertEqual(_page(rows=rows), {})

    def test_every_member_the_client_reads_is_published(self):
        """Read off the client's own parser: a member it reads and the page
        omits silently becomes a default, and a default here is a claim."""
        expected = {
            "Scope", "Item", "ValueText", "WriteKey", "WriteRevision",
            "ConfigKind", "ValueType", "Writable", "RequiresReady",
            "HasMinimum", "HasMaximum", "Minimum", "Maximum", "Unit",
            "LabelKey", "EnumDomain", "UnitCode", "EnumLabelKey", "ClassId",
            "ReadLevel", "WriteLevel", "Readable", "ModelScoped", "CanCapture", "CaptureSource",
        }
        for entry in _entries(_page()):
            self.assertEqual(set(entry), expected)


class ResolvedFromTheController(unittest.TestCase):
    def test_labels_come_from_the_snapshot_catalogue(self):
        """Not from the local declaration. A controller whose catalogue
        numbers things differently must be read through ITS numbering."""
        rows = dict(ROWS, Localization=[
            dict(row, PortableKey="shifted." + row["PortableKey"])
            for row in ROWS["Localization"]])
        for entry in _entries(_page(rows=rows)):
            self.assertTrue(entry["LabelKey"].startswith("shifted."),
                            entry["LabelKey"])

    def test_an_unresolvable_path_key_drops_the_entry(self):
        """The page still exists - the station HAS capabilities - but names
        nothing, which is the same shape as a value that did not read. The
        alternative, guessing a path from the local declaration, is exactly
        the cross-build read this whole assembly avoids."""
        rows = dict(ROWS, Localization=[])
        page = _page(rows=rows)
        self.assertEqual(page[f"{BASE}/EntryCount"], 0)
        self.assertEqual(_entries(page), [])

    def test_bounds_come_from_the_capability_row(self):
        rows = dict(ROWS, WriteCapabilities=[
            dict(row, Minimum=-5, Maximum=5) for row in ROWS["WriteCapabilities"]])
        for entry in _entries(_page(rows=rows)):
            self.assertEqual((entry["Minimum"], entry["Maximum"]), (-5, 5))


class Values(unittest.TestCase):
    def test_the_live_value_travels_as_text(self):
        page = _page(values=_values(FRK_T_PressStationCfg={"StationNumber": 42}))
        entry = next(e for e in _entries(page)
                     if e["WriteKey"] == "station.number")
        self.assertEqual(entry["ValueText"], "42")

    def test_a_value_that_did_not_read_is_left_out_entirely(self):
        """A dwell time an operator believes is 0 ms is worse than a field
        that is missing."""
        values = _values()
        values.pop("FRK_T_PressStationCfg")
        keys = [e["WriteKey"] for e in _entries(_page(values=values))]
        self.assertNotIn("station.number", keys)
        self.assertIn("press.dwellMs", keys)

    def test_no_record_read_at_all_publishes_no_entries(self):
        self.assertEqual(_page(values={})[f"{BASE}/EntryCount"], 0)


class ClientContract(unittest.TestCase):
    def test_the_write_revision_is_non_zero(self):
        """`hasWriteCapability` requires it, so a zero here would render every
        field read-only while claiming to be writable."""
        for entry in _entries(_page()):
            self.assertGreater(entry["WriteRevision"], 0)

    def test_the_write_revision_is_the_published_one(self):
        revision = manifest.config_revision(APP)
        for entry in _entries(_page()):
            self.assertEqual(entry["WriteRevision"], revision)

    def test_the_write_key_is_the_one_the_controller_dispatches_on(self):
        for entry in _entries(_page()):
            self.assertIsNotNone(
                mailbox.config_ordinal(APP, entry["WriteKey"]),
                entry["WriteKey"])

    def test_access_levels_are_published_by_the_enabled_controller(self):
        for entry in _entries(_page()):
            self.assertEqual(entry["ReadLevel"], 0)
            self.assertIn(entry["WriteLevel"], (0, 3))

    def test_a_duration_is_typed_as_one(self):
        entry = next(e for e in _entries(_page())
                     if e["WriteKey"] == "press.dwellMs")
        self.assertEqual(entry["ValueType"], projection.CFG_TYPE_DURATION)

    def test_deployment_and_recipe_values_are_distinguished(self):
        by_key = {e["WriteKey"]: e["ConfigKind"] for e in _entries(_page())}
        self.assertEqual(by_key["press.dwellMs"], manifest.CFG_KIND_PAR)
        self.assertEqual(by_key["station.number"], manifest.CFG_KIND_STATION)


class ControllerAccepts(unittest.TestCase):
    def test_query_config_is_no_longer_refused(self):
        self.assertNotIn(mailbox.QUERY_CONFIG, mailbox.refused_for(APP))

    def test_it_has_a_branch_that_accepts(self):
        text = "\n".join(mailbox._dispatch(APP))
        self.assertIn(f"{mailbox.QUERY_CONFIG}: (* QUERY_CONFIG *)", text)

    def test_a_station_with_nothing_editable_still_refuses_by_name(self):
        import dataclasses
        bare = dataclasses.replace(APP, records=tuple(
            dataclasses.replace(r, members=tuple(
                dataclasses.replace(m, write_key="") for m in r.members))
            for r in APP.records))
        self.assertEqual(mailbox.refused_for(bare)[mailbox.QUERY_CONFIG],
                         "project.mailbox.refused.no_config_manifest")


class ConfigRevision(unittest.TestCase):
    """HMI_CONTRACT: the client caches the manifest and re-fetches on
    Status/ConfigRev. Publishing none means an EMPTY signature, and the client
    reads that as "a PLC without the manifest protocol" and never asks - which
    is how the whole editable surface first shipped served-but-invisible.
    """

    def test_a_revision_is_published(self):
        self.assertIn("Status/ConfigRev", _page())

    def test_it_is_stable_for_an_unchanged_station(self):
        self.assertEqual(_page()["Status/ConfigRev"],
                         _page()["Status/ConfigRev"])

    def test_it_moves_when_a_value_changes(self):
        """The entry carries the live value, so a revision that only moved on
        a new download would leave an accepted edit showing its old number."""
        before = _page()["Status/ConfigRev"]
        after = _page(values=_values(
            FRK_T_PressParCfg={"PressDwellMs": 600}))["Status/ConfigRev"]
        self.assertNotEqual(before, after)

    def test_it_moves_when_the_build_changes(self):
        import unittest.mock as mock
        with mock.patch.object(manifest, "config_revision", return_value=999):
            other = _page()["Status/ConfigRev"]
        self.assertNotEqual(_page()["Status/ConfigRev"], other)

    def test_it_is_a_positive_dint(self):
        self.assertTrue(0 < _page()["Status/ConfigRev"] < 2 ** 31)

    def test_a_station_with_nothing_editable_publishes_none(self):
        """No capabilities, no page, no revision - the client correctly reads
        that as a station with no manifest protocol rather than an empty one."""
        self.assertEqual(_page(rows=dict(ROWS, WriteCapabilities=[])), {})


class ControllerAccessLevel(unittest.TestCase):
    def state(self):
        import fraktal_ab_access as access
        import fraktal_ab_st_model as st
        return st.structure(access.state_members(APP))

    def test_missing_controller_access_fails_closed(self):
        self.assertEqual(projection.access_status(APP, projection.ACCESS_ADMIN), {})

    def test_deployment_cannot_grant_a_prelogin_level(self):
        self.assertEqual(projection.access_status(APP, projection.ACCESS_ENGINEER, self.state())['Access/CurrentLevel'], 0)

    def test_the_ladder_matches_the_client(self):
        self.assertEqual(projection.ACCESS_LEVELS, {'none': 0, 'operator': 1, 'technician': 2, 'engineer': 3, 'admin': 4})

    def test_the_plc_user_level_reaches_the_snapshot(self):
        import test_fraktal_ab_projection as fixture
        s = self.state()
        s.update(CurrentLevel=3, UserLength=8, UserBytes=list(b'engineer') + [0] * 24)
        doc = fixture.build(access_level=projection.ACCESS_NONE, access_state=s)
        self.assertEqual(doc['values']['Press/Access/CurrentLevel'], 3)
        self.assertEqual(doc['values']['Press/Access/CurrentUser'], 'engineer')

    def test_policy_defaults_match_tc3(self):
        values = projection.access_status(APP, 4, self.state())
        self.assertEqual({v for k, v in values.items() if 'Required' in k}, {projection.ACCESS_NONE})

    def test_legacy_declarations_keep_the_deployment_level(self):
        import dataclasses
        legacy = dataclasses.replace(APP, access_users=None)
        self.assertEqual(projection.access_status(legacy, 3)['Access/CurrentLevel'], 3)


if __name__ == '__main__':
    unittest.main()
