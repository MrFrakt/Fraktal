"""Execute the generated V6.11 host ingress against adversarial host writers."""
from copy import deepcopy
from types import SimpleNamespace
import unittest

import fraktal_ab_canonical_publication as pub
import fraktal_ab_genealogy_s4b_owner_demo as demo
import fraktal_ab_host_service_binding as binding
import fraktal_ab_host_services as host
import fraktal_ab_st_model as st
from test_fraktal_ab_canonical_commands import initial

APP = SimpleNamespace(name='Mixer', task_period_ms=10)
MANIFEST_REVISION = 4242


def dint(value):
    return value - (1 << 32) if value >= 1 << 31 else value


def service_routine():
    """A stand-in service: open on request, accept any body, finish on Final."""
    w, r, s = host.work_tag(APP), host.work_tag(APP) + '.Reply', host.sample_tag(APP)
    return '\n'.join([f'IF {w}.Accept <> 0 THEN', f'IF {s}.JobSequence = 0 THEN',
                      *host.open_job(APP, 3, 29, binding.RESTORE), 'END_IF;',
                      f'IF {s}.Final <> 0 THEN', *host.complete(APP), 'ELSE', *host.advance(APP), 'END_IF;',
                      'END_IF;'])


class HostIngressTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.definitions = {}
        host.augment(APP, cls.definitions, snapshot_count=3)
        cls.scan = st.parse('\n'.join([*host.ingress(APP), service_routine(), *host.finish(APP)]))
        cls.plc_job = st.parse('\n'.join(host.open_job(APP, 1, 29, binding.FETCH)))

    def value(self, kind):
        return initial(self.definitions, kind)

    def setUp(self):
        self.work, self.request = self.value(host.WORK), self.value(host.REQUEST)
        self.copies = 0
        self.tags = {'S:FS': False, host.work_tag(APP): self.work, host.request_tag(APP): self.request,
                     host.sample_tag(APP): self.value(host.REQUEST), host.reply_tag(APP): self.value(host.REPLY),
                     host.commit_tag(APP): 0, pub.header_tag(APP): dict(ConfigRevision=MANIFEST_REVISION)}
        self.plc = st.Controller(self.tags, calls={'CPS': self.cps})
        self.plc.run(self.scan)  # first scan after a download: arm only

    # CPS gives its destination new storage, so read both through the tag table.
    @property
    def reply(self):
        return self.tags[host.reply_tag(APP)]

    @property
    def sample(self):
        return self.tags[host.sample_tag(APP)]

    def cps(self, controller, args):
        if controller.describe(args[1]) == host.reply_tag(APP):
            self.copies += 1
        st.cps_structure(controller, args)

    def chunk(self, sequence, *, job=0, chunk=0, final=0, service=3, operation=29, staged=None, **body):
        # A DINT carries the uint32 bits, exactly as the CIP writer sends them.
        self.request.update(SchemaVersion=1, ManifestRevision=MANIFEST_REVISION,
                            StagedSequence=dint(sequence if staged is None else staged), Service=service,
                            JobSequence=job, Operation=operation, Argument=0, Chunk=chunk, Final=final, Status=1)
        for name, value in body.items():
            self.request['Body'][name] = value
        self.tags[host.commit_tag(APP)] = dint(sequence)

    def step(self):
        self.plc.run(self.scan)
        return self.reply['AckSequence'] & 0xffffffff, self.reply['Accepted'], self.reply['ErrorCode']

    def open_restore(self):
        self.chunk(1, final=0)
        self.assertEqual(self.step(), (1, 1, 0))
        return self.reply['JobSequence']

    def test_download_seeds_the_serial_without_consuming_or_publishing(self):
        self.assertEqual((self.work['Armed'], self.work['Serial'], self.work['New']), (1, 0, 0))
        self.assertEqual(self.copies, 0)
        self.plc.run(self.scan)
        self.assertEqual(self.copies, 0, 'an idle scan publishes nothing')

    def test_a_host_opens_a_job_and_streams_chunks_in_order_to_completion(self):
        job = self.open_restore()
        self.assertGreater(job, 0)
        self.assertEqual((self.reply['JobService'], self.reply['JobPhase'], self.reply['NextChunk']), (3, 5, 1))
        self.assertEqual(binding.next_sequence(self.reply), 2)
        self.chunk(2, job=job, chunk=1)
        self.assertEqual(self.step(), (2, 1, 0))
        self.chunk(3, job=job, chunk=2, final=1)
        self.assertEqual(self.step(), (3, 1, 0))
        self.assertEqual((self.reply['JobSequence'], self.work['Outcome']), (0, host.COMPLETED))

    def test_a_replayed_or_behind_commit_is_stale_and_its_payload_is_never_sampled(self):
        job = self.open_restore()
        before = deepcopy(self.sample)
        # Rewriting the value the PLC last saw is not a new commit at all.
        self.chunk(1, job=job, chunk=1)
        self.assertEqual((self.step(), self.copies), ((1, 1, 0), 1))
        # Each later value differs from the last one seen, and none is ahead.
        for stale in (0, 1, (1 << 32) - 5, 1 + (1 << 31)):
            self.chunk(stale, job=job, chunk=1)
            self.assertEqual(self.step(), (stale, 0, binding.STALE_SERIAL))
            self.assertEqual(self.sample, before)
            self.assertEqual((self.work['Serial'], self.reply['Serial']), (1, 1))
        self.assertEqual(self.reply['JobSequence'], job, 'an unsampled write claims nothing')
        self.assertEqual(binding.next_sequence(self.reply), 2, 'a writer advances from Serial, not the refusal')

    def test_the_serial_wraps_through_uint32_and_publishes_the_writer_position(self):
        # The furthest a writer may step is just under half the circle.
        for sequence in ((1 << 31) - 1, (1 << 32) - 2, (1 << 32) - 1):
            self.chunk(sequence, final=1)
            self.assertEqual(self.step(), (sequence, 1, 0))
        self.assertEqual(binding.next_sequence(self.reply), 0)
        self.chunk(0, final=1)
        self.assertEqual(self.step(), (0, 1, 0))
        self.chunk(1 << 31, final=1)
        self.assertEqual(self.step()[2], binding.STALE_SERIAL, 'exactly half the circle is not ahead')

    def test_payload_commit_disagreement_is_a_collision_and_abandons_the_claimed_job(self):
        job = self.open_restore()
        self.chunk(2, job=job, chunk=1, staged=3)
        self.assertEqual(self.step(), (2, 0, binding.COLLIDED))
        self.assertEqual((self.reply['JobSequence'], self.work['Outcome']), (0, host.ABANDONED))

    def test_a_commit_written_while_the_payload_is_copied_is_a_collision(self):
        job = self.open_restore()
        self.chunk(2, job=job, chunk=1)

        def racing(controller, args):
            self.cps(controller, args)
            if controller.describe(args[1]) == host.sample_tag(APP):
                self.tags[host.commit_tag(APP)] = 3  # a second writer's commit lands mid-scan
        self.plc.calls['CPS'] = racing
        self.assertEqual(self.step(), (2, 0, binding.COLLIDED))
        self.assertEqual(self.reply['JobSequence'], 0)

    def test_a_stale_manifest_revision_is_refused_by_its_own_code(self):
        self.chunk(1)
        self.request['ManifestRevision'] = MANIFEST_REVISION + 1
        self.assertEqual(self.step(), (1, 0, binding.STALE_REVISION))
        self.assertEqual(self.reply['JobSequence'], 0)

    def test_out_of_bounds_fields_and_key_extents_refuse_before_any_service_runs(self):
        cases = [dict(final=2), dict(Kind=5), dict(Count=65), dict(Total=-1)]
        for index, case in enumerate(cases, 1):
            body = {k: v for k, v in case.items() if k[0].isupper()}
            self.chunk(index, final=case.get('final', 0), **body)
            self.assertEqual(self.step(), (index, 0, binding.INVALID), case)
            self.assertEqual(self.reply['JobSequence'], 0)
            self.request['Body'].update(Kind=0, Count=0, Total=0)
        for name, width in (('Line', 480), ('Scope', 80)):
            self.request['Body'][name]['LEN'] = width + 1
            self.chunk(len(cases) + 1)
            self.assertEqual(self.step()[2], binding.INVALID, name)
            self.request['Body'][name]['LEN'] = 0
            cases.append(name)
        job_commit = len(cases) + 1
        self.chunk(job_commit)
        self.assertEqual(self.step()[1], 1)
        job = self.reply['JobSequence']
        self.request['Body']['Keys'][7]['LEN'] = 161
        self.chunk(job_commit + 1, job=job, chunk=1)
        self.assertEqual(self.step()[2], binding.INVALID)
        self.assertEqual((self.reply['JobSequence'], self.work['Outcome']), (0, host.ABANDONED))

    def test_a_chunk_for_another_job_is_refused_without_touching_the_active_one(self):
        job = self.open_restore()
        self.chunk(2, job=job + 7, chunk=1)
        self.assertEqual(self.step(), (2, 0, binding.NO_JOB))
        self.assertEqual((self.reply['JobSequence'], self.reply['NextChunk']), (job, 1))

    def test_reordered_repeated_or_retargeted_chunks_abandon_the_stream(self):
        for change in (dict(chunk=2), dict(chunk=0), dict(chunk=1, service=1), dict(chunk=1, operation=37)):
            self.setUp()
            job = self.open_restore()
            self.chunk(2, job=job, **change)
            self.assertEqual(self.step(), (2, 0, binding.ORDER), change)
            self.assertEqual((self.reply['JobSequence'], self.work['Outcome']), (0, host.ABANDONED))

    def test_a_second_open_while_a_job_is_active_is_busy_and_not_queued(self):
        job = self.open_restore()
        self.chunk(2)
        self.assertEqual(self.step(), (2, 0, binding.BUSY))
        self.assertEqual(self.reply['JobSequence'], job)
        self.plc.run(self.scan)
        self.assertEqual((self.reply['JobSequence'], self.reply['NextChunk']), (job, 1))

    def test_a_plc_job_is_answered_by_its_published_identity_only(self):
        self.plc.run(self.plc_job)
        self.plc.run(self.scan)
        job = self.reply['JobSequence']
        self.assertEqual((self.reply['JobService'], self.reply['JobPhase']), (1, binding.FETCH))
        self.chunk(1, job=job, service=1, final=1)
        self.assertEqual(self.step(), (1, 1, 0))
        self.assertEqual(self.work['Outcome'], host.COMPLETED)

    def test_an_unanswered_job_times_out_and_clears_its_transported_text(self):
        job = self.open_restore()
        self.work['Reply']['JobText']['LEN'] = 3
        self.work['Reply']['JobText']['DATA'][:3] = [65, 66, 67]
        scans = host.ANSWER_MS // APP.task_period_ms
        for _ in range(scans - 2):
            self.plc.run(self.scan)
        self.assertEqual(self.reply['JobSequence'], job)
        self.plc.run(self.scan)
        self.assertEqual((self.reply['JobSequence'], self.work['Outcome']), (0, host.TIMED_OUT))
        self.assertEqual(self.reply['JobText']['LEN'], 0)
        self.assertFalse(any(self.reply['JobText']['DATA']))
        self.plc.run(self.scan)
        self.assertEqual(self.work['Outcome'], 0, 'an outcome lasts the scan it is set')

    def test_a_first_scan_abandons_the_job_and_still_consumes_a_changed_commit(self):
        job = self.open_restore()
        self.chunk(2, job=job, chunk=1)
        self.tags['S:FS'] = True
        self.assertEqual(self.step(), (2, 0, binding.NO_JOB))
        self.assertEqual(self.work['Outcome'], host.ABANDONED)
        self.tags['S:FS'] = False
        self.assertEqual(binding.next_sequence(self.reply), 3)

    def test_the_reply_is_published_by_one_copy_per_changed_scan(self):
        self.copies = 0
        self.open_restore()
        self.assertEqual(self.copies, 1)
        self.plc.run(self.scan)
        self.assertEqual(self.copies, 1)

    def test_client_outcome_matches_only_its_own_commit(self):
        self.chunk(1)
        self.step()
        self.assertIsNone(binding.outcome(self.reply, 2))
        self.assertEqual(binding.outcome(self.reply, 1), (True, 0))
        broken = dict(self.reply, Accepted=1, ErrorCode=binding.BUSY)
        with self.assertRaisesRegex(ValueError, 'inconsistent'):
            binding.outcome(broken, 1)


class HostRowsTests(unittest.TestCase):
    def test_a_root_advertises_only_the_services_it_serves_on_one_ingress(self):
        app = demo.application()
        rows = host.rows(app)
        self.assertEqual([r['Service'] for r in rows], [1, 2, 3, 4])
        mutating = [r for r in rows if r['Service'] != 4]
        self.assertEqual(len({tuple(r[k] for k in binding.SHARED) for r in mutating}), 1)
        self.assertEqual([r['AccessGate'] for r in rows], [-1, -1, 11, -1])
        self.assertEqual(rows[3]['CanonicalRoot'], 'Press/HostEvents')
        self.assertTrue(all(len(r[k]) <= 40 for r in rows for k in binding.ENDPOINTS))

    def test_the_request_record_fits_its_published_chunk_bound(self):
        definitions = {}
        host.augment(APP, definitions, snapshot_count=64)
        widths = {**binding.TEXTS, 'Keys': binding.KEY_WIDTH}
        chunk = sum(4 * (m.count or 1) if m.kind == 'DINT' else
                    (4 + -(-widths[m.name] // 4) * 4) * (m.count or 1) for m in definitions[host.CHUNK])
        request = chunk + 4 * (len(binding.HEADER) + len(binding.ENVELOPE))
        self.assertLessEqual(request, host.maximum_chunk_bytes())


class BindingTableTests(unittest.TestCase):
    def rows(self):
        return deepcopy(host.rows(demo.application()))

    def test_valid_rows_pass(self):
        self.assertEqual(binding.bindings(self.rows()), self.rows())

    def test_each_rule_refuses(self):
        cases = [
            lambda r: r[0].update(Version=2),
            lambda r: r[0].update(Service=5),
            lambda r: r.append(dict(r[0])),
            lambda r: r[0].update(RequestSymbol=''),
            lambda r: r[0].update(CommitSymbol=r[0]['ReplySymbol']),
            lambda r: r[0].update(ConnectionBytes=499),
            lambda r: r[0].update(MaximumChunkBytes=r[0]['ConnectionBytes'] - 255),
            lambda r: r[0].update(CanonicalRoot='Press/Anything'),
            lambda r: r[0].update(AccessGate=11),
            lambda r: r[2].update(AccessGate=12),
            lambda r: r[1].update(ReplySymbol='OtherReply'),
            lambda r: r[3].update(ReplySymbol='Writable'),
            lambda r: r[3].update(CanonicalRoot='Press/Events'),
            lambda r: r[3].update(AccessGate=0),
            lambda r: r[0].update(Service=True),
            lambda r: r[0].update(RootSymbol=r[0]['RequestSymbol']),
        ]
        for index, mutate in enumerate(cases):
            rows = self.rows()
            mutate(rows)
            with self.assertRaises(ValueError, msg=index):
                binding.bindings(rows)

    def test_endpoints_cannot_be_shared_between_roots(self):
        rows = self.rows()
        other = [dict(r, RootSymbol='Oven', CanonicalRoot='Oven/HostEvents' if r['Service'] == 4 else '')
                 for r in rows]
        with self.assertRaisesRegex(ValueError, 'between roots'):
            binding.bindings(rows + other)


if __name__ == '__main__':
    unittest.main()
