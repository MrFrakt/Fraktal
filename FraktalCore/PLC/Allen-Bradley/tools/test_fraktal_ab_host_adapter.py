"""The declaration-free host adapter against the emitted controller code (WP6.5).

`RootService` answers the jobs the generated routines open, on the bench,
through a port that reads the published reply and writes the request exactly
as a client does. Its file store and medium are real folders. What it renders
from published facts must equal what the engineering code renders from the
declaration, and its process must import neither the declaration nor the
generator.
"""
import dataclasses
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import fraktal_ab_canonical_publication as pub
import fraktal_ab_generate as gen
import fraktal_ab_genealogy_s4b_owner_demo as demo
import fraktal_ab_host_adapter as adapter
import fraktal_ab_host_service_binding as binding
import fraktal_ab_host_services as host
import fraktal_ab_live as live
import fraktal_ab_live_medium as medium
import fraktal_ab_manifest as mf
import fraktal_ab_mailbox as mb
import fraktal_ab_set_documents as documents
import fraktal_ab_sets as sets
import test_fraktal_ab_host_sets as bench_sets
from test_fraktal_ab_host_sets import Context, Station

SETS = LIVE = None


def setUpModule():
    global SETS, LIVE
    SETS = Context(bench_sets.application())
    LIVE = Context(dataclasses.replace(demo.application(), canonical_host_services=True))


def _signed(value):
    return value - 0x100000000 if value > 0x7fffffff else value


class BenchPort:
    """The adapter's port over one bench station: published reply in, request and commit out."""

    def __init__(self, station):
        self.s, self.app, self.root = station, station.app, station.app.name

    def _plain(self, value):
        if isinstance(value, dict) and set(value) == {'LEN', 'DATA'}:
            return self.s.bench.text(value)
        if isinstance(value, dict):
            return {k: self._plain(v) for k, v in value.items()}
        if isinstance(value, list):
            return [self._plain(v) for v in value]
        return value

    def reply(self):
        return self._plain(self.s.host_reply)

    def wait(self):
        self.s.scan()

    def submit(self, envelope, body):
        sequence = binding.next_sequence(self.reply())
        request = self.s.t[host.request_tag(self.app)]
        request.update(SchemaVersion=1, StagedSequence=_signed(sequence),
                       ManifestRevision=self.s.t[pub.header_tag(self.app)]['ConfigRevision'], **envelope)
        target = request['Body']
        for name, value in target.items():
            if isinstance(value, dict):
                self.s.bench.put(value, '')
            elif isinstance(value, list):
                for i, item in enumerate(value):
                    if isinstance(item, dict):
                        self.s.bench.put(item, '')
                    else:
                        value[i] = 0
            else:
                target[name] = 0
        for name, value in body.items():
            if name == 'Keys':
                for i, key in enumerate(value):
                    self.s.bench.put(target['Keys'][i], key)
            elif isinstance(value, str):
                self.s.bench.put(target[name], value)
            elif isinstance(value, list):
                target[name][:len(value)] = value
            else:
                target[name] = value
        self.s.t[host.commit_tag(self.app)] = _signed(sequence)
        self.s.scan()
        answer = self.reply()
        if answer['AckSequence'] & 0xffffffff != sequence:
            raise adapter.Unanswered('no acknowledgement')
        return answer

    def facts(self):
        t, root = self.s.t, self.s.t[self.root]
        keys = {row['NumericKey']: self.s.bench.text(row['PortableKey']) for row in t[f'FRK_{self.root}_MfLocalization']}
        capabilities = tuple(adapter.Capability(r['CapabilityIndex'], keys[r['WriteKeyKey']], r['ConfigKind'], r['ValueType'])
                             for r in t[f'FRK_{self.root}_MfWriteCapabilities'] if r['CapabilityIndex'])
        codes = tuple(self.s.bench.text(m['ModelCode']) for m in root['AvailableModels'][:root['AvailableModelCount']])
        legacy = self.s.bench.text(t[pub.header_tag(self.app)]['LegacyContentHash'])
        return adapter.Facts(self.root, adapter.revision_of(legacy), capabilities, codes, root['ModelCapacity'])

    def key_text(self, numeric):
        return next((self.s.bench.text(r['PortableKey']) for r in self.s.t[f'FRK_{self.root}_MfLocalization']
                     if r['NumericKey'] == numeric), '')


class Rig:
    """A station, its host adapter, and the folders the adapter keeps."""

    def __init__(self, ctx):
        self.folder = tempfile.TemporaryDirectory()
        self.s = Station(ctx)
        self.store = documents.FileStore(Path(self.folder.name) / 'sets')
        self.medium = medium.FileMedium(Path(self.folder.name) / 'live')
        self.now = [100.0]
        self.service = adapter.RootService(BenchPort(self.s), self.store,
                                           self.medium if ctx is LIVE else None,
                                           clock=lambda: self.now[0], wall=lambda: 1790899200,
                                           keep_interval=0.0, retry=0.0)

    def close(self):
        self.folder.cleanup()

    def command(self, kind, **arguments):
        """An operator command, answered with whatever the adapter serves."""
        sequence = self.s.command(kind, **arguments)
        for _ in range(40):
            if self.s.answered(sequence):
                return self.s.reply
            self.s.scan()
            self.service.step()
        raise AssertionError('the command was never answered')

    def settle(self, steps=10):
        for _ in range(steps):
            self.s.scan()
            self.service.step()


class ConfigurationSets(unittest.TestCase):
    def setUp(self):
        self.rig = Rig(SETS)
        self.addCleanup(self.rig.close)

    def test_save_list_load_export_and_delete_go_through_the_adapters_store(self):
        r, app = self.rig, SETS.app
        self.assertTrue(r.command(mb.SAVE_CONFIG_SET, TextValue='alpha', IntValue=1)['Accepted'])
        r.settle()
        self.assertEqual(r.s.persist()['Pending'], 0)
        saved = r.store.read('alpha')
        # The adapter rendered from published facts what the declaration renders.
        expected = sets.values_document(app, 'alpha', 1, lambda o, rec, m: r.s.t[rec.name + 'Tag'][m.name], '',
                                        saved[0]['created'], saved[0]['clock'])
        self.assertEqual(saved, expected)
        self.assertTrue(r.command(mb.LIST_CONFIG_SETS)['Accepted'])
        self.assertEqual((r.s.t[app.name]['ConfigSetCount'], r.s.bench.text(r.s.t[app.name]['ConfigSets'][0]['SetName'])),
                         (1, 'alpha'))
        before = r.s.station()
        number = next(m for _o, rec, m in gen.editable_values(app) if rec.station_cfg)
        r.s.t[next(rec for rec in app.records if rec.station_cfg).name + 'Tag'][number.name] = number.maximum
        self.assertTrue(r.command(mb.LOAD_CONFIG_SET, TextValue='alpha')['Accepted'])
        self.assertEqual(r.s.station(), before)
        self.assertTrue(r.command(mb.EXPORT_CONFIG_SET, TextValue='alpha', IntValue=2)['Accepted'])
        self.assertEqual(r.s.bench.text(r.s.t[app.name]['ConfigSetDocument']), documents.render_line(saved[2]))
        self.assertTrue(r.command(mb.DELETE_CONFIG_SET, TextValue='alpha')['Accepted'])
        r.settle()
        self.assertEqual(r.store.list(), [])

    def test_a_current_export_is_rendered_then_served_line_by_line(self):
        r, app = self.rig, SETS.app
        self.assertTrue(r.command(mb.EXPORT_CURRENT_CONFIG, TextValue='now', IntValue=1)['Accepted'])
        header = json.loads(r.s.bench.text(r.s.t[app.name]['ConfigSetDocument']))
        self.assertEqual((header['set'], header['kind'], header['configRev']), ('now', 1, mf.config_revision(app)))
        lines = r.s.t[app.name]['ConfigSetDocumentLines']
        self.assertTrue(r.command(mb.EXPORT_CONFIG_SET, TextValue='now', IntValue=lines)['Accepted'])
        self.assertEqual(r.s.t[app.name]['ConfigSetDocumentLine'], lines)

    def test_an_import_in_pieces_is_stored_on_commit(self):
        r, app = self.rig, SETS.app
        document = sets.values_document(app, 'imported', 1, lambda o, rec, m: m.initial, '', 0, 0)
        lines = [documents.render_line(v) for v in document]
        for index, text in enumerate(lines):
            pieces = [text[i:i + 200] for i in range(0, len(text), 200)]
            for p, piece in enumerate(pieces):
                last = index == len(lines) - 1 and p == len(pieces) - 1
                answer = r.command(mb.IMPORT_CONFIG_SET, TextValue=piece, IntValue=int(p < len(pieces) - 1),
                                   BoolValue=int(last))
                self.assertTrue(answer['Accepted'], (index, p))
        r.settle()
        self.assertEqual(r.store.read('imported'), document)

    def test_a_stored_value_the_controller_cannot_parse_is_sent_as_invalid_never_coerced(self):
        r, app = self.rig, SETS.app
        document = sets.values_document(app, 'bad', 1, lambda o, rec, m: m.initial, '', 0, 0)
        # A value whose range admits 0: coerced to a number, it would load.
        members = {m.write_key: m for _o, _rec, m in gen.editable_values(app)}
        target = next(x for x in document[1:] if x['type'] != 2
                      and members[x['key']].minimum <= 0 <= members[x['key']].maximum)
        target['value'] = '3.5'
        r.store.save(document)
        before = r.s.station()
        self.assertFalse(r.command(mb.LOAD_CONFIG_SET, TextValue='bad')['Accepted'])
        self.assertEqual(r.s.station(), before)
        self.assertEqual(r.s.bench.text(r.s.t[app.name]['ConfigPersist']['LastRejectKey']), target['key'])

    def test_a_missing_set_and_a_full_store_refuse(self):
        r = self.rig
        self.assertFalse(r.command(mb.LOAD_CONFIG_SET, TextValue='nothing')['Accepted'])
        # Refused by the transaction, which audits it: the host answered, it did not fail.
        self.assertEqual(r.s.bench.text(r.s.reply['Diagnostic']), sets.REJECTED_KEY)
        self.assertEqual(r.s.t[sets.state_tag(SETS.app)]['AuditCount'], 1)
        for name in ('a', 'b', 'c', 'd'):
            self.assertTrue(r.command(mb.SAVE_CONFIG_SET, TextValue=name, IntValue=1)['Accepted'])
            r.settle()
        self.assertFalse(r.command(mb.SAVE_CONFIG_SET, TextValue='e', IntValue=1)['Accepted'])
        self.assertTrue(r.command(mb.SAVE_CONFIG_SET, TextValue='a', IntValue=1)['Accepted'])


class LiveDocuments(unittest.TestCase):
    def setUp(self):
        self.rig = Rig(LIVE)
        self.addCleanup(self.rig.close)

    def kept(self, app, values_of):
        held = live.Capture(restoring=False, records=values_of['records'], banks=values_of['banks'],
                            codes=values_of['codes'], model_ordinal=values_of['model'])
        return live.documents(app, held, 1790899200)

    def test_a_download_is_restored_from_the_medium_and_then_kept(self):
        r, app = self.rig, LIVE.app
        codes = [m.code for m in app.models]
        def value(_o, _rec, m):
            return (0 if m.initial else 1) if m.kind == 'boolean' else (m.maximum if m.initial != m.maximum else m.minimum)
        station = sets.values_document(app, live.LIVE_NAME, 1, value, codes[0], 1790899200, 0)
        model = sets.values_document(app, live.LIVE_NAME, 0, value, codes[0], 1790899200, 0)
        r.medium.write(live.station_key(app), station)
        r.medium.write(live.model_key(app, 1), model)
        self.assertTrue(r.s.host_reply['Restoring'])
        r.settle(4)
        self.assertTrue(r.service.health.restored_at, r.service.health.as_dict())
        self.assertEqual(r.service.health.losses, [])
        self.assertEqual(r.s.t[gen.station_cfg_record(app).name + 'Tag']['SchemaVersion'],
                         gen.station_cfg_record(app).schema_version)
        self.assertEqual(r.s.station(), {x['key']: (1 if x['value'] == 'TRUE' else 0 if x['value'] == 'FALSE' else int(x['value']))
                                         for x in station[1:]})
        # Now kept: every document rewritten from the controller, as the keeper renders it.
        r.settle(12)
        records = {rec.name: dict(r.s.t[rec.name + 'Tag']) for rec in app.records}
        banks = [dict(b) for b in r.s.t[gen.model_cfg_tag(app)][:len(codes)]]
        expected = self.kept(app, dict(records=records, banks=banks, codes=codes,
                                       model=r.s.t[f'FRK_{app.name}_Unit']['ModelOrdinal']))
        for key, document in expected.items():
            self.assertEqual(medium.content(r.medium.read(key)), medium.content(document), key)

    def test_a_lost_document_is_restored_as_a_loss(self):
        r, app = self.rig, LIVE.app
        station = sets.values_document(app, live.LIVE_NAME, 1, lambda o, rec, m: m.initial, app.models[0].code, 0, 0)
        r.medium.write(live.station_key(app), station)
        r.medium.write(live.model_key(app, 1), sets.values_document(app, live.LIVE_NAME, 0, lambda o, rec, m: m.initial,
                                                                     app.models[0].code, 0, 0))
        r.medium._path(live.model_key(app, 1)).unlink()
        r.settle(4)
        self.assertTrue(r.service.health.restored_at)
        self.assertEqual([key for key, _why in r.service.health.losses], [live.model_key(app, 1)])
        self.assertEqual(r.s.persist()['RestoreLost'], 1)

    def test_an_unreadable_medium_restores_nothing(self):
        r, app = self.rig, LIVE.app
        (Path(r.folder.name) / 'live').mkdir(parents=True)
        (Path(r.folder.name) / 'live' / medium.INDEX_NAME).write_text('not json', encoding='ascii')
        r.settle(4)
        self.assertEqual(r.service.health.state, 'unreadable')
        self.assertTrue(r.s.host_reply['Restoring'])


class Process(unittest.TestCase):
    def test_the_adapter_imports_neither_the_declaration_nor_the_generator(self):
        tools = Path(__file__).resolve().parent
        probe = ('import sys; sys.path.insert(0, %r); import fraktal_ab_host_adapter, fraktal_ab_host_cip; '
                 'print(sorted(m for m in sys.modules if m.startswith("fraktal_ab")))' % str(tools))
        loaded = json.loads(subprocess.run([sys.executable, '-I', '-c', probe], capture_output=True, text=True,
                                           check=True).stdout.replace("'", '"'))
        forbidden = {'fraktal_ab_declaration', 'fraktal_ab_generate', 'fraktal_ab_station', 'fraktal_ab_projection',
                     'fraktal_ab_manifest', 'fraktal_ab_sets', 'fraktal_ab_live', 'fraktal_ab_mailbox'}
        self.assertFalse(forbidden & set(loaded), loaded)

    def test_the_core_kinds_are_the_mailbox_ordinals(self):
        self.assertEqual((adapter.SAVE, adapter.LOAD, adapter.LIST, adapter.EXPORT, adapter.IMPORT, adapter.DELETE,
                          adapter.CREATE, adapter.EXPORT_CURRENT),
                         (mb.SAVE_CONFIG_SET, mb.LOAD_CONFIG_SET, mb.LIST_CONFIG_SETS, mb.EXPORT_CONFIG_SET,
                          mb.IMPORT_CONFIG_SET, mb.DELETE_CONFIG_SET, mb.CREATE_MODEL, mb.EXPORT_CURRENT_CONFIG))
        import fraktal_ab_access as access
        self.assertEqual(adapter.DENIED_KEY, access.DENIED)


if __name__ == '__main__':
    unittest.main()
