"""C5b3 policy fixtures: native facts, published identity and independent cleanup."""
import asyncio
import struct
from pathlib import Path
from types import SimpleNamespace as NS
import unittest
from unittest.mock import AsyncMock, Mock, patch

import fraktal_ab_canonical_live as live
import fraktal_ab_canonical_reader as reader
import fraktal_ab_fixture_reads as views
import fraktal_ab_phase6_access_execute as users
import fraktal_ab_phase6_data_execute as data
import fraktal_ab_phase6_shelving_execute as shelf
import fraktal_ab_phase6_sets_execute as sets_fixture
import fraktal_ab_press_s6_collapse_echo38 as profile
import test_fraktal_ab_canonical_keys as key_seam
import test_fraktal_ab_harness_documents as config_seam

APP = profile.application()


class Capabilities(unittest.TestCase):
    def make(self, rows=((19, 731, 1), (701, 8, 0))):
        seam = key_seam.Keys()
        seam.setUp()
        cap = seam.capture['manifest']['commandBindings'][0]
        native = next(s for s in seam.capture['symbols'] if s['name'] == cap['CapabilitiesSymbol'])
        native['name'] = 'UnrelatedCapabilities'
        cap.update(CapabilitiesSymbol=native['name'], CapabilitiesCount=len(rows))
        subject = seam.build()
        handle = native['handle']
        fields = {m['name']: m for m in reader.member_table(subject._objects[handle])}
        raw = bytearray(subject._sizes[handle] * len(rows))
        for i, row in enumerate(rows):
            for name, value in zip(('CapabilityIndex', 'WriteKeyKey', 'ConfigKind'), row):
                struct.pack_into('<i', raw, i * subject._sizes[handle] + fields[name]['offset'], value)
        old = subject._body._raw
        subject._body = live.LeafBody(lambda loc: raw[loc.offset:loc.offset + loc.width]
            if loc.source == native['name'] else old(loc))
        return subject, seam

    def test_sparse_native_ids_follow_the_published_key_table_and_are_immutable(self):
        subject, seam = self.make()
        result = subject.command_capabilities('Press')
        self.assertEqual(dict(result), {'std.fixture.denied': 19, 'std.fixture.unknown': 701})
        self.assertIs(subject.command_capabilities('Press'), result)
        with self.assertRaises(TypeError):result['invented'] = 4

    def test_unknown_key_duplicate_id_or_duplicate_key_refuses_without_caching(self):
        for rows in (((19, 731, 1), (19, 8, 0)), ((19, 731, 1), (20, 731, 0)), ((1, 999999, 1),), ((1, 731, 3),)):
            with self.subTest(rows=rows):
                subject, seam = self.make(rows)
                with self.assertRaises(ValueError):subject.command_capabilities('Press')
                self.assertEqual(subject._command_capabilities, {})

    def test_changed_revision_and_invalid_template_refuse(self):
        subject, seam = self.make()
        subject.command_keys('Press')
        seam.epoch_reads = 0
        seam.change_epoch = True
        with self.assertRaisesRegex(ValueError, 'crossed a root revision'):
            subject.command_capabilities('Press')
        self.assertEqual(subject._command_capabilities, {})
        subject, seam = self.make()
        symbol = next(s for s in subject._symbols.values() if s['name'] == 'UnrelatedCapabilities')
        field = reader.member_table(subject._objects[symbol['handle']])[0]
        field['array'] = 1
        # Mutate the actual parsed Template record, not the detached member table.
        target = subject._objects[symbol['handle']]
        original = live.member_table
        def changed(template):
            rows = original(template)
            if template is target:
                rows = [dict(r, atomic=0xc1) if r['name'] == 'CapabilityIndex' else r for r in rows]
            return rows
        with patch.object(live, 'member_table', changed), self.assertRaises(ValueError):
            subject.command_capabilities('Press')


class Reads(unittest.TestCase):
    def test_raw_access_and_alarm_fields_are_not_retyped_or_projected(self):
        states = dict(AccessState={'LoginResultSequence': -1, 'LoginBusy': 1},
            AccessAudit={'Sequence': [-2147483648, -1, 0], 'Key': [31, 5, 0]},
            AlarmActive={'ActShelved': [0, 1]}, AlarmRing={'SchemaVersion': 2})
        session = NS(surface=lambda name: states[name])
        with patch.object(views, '_session', return_value=session):
            self.assertEqual(views.read_access(object(), app=APP)['LoginResultSequence'], -1)
            self.assertEqual(views.read_access(object(), app=APP, audit=True)['Sequence'], [-2147483648, -1, 0])
            self.assertEqual(views.read_alarm_log(object(), app=APP), (states['AlarmActive'], states['AlarmRing']))

    def classes(self, duplicate=False):
        values = {'Press/Access/ClassCount': 2}
        for i, identity in enumerate(('public', 'public' if duplicate else 'commissioning'), 1):
            for name, value in dict(ClassId=identity, ReadLevel=0, WriteLevel=i).items():
                values[f'Press/Access/Classes[{i}]/{name}'] = value
        return values

    def test_classes_come_from_core_and_duplicate_ids_fail(self):
        for duplicate in (False, True):
            held = self.classes(duplicate)
            with patch.object(views, '_session', return_value=NS(root='Press')), \
                    patch.object(views, 'values', side_effect=lambda comm, paths, app: {p: held[p] for p in paths}):
                if duplicate:
                    with self.assertRaises(ValueError):views.class_levels(object(), app=APP)
                else:self.assertEqual(views.class_levels(object(), app=APP)['commissioning'], dict(read=0, write=2))

    def configuration(self):
        seam = config_seam.Reader()
        for i in range(3):
            for name, value in dict(ClassId='public', ReadLevel=0, WriteLevel=3).items():
                seam.values[f'{seam.prefix}/Definitions[{i}]/{name}'] = value
        return seam

    def test_configuration_reads_active_values_only_and_keeps_masked_metadata(self):
        seam = self.configuration()
        seam.values[seam.prefix + '/Values[1]/Readable'] = False
        seam.values[seam.prefix + '/Values[1]/ValueText'] = ''
        with patch.object(views, '_session', return_value=NS(root='Press', reader=seam)):
            entries = views.configuration_entries(object(), app=APP)
        self.assertFalse(entries['station.value']['Readable'])
        self.assertEqual(entries['station.value']['WriteLevel'], 3)
        self.assertEqual(entries['station.value']['ValueText'], '')
        paths = [p for group in seam.calls for p in group]
        self.assertNotIn(seam.prefix + '/Values[3]/ValueText', paths)
        self.assertNotIn(seam.prefix + '/Values[4]/Readable', paths)

    def test_configuration_refuses_duplicate_active_rows_bad_masks_and_changed_revision(self):
        for suffix, value in (('Values[1]/DefinitionIndex', 0), ('Values[0]/ModelOrdinal', 3),
                              ('Values[0]/Revision', 12), ('Values[0]/Readable', False)):
            seam = self.configuration()
            seam.values[seam.prefix + '/' + suffix] = value
            with self.subTest(suffix=suffix), patch.object(views, '_session', return_value=NS(root='Press', reader=seam)), self.assertRaises(ValueError):
                views.configuration_entries(object(), app=APP)

    def test_alarm_descriptions_keep_per_row_proofs_and_actual_native_slots(self):
        calls = []
        def read(comm, paths, app):
            paths = tuple(paths);calls.append(paths)
            return {paths[0]: 'published audit'}
        with patch.object(views, '_session', return_value=NS(root='Press')), patch.object(views, 'values', side_effect=read):
            result = views.alarm_descriptions(object(), (0, 63), app=APP)
        self.assertEqual(len(calls), 2)
        self.assertIn('AlarmLog/Ring[64]/Description', result)
        self.assertTrue(all(len(group) == 1 for group in calls))


class Requests(unittest.IsolatedAsyncioTestCase):
    async def test_typed_probe_does_not_reinitialize_or_use_legacy_serial_lookup(self):
        client = users.Client.__new__(users.Client)
        client.comm = object()
        with patch.object(users, 'APP', APP), patch.object(users.px, 'command', return_value={'accepted': False}) as send, \
                patch.object(users.projection, 'verify_serial', side_effect=AssertionError('legacy identity')), \
                patch.object(users.Client, '__init__', side_effect=AssertionError('reinitialized')):
            answer = client.native(users.mb.SET_ACCESS_LEVEL, IntValue=8, TextValue='0', User='claimed-admin')
        self.assertFalse(answer['accepted'])
        self.assertEqual(send.call_count, 1)

    async def test_configuration_probe_preserves_claimed_user_and_uses_typed_identity(self):
        client = users.Client.__new__(users.Client)
        client.comm = object();client.native = Mock(return_value={'accepted': False})
        with patch.object(users, 'APP', APP), patch.object(views, 'revision', return_value=37):
            client.probe_config('station.number', 41, User='claimed-admin')
        self.assertEqual(client.native.call_args.kwargs, dict(TargetPath='Press', NameValue='station.number',
            IntValue=37, TextValue='41', DurationMs=0, User='claimed-admin'))

    async def test_login_waits_for_its_wrapped_result_and_uses_published_timeout(self):
        client = users.Client.__new__(users.Client)
        client.comm = object();client.login_timings = []
        client.command = AsyncMock(return_value={'accepted': True, 'sequence': 0xffffffff})
        state = dict(LoginBusy=0, LoginResultSequence=-1, LoginFailed=0, CurrentLevel=4,
                     UserLength=3, UserBytes=list(b'ops'))
        with patch.object(users, 'APP', APP), patch.object(users, 'read_access', side_effect=[{'LoginTimeoutMs': 31}, state]):
            answer, actual = await client.login(dict(user='ops', level=4, pin='synthetic'))
        self.assertEqual(actual['LoginResultSequence'], -1)
        self.assertTrue(client.login_timings[0]['authenticated'])
        self.assertNotIn('synthetic', str(client.login_timings))

    async def test_invalid_timeout_refuses_before_sending_a_pin(self):
        client = users.Client.__new__(users.Client);client.comm = object();client.command = AsyncMock()
        with patch.object(users, 'APP', APP), patch.object(users, 'read_access', return_value={'LoginTimeoutMs': 0}), self.assertRaises(ValueError):
            await client.login(dict(user='ops', level=4, pin='synthetic'))
        client.command.assert_not_called()

    async def test_independent_cleanup_deletes_fixture_set_before_logout_despite_one_field_failure(self):
        calls = []
        client = NS(comm=object(), store=NS(list=lambda: [{'set': data.SET_NAME}]))
        async def command(kind, **args):
            calls.append((kind, args))
            if kind == users.mb.SET_ACCESS_LEVEL and args['IntValue'] == 0:raise RuntimeError('one gate failed')
            return {'accepted': True}
        client.command = command
        client.login = AsyncMock(return_value=({'accepted': True}, dict(CurrentLevel=4, LoginFailed=0, UserBytes=list(b'ops'), UserLength=3)))
        client.native = Mock(return_value={'accepted': True});client.write_config = AsyncMock(return_value={'accepted': True})
        original = dict(Required=[0, 0], SessionTimeout=0, **{'station.number': 7})
        held = dict(Required=[0, 0], SessionTimeout=0, CurrentLevel=0, UserLength=0)
        with patch.object(users, 'read_access', return_value=held), patch.object(sets_fixture, 'station_values', return_value={'station.number': 7}):
            result = await users.restore(client, original, dict(user='ops', level=4), {}, set_names=(data.SET_NAME,))
        self.assertFalse(result)
        self.assertIn((users.mb.SET_ACCESS_LEVEL, {'IntValue': 1, 'TextValue': '0'}), calls)
        self.assertLess(next(i for i, r in enumerate(calls) if r[0] == users.mb.DELETE_CONFIG_SET),
                        next(i for i, r in enumerate(calls) if r[0] == users.mb.LOGOUT))

    async def test_alarm_identity_uses_the_plc_description_and_rejects_a_changed_reason(self):
        active = dict(ActReasonCode=[77], ActState=[1])
        for code in (77, 78):
            held = {'Press/AlarmLog/Active[1]/ReasonCode': code,
                    'Press/AlarmLog/Active[1]/Description': 'published.reason'}
            with patch.object(shelf, 'APP', APP), patch.object(shelf, 'read_alarm_log', return_value=(active, {})), \
                    patch.object(views, 'values', return_value=held), \
                    patch.object(shelf.projection, 'reason_description', side_effect=AssertionError('declaration text')):
                if code == 77:self.assertEqual(shelf.reason_description(object(), 77), 'published.reason')
                else:
                    with self.assertRaises(ValueError):shelf.reason_description(object(), 77)

    async def test_configuration_selection_does_not_read_other_active_value_text(self):
        seam = Reads().configuration()
        with patch.object(views, '_session', return_value=NS(root='Press', reader=seam)):
            result = views.configuration_entries(object(), app=APP, keys=('station.value',))
        self.assertEqual(set(result), {'station.value'})
        paths = [p for group in seam.calls for p in group]
        self.assertNotIn(seam.prefix + '/Values[0]/ValueText', paths)
        self.assertNotIn(seam.prefix + '/Definitions[0]/ReadLevel', paths)

    async def test_client_closes_when_original_snapshot_fails(self):
        calls = []
        class Client:
            comm = object()
            def __enter__(self):return self
            def __exit__(self, *unused):calls.append('closed')
        with patch.object(users, 'APP', APP), patch.object(users, 'Client', return_value=Client()), \
                patch.object(sets_fixture, 'read_records', side_effect=ValueError('snapshot failed')):
            with self.assertRaises(ValueError):await users.fixture(object(), '601FC87B', [], {}, 'unused')
        self.assertEqual(calls, ['closed'])


if __name__ == '__main__':unittest.main()
