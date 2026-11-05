"""Execute the emitted V6.11 LiveDocuments jobs: keep and restore, on the bench.

The press as declared keeps live documents, so a downloaded image starts
restoring. A host restores each document through a job of its own, which
resumes as a silent owner pass: the set transaction validates it, the
operator's sequence, acknowledgement and answer do not move, and the verdict
returns on the job. A host keeps each document through a snapshot job, which
an operator's set command preempts.
"""
import copy
import dataclasses
import unittest

import fraktal_ab_access as access
import fraktal_ab_canonical_commands as commands
import fraktal_ab_canonical_mailbox as canonical_mailbox
import fraktal_ab_generate as gen
import fraktal_ab_genealogy_s4b_owner_demo as demo
import fraktal_ab_host_service_binding as binding
import fraktal_ab_host_services as host
import fraktal_ab_host_sets as host_sets
import fraktal_ab_live as live
import fraktal_ab_mailbox as mb
import fraktal_ab_models as models
import fraktal_ab_sets as sets
from test_fraktal_ab_host_sets import Context, Station

CTX = APP = None
DOCUMENTS, SNAPSHOT = binding.SERVICES['LiveDocuments'], binding.SNAPSHOT_PHASE


def setUpModule():
    global CTX, APP
    CTX = Context(dataclasses.replace(demo.application(), canonical_host_services=True))
    APP = CTX.app


def changed(kind, code=''):
    """A live document whose every value differs from the downloaded one."""
    def value(_ordinal, _record, member):
        if member.kind == 'boolean':
            return 0 if member.initial else 1
        return member.maximum if member.initial != member.maximum else member.minimum
    return sets.values_document(APP, live.LIVE_NAME, kind, value, code, 1790899200, 0)


def numbers(document):
    return {r['key']: 1 if r['value'] == 'TRUE' else 0 if r['value'] == 'FALSE' else int(r['value'])
            for r in document[1:]}


class Restore(Station):
    """A station with its host: opens restore and keep jobs, as an adapter would."""

    def __init__(self):
        super().__init__(CTX)

    def restore(self, document, operation=mb.LOAD_CONFIG_SET, argument=0, status=binding.OK):
        """One restore document; returns the verdict (Accepted, key), or the refusal code."""
        header, records = document[0], document[1:]
        opened = self.send(job=0, chunk=0, service=DOCUMENTS, operation=operation, argument=argument,
                           status=status, final=int(not records), Kind=binding.HEADER_CHUNK, Total=len(records),
                           Scope=header['root'], Name=header['set'], Model=header['model'],
                           SetSchema=header['schema'], ConfigRev=header['configRev'], RecordKind=header['kind'])
        if opened['ErrorCode']:
            return opened['ErrorCode']
        for start in range(0, len(records), host.RECORDS_PER_CHUNK):
            part = records[start:start + host.RECORDS_PER_CHUNK]
            self.send(final=int(start + host.RECORDS_PER_CHUNK >= len(records)), Kind=binding.RECORDS,
                      Count=len(part), Total=len(records), Scope=part[0]['scope'], Keys=[r['key'] for r in part],
                      Revisions=[r['rev'] for r in part], RecordKinds=[r['kind'] for r in part],
                      ValueTypes=[r['type'] for r in part], Values=list(numbers([header, *part]).values()))
        self.scan()
        job = self.host_reply
        assert (job['JobService'], job['JobPhase']) == (DOCUMENTS, binding.STORE), job
        verdict = (job['JobBool'], job['JobInt'])
        self.send(final=1)  # the host has read it: close the job
        assert self.host_reply['JobSequence'] == 0
        return verdict

    def keep(self, kind, index=0):
        return self.send(job=0, chunk=0, service=DOCUMENTS, operation=mb.EXPORT_CURRENT_CONFIG,
                         Kind=binding.NONE, RecordKind=kind, Count=index)

    def restoring(self):
        return self.t[gen.station_cfg_record(APP).name + 'Tag']['SchemaVersion'] == 0

    def bank(self, index):
        return {m.write_key: self.t[gen.model_cfg_tag(APP)][index - 1][m.name]
                for _o, r, m in gen.editable_values(APP) if sets.config_kind(r) == 0}

    def answer(self):
        """Everything an operator's client reads of the last command."""
        return (copy.deepcopy(self.reply), dict(self.response),
                self.t[canonical_mailbox.input_tag(APP)]['ResponseRevision'],
                self.t[commands.work_tag(APP)]['OwnerAck'], self.t[commands.work_tag(APP)]['OwnerSequence'])

    def restore_all(self):
        code = APP.models[0].code
        assert self.restore(changed(0, code), argument=1) == (1, 0)
        assert self.restore(changed(1, code), argument=1) == (1, 0)
        self.scan()


class Restoring(unittest.TestCase):
    def test_a_downloaded_image_restores_through_silent_passes_and_answers_no_operator(self):
        s = Restore()
        self.assertTrue(s.restoring())
        self.assertEqual((s.host_reply['Restoring'], s.host_reply['SessionPermits']), (1, 1))
        first = s.command(mb.SET_MODE, IntValue=APP.manual_mode)
        self.assertTrue(s.answered(first))
        answer = s.answer()
        code = APP.models[0].code
        model = changed(0, code)
        self.assertEqual(s.restore(model, argument=1), (1, 0))
        self.assertEqual(s.bank(1), numbers(model))
        self.assertTrue(s.restoring())
        station = changed(1, code)
        self.assertEqual(s.restore(station, argument=1), (1, 0))
        self.assertFalse(s.restoring())
        self.assertEqual(s.station(), numbers(station))
        self.assertEqual(s.answer(), answer)  # no operator sequence, ack or answer moved
        s.scan()
        self.assertEqual(s.host_reply['Restoring'], 0)
        audit = s.t[sets.state_tag(APP)]
        self.assertEqual([audit['AuditSequence'][i] for i in range(2)], [0, 0])
        self.assertEqual([audit['AuditAccepted'][i] for i in range(2)], [1, 1])
        self.assertEqual(s.persist()['RestoreLost'], 0)

    def test_a_lost_document_is_raised_with_the_station_answer(self):
        s = Restore()
        self.assertEqual(s.restore(changed(1, APP.models[0].code), argument=1, status=binding.LOST), (1, 0))
        self.assertFalse(s.restoring())
        self.assertEqual((s.persist()['RestoreLost'], s.persist()['LostModuleId']), (1, 1))

    def test_a_refused_document_returns_its_verdict_and_the_restore_continues(self):
        s = Restore()
        document = changed(1, APP.models[0].code)
        document[1]['rev'] = 0
        accepted, key = s.restore(document, argument=1)
        self.assertEqual(accepted, 0)
        self.assertNotEqual(key, 0)
        self.assertTrue(s.restoring())

    def test_a_model_the_catalog_lost_is_created_under_its_own_code(self):
        s = Restore()
        count = s.t[models.tag(APP)]['Count']
        self.assertEqual(s.restore(changed(0, 'M9'), operation=mb.CREATE_MODEL), (1, 0))
        self.assertEqual(s.t[models.tag(APP)]['Count'], count + 1)

    def test_restore_jobs_open_only_while_restoring_and_under_the_set_gate(self):
        s = Restore()
        state = s.t[access.tag(APP, 'State')]
        state['Required'][access.GATES[mb.LOAD_CONFIG_SET]] = 3
        state['CurrentLevel'] = 1
        s.scan()
        self.assertEqual(s.host_reply['SessionPermits'], 0)
        self.assertEqual(s.restore(changed(1)), binding.ACCESS)
        state['CurrentLevel'] = 4
        s.restore_all()
        self.assertEqual(s.restore(changed(1)), binding.NOT_RESTORING)

    def test_restore_jobs_are_offered_only_to_a_session_that_could_load_every_document(self):
        # S6 session 02: the gate admitted a logged-out session that the line's
        # level-3 values then refused, and a host retried on it every 10 s.
        s = Restore()
        state = s.t[access.tag(APP, 'State')]
        self.assertEqual(state['Required'][access.GATES[mb.LOAD_CONFIG_SET]], 0)
        state['CurrentLevel'] = 0
        s.scan()
        self.assertEqual((s.host_reply['Restoring'], s.host_reply['SessionPermits']), (1, 0))
        self.assertEqual(s.restore(changed(1)), binding.ACCESS)
        state['CurrentLevel'] = 4
        s.scan()
        self.assertEqual(s.host_reply['SessionPermits'], 1)
        s.restore_all()
        self.assertEqual(s.restore(changed(1)), binding.NOT_RESTORING)

    def test_a_parked_operator_command_holds_off_a_restore(self):
        s = Restore()
        s.restore_all()
        s.command(mb.LOAD_CONFIG_SET, TextValue='commissioning')
        self.assertEqual(s.send(job=0, chunk=0, service=DOCUMENTS, operation=mb.LOAD_CONFIG_SET,
                                Kind=binding.HEADER_CHUNK)['ErrorCode'], binding.BUSY)

    def test_a_host_that_stops_mid_document_applies_nothing(self):
        s = Restore()
        before = s.station()
        document = changed(1, APP.models[0].code)
        header = document[0]
        s.send(job=0, chunk=0, service=DOCUMENTS, operation=mb.LOAD_CONFIG_SET, argument=1,
               Kind=binding.HEADER_CHUNK, Total=len(document) - 1, Scope=header['root'], Name=header['set'],
               SetSchema=1, ConfigRev=header['configRev'], RecordKind=1)
        s.scan(160)
        self.assertEqual(s.host_reply['JobSequence'], 0)
        self.assertEqual(s.station(), before)
        self.assertTrue(s.restoring())
        self.assertEqual(s.t[sets.state_tag(APP)]['AuditCount'], 0)  # no transaction ran at all


class Keeping(unittest.TestCase):
    def test_a_keep_job_publishes_one_documents_values_and_its_receipt_settles_the_keep(self):
        s = Restore()
        s.restore_all()
        job = s.keep(1)
        self.assertEqual((job['ErrorCode'], job['JobService'], job['JobPhase']), (0, DOCUMENTS, SNAPSHOT))
        snapshot = job['Snapshot']
        values = {m.write_key: snapshot['Values'][o - 1] for o, r, m in gen.editable_values(APP) if r.station_cfg}
        self.assertEqual(values, s.station())
        self.assertEqual((snapshot['Kind'], snapshot['ModelOrdinal']), (1, s.t[f'FRK_{APP.name}_Unit']['ModelOrdinal']))
        s.send(final=1, status=binding.FAILED)
        self.assertEqual((s.work['KeepFailed'], s.host_reply['JobSequence']), (1, 0))
        s.keep(0, 2)
        values = {m.write_key: s.host_reply['Snapshot']['Values'][o - 1]
                  for o, r, m in gen.editable_values(APP) if sets.config_kind(r) == 0}
        self.assertEqual((values, s.host_reply['Snapshot']['ModelOrdinal']), (s.bank(2), 2))
        s.send(final=1)
        self.assertEqual(s.work['KeepFailed'], 0)

    def test_a_keep_failure_is_published_as_a_persistence_failure(self):
        line = f'{APP.name}.ConfigPersist.Failed := {APP.name}.ConfigPersist.Failed OR ({host_sets.work_tag(APP)}.KeepFailed <> 0);'
        self.assertIn(line, CTX.bench.sources['FRK_Press_ScanCanonical'])

    def test_nothing_is_kept_while_restoring_or_out_of_range(self):
        s = Restore()
        self.assertEqual(s.keep(1)['ErrorCode'], binding.BUSY)
        s.restore_all()
        for kind, index in ((3, 0), (0, 0), (0, len(APP.models) + 1)):
            with self.subTest(kind=kind, index=index):
                self.assertEqual(s.keep(kind, index)['ErrorCode'], binding.INVALID)

    def test_an_operator_set_command_preempts_a_keep_job(self):
        s = Restore()
        s.restore_all()
        kept = s.keep(1)['JobSequence']
        sequence = s.command(mb.LOAD_CONFIG_SET, TextValue='commissioning')
        s.scan()
        self.assertEqual((s.host_reply['JobService'], s.host_reply['JobPhase']), (binding.SERVICES['ConfigSets'], binding.FETCH))
        self.assertEqual(s.send(job=kept, chunk=1, service=DOCUMENTS, operation=mb.EXPORT_CURRENT_CONFIG,
                                final=1)['ErrorCode'], binding.NO_JOB)
        self.assertFalse(s.answered(sequence))


if __name__ == '__main__':
    unittest.main()
