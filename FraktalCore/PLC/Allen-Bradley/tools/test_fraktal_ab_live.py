"""Core 3.8b: the declared medium and the live documents, executed offline.

The controller half runs the emitted ST through the executable model; the host
half runs the medium, the keeper and the restore plan against a temporary
folder and against that same executed controller. Nothing here claims physical
retention: power-cycle and download acceptance are owner steps on the bench.
"""
import copy
import dataclasses
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import fraktal_ab_access as access
import fraktal_ab_config as config
import fraktal_ab_declaration as decl
import fraktal_ab_gateway as gw
import fraktal_ab_generate as gen
import fraktal_ab_live as live
import fraktal_ab_mailbox as mb
import fraktal_ab_manifest as mf
import fraktal_ab_medium as medium
import fraktal_ab_models as models
import fraktal_ab_set_broker as broker
import fraktal_ab_sets as sets
import fraktal_ab_station_template as template
from test_fraktal_ab_capture import execute
from test_fraktal_ab_sets import APP, NativeComm, controller, document, run

LIVE = dataclasses.replace(APP, config_medium=decl.ConfigMedium(live_documents=True))
# The same station before it chose a medium: the file medium, no live documents.
BASE = dataclasses.replace(APP, config_medium=None)
STATION = gen.station_cfg_record(APP)
STATION_TAG = STATION.name + 'Tag'
VERSION = STATION.schema_version


def live_controller(*, restoring):
    c = controller(LIVE)
    c.tags[STATION_TAG]['SchemaVersion'] = 0 if restoring else VERSION
    return c


def scoped():
    return [(o, m) for o, r, m in gen.editable_values(APP) if gen.is_model_scoped(APP, r, m.name)]


class MediumChoice(unittest.TestCase):
    """1b: the declaration picks the medium; the directory is deployment data."""

    def test_a_set_store_without_a_declared_medium_is_the_file_medium(self):
        self.assertEqual(decl.config_medium(BASE), decl.ConfigMedium())
        self.assertIsNone(decl.config_medium(dataclasses.replace(BASE, config_sets=False)))
        self.assertFalse(decl.live_documents(BASE))
        self.assertTrue(decl.live_documents(LIVE))

    def test_the_file_store_opens_where_the_gateway_always_kept_it(self):
        base = {'LOCALAPPDATA': 'C:/data'}
        store = medium.open_set_store(APP, '7036B510', base)
        self.assertIsInstance(store, sets.FileStore)
        self.assertEqual(store.directory, Path('C:/data/Fraktal/ConfigSets/7036B510-Press'))
        chosen = medium.open_set_store(APP, '7036B510', {medium.SET_DIR_ENV: 'D:/sets', **base})
        self.assertEqual(chosen.directory, Path('D:/sets'))
        self.assertEqual(live.live_directory(APP, '7036B510', base),
                         Path('C:/data/Fraktal/ConfigSets/7036B510-Press/live'))
        self.assertIsNone(medium.open_set_store(dataclasses.replace(BASE, config_sets=False), '7036B510', base))

    def test_unimplemented_or_inconsistent_media_are_refused(self):
        external = dataclasses.replace(APP, config_medium=decl.ConfigMedium(store=decl.CONFIG_STORE_EXTERNAL))
        self.assertTrue(any('database medium' in f for f in decl.validate(external)))
        with self.assertRaises(ValueError):
            medium.open_set_store(external, '7036B510', {})
        no_sets = dataclasses.replace(BASE, config_sets=False, config_medium=decl.ConfigMedium())
        self.assertTrue(any('declare config_sets' in f for f in decl.validate(no_sets)))
        anonymous = dataclasses.replace(LIVE, access_users=None)
        self.assertTrue(any('controller session' in f for f in decl.validate(anonymous)))
        self.assertEqual([f for f in decl.validate(LIVE) if 'medium' in f or 'live' in f], [])

    def test_store_kind_ordinals_are_core_e_config_store(self):
        text = Path(__file__).resolve().parents[2].joinpath(
            'TwinCAT/Framework/Fraktal_Core/DUTs/E_ConfigStore.TcDUT').read_text(encoding='utf-8')
        for ordinal, name in decl.CONFIG_STORE_NAMES.items():
            self.assertIn(f'{name}', text)
            self.assertRegex(text, rf'{name}\s*:=\s*{ordinal}\b')
        self.assertIn(f'.StoreKind := 1; (* FILE_JSON *)', '\n'.join(sets.dispatch_logic(BASE)))

    def test_an_explicit_file_medium_emits_what_the_default_emits(self):
        explicit = dataclasses.replace(BASE, config_medium=decl.ConfigMedium())
        for emit in (sets.dispatch_logic, config.write_logic, gen.start_release_logic,
                     gen.config_restore_logic, gen.release_keys):
            self.assertEqual(emit(explicit), emit(BASE), emit.__name__)
        self.assertEqual(mf.content(explicit), mf.content(BASE))


class ControllerRestore(unittest.TestCase):
    """The emitted controller half with live documents declared."""

    def first_scan(self, version):
        c = controller(LIVE)
        c.tags['S:FS'] = True
        for member in STATION.members:
            c.tags[STATION_TAG][member.name] = member.initial + 1
        c.tags[STATION_TAG]['SchemaVersion'] = version
        c.tags[gen.config_persist_tag(LIVE)].update(RestoreLost=0, LostModuleId=0)
        c.run('\n'.join(gen.config_restore_logic(LIVE)))
        return c.tags[STATION_TAG], c.tags[gen.config_persist_tag(LIVE)]

    def test_a_fresh_image_installs_defaults_and_stays_unstamped(self):
        image, persist = self.first_scan(0)
        self.assertEqual(image['SchemaVersion'], 0)
        for member in STATION.members[1:]:
            self.assertEqual(image[member.name], member.initial)
        self.assertEqual(persist['RestoreLost'], 0)

    def test_an_intact_image_is_kept_and_a_rejected_one_awaits_the_documents(self):
        image, persist = self.first_scan(VERSION)
        self.assertEqual(image['SchemaVersion'], VERSION)
        self.assertEqual(image[STATION.members[1].name], STATION.members[1].initial + 1)
        image, persist = self.first_scan(VERSION + 7)
        self.assertEqual((image['SchemaVersion'], persist['RestoreLost']), (0, 1))

    def test_without_live_documents_the_gate_still_stamps(self):
        c = controller(BASE)
        c.tags['S:FS'] = True
        c.tags[STATION_TAG]['SchemaVersion'] = 0
        c.run('\n'.join(gen.config_restore_logic(BASE)))
        self.assertEqual(c.tags[STATION_TAG]['SchemaVersion'], VERSION)

    def test_start_names_the_restore_until_the_image_is_stamped(self):
        key = mf.numeric_key(LIVE, gen.CONFIG_RESTORING_KEY)
        from test_fraktal_ab_capture import initial
        for restoring in (True, False):
            c = live_controller(restoring=restoring)
            c.tags[f'FRK_{LIVE.name}_Unit']['Mode'] = 1
            c.tags[gen.start_release_tag(LIVE)] = initial(gen.release_report_members())
            c.run('\n'.join(gen.start_release_logic(LIVE)))
            report = c.tags[gen.start_release_tag(LIVE)]
            held = report['Key'][:report['Count']]
            self.assertEqual(key in held, restoring, held)
        self.assertNotIn(gen.CONFIG_RESTORING_KEY, gen.release_keys(BASE))

    def test_configuration_writes_and_captures_wait_for_the_restore(self):
        ordinal, member = next((o, m) for o, r, m in gen.editable_values(LIVE) if r.station_cfg)
        for restoring in (True, False):
            c = live_controller(restoring=restoring)
            answer = execute(c, LIVE, Kind=mb.WRITE_CONFIG, DurationMs=0, IntValue=ordinal,
                             BoolValue=member.minimum)
            if restoring:
                self.assertEqual((answer['Accepted'], answer['DiagnosticKey']),
                                 (0, mf.numeric_key(LIVE, gen.CONFIG_RESTORING_KEY)))
                self.assertEqual(c.tags[STATION_TAG][member.name], member.initial)
            else:
                self.assertEqual(answer['Accepted'], 1)

    def test_a_set_saved_before_the_restore_answered_is_refused(self):
        self.assertEqual(run(live_controller(restoring=True), LIVE, kind=mb.SAVE_CONFIG_SET)['Accepted'], 0)
        self.assertEqual(run(live_controller(restoring=False), LIVE, kind=mb.SAVE_CONFIG_SET)['Accepted'], 1)

    def model_load(self, c, ordinal, values, **proposal):
        doc = document(LIVE, name=live.LIVE_NAME, kind=0)
        for record, (_o, m) in zip(doc[1:], scoped()):
            record['value'] = str(values[m.name])
        c.tags[mb.request_tag_name(LIVE)]['DurationMs'] = ordinal
        return run(c, LIVE, doc=doc, **proposal)

    def test_model_documents_load_into_their_bank_only_while_restoring(self):
        values = {m.name: max(m.minimum, 1) + 3 for _o, m in scoped()}
        c = live_controller(restoring=False)
        before = copy.deepcopy(c.tags[gen.model_cfg_tag(LIVE)])
        self.assertEqual(self.model_load(c, 2, values)['DiagnosticKey'], mf.numeric_key(LIVE, sets.MODEL_KEY))
        self.assertEqual(c.tags[gen.model_cfg_tag(LIVE)], before)
        c = live_controller(restoring=True)
        parcfg = copy.deepcopy(c.tags[APP.records[0].name + 'Tag'])
        c.tags[f'FRK_{LIVE.name}_Unit'].update(ModelOrdinal=1, CommitModel=0)
        self.assertEqual(self.model_load(c, 2, values)['Accepted'], 1)
        for name, value in values.items():
            self.assertEqual(c.tags[gen.model_cfg_tag(LIVE)][1][name], value)
            self.assertEqual(c.tags[gen.model_cfg_tag(LIVE)][0][name], before[0][name])
        self.assertEqual(c.tags[APP.records[0].name + 'Tag'], parcfg)  # never live ParCfg
        self.assertEqual(c.tags[f'FRK_{LIVE.name}_Unit']['CommitModel'], 0)
        self.assertEqual(self.model_load(c, 1, values)['Accepted'], 1)
        self.assertEqual(c.tags[f'FRK_{LIVE.name}_Unit']['CommitModel'], 1)  # the changeover's own copy
        self.assertEqual(c.tags[STATION_TAG]['SchemaVersion'], 0)  # a model never ends the restore

    def test_a_model_document_needs_a_bank_the_catalog_offers(self):
        values = {m.name: m.maximum for _o, m in scoped()}
        for ordinal in (0, -1, len(LIVE.models) + 1, LIVE.model_capacity + 1):
            c = live_controller(restoring=True)
            before = copy.deepcopy(c.tags[gen.model_cfg_tag(LIVE)])
            self.assertEqual(self.model_load(c, ordinal, values)['Accepted'], 0, ordinal)
            self.assertEqual(c.tags[gen.model_cfg_tag(LIVE)], before)
        c = live_controller(restoring=True)
        bad = {m.name: m.maximum + 1 for _o, m in scoped()}
        self.assertEqual(self.model_load(c, 1, bad)['Accepted'], 0)

    def station_load(self, c, *, model=0, result=1, value='41'):
        doc = document(LIVE, name=live.LIVE_NAME)
        doc[1]['value'] = value
        c.tags[mb.request_tag_name(LIVE)]['DurationMs'] = model
        return run(c, LIVE, doc=doc, StoreResult=result)

    def test_the_station_document_answers_the_restore(self):
        c = live_controller(restoring=True)
        unit = c.tags[f'FRK_{LIVE.name}_Unit']
        unit.update(ModelOrdinal=1, CommitModel=0)
        self.assertEqual(self.station_load(c, model=3)['Accepted'], 1)
        self.assertEqual(c.tags[STATION_TAG]['SchemaVersion'], VERSION)
        self.assertEqual(c.tags[STATION_TAG]['StationNumber'], 41)
        self.assertEqual((unit['ModelOrdinal'], unit['CommitModel']), (3, 3))
        self.assertEqual(c.tags[gen.config_persist_tag(LIVE)]['RestoreLost'], 0)

    def test_an_announced_loss_is_raised_with_the_answer(self):
        c = live_controller(restoring=True)
        self.assertEqual(self.station_load(c, result=live.STORE_LOST)['Accepted'], 1)
        persist = c.tags[gen.config_persist_tag(LIVE)]
        self.assertEqual((persist['RestoreLost'], persist['LostModuleId']), (1, 1))
        self.assertEqual(c.tags[f'FRK_{LIVE.name}_Unit']['CommitModel'], 0)  # model 0: keep the image's

    def test_an_invalid_active_model_refuses_the_whole_answer(self):
        c = live_controller(restoring=True)
        before = copy.deepcopy(c.tags[STATION_TAG])
        self.assertEqual(self.station_load(c, model=len(LIVE.models) + 1)['Accepted'], 0)
        self.assertEqual(c.tags[STATION_TAG], before)

    def test_outside_a_restore_a_station_load_changes_nothing_else(self):
        c = live_controller(restoring=False)
        unit = c.tags[f'FRK_{LIVE.name}_Unit']
        before = (unit['ModelOrdinal'], unit['CommitModel'])
        self.assertEqual(self.station_load(c, model=99, result=live.STORE_LOST)['Accepted'], 1)
        self.assertEqual((unit['ModelOrdinal'], unit['CommitModel']), before)
        self.assertEqual(c.tags[STATION_TAG]['SchemaVersion'], VERSION)
        self.assertEqual(c.tags[gen.config_persist_tag(LIVE)]['RestoreLost'], 0)

    def test_a_set_saved_before_live_documents_still_loads(self):
        """The restore text moves the published revision; the values did not."""
        earlier = mf.config_revision(BASE)
        self.assertNotEqual(earlier, mf.config_revision(LIVE))
        for revision, accepted in ((earlier, 1), (mf.config_revision(LIVE), 1), (123456, 0)):
            c, doc = live_controller(restoring=False), document(LIVE)
            doc[0]['configRev'] = revision
            for record in doc[1:]:
                record['rev'] = revision
            self.assertEqual(run(c, LIVE, doc=doc)['Accepted'], accepted, revision)

    def test_the_template_restores_through_the_same_transaction(self):
        app = dataclasses.replace(template.application(), config_medium=decl.ConfigMedium(live_documents=True))
        self.assertEqual(decl.validate(app), [])
        c = controller(app)
        c.tags[gen.station_cfg_record(app).name + 'Tag']['SchemaVersion'] = 0
        c.tags[mb.request_tag_name(app)]['DurationMs'] = 0  # keep the image's model
        self.assertEqual(run(c, app, document(app, name=live.LIVE_NAME), StoreResult=1)['Accepted'], 1)
        self.assertEqual(c.tags[gen.station_cfg_record(app).name + 'Tag']['SchemaVersion'],
                         gen.station_cfg_record(app).schema_version)


def held(app=LIVE, *, restoring=False, level=4, codes=None, ordinal=1, banks=None):
    records = {r.name: {m.name: m.initial for m in r.members} for r in app.records}
    records[STATION.name]['SchemaVersion'] = 0 if restoring else VERSION
    codes = codes if codes is not None else [m.code for m in app.models]
    if banks is None:
        # A model created at run time starts from the first declared model.
        source = [app.models[min(i, len(app.models) - 1)] for i in range(len(codes))]
        banks = [{m.name: model.values.get(m.name, m.initial) for m in gen.model_cfg_members(app)}
                 for model in source]
    return live.Capture(restoring=restoring, records=records, banks=banks, codes=codes,
                        model_ordinal=ordinal, level=level, required=3)


class Medium(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.dir = Path(folder.name) / 'live'
        self.medium = live.FileMedium(self.dir)

    def test_documents_round_trip_and_the_index_counts_generations(self):
        docs = live.documents(LIVE, held(), 1790899200)
        self.assertEqual(set(docs), {'Press.station', 'Press.line', 'Press.model1', 'Press.model2', 'Press.model3'})
        for key, doc in docs.items():
            self.medium.write(key, doc)
        self.medium.write('Press.station', docs['Press.station'])
        for key, doc in docs.items():
            self.assertEqual(self.medium.read(key), doc)
        index = json.loads((self.dir / live.INDEX_NAME).read_text())
        self.assertEqual(index['documents']['Press.station']['generation'], 2)
        self.assertEqual(index['documents']['Press.line']['generation'], 1)

    def test_never_written_lost_and_damaged_are_three_different_answers(self):
        self.assertIsNone(self.medium.read('Press.station'))
        doc = live.documents(LIVE, held(), 0)['Press.station']
        self.medium.write('Press.station', doc)
        self.medium._path('Press.station').unlink()
        with self.assertRaises(live.DocumentLost):
            self.medium.read('Press.station')
        self.medium.write('Press.station', doc)
        self.medium._path('Press.station').write_text('{"set":', encoding='ascii')
        with self.assertRaises(live.DocumentLost):
            self.medium.read('Press.station')

    def test_a_medium_that_cannot_answer_is_not_nothing_there(self):
        self.medium.write('Press.station', live.documents(LIVE, held(), 0)['Press.station'])
        (self.dir / live.INDEX_NAME).write_text('{damaged', encoding='ascii')
        with self.assertRaises(live.MediumUnreadable):
            self.medium.read('Press.station')
        (self.dir / live.INDEX_NAME).unlink()
        with mock.patch.object(Path, 'read_text', side_effect=PermissionError('locked')):
            with self.assertRaises(live.MediumUnreadable):
                self.medium.read('Press.station')

    def test_documents_carry_the_controller_values_and_identities(self):
        h = held(ordinal=2)
        h.records[STATION.name]['StationNumber'] = 41
        h.banks[2]['PressDwellMs'] = 777
        docs = live.documents(LIVE, h, 5)
        station = docs['Press.station']
        self.assertEqual((station[0]['set'], station[0]['kind'], station[0]['model']), (live.LIVE_NAME, 1, 'M-200'))
        self.assertIn({'scope': 'Press', 'key': 'station.number', 'rev': mf.config_revision(LIVE),
                       'kind': 1, 'type': 0, 'value': '41'}, station[1:])
        model = docs['Press.model3']
        self.assertEqual((model[0]['kind'], model[0]['model']), (0, 'M-050'))
        self.assertIn('777', [r['value'] for r in model[1:] if r['key'] == 'press.dwellMs'])
        self.assertEqual(live.content(station), live.content(live.documents(LIVE, h, 99)['Press.station']))


class Recorder:
    """A controller stand-in for the restore plan: records every transaction."""
    def __init__(self, refuse=(), deny=(), drop=()):
        self.calls, self.refuse, self.deny, self.drop = [], refuse, deny, drop

    def __call__(self, kind, staged, *, name='', model=0, store_result=0):
        self.calls.append((kind, staged[0]['kind'], staged[0]['model'], name, model, store_result, len(staged) - 1))
        index = len(self.calls)
        if index in self.drop:
            return None
        if index in self.deny:
            return {'Accepted': 0, 'DiagnosticKey': mf.numeric_key(LIVE, access.DENIED)}
        return {'Accepted': 0 if index in self.refuse else 1, 'DiagnosticKey': 7 if index in self.refuse else 0}


class RestorePlan(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.medium = live.FileMedium(Path(folder.name))
        self.commissioned = held(codes=['M-100', 'M-200', 'M-050', 'M-101'], ordinal=4)
        for key, doc in live.documents(LIVE, self.commissioned, 1).items():
            self.medium.write(key, doc)

    def restore(self, recorder, after=None):
        fresh = after or held(restoring=True)
        return live.restore(LIVE, fresh, live.plan(LIVE, self.medium), recorder)

    def test_models_then_line_then_the_station_with_the_active_model(self):
        recorder = Recorder()
        outcome = self.restore(recorder)
        self.assertTrue(outcome.complete)
        self.assertEqual(outcome.losses, [])
        kinds = [(k, doc_kind) for k, doc_kind, *_ in recorder.calls]
        self.assertEqual(kinds, [(mb.LOAD_CONFIG_SET, 0)] * 3 + [(mb.CREATE_MODEL, 0), (mb.LOAD_CONFIG_SET, 2),
                                                                  (mb.LOAD_CONFIG_SET, 1)])
        self.assertEqual([c[4] for c in recorder.calls[:3]], [1, 2, 3])  # bank ordinals
        self.assertEqual(recorder.calls[3][3], 'M-101')  # recreated under its code
        self.assertEqual(recorder.calls[-1][4:6], (4, live.STORE_OK))

    def test_a_catalog_that_moved_is_a_loss_announced_with_the_answer(self):
        recorder = Recorder()
        outcome = self.restore(recorder, held(restoring=True, codes=['M-100', 'M-050', 'M-200']))
        self.assertTrue(outcome.complete)
        # Two banks no longer hold the model their document names; the
        # runtime model still has its own next position and is recreated.
        self.assertEqual({k for k, _ in outcome.losses}, {'Press.model2', 'Press.model3'})
        self.assertEqual([c[3] for c in recorder.calls if c[0] == mb.CREATE_MODEL], ['M-101'])
        self.assertEqual(recorder.calls[-1][5], live.STORE_LOST)
        # The active model was kept by code, not by position.
        self.assertEqual(recorder.calls[-1][4], 4)

    def test_a_refused_document_is_a_loss_but_the_restore_still_answers(self):
        recorder = Recorder(refuse=(5,))
        outcome = self.restore(recorder)
        self.assertTrue(outcome.complete)
        self.assertEqual([k for k, _ in outcome.losses], ['Press.line'])
        self.assertEqual(recorder.calls[-1][5], live.STORE_LOST)

    def test_an_access_refusal_or_lost_transport_concludes_nothing(self):
        outcome = self.restore(Recorder(deny=(1,)))
        self.assertFalse(outcome.complete)
        with self.assertRaises(live.MediumUnreadable):
            self.restore(Recorder(drop=(2,)))

    def test_a_missing_confirmed_station_answers_with_an_empty_load_and_a_loss(self):
        self.medium._path('Press.station').unlink()
        recorder = Recorder()
        outcome = self.restore(recorder)
        self.assertEqual([k for k, _ in outcome.losses], ['Press.station'])
        self.assertEqual(recorder.calls[-1][-1], 0)  # no records
        self.assertEqual(recorder.calls[-1][5], live.STORE_LOST)

    def test_a_first_commissioning_answers_with_no_loss(self):
        with tempfile.TemporaryDirectory() as empty:
            recorder = Recorder()
            outcome = live.restore(LIVE, held(restoring=True), live.plan(LIVE, live.FileMedium(empty)), recorder)
        self.assertTrue(outcome.complete)
        self.assertEqual(recorder.calls, [(mb.LOAD_CONFIG_SET, 1, '', '', 0, live.STORE_OK, 0)])


class KeeperBehavior(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.now = [100.0]
        self.medium = live.FileMedium(Path(folder.name))
        self.keeper = live.Keeper(LIVE, self.medium, clock=lambda: self.now[0], wall=lambda: 1790899200)

    def test_it_writes_once_then_only_what_changed_and_never_while_restoring(self):
        h = held()
        self.assertEqual(len(self.keeper.keep(h)), 5)
        self.assertEqual(self.keeper.keep(h), [])
        h.records[STATION.name]['StationNumber'] = 41
        self.assertEqual(self.keeper.keep(h), ['Press.station'])
        restarted = live.Keeper(LIVE, self.medium)
        self.assertEqual(restarted.keep(h), [])  # a gateway restart rewrites nothing
        self.assertEqual(self.keeper.keep(held(restoring=True)), [])
        self.assertEqual(self.medium.read('Press.station')[1]['value'], '41')

    def test_a_failed_write_is_shown_and_retried(self):
        with mock.patch.object(sets.os, 'replace', side_effect=OSError('disk full')):
            self.assertEqual(self.keeper.keep(held()), [])
        self.assertTrue(self.keeper.failed)
        self.assertEqual(self.keeper.values({})['Press/ConfigPersist/Failed'], True)
        self.assertEqual(self.keeper.keep(held()), [])  # inside the retry window
        self.now[0] += live.RETRY_S
        self.assertEqual(len(self.keeper.keep(held())), 5)
        self.assertFalse(self.keeper.failed)

    def test_restore_waits_for_a_session_the_set_gate_permits(self):
        self.assertFalse(self.keeper.wants_restore(held(restoring=True, level=2)))
        self.assertFalse(self.keeper.wants_restore(held(restoring=False)))
        self.assertTrue(self.keeper.wants_restore(held(restoring=True)))

    def test_an_unreadable_medium_never_completes_and_sends_nothing(self):
        self.keeper.keep(held())
        (Path(self.medium.directory) / live.INDEX_NAME).write_text('damaged', encoding='ascii')
        recorder = Recorder()
        self.assertIsNone(self.keeper.run_restore(held(restoring=True), recorder))
        self.assertEqual((self.keeper.state, recorder.calls), ('unreadable', []))
        self.assertTrue(self.keeper.failed)
        self.assertFalse(self.keeper.wants_restore(held(restoring=True)))
        self.now[0] += live.RETRY_S
        self.assertTrue(self.keeper.wants_restore(held(restoring=True)))

    def test_losses_are_named_for_every_viewer_and_in_health(self):
        self.keeper.keep(held())
        self.medium._path('Press.line').unlink()
        outcome = self.keeper.run_restore(held(restoring=True), Recorder())
        self.assertTrue(outcome.complete)
        self.assertEqual(self.keeper.values({}), {'Press/ConfigPersist/LastRejectScope': 'Press',
                                                  'Press/ConfigPersist/LastRejectKey': 'Press.line'})
        self.assertEqual(self.keeper.health()['losses'][0]['key'], 'Press.line')


class EndToEnd(unittest.TestCase):
    """Documents from a commissioned controller restore a freshly downloaded
    one, through the guarded writer and the emitted ST."""

    def test_a_download_comes_back_as_it_was_kept(self):
        with tempfile.TemporaryDirectory() as folder:
            store = live.FileMedium(folder)
            kept = held(codes=['M-100', 'M-200', 'M-050', 'M-101'], ordinal=4)
            kept.records[STATION.name]['StationNumber'] = 41
            kept.banks[3]['PressDwellMs'] = 1234
            kept.banks[0]['TransferSettleMs'] = 321
            for key, doc in live.documents(LIVE, kept, 1).items():
                store.write(key, doc)
            comm = NativeComm(LIVE)
            c = comm.c
            c.tags[STATION_TAG]['SchemaVersion'] = 0  # the download left it never-written
            c.tags[f'FRK_{LIVE.name}_Unit'].update(ModelOrdinal=1, CommitModel=0)
            writer = gw.MailboxWriter('unused', 0, '7036B510', LIVE, set_store=object())
            sequence = [0]

            def command(kind, staged, *, name='', model=0, store_result=0):
                sequence[0] += 1
                writes = [('Press/HmiRequest/Kind', 'int32', kind),
                          ('Press/HmiRequest/TextValue', 'string', live.LIVE_NAME),
                          ('Press/HmiRequest/NameValue', 'string', name),
                          ('Press/HmiRequest/BoolValue', 'boolean', kind == mb.CREATE_MODEL),
                          ('Press/HmiRequest/DurationMs', 'uint32', model),
                          ('Press/HmiRequest/Sequence', 'uint32', sequence[0])]
                with mock.patch('pylogix.PLC', return_value=comm):
                    return writer.live_command(writes, 'Press/HmiRequest', staged, store_result)

            fresh = held(restoring=True)
            outcome = live.restore(LIVE, fresh, live.plan(LIVE, store), command)
            self.assertTrue(outcome.complete, outcome)
            self.assertEqual(outcome.losses, [])
            c.run('\n'.join(gen.model_commit_logic(LIVE)))
            self.assertEqual(c.tags[STATION_TAG]['SchemaVersion'], VERSION)
            self.assertEqual(c.tags[STATION_TAG]['StationNumber'], 41)
            self.assertEqual(models.decode(LIVE, c.tags[models.tag(LIVE)]), ['M-100', 'M-200', 'M-050', 'M-101'])
            self.assertEqual(c.tags[gen.model_cfg_tag(LIVE)][3]['PressDwellMs'], 1234)
            self.assertEqual(c.tags[gen.model_cfg_tag(LIVE)][0]['TransferSettleMs'], 321)
            self.assertEqual(c.tags[f'FRK_{LIVE.name}_Unit']['ModelOrdinal'], 4)
            self.assertEqual(c.tags[APP.records[0].name + 'Tag']['PressDwellMs'], 1234)
            self.assertEqual(c.tags[gen.config_persist_tag(LIVE)]['RestoreLost'], 0)
            commits = [v for t, v in comm.writes if t == mb.request_tag_name(LIVE) + '.Sequence']
            self.assertEqual(commits, list(range(1, sequence[0] + 1)))


class GatewayLive(unittest.IsolatedAsyncioTestCase):
    def fixture(self, held_value, *, write_token='fixture'):
        values = {'Press/HmiRequest/Sequence': 9, 'Press/HmiResponse/AckSequence': 9,
                  'Press/ConfigPersist/Failed': False, 'Press/ConfigPersist/LastRejectKey': ''}
        station = gw.Station(lambda: {'values': dict(values), 'liveConfig': held_value}, cache_ttl=0)
        writer = mock.Mock()
        writer.live_command = mock.Mock(return_value={'Accepted': 1, 'DiagnosticKey': 0})
        keeper = mock.Mock(wraps=live.Keeper(LIVE, live.FileMedium(self.folder)))
        g = gw.Gateway(station, write_token=write_token, write_roots=frozenset({'Press'}),
                       write_fn=writer, live_keeper=keeper)
        return g, writer, keeper

    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.folder = folder.name

    async def test_a_read_only_gateway_keeps_documents_but_never_restores(self):
        g, writer, keeper = self.fixture(held(restoring=True), write_token='')
        await g.live_cycle()
        writer.live_command.assert_not_called()
        self.assertIn('read-only', keeper.error)

    async def test_a_restore_burns_forward_sequences_under_the_mailbox_lock(self):
        g, writer, _keeper = self.fixture(held(restoring=True))
        await g.live_cycle()
        sequences = [call.args[0][-1][2] for call in writer.live_command.call_args_list]
        self.assertEqual(sequences, list(range(10, 10 + len(sequences))))
        self.assertGreaterEqual(len(sequences), 1)
        self.assertEqual(g._mailbox_sequences['Press/HmiRequest'], sequences[-1])
        state = gw._ConnState()
        state.authenticated = True
        stale = {'writes': [{'path': 'Press/HmiRequest/Kind', 'valueType': 'int32', 'value': mb.STOP},
                            {'path': 'Press/HmiRequest/Sequence', 'valueType': 'uint32', 'value': sequences[-1]}]}
        with self.assertRaises(gw.WriteRefused):
            await g._write_batch(state, stale)  # an HMI that raced it is refused, never mis-acknowledged

    async def test_an_intact_controller_is_kept_and_the_capture_is_never_sent(self):
        g, writer, keeper = self.fixture(held())
        await g.live_cycle()
        keeper.keep.assert_called_once()
        writer.live_command.assert_not_called()
        snapshot = await g._snapshot(gw._ConnState())
        self.assertNotIn('liveConfig', snapshot)

    async def test_a_keeper_failure_overlays_the_published_status(self):
        g, _writer, keeper = self.fixture(held())
        keeper.values = mock.Mock(return_value={'Press/ConfigPersist/Failed': True, 'Press/Unpublished': 1})
        doc = await g.station.document()
        values = g._values_for(gw._ConnState(), doc)
        self.assertTrue(values['Press/ConfigPersist/Failed'])
        self.assertNotIn('Press/Unpublished', values)  # the path set never moves


if __name__ == '__main__':
    unittest.main()
