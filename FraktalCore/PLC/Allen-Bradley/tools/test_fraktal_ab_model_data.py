"""Core §3.8a / §149 / §151 on Allen-Bradley: model data an operator can edit.

Until this, a model's values were literals in the changeover chain - changeable
only by editing the declaration and downloading, so the client correctly
offered no model picker. They now live in a per-model record array on the
controller: the chain names a model, the routine copies its stored values, and
an operator can edit any model's numbers without touching the running ones.
"""

import unittest
import dataclasses

import fraktal_ab_generate as gen
import fraktal_ab_mailbox as mailbox
import fraktal_ab_manifest as manifest
import fraktal_ab_press_demo as demo
import fraktal_ab_projection as projection
from test_fraktal_ab_data_access import effective_levels
from test_fraktal_ab_capture import initial
from fraktal_ab_st_model import Controller


APP = dataclasses.replace(demo.application(), model_capacity=0)
ROWS = manifest.content(APP)
REQ = f"{APP.name}/HmiRequest"


def _stored():
    return [dict(m.values) for m in APP.models]


def _running():
    return {r.name: {m.name: m.initial for m in r.members} for r in APP.records}


def _page(model, stored=None):
    return projection.config_page(APP, ROWS, _running(),
                                  stored if stored is not None else _stored(),
                                  model, effective_levels(APP))


def _values(page):
    out = {}
    for i in range(1, page["HmiResponse/ConfigPage/EntryCount"] + 1):
        key = page[f"HmiResponse/ConfigPage/Entries[{i}]/WriteKey"]
        out[key] = (page[f"HmiResponse/ConfigPage/Entries[{i}]/ValueText"],
                    page[f"HmiResponse/ConfigPage/Entries[{i}]/ModelScoped"])
    return out


class Storage(unittest.TestCase):
    def test_model_scoped_members_are_derived_from_the_models(self):
        """Named once, in Model.values, and derived here - never marked a
        second time on the member, where the two could disagree."""
        names = {m.name for m in gen.model_scoped_members(APP)}
        self.assertEqual(names, set(APP.models[0].values))

    def test_one_element_per_model(self):
        elements = gen.model_cfg_elements(APP)
        self.assertEqual(len(elements), len(APP.models))

    def test_each_element_starts_never_written(self):
        """Zero, so a download reads as a first boot for every model."""
        for element in gen.model_cfg_elements(APP):
            self.assertEqual(element[0].name, "SchemaVersion")
            self.assertEqual(element[0].initial, 0)

    def test_each_element_is_initialized_to_its_models_values(self):
        for model, element in zip(APP.models, gen.model_cfg_elements(APP)):
            held = {m.name: m.initial for m in element[1:]}
            self.assertEqual(held, model.values)

    def test_the_array_is_not_directly_writable(self):
        """Writing it directly would skip every bound the mailbox checks."""
        self.assertNotIn(gen.model_cfg_tag(APP), gen.externally_writable(APP))
        tag = gen._structure_array_tag(gen.model_cfg_tag(APP),
                                       gen.model_cfg_name(APP),
                                       gen.model_cfg_elements(APP))
        self.assertIn('ExternalAccess="Read Only"', tag)


class Restore(unittest.TestCase):
    def restore(self, version):
        banks = [initial(ms) for ms in gen.model_cfg_elements(APP)]
        for bank in banks:
            for name in bank:
                bank[name] += 1
            bank['SchemaVersion'] = version
        before = [dict(bank) for bank in banks]
        c = Controller({gen.model_cfg_tag(APP): banks,
                        'P': {'RestoreLost': 0, 'LostModuleId': 0}})
        c.run('\n'.join(gen._model_restore_logic(APP, 'P')))
        return banks, c.tags['P'], before

    def test_every_model_is_restored_on_first_scan(self):
        banks, persist, _ = self.restore(0)
        for bank, model in zip(banks, APP.models):
            self.assertEqual(bank['SchemaVersion'], gen.model_cfg_schema_version(APP))
            for name, value in model.values.items():
                self.assertEqual(bank[name], value, (model.code, name))
        self.assertEqual(persist['RestoreLost'], 0)

    def test_an_unrecognized_model_image_is_rejected_and_annunciated(self):
        """D1 of the 2026-09-29 audit. The first version handled zero only, so
        an element carrying an unrecognized version was kept and driven as-is -
        §3.8a: it "shall not be interpreted by field position" and a rejection
        "shall be annunciated"."""
        banks, persist, _ = self.restore(99)
        for bank, model in zip(banks, APP.models):
            self.assertEqual(bank['SchemaVersion'], gen.model_cfg_schema_version(APP))
            for name, value in model.values.items():
                self.assertEqual(bank[name], value, (model.code, name))
        self.assertEqual((persist['RestoreLost'], persist['LostModuleId']), (1, 1))

    def test_the_model_version_is_the_par_cfg_version(self):
        """One source: a model element means what its ParCfg values mean."""
        self.assertEqual(gen.model_cfg_schema_version(APP),
                         next(r for r in APP.records if r.par_cfg).schema_version)

    def test_a_commissioned_model_is_left_alone(self):
        """Every model retains its own commissioned values on a valid boot."""
        banks, persist, before = self.restore(gen.model_cfg_schema_version(APP))
        self.assertEqual(banks, before)
        self.assertEqual(persist['RestoreLost'], 0)


class Commit(unittest.TestCase):
    def test_the_commit_runs_after_the_unit_asks(self):
        routine = list(gen.routine_logic(APP))
        unit = next(i for i, line in enumerate(routine)
                    if line.startswith(gen.unit_aoi_name(APP)))
        commit = next(i for i, line in enumerate(routine)
                      if "CommitModel >= 1" in line)
        self.assertGreater(commit, unit, "same-scan commit needs the AOI first")


class WriteRouting(unittest.TestCase):
    def setUp(self):
        self.text = "\n".join(mailbox._dispatch(APP))

    def test_model_zero_writes_the_running_record(self):
        self.assertIn(f"{mailbox._request(APP, 'DurationMs')} = 0", self.text)

    def test_another_model_writes_its_own_element(self):
        array = gen.model_cfg_tag(APP)
        model = mailbox._request(APP, "DurationMs")
        for member in gen.model_scoped_members(APP):
            self.assertIn(f"{array}[{model} - 1].{member.name} :=", self.text)

    def test_an_undeclared_model_is_refused_not_faulted(self):
        self.assertIn(f"<= {len(APP.models)}) THEN", self.text)
        self.assertIn("model_not_declared", self.text)

    def test_idleness_applies_to_the_running_record_only(self):
        """Preparing the NEXT model while this one runs is the point of the
        feature; refusing it while running would make it useless exactly when
        it is wanted."""
        model = mailbox._request(APP, "DurationMs")
        flags = __import__('fraktal_ab_config').scratch_names(APP)[2]
        self.assertIn(f'OR ({model} = 0) THEN', self.text)
        self.assertIn(f'IF (({flags} MOD 4) < 2)', self.text)
        self.assertIn(f'IF FRK_{APP.name}_Unit.Running <> 0 THEN', self.text)

    def test_station_values_are_not_model_routed(self):
        """StationNumber belongs to the cabinet, not to a product."""
        import copy
        from test_fraktal_ab_capture import controller, execute
        c = controller()
        banks = copy.deepcopy(c.tags[gen.model_cfg_tag(APP)])
        answer = execute(c, Kind=mailbox.WRITE_CONFIG, DurationMs=2,
                         IntValue=mailbox.config_ordinal(APP, 'station.number'), BoolValue=42)
        self.assertEqual(answer['Accepted'], 1)
        station = next(r for r in APP.records if r.station_cfg)
        self.assertEqual(c.tags[station.name + 'Tag']['StationNumber'], 42)
        self.assertEqual(c.tags[gen.model_cfg_tag(APP)], banks)


class Page(unittest.TestCase):
    def test_model_zero_is_the_running_record(self):
        values = _values(_page(0))
        running = _running()[APP.records[0].name]
        self.assertEqual(values["press.dwellMs"][0], str(running["PressDwellMs"]))

    def test_another_model_serves_its_stored_values(self):
        stored = _stored()
        stored[1]["PressDwellMs"] = 777
        values = _values(_page(2, stored))
        self.assertEqual(values["press.dwellMs"][0], "777")

    def test_model_scoped_entries_say_so(self):
        """The client offers a model picker only when something is."""
        values = _values(_page(0))
        self.assertTrue(values["press.dwellMs"][1])
        self.assertFalse(values["station.number"][1])

    def test_station_values_do_not_change_with_the_model(self):
        self.assertEqual(_values(_page(0))["station.number"],
                         _values(_page(3))["station.number"])

    def test_the_path_set_is_identical_for_every_model(self):
        """So answering a different model never moves discoveryRevision."""
        keys = [set(_page(m)) for m in range(len(APP.models) + 1)]
        self.assertTrue(all(k == keys[0] for k in keys))

    def test_an_unreadable_array_offers_no_other_model(self):
        """A commissioned M-200 read back as the shipped M-200 is the
        confidently-wrong case, so an unread array drops the entries."""
        values = _values(_page(2, stored=[]))
        self.assertNotIn("press.dwellMs", values)
        self.assertIn("station.number", values)


class ConnectionModel(unittest.TestCase):
    def _batch(self, kind, model=None):
        writes = [(f"{REQ}/Kind", "int32", kind)]
        if model is not None:
            writes.append((f"{REQ}/DurationMs", "int32", model))
        writes.append((f"{REQ}/Sequence", "int32", 9))
        return writes

    def test_a_query_sets_the_model(self):
        self.assertEqual(mailbox.requested_config_model(
            self._batch(mailbox.QUERY_CONFIG, 2), 0), 2)

    def test_the_ordinary_manifest_fetch_returns_to_the_running_record(self):
        self.assertEqual(mailbox.requested_config_model(
            self._batch(mailbox.QUERY_CONFIG), 3), 0)

    def test_any_other_command_leaves_the_model_alone(self):
        """The bug caught before it shipped: a START must not silently drop
        the operator's editor back onto the running record."""
        self.assertEqual(mailbox.requested_config_model(
            self._batch(mailbox.START), 2), 2)

    def test_the_gateway_passes_the_current_model_through(self):
        import asyncio
        import fraktal_ab_gateway as gateway
        station = gateway.Station(lambda: {'values': {f'{REQ}/Sequence': 8}})
        g = gateway.Gateway(station, write_fn=lambda _writes, _mailbox: True)
        state = gateway._ConnState()
        batch = self._batch(mailbox.QUERY_CONFIG, 2)
        batch.insert(-1, (f'{REQ}/IntValue', 'int32', 0))
        batch[-1] = (f'{REQ}/Sequence', 'uint32', 9)
        params = {'writes': [{'path': p, 'valueType': t, 'value': v} for p, t, v in batch]}
        self.assertTrue(asyncio.run(g._write_batch(state, params)))
        self.assertEqual(state.config_model, 2)

    def test_the_private_page_map_never_reaches_a_client(self):
        import pathlib
        source = pathlib.Path(__import__("fraktal_ab_gateway").__file__
                              ).read_text(encoding="utf-8")
        self.assertIn('result.pop("configPages", None)', source)


if __name__ == "__main__":
    unittest.main()
