"""Execute the emitted V6.11 configuration-set service against its host answers.

The bench runs the generated typed-ingress and mailbox routines as emitted,
then the canonical response publication's cyclic block, over the generated
tag initializers. A set command parks, the host answers chunk by chunk, and
the command resumes through the unchanged set transaction.
"""
import copy
import dataclasses
import unittest

import fraktal_ab_access as access
import fraktal_ab_canonical_commands as commands
import fraktal_ab_canonical_mailbox as canonical_mailbox
import fraktal_ab_canonical_publication as pub
import fraktal_ab_declaration as decl
import fraktal_ab_document_revision as docrev
import fraktal_ab_generate as gen
import fraktal_ab_genealogy_s4b_owner_demo as demo
import fraktal_ab_host_service_binding as binding
import fraktal_ab_host_services as host
import fraktal_ab_host_sets as host_sets
import fraktal_ab_manifest as mf
import fraktal_ab_mailbox as mb
import fraktal_ab_sets as sets
import fraktal_ab_st_bench as st_bench
import fraktal_ab_st_model as st

CTX = BENCH = APP = None


def application():
    a = demo.application()
    # Live documents off: a commissioned station, not restoring. The keep and
    # restore jobs run in test_fraktal_ab_host_live on the press as declared.
    return dataclasses.replace(a, canonical_host_services=True,
                               config_medium=decl.ConfigMedium(store=a.config_medium.store, live_documents=False))


# The main routine's order, up to the module AOIs the model cannot run. The
# canonical response cyclic follows, as ScanCanonical runs it.
SCAN = ('FRK_Press_ScanCanonicalBegin', 'FRK_Press_ScanAccessStartup', 'FRK_Press_ScanHostClock',
        'FRK_PressHmiFrame', 'FRK_PressHmiMailbox', 'FRK_Press_ScanConfigRestore')


class Context:
    """One generated application on the bench, after a first scan and a login."""

    def __init__(self, app):
        self.app, self.bench = app, st_bench.for_application(app)
        # The response cyclic as emitted inside ScanCanonical: located by its first
        # line, taken at its generated length, so the emitted text is what runs.
        block = gen.format_lines(canonical_mailbox.cyclic(app))
        routine = self.bench.sources['FRK_Press_ScanCanonical']
        assert routine.count(block[0]) == 1
        start = routine.index(block[0])
        self.reply = st.parse('\n'.join(routine[start:start + len(block)]))
        main = [line for line in self.bench.sources[app.routine] if line.startswith('JSR(')]
        assert [line.split('(')[1].split(',')[0] for line in main[:len(SCAN)]] == list(SCAN), main
        # A downloaded controller's first scan, then a logged-in owner.
        self.bench.tags['S:FS'] = True
        for name in SCAN:
            self.bench.run(name)
        self.bench.tags['S:FS'] = False
        state = self.bench.tags[access.tag(app, 'State')]
        state.update(CurrentLevel=4, UserLength=5)
        state['UserBytes'][:5] = list(b'owner')
        self.baseline = copy.deepcopy(self.bench.tags)


def setUpModule():
    global CTX, BENCH, APP
    CTX = Context(application())
    BENCH, APP = CTX.bench, CTX.app


class Station:
    """One downloaded controller, an operator client and a host, scan by scan."""

    def __init__(self, ctx=None):
        self.ctx = ctx or CTX
        self.app, self.bench = self.ctx.app, self.ctx.bench
        self.bench.tags.clear()
        self.bench.tags.update(copy.deepcopy(self.ctx.baseline))
        self.t, self.command_serial, self.host_serial = self.bench.tags, 0, 0
        self.scan(2)
        self.revision = self.t[pub.header_tag(self.app)]['ConfigRevision']

    def scan(self, count=1):
        for _ in range(count):
            for name in SCAN:
                self.bench.run(name)
            # ScanCanonical's LINT arithmetic is outside the model; its header
            # Valid and response cyclic are the parts the reply depends on.
            self.t[pub.header_tag(self.app)]['Valid'] = True
            self.bench.plc.run(self.ctx.reply)

    # -- the operator's typed command -------------------------------------
    def command(self, kind, scans=1, **arguments):
        self.command_serial += 1
        payload = self.t[commands.payload_tag(self.app)]
        payload.update(SchemaVersion=1, ManifestRevision=self.revision, StagedSequence=self.command_serial)
        arguments.setdefault('User', 'owner')
        for name in ('TextValue', 'NameValue'):
            arguments.setdefault(name, '')
        for name, value in dict(arguments, Kind=kind).items():
            if isinstance(value, str):
                self.bench.put(payload['Arguments'][name], value)
            elif isinstance(payload['Arguments'][name], bool):
                payload['Arguments'][name] = bool(value)  # a BOOL member, as a client writes it
            else:
                payload['Arguments'][name] = value
        self.t[commands.commit_tag(self.app)] = self.command_serial
        self.scan(scans)
        return self.command_serial

    @property
    def reply(self):
        return self.t[commands.reply_tag(self.app)]

    @property
    def response(self):
        return self.t[mb.response_tag_name(self.app)]

    def answered(self, sequence):
        return self.reply['AckSequence'] == sequence

    def diagnostic(self):
        return self.bench.text(self.reply['Diagnostic'])

    # -- the host ------------------------------------------------------------
    @property
    def host_reply(self):
        return self.t[host.reply_tag(self.app)]

    @property
    def work(self):
        return self.t[host_sets.work_tag(self.app)]

    def send(self, final=0, status=binding.OK, job=None, chunk=None, service=None, operation=None,
             argument=0, **body):
        """One request write and its commit, then a scan; returns the host reply."""
        published = self.host_reply
        self.host_serial += 1
        request = self.t[host.request_tag(self.app)]
        request.update(SchemaVersion=1, ManifestRevision=self.revision, StagedSequence=self.host_serial,
                       Service=published['JobService'] if service is None else service,
                       Operation=published['JobOperation'] if operation is None else operation,
                       JobSequence=published['JobSequence'] if job is None else job,
                       Argument=argument, Chunk=published['NextChunk'] if chunk is None else chunk,
                       Final=final, Status=status)
        target = request['Body']
        target.update(Kind=binding.NONE, Count=0, Total=0)
        for name, value in body.items():
            if name == 'Keys':
                for i, key in enumerate(value):
                    self.bench.put(target['Keys'][i], key)
            elif isinstance(value, str):
                self.bench.put(target[name], value)
            elif isinstance(value, list):
                target[name][:len(value)] = value
            else:
                target[name] = value
        self.t[host.commit_tag(self.app)] = self.host_serial
        self.scan()
        return self.host_reply

    def serve(self, document, *, line=None, scope=None):
        """Answer the published FETCH job with a document, eight records a chunk."""
        header, records = document[0], document[1:]
        answers = [self.send(final=int(not records and line is None), Kind=binding.HEADER_CHUNK,
                             Total=len(records), Scope=header['root'], Name=header['set'], Model=header['model'],
                             SetSchema=header['schema'], ConfigRev=header['configRev'], RecordKind=header['kind'])]
        for start in range(0, len(records), host.RECORDS_PER_CHUNK):
            part = records[start:start + host.RECORDS_PER_CHUNK]
            last = start + host.RECORDS_PER_CHUNK >= len(records)
            answers.append(self.send(
                final=int(last and line is None), Kind=binding.RECORDS, Count=len(part), Total=len(records),
                Scope=scope or part[0]['scope'], Keys=[r['key'] for r in part], Revisions=[r['rev'] for r in part],
                RecordKinds=[r['kind'] for r in part], ValueTypes=[r['type'] for r in part],
                Values=[1 if r['value'] == 'TRUE' else 0 if r['value'] == 'FALSE' else int(r['value']) for r in part]))
        if line is not None:
            answers.append(self.send(final=1, Kind=binding.TEXT, Count=line, Total=len(records),
                                     Line=sets.render_line(document[line])))
        return answers

    def station(self):
        return {m.write_key: self.t[r.name + 'Tag'][m.name] for _o, r, m in gen.editable_values(self.app) if r.station_cfg}

    def persist(self):
        return self.t[gen.config_persist_tag(self.app)]


def changed_station(name='commissioning'):
    """A station document whose every value differs from the downloaded one."""
    def value(_ordinal, _record, member):
        if member.kind == 'boolean':
            return 0 if member.initial else 1
        return member.maximum if member.initial != member.maximum else member.minimum
    return sets.values_document(APP, name, 1, value, '', 1790899200, 0)


def key(portable):
    return portable


class ParkedCommands(unittest.TestCase):
    def test_a_load_parks_without_an_answer_then_applies_what_the_host_fetched(self):
        s = Station()
        before = s.station()
        sequence = s.command(mb.LOAD_CONFIG_SET, TextValue='commissioning')
        # Parked: nothing acknowledged, nothing applied, the job is asked for.
        self.assertFalse(s.answered(sequence))
        self.assertEqual(s.station(), before)
        s.scan()
        published = s.host_reply
        self.assertEqual((published['JobService'], published['JobOperation'], published['JobPhase']),
                         (binding.SERVICES['ConfigSets'], mb.LOAD_CONFIG_SET, binding.FETCH))
        self.assertEqual(BENCH.text(published['JobName']), 'commissioning')
        answers = s.serve(changed_station())
        self.assertTrue(all(a['Accepted'] == 1 and a['ErrorCode'] == 0 for a in answers))
        self.assertTrue(s.answered(sequence))
        self.assertTrue(s.reply['Accepted'])
        expected = {r['key']: (1 if r['value'] == 'TRUE' else 0 if r['value'] == 'FALSE' else int(r['value']))
                    for r in changed_station()[1:]}
        self.assertEqual(s.station(), expected)
        self.assertNotEqual(expected, before)
        audit = s.t[sets.state_tag(APP)]
        self.assertEqual((audit['AuditAccepted'][0], audit['AuditRecords'][0]), (1, len(expected)))
        # The job closed with the answer; its name never outlives it.
        s.scan()
        self.assertEqual((s.host_reply['JobSequence'], s.host_reply['JobName']['LEN']), (0, 0))
        self.assertFalse(any(s.host_reply['JobName']['DATA']))

    def test_the_previous_answer_stays_published_while_a_command_is_parked(self):
        s = Station()
        first = s.command(mb.LOAD_CONFIG_SET, TextValue='commissioning')
        s.scan()
        s.serve(changed_station())
        answer = (copy.deepcopy(s.reply), dict(s.response), s.t[canonical_mailbox.input_tag(APP)]['ResponseRevision'])
        second = s.command(mb.LOAD_CONFIG_SET, TextValue='commissioning')
        s.scan(3)
        self.assertEqual(s.reply, answer[0])
        self.assertEqual(s.response, answer[1])
        self.assertEqual(s.t[canonical_mailbox.input_tag(APP)]['ResponseRevision'], answer[2])
        self.assertTrue(s.answered(first))
        self.assertFalse(s.answered(second))

    def test_a_second_set_command_is_refused_busy_and_the_parked_one_still_runs(self):
        s = Station()
        parked = s.command(mb.LOAD_CONFIG_SET, TextValue='commissioning')
        busy = s.command(mb.DELETE_CONFIG_SET, TextValue='other')
        self.assertTrue(s.answered(busy))
        self.assertFalse(s.reply['Accepted'])
        self.assertEqual(s.diagnostic(), host_sets.BUSY_KEY)
        s.scan()
        s.serve(changed_station())
        self.assertTrue(s.answered(parked))
        self.assertTrue(s.reply['Accepted'])

    def test_other_commands_proceed_while_a_set_is_parked_and_cannot_change_its_arguments(self):
        s = Station()
        parked = s.command(mb.LOAD_CONFIG_SET, TextValue='commissioning')
        mode = s.command(mb.SET_MODE, IntValue=APP.manual_mode, TextValue='not-a-set')
        self.assertTrue(s.answered(mode))
        self.assertTrue(s.reply['Accepted'])
        s.scan()
        s.serve(changed_station())
        self.assertTrue(s.answered(parked))
        self.assertTrue(s.reply['Accepted'])
        self.assertEqual(s.t[mb.request_tag_name(APP)]['Kind'], mb.LOAD_CONFIG_SET)

    def test_a_silent_host_refuses_the_command_within_its_window_and_applies_nothing(self):
        s = Station()
        before = s.station()
        sequence = s.command(mb.LOAD_CONFIG_SET, TextValue='commissioning')
        scans = 0
        while not s.answered(sequence) and scans < 400:
            s.scan()
            scans += 1
        self.assertTrue(s.answered(sequence))
        self.assertLessEqual((scans + 1) * APP.task_period_ms, host_sets.PARK_MS)
        self.assertFalse(s.reply['Accepted'])
        self.assertEqual(s.diagnostic(), host_sets.UNAVAILABLE_KEY)
        self.assertEqual(s.station(), before)
        self.assertEqual(s.work['Parked'], 0)

    def test_a_resume_yields_to_a_command_that_arrives_in_the_same_scan(self):
        s = Station()
        parked = s.command(mb.LOAD_CONFIG_SET, TextValue='commissioning')
        s.scan()
        document = changed_station()
        s.send(Kind=binding.HEADER_CHUNK, Total=len(document) - 1, Scope=APP.name, Name='commissioning',
               SetSchema=1, ConfigRev=document[0]['configRev'], RecordKind=1)
        mode = s.command(mb.SET_MODE, scans=0, IntValue=APP.manual_mode)
        records = document[1:]
        s.send(final=1, Kind=binding.RECORDS, Count=len(records), Total=len(records), Scope=APP.name,
               Keys=[r['key'] for r in records], Revisions=[r['rev'] for r in records],
               RecordKinds=[r['kind'] for r in records], ValueTypes=[r['type'] for r in records],
               Values=[1 if r['value'] == 'TRUE' else 0 if r['value'] == 'FALSE' else int(r['value']) for r in records])
        self.assertTrue(s.answered(mode))
        s.scan()
        self.assertTrue(s.answered(parked))
        self.assertTrue(s.reply['Accepted'])

    def test_a_command_that_could_only_run_after_its_window_is_refused(self):
        s = Station()
        before = s.station()
        parked = s.command(mb.LOAD_CONFIG_SET, TextValue='commissioning')
        s.scan(130)
        document = changed_station()
        records = document[1:]
        s.send(Kind=binding.HEADER_CHUNK, Total=len(records), Scope=APP.name, Name='commissioning',
               SetSchema=1, ConfigRev=document[0]['configRev'], RecordKind=1)
        # The fetch completes just inside the job window, in a scan with a command.
        s.command(mb.SET_MODE, scans=0, IntValue=APP.manual_mode)
        s.send(final=1, Kind=binding.RECORDS, Count=len(records), Total=len(records), Scope=APP.name,
               Keys=[r['key'] for r in records], Revisions=[r['rev'] for r in records],
               RecordKinds=[r['kind'] for r in records], ValueTypes=[r['type'] for r in records],
               Values=[1 if r['value'] == 'TRUE' else 0 if r['value'] == 'FALSE' else int(r['value']) for r in records])
        self.assertFalse(s.answered(parked))
        while s.work['ParkedMs'] < host_sets.PARK_MS:
            s.command(mb.SET_MODE, IntValue=APP.manual_mode)  # one per scan: the resume keeps yielding
        self.assertFalse(s.answered(parked))
        s.scan()
        self.assertTrue(s.answered(parked))
        self.assertEqual(s.diagnostic(), host_sets.UNAVAILABLE_KEY)
        self.assertEqual(s.station(), before)

    def test_a_name_outside_the_ascii_set_refuses_without_asking_the_host(self):
        s = Station()
        sequence = s.command(mb.LOAD_CONFIG_SET, TextValue='comm\xe9')
        self.assertTrue(s.answered(sequence))
        self.assertFalse(s.reply['Accepted'])
        self.assertEqual((s.work['Parked'], s.host_reply['JobSequence']), (0, 0))
        audit = s.t[sets.state_tag(APP)]
        self.assertEqual((audit['AuditCount'], audit['AuditAccepted'][0], audit['AuditNameLength'][0]), (1, 0, 0))

    def test_a_first_scan_refuses_a_parked_command(self):
        s = Station()
        sequence = s.command(mb.LOAD_CONFIG_SET, TextValue='commissioning')
        s.t['S:FS'] = True
        s.scan()
        s.t['S:FS'] = False
        self.assertTrue(s.answered(sequence))
        self.assertEqual(s.diagnostic(), host_sets.UNAVAILABLE_KEY)


class HostAnswers(unittest.TestCase):
    def fetched(self, kind=mb.LOAD_CONFIG_SET, **arguments):
        s = Station()
        arguments.setdefault('TextValue', 'commissioning')
        sequence = s.command(kind, **arguments)
        s.scan()
        return s, sequence

    def test_an_unknown_key_refuses_the_whole_load_and_names_that_record(self):
        s, sequence = self.fetched()
        before = s.station()
        document = changed_station()
        document[-1]['key'] = 'station.notAKey'
        s.serve(document)
        self.assertTrue(s.answered(sequence))
        self.assertFalse(s.reply['Accepted'])
        self.assertEqual(s.station(), before)
        persist = s.t[APP.name]['ConfigPersist']
        self.assertEqual((BENCH.text(persist['LastRejectScope']), BENCH.text(persist['LastRejectKey'])),
                         (APP.name, 'station.notAKey'))
        self.assertEqual(s.t[sets.state_tag(APP)]['RejectIndex'], len(document) - 1)

    def test_a_range_violation_is_named_by_the_controllers_own_key_text(self):
        s, sequence = self.fetched()
        document = changed_station()
        member = next(m for _o, r, m in gen.editable_values(APP) if r.station_cfg and m.kind != 'boolean')
        target = next(r for r in document[1:] if r['key'] == member.write_key)
        target['value'] = str(member.maximum + 1)
        s.serve(document)
        persist = s.t[APP.name]['ConfigPersist']
        self.assertFalse(s.reply['Accepted'])
        self.assertEqual((BENCH.text(persist['LastRejectScope']), BENCH.text(persist['LastRejectKey'])),
                         (APP.name, member.write_key))

    def test_records_of_another_root_resolve_to_nothing_and_refuse(self):
        s, sequence = self.fetched()
        before = s.station()
        s.serve(changed_station(), scope='Other')
        self.assertFalse(s.reply['Accepted'])
        self.assertEqual(s.station(), before)
        self.assertEqual(BENCH.text(s.t[APP.name]['ConfigPersist']['LastRejectScope']), 'Other')

    def test_a_host_that_cannot_serve_has_the_transaction_refuse_and_audit_it(self):
        for status in (binding.REFUSED, binding.UNAVAILABLE, binding.FAILED):
            with self.subTest(status=status):
                s, sequence = self.fetched()
                answer = s.send(final=1, status=status)
                self.assertEqual(answer['Accepted'], 1)
                self.assertTrue(s.answered(sequence))
                self.assertFalse(s.reply['Accepted'])
                audit = s.t[sets.state_tag(APP)]
                self.assertEqual((audit['AuditCount'], audit['AuditAccepted'][0]), (1, 0))
                self.assertEqual(BENCH.text(s.t[APP.name]['ConfigPersist']['LastRejectKey']), 'commissioning')

    def test_a_malformed_stream_is_abandoned_never_half_applied(self):
        cases = {
            'records before the header': lambda s: s.send(Kind=binding.RECORDS, Count=1, Total=1, Scope=APP.name,
                                                          Keys=['station.number'], Values=[5]),
            'a chunk out of order': lambda s: s.send(chunk=3, Kind=binding.HEADER_CHUNK),
            'more records than the header': lambda s: (s.send(Kind=binding.HEADER_CHUNK, Total=1, Scope=APP.name,
                                                              Name='commissioning', SetSchema=1, RecordKind=1),
                                                       s.send(Kind=binding.RECORDS, Count=2, Total=1)),
            'a final chunk before every record': lambda s: s.send(final=1, Kind=binding.HEADER_CHUNK, Total=4,
                                                                  Scope=APP.name, Name='commissioning'),
        }
        for label, act in cases.items():
            with self.subTest(label):
                s, sequence = self.fetched()
                before = s.station()
                act(s)
                self.assertEqual(s.host_reply['ErrorCode'] != 0, True)
                s.scan()
                self.assertTrue(s.answered(sequence))
                self.assertEqual(s.diagnostic(), host_sets.UNAVAILABLE_KEY)
                self.assertEqual(s.station(), before)
                self.assertEqual(s.host_reply['JobSequence'], 0)

    def test_a_host_cannot_open_a_set_job_or_answer_another(self):
        s = Station()
        self.assertEqual(s.send(job=0)['ErrorCode'], binding.NO_JOB)
        s, _sequence = self.fetched()
        self.assertEqual(s.send(job=s.host_reply['JobSequence'] + 7)['ErrorCode'], binding.NO_JOB)

    def test_the_stored_set_must_answer_the_name_asked_for(self):
        for name in ('other', 'commissionin', 'commissioning2'):
            with self.subTest(name=name):
                s, sequence = self.fetched()
                s.serve(changed_station(name))
                self.assertTrue(s.answered(sequence))
                self.assertFalse(s.reply['Accepted'])

    def test_a_document_of_another_root_refuses_and_names_that_root(self):
        s, sequence = self.fetched()
        before = s.station()
        document = changed_station()
        document[0]['root'] = 'Other'
        s.serve(document)
        self.assertTrue(s.answered(sequence))
        self.assertFalse(s.reply['Accepted'])
        self.assertEqual(s.station(), before)
        self.assertEqual(BENCH.text(s.t[APP.name]['ConfigPersist']['LastRejectScope']), 'Other')


class Operations(unittest.TestCase):
    def test_export_validates_the_document_and_publishes_the_requested_line(self):
        s = Station()
        sequence = s.command(mb.EXPORT_CONFIG_SET, TextValue='commissioning', IntValue=2)
        s.scan()
        document = changed_station()
        s.serve(document, line=2)
        self.assertTrue(s.answered(sequence))
        self.assertTrue(s.reply['Accepted'])
        root = s.t[APP.name]
        self.assertEqual(BENCH.text(root['ConfigSetDocument']), sets.render_line(document[2]))
        self.assertEqual((root['ConfigSetDocumentLine'], root['ConfigSetDocumentLines']), (2, len(document) - 1))

    def test_an_export_of_an_invalid_document_publishes_no_line(self):
        s = Station()
        sequence = s.command(mb.EXPORT_CONFIG_SET, TextValue='commissioning', IntValue=1)
        s.scan()
        document = changed_station()
        document[1]['rev'] = 0
        s.serve(document, line=1)
        self.assertTrue(s.answered(sequence))
        self.assertFalse(s.reply['Accepted'])
        root = s.t[APP.name]
        self.assertEqual((root['ConfigSetDocument']['LEN'], root['ConfigSetDocumentLine']), (0, -1))

    def save(self, receipt):
        s = Station()
        sequence = s.command(mb.SAVE_CONFIG_SET, TextValue='commissioning', IntValue=1)
        s.scan()
        s.send(final=1)
        self.assertTrue(s.answered(sequence))
        self.assertTrue(s.reply['Accepted'])
        self.assertEqual(s.persist()['Pending'], 1)
        s.scan()
        job = s.host_reply
        self.assertEqual((job['JobPhase'], job['JobOperation'], BENCH.text(job['JobName'])),
                         (binding.STORE, mb.SAVE_CONFIG_SET, 'commissioning'))
        # The host renders exactly the station values the transaction snapshotted.
        snapshot = {m.write_key: job['Snapshot']['Values'][o - 1]
                    for o, r, m in gen.editable_values(APP) if r.station_cfg}
        self.assertEqual(snapshot, s.station())
        self.assertEqual((job['Snapshot']['Count'], job['Snapshot']['Kind'], job['Snapshot']['Revision']),
                         (len(snapshot), 1, docrev.revision(APP)))
        s.send(final=1, status=receipt)
        s.scan()
        return s

    def test_a_save_stores_the_snapshot_and_its_receipt_settles_persistence(self):
        s = self.save(binding.OK)
        self.assertEqual((s.persist()['Pending'], s.persist()['Failed']), (0, 0))
        self.assertEqual(s.host_reply['JobSequence'], 0)

    def test_a_failed_store_receipt_is_a_persistence_failure(self):
        s = self.save(binding.FAILED)
        self.assertEqual((s.persist()['Pending'], s.persist()['Failed']), (0, 1))

    def test_a_save_into_a_full_store_is_refused(self):
        s = Station()
        sequence = s.command(mb.SAVE_CONFIG_SET, TextValue='fifth', IntValue=1)
        s.scan()
        s.send(final=1, status=binding.REFUSED)
        self.assertTrue(s.answered(sequence))
        self.assertFalse(s.reply['Accepted'])
        self.assertEqual(s.persist()['Pending'], 0)

    def create(self, source):
        import fraktal_ab_models as models
        s = Station()
        count = s.t[models.tag(APP)]['Count']
        sequence = s.command(mb.CREATE_MODEL, TextValue=source[0]['set'], NameValue='M9', BoolValue=1)
        s.scan()
        self.assertEqual(BENCH.text(s.host_reply['JobName']), source[0]['set'])
        s.serve(source)
        self.assertTrue(s.answered(sequence))
        return s, s.t[models.tag(APP)]['Count'] - count

    def test_a_creation_copies_a_model_set(self):
        model = sets.values_document(APP, 'recipe', 0, lambda _o, _r, m: m.initial, APP.models[0].code, 0, 0)
        s, added = self.create(model)
        self.assertTrue(s.reply['Accepted'])
        self.assertEqual(added, 1)

    def test_a_creation_refuses_a_station_set_as_its_source(self):
        s, added = self.create(changed_station())
        self.assertFalse(s.reply['Accepted'])
        self.assertEqual(added, 0)

    def test_every_set_operation_is_published_supported_with_nothing_to_stage(self):
        rows = {row['Kind']: row for row in commands.operations(APP)}
        for kind in sets.SET_KINDS:
            self.assertTrue(rows[kind]['Supported'], kind)
        self.assertFalse(any(row['RequiresSetStage'] for row in rows.values()))


def catalog_entry(name, records=3, kind=1, created=1790899200, synchronized=1, model=''):
    return dict(Kind=binding.CATALOG, Count=records, Scope=APP.name, Name=name, Model=model, SetSchema=1,
                ConfigRev=docrev.revision(APP), RecordKind=kind, CreatedSeconds=created,
                Synchronized=synchronized)


class Listing(unittest.TestCase):
    def listed(self):
        s = Station()
        sequence = s.command(mb.LIST_CONFIG_SETS)
        s.scan()
        job = s.host_reply
        self.assertEqual((job['JobService'], job['JobPhase'], job['JobOperation']),
                         (binding.SERVICES['ConfigProvider'], binding.PRESENT, mb.LIST_CONFIG_SETS))
        return s, sequence

    def catalog(self, s):
        root = s.t[APP.name]
        return root['ConfigSetCount'], [(e['Used'], BENCH.text(e['SetName']), e['RecordCount'], e['Kind'])
                                        for e in root['ConfigSets']]

    def test_a_list_publishes_the_whole_catalog_with_its_answer(self):
        s, sequence = self.listed()
        before = self.catalog(s)
        s.send(Total=2, **catalog_entry('commissioning', records=5))
        self.assertEqual(self.catalog(s), before)  # never a half catalog
        self.assertFalse(s.answered(sequence))
        s.send(final=1, Total=2, **catalog_entry('recipe', records=4, kind=0, model=APP.models[0].code))
        self.assertTrue(s.answered(sequence))
        self.assertTrue(s.reply['Accepted'])
        count, entries = self.catalog(s)
        self.assertEqual(count, 2)
        self.assertEqual(entries[:2], [(True, 'commissioning', 5, 1), (True, 'recipe', 4, 0)])
        self.assertEqual(entries[2:], [(False, '', 0, 0)] * (sets.MAX_SETS - 2))
        entry = s.t[APP.name]['ConfigSets'][1]
        self.assertEqual((BENCH.text(entry['ModelCode']), BENCH.text(entry['RootIdentity']), entry['TimeSynchronized']),
                         (APP.models[0].code, APP.name, True))

    def test_an_empty_store_lists_no_sets(self):
        s, sequence = self.listed()
        s.send(final=1)
        self.assertTrue(s.reply['Accepted'])
        self.assertEqual(self.catalog(s)[0], 0)

    def test_a_malformed_catalog_is_abandoned_and_the_published_one_kept(self):
        cases = {'a repeated name': [catalog_entry('a'), catalog_entry('a')],
                 'a record kind out of range': [catalog_entry('a', kind=3)],
                 'a name outside ASCII': [catalog_entry('caf\xe9')],
                 'more entries than a store holds': [catalog_entry('a')]}
        for label, entries in cases.items():
            with self.subTest(label):
                s, sequence = self.listed()
                before = self.catalog(s)
                total = sets.MAX_SETS + 1 if label.startswith('more') else len(entries)
                for index, entry in enumerate(entries):
                    s.send(final=int(index == len(entries) - 1), Total=total, **entry)
                s.scan()
                self.assertTrue(s.answered(sequence))
                self.assertEqual(s.diagnostic(), host_sets.UNAVAILABLE_KEY)
                self.assertEqual(self.catalog(s), before)

    def test_an_unreadable_store_refuses_the_list_and_audits_it(self):
        s, sequence = self.listed()
        s.send(final=1, status=binding.UNAVAILABLE)
        self.assertTrue(s.answered(sequence))
        self.assertFalse(s.reply['Accepted'])
        audit = s.t[sets.state_tag(APP)]
        self.assertEqual((audit['AuditCount'], audit['AuditKind'][0], audit['AuditAccepted'][0]),
                         (1, mb.LIST_CONFIG_SETS, 0))


class CurrentExport(unittest.TestCase):
    def exported(self):
        s = Station()
        sequence = s.command(mb.EXPORT_CURRENT_CONFIG, TextValue='snapshot', IntValue=1)
        self.assertFalse(s.answered(sequence))
        s.scan()
        return s, sequence

    def test_the_host_renders_the_snapshot_before_the_answer(self):
        s, sequence = self.exported()
        job = s.host_reply
        self.assertEqual((job['JobService'], job['JobPhase'], BENCH.text(job['JobName'])),
                         (binding.SERVICES['ConfigProvider'], binding.PRESENT, 'snapshot'))
        snapshot = {m.write_key: job['Snapshot']['Values'][o - 1]
                    for o, r, m in gen.editable_values(APP) if r.station_cfg}
        self.assertEqual(snapshot, s.station())
        document = sets.values_document(APP, 'snapshot', 1, lambda o, _r, _m: job['Snapshot']['Values'][o - 1],
                                        '', 0, job['Snapshot']['Synchronized'])
        s.send(final=1, Kind=binding.TEXT, Count=0, Total=len(document) - 1, Line=sets.render_line(document[0]))
        self.assertTrue(s.answered(sequence))
        self.assertTrue(s.reply['Accepted'])
        root = s.t[APP.name]
        self.assertEqual(BENCH.text(root['ConfigSetDocument']), sets.render_line(document[0]))
        self.assertEqual((root['ConfigSetDocumentLine'], root['ConfigSetDocumentLines']), (0, len(document) - 1))
        # Audited once, when the command arrived and the snapshot was taken.
        self.assertEqual(s.t[sets.state_tag(APP)]['AuditCount'], 1)

    def test_a_rendering_the_host_cannot_make_is_refused_unavailable(self):
        # A count inside the ingress's bounds, so the controller's own check decides.
        records = sum(1 for _o, r, _m in gen.editable_values(APP) if r.station_cfg)
        for answer in (dict(final=1, status=binding.UNAVAILABLE),
                       dict(final=1, Kind=binding.TEXT, Count=0, Total=records + 1, Line='{}')):
            with self.subTest(answer=answer):
                s, sequence = self.exported()
                s.send(**answer)
                s.scan()
                self.assertTrue(s.answered(sequence))
                self.assertEqual(s.diagnostic(), host_sets.UNAVAILABLE_KEY)
                self.assertEqual(s.t[APP.name]['ConfigSetDocument']['LEN'], 0)

    def test_an_export_the_transaction_refuses_never_asks_the_host(self):
        s = Station()
        sequence = s.command(mb.EXPORT_CURRENT_CONFIG, TextValue='snapshot', IntValue=7)
        self.assertTrue(s.answered(sequence))
        self.assertFalse(s.reply['Accepted'])
        self.assertEqual(s.host_reply['JobSequence'], 0)


class Import(unittest.TestCase):
    def piece(self, s, text, more, commit, name='imported', records=0, status=binding.OK):
        sequence = s.command(mb.IMPORT_CONFIG_SET, TextValue=text, IntValue=more, BoolValue=commit)
        s.scan()
        job = s.host_reply
        self.assertEqual((job['JobPhase'], BENCH.text(job['JobText']), job['JobInt'], job['JobBool']),
                         (binding.FETCH, text, more, commit))
        s.send(final=1, status=status, Kind=binding.HEADER_CHUNK, Name=name, Total=records)
        self.assertTrue(s.answered(sequence))
        return sequence

    def test_pieces_are_answered_by_the_host_and_a_commit_is_stored(self):
        s = Station()
        # Before a header line is complete the broker's placeholder names the import.
        self.piece(s, '{"set":"imported",', 1, 0, name='(import)')
        self.assertTrue(s.reply['Accepted'])
        self.piece(s, '"root":"Press"}', 0, 0)
        self.assertTrue(s.reply['Accepted'])
        self.assertEqual(s.persist()['Pending'], 0)
        self.piece(s, '{"scope":"Press"}', 0, 1, records=1)
        self.assertTrue(s.reply['Accepted'])
        self.assertEqual(s.persist()['Pending'], 1)
        s.scan()
        job = s.host_reply
        self.assertEqual((job['JobPhase'], job['JobOperation'], BENCH.text(job['JobName']), job['JobText']['LEN']),
                         (binding.STORE, mb.IMPORT_CONFIG_SET, 'imported', 0))
        self.assertFalse(any(job['JobText']['DATA']))
        s.send(final=1)
        s.scan()
        self.assertEqual((s.persist()['Pending'], s.persist()['Failed']), (0, 0))

    def test_a_piece_the_host_cannot_parse_is_refused_and_audited_by_name(self):
        s = Station()
        self.piece(s, 'not json', 0, 0, status=binding.REFUSED)
        self.assertFalse(s.reply['Accepted'])
        self.assertEqual(BENCH.text(s.t[APP.name]['ConfigPersist']['LastRejectKey']), 'imported')
        audit = s.t[sets.state_tag(APP)]
        self.assertEqual((audit['AuditKind'][0], audit['AuditAccepted'][0]), (mb.IMPORT_CONFIG_SET, 0))


class Declaration(unittest.TestCase):
    def test_the_opt_in_publishes_v611_with_the_ring_on_its_own_revision(self):
        header = pub.manifest_values(APP)
        self.assertEqual(header['SchemaMinor'], host.MINOR)
        services = {row['Service'] for row in header['HostServiceBindings']}
        self.assertEqual(services, {1, 2, 4})
        ring = [r for r in header['OwnerReadBindings'] if r['CanonicalPrefix'] == APP.name + '/HostEvents']
        self.assertEqual([r['RevisionSymbol'] for r in ring], [host.ring_revision_tag(APP)])

    def test_live_documents_add_their_own_row_under_the_set_gate(self):
        live = dataclasses.replace(demo.application(), canonical_host_services=True)
        self.assertEqual((host.validate(live), host.validate(APP)), ([], []))
        rows = {row['Service']: row for row in host.rows(live)}
        self.assertEqual(set(rows), {1, 2, 3, 4})
        self.assertEqual(rows[binding.SERVICES['LiveDocuments']]['AccessGate'],
                         access.GATES[mb.LOAD_CONFIG_SET])
        self.assertNotIn(binding.SERVICES['LiveDocuments'], {row['Service'] for row in host.rows(APP)})

    def test_without_the_opt_in_nothing_changes(self):
        old = demo.application()
        self.assertEqual(host_sets.routines(old), [])
        self.assertEqual(host.tags(old, None), [])
        self.assertNotIn(host_sets.UNAVAILABLE_KEY, mb.localization_keys(old))
        self.assertEqual(pub.manifest_values(old)['SchemaMinor'], 10)


if __name__ == '__main__':
    unittest.main()
