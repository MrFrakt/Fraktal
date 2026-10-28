"""D5 paired checks: a read-only viewer can query, never mutate or stage."""
import asyncio
import unittest
import threading
import fraktal_ab_gateway as gw
import fraktal_ab_mailbox as mb


def query(root='Press', sequence=8, model=0):
    return {'writes': [
        {'path': f'{root}/HmiRequest/Kind', 'valueType': 'int32', 'value': mb.QUERY_CONFIG},
        {'path': f'{root}/HmiRequest/IntValue', 'valueType': 'int32', 'value': 0},
        {'path': f'{root}/HmiRequest/DurationMs', 'valueType': 'uint32', 'value': model},
        {'path': f'{root}/HmiRequest/Sequence', 'valueType': 'uint32', 'value': sequence}]}


class ConfigQuery(unittest.TestCase):
    def setUp(self):
        self.calls = []
        self.state = gw._ConnState()
        self.g = gw.Gateway(gw.Station(lambda: {
            'values': {'Press/HmiRequest/Sequence': 7, 'Press/Status/Name': 'Press'},
            'dataValues': {}, 'truncated': False}),
            write_fn=lambda writes, mailbox: self.calls.append((writes, mailbox)) or True)

    def run_batch(self, batch):
        return asyncio.run(self.g._write_batch(self.state, batch))

    def test_query_works_without_a_bearer_or_write_root(self):
        self.assertTrue(self.run_batch(query(model=2)))
        self.assertEqual(self.state.config_model, 2)
        self.assertEqual(self.calls[0][0][-1][0], 'Press/HmiRequest/Sequence')

    def test_every_mutation_still_needs_authorization(self):
        for kind in mb.KINDS.values():
            if kind == mb.QUERY_CONFIG:
                continue
            batch = query()
            batch['writes'][0]['value'] = kind
            with self.subTest(kind=kind), self.assertRaises(gw.WriteRefused):
                self.run_batch(batch)
        self.assertEqual(self.calls, [])

    def test_full_hmi_shape_with_empty_unused_arguments_is_a_query(self):
        batch = query()
        batch['writes'][1:1] = [
            {'path': f'Press/HmiRequest/{m}', 'valueType': 'string', 'value': ''}
            for m in ('TargetPath', 'NameValue', 'TextValue', 'User', 'Secret')]
        batch['writes'].insert(-1, {'path': 'Press/HmiRequest/BoolValue', 'valueType': 'boolean', 'value': False})
        self.assertTrue(self.run_batch(batch))

    def test_unused_arguments_cannot_smuggle_a_mutation(self):
        for member, vtype, value in (('TextValue', 'string', '950'), ('Secret', 'string', 'pin'),
                                     ('BoolValue', 'boolean', True), ('Unexpected', 'int32', 1)):
            batch = query()
            batch['writes'].insert(-1, {'path': f'Press/HmiRequest/{member}', 'valueType': vtype, 'value': value})
            with self.subTest(member=member), self.assertRaises(gw.WriteRefused):
                self.run_batch(batch)
        self.assertEqual(self.calls, [])

    def test_nested_kind_cannot_mask_a_real_kind_write(self):
        batch = query()
        batch['writes'][0]['value'] = mb.START
        batch['writes'].insert(-1, {'path': 'Press/HmiRequest/Hidden/Kind', 'valueType': 'int32', 'value': mb.QUERY_CONFIG})
        with self.assertRaises(gw.WriteRefused):
            self.run_batch(batch)
        self.assertEqual(self.calls, [])

    def test_missing_kind_page_model_or_commit_never_acquires_read_authority(self):
        for index in range(4):
            batch = query()
            batch['writes'].pop(index)
            with self.subTest(index=index), self.assertRaises((gw.WriteRefused, ValueError)):
                self.run_batch(batch)
        self.assertEqual(self.calls, [])

    def test_another_root_and_a_stale_sequence_are_refused_without_changing_the_page(self):
        for batch in (query(root='Other'), query(sequence=7, model=2)):
            with self.assertRaises(gw.WriteRefused):
                self.run_batch(batch)
        self.assertEqual(self.state.config_model, 0)
        self.assertEqual(self.calls, [])

    def test_queries_keep_the_ordinary_global_sequence_discipline(self):
        self.assertTrue(self.run_batch(query()))
        with self.assertRaises(gw.WriteRefused):
            self.run_batch(query())
        self.assertTrue(self.run_batch(query(sequence=9)))
        self.assertEqual(len(self.calls), 2)

    def test_single_member_staging_does_not_obtain_the_exception(self):
        with self.assertRaises(gw.WriteRefused):
            asyncio.run(self.g._write(self.state, query()['writes'][0]))

    def test_two_viewers_cannot_commit_the_same_sequence_in_parallel(self):
        entered, release = threading.Event(), threading.Event()
        def write(writes, mailbox):
            self.calls.append((writes, mailbox))
            entered.set()
            self.assertTrue(release.wait(2))
            return True
        self.g._write_fn = write
        async def race():
            first = asyncio.create_task(self.g._write_batch(self.state, query()))
            self.assertTrue(await asyncio.to_thread(entered.wait, 2))
            second = asyncio.create_task(self.g._write_batch(gw._ConnState(), query()))
            await asyncio.sleep(0)
            release.set()
            return await asyncio.gather(first, second, return_exceptions=True)
        results = asyncio.run(race())
        self.assertTrue(results[0])
        self.assertIsInstance(results[1], gw.WriteRefused)
        self.assertEqual(len(self.calls), 1)

    def test_failed_transport_burns_sequence_without_changing_connection_page(self):
        self.g._write_fn = lambda *_: False
        self.assertFalse(self.run_batch(query(model=2)))
        self.assertEqual(self.state.config_model, 0)
        self.assertTrue(self.run_batch(query(sequence=9)) is False)
        self.assertEqual(self.calls, [])


if __name__ == '__main__':
    unittest.main()
