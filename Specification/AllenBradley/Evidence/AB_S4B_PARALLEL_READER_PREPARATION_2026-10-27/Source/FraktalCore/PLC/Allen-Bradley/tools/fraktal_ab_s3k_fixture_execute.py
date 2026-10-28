"""Inherited S3k walk plus fixed typed-ingress vectors on local Echo.

The inherited apparatus runs unchanged through the legacy Frame writer, which
S3k now serves through its ingress adapter. The typed vectors use a second
client: its own 4,000-byte connection, the PLC-published command binding and
the generic encoder, never a station map. They write only the typed payload
and its commit, plus the legacy Frame and Sequence for the collision vector.
Every changed value is restored. Credentials are never recorded.
"""
import argparse
import json
import re
import time

import fraktal_ab_canonical_commands as commands
import fraktal_ab_canonical_mailbox as publication
import fraktal_ab_canonical_reader as reader
import fraktal_ab_command_binding as binding
import fraktal_ab_config as config
import fraktal_ab_generate as gen
import fraktal_ab_genealogy_execute as genealogy
import fraktal_ab_genealogy_s3k_demo as candidate
import fraktal_ab_mailbox as mb
import fraktal_ab_mailbox_frame as frame
import fraktal_ab_part_execute as guarded
import fraktal_ab_press_execute as execute
import fraktal_ab_projection as projection
import fraktal_ab_s3b_fixture_execute as observer
import fraktal_ab_s3a_fixture_execute as capture
import fraktal_ab_s3f_fixture_execute as previous
import fraktal_ab_s3k_equivalence as equivalence

SERIAL = '601FC87B'
FOREIGN_ROOT = 'NotThisRoot'
UNKNOWN_KEY = 'fixture.not.a.declared.key'


def authorize(path, pin):
    value = json.loads(path.read_text(encoding='utf-8'))
    if not re.fullmatch(r'[A-F0-9]{64}', pin) or value.get('CurrentOwnerApproved') is not True \
            or value.get('MailboxOrTagWritesAuthorized') is not True or value.get('Serial') != SERIAL \
            or value.get('CanonicalSha256') != pin or value.get('FaultClearAuthorized') is not False \
            or value.get('ClockSetAuthorized') is not False:
        raise guarded.FixtureRefused('current exact-image S3k request-case authorization required')
    return value


def signed(value):
    value &= 0xffffffff
    return value - (1 << 32) if value & 0x80000000 else value


def string_regions(raw, capture_, symbol, names):
    """(LEN, full-width DATA) per argument, from Template offsets, not decoded text."""
    objects, sizes = reader.template_objects(capture_['templates'])
    handle = {s['name']: s for s in capture_['symbols']}[symbol]['handle']
    if len(raw) != sizes[handle]:
        raise ValueError('command payload length differs from its Template')
    outer = {m['name']: m for m in reader.member_table(objects[handle])}
    args = outer['Arguments']
    inner = {m['name']: m for m in reader.member_table(objects[args['handle']])}
    result = {}
    for name in names:
        row = inner[name]
        parts = {m['name']: m for m in reader.member_table(objects[row['handle']])}
        at = args['offset'] + row['offset']
        width = reader.is_string(reader.member_table(objects[row['handle']]))
        start = at + parts['DATA']['offset']
        result[name] = (int.from_bytes(raw[at+parts['LEN']['offset']:at+parts['LEN']['offset']+4], 'little', signed=True),
                        raw[start:start+width])
    return result


def arguments(**supplied):
    value = {n: (False if n == 'BoolValue' else '' if n in binding.WIDTHS else 0) for n in binding.ARGUMENTS}
    unknown = set(supplied) - set(value)
    if unknown:
        raise ValueError(f'not Core command arguments: {sorted(unknown)}')
    value.update(supplied)
    return value


class TypedWriter:
    """A second client with a fixed write surface; the run's guard precedes every write."""

    def __init__(self, run):
        from pylogix import PLC
        self.run, app = run, run.app
        self.plc = PLC('127.0.0.1')
        self.plc.ProcessorSlot, self.plc.SocketTimeout = 0, 5
        self.plc.ConnectionSize = 4000
        # Discovery on this client's own connection: the legacy writer shares
        # the run's connection and resizes it to its 500-byte profile.
        unused, capture_ = reader.read_document(self.plc, expect_serial=run.evidence['serial'])
        self.capture = capture_
        rows = capture_['manifest']['commandBindings']
        run.check(len(rows) == 1, 'exactly one PLC-published command binding required')
        self.descriptor = descriptor = rows[0]
        expected = dict(RootSymbol=app.name, PayloadSymbol=commands.payload_tag(app), CommitSymbol=commands.commit_tag(app),
                        ResponseSymbol=commands.reply_tag(app), StatusSymbol=publication.input_tag(app))
        run.check(all(descriptor[k] == v for k, v in expected.items()), 'published command endpoints differ from the fixture surface')
        self.legacy_frame, self.legacy_commit = frame.native_path(app), mb.request_tag_name(app) + '.Sequence'
        self.allowed = frozenset((descriptor['PayloadSymbol'], descriptor['CommitSymbol'], self.legacy_frame, self.legacy_commit))
        run.check(descriptor['ConnectionBytes'] == self.plc.ConnectionSize, 'published command connection differs')
        self.symbols = {s['name']: s for s in capture_['symbols']}

    def close(self):
        self.plc.Close()

    def send(self, symbol, request):
        self.run.check(symbol in (self.descriptor['PayloadSymbol'], self.descriptor['CommitSymbol']), 'raw write outside the typed surface')
        self.run.comm.guard()
        connected = self.plc.conn.connect()
        self.run.check(bool(connected[0]) and self.plc.ConnectionSize == self.descriptor['ConnectionBytes'],
                       'typed writer needs the PLC-published connection size')
        status, unused = self.plc.conn.send(request)
        self.run.check(status == 0, f'one-packet typed write refused by the controller (status {status})')

    def write(self, pairs):
        """Plain tag writes; one call with several pairs is one multi-service request."""
        self.run.check(all(tag in self.allowed for tag, unused in pairs), 'write outside the typed fixture surface')
        self.run.comm.guard()
        answer = self.plc.Write(pairs) if len(pairs) > 1 else self.plc.Write(*pairs[0])
        answers = answer if isinstance(answer, list) else [answer]
        self.run.check(all(a.Status == 'Success' for a in answers), 'typed fixture write refused')

    def record(self, symbol):
        reply = self.plc.Read(symbol)
        self.run.check(reply.Status == 'Success' and isinstance(reply.Value, (bytes, bytearray)), 'command record read failed')
        return bytes(reply.Value)

    def reply(self):
        symbol = self.descriptor['ResponseSymbol']
        return reader.decode_record(self.record(symbol), self.symbols[symbol]['handle'], self.capture['templates'])

    def serial(self):
        value = execute.read_scalar(self.run.comm, self.descriptor['StatusSymbol'] + '.CoreSerial')
        self.run.check(type(value) is int, 'typed commit serial unavailable')
        return value & 0xffffffff

    def plan(self, sequence, **supplied):
        return binding.write_plan(self.capture, self.descriptor, arguments(**supplied), sequence,
                                  connection_bytes=self.descriptor['ConnectionBytes'])

    def await_reply(self, sequence, timeout=4):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            answer = self.reply()
            if answer['AckSequence'] & 0xffffffff == sequence & 0xffffffff:
                return answer
            time.sleep(.02)
        raise guarded.FixtureRefused(f'no typed acknowledgement of {sequence}')

    def wiped(self):
        regions = string_regions(self.record(self.descriptor['PayloadSymbol']), self.capture,
                                 self.descriptor['PayloadSymbol'], ('Secret', 'TextValue'))
        return all(length == 0 and not any(data) for length, data in regions.values())


def paired_run(destination, *, candidate_factory=None, equivalence_gate=None, base=None):
    parent = previous.paired_run(destination, candidate_factory=candidate_factory or candidate.application,
                                 equivalence_gate=equivalence_gate or equivalence.run, prefix='s3k', base=base)

    class TypedRun(parent):
        def typed_row(self, case, **details):
            self.evidence.setdefault('s3kTypedRows', []).append(dict(case=case, passed=True, **details))

        def legacy_ack(self):
            value = execute.read_scalar(self.comm, mb.response_tag_name(self.app) + '.AckSequence')
            self.check(type(value) is int, 'legacy acknowledgement unavailable')
            return value & 0xffffffff

        def key_text(self, key):
            return key.encode().hex()

        def typed(self, case, kind, *, key=None, commit=None, staged=None, **supplied):
            """One typed request; key=None means accepted. Returns the typed reply."""
            w = self.writer
            legacy_before, serial_before = self.legacy_ack(), w.serial()
            token = (serial_before + 1) & 0xffffffff if commit is None else commit & 0xffffffff
            if staged is not False:
                plan = w.plan((token if staged is None else staged) & 0xffffffff, Kind=kind, **supplied)
                w.send(plan.payload_symbol, plan.payload_request)
            w.send(w.descriptor['CommitSymbol'], w.plan(token, Kind=kind).commit_request)
            answer = w.await_reply(token)
            accepted = key is None
            self.check(answer['Accepted'] is accepted, f'{case}: typed acceptance differs')
            diagnostic = answer['Diagnostic']
            self.check(diagnostic['bytes'] == ('' if accepted else self.key_text(key)), f'{case}: typed refusal reason differs')
            self.check(self.legacy_ack() == legacy_before, f'{case}: typed request moved the legacy acknowledgement')
            self.check(w.wiped(), f'{case}: typed transport Secret/TextValue not wiped across full width')
            self.typed_row(case, kind=kind, token=token, accepted=accepted,
                           refusalKey=key, serialBefore=serial_before, serialAfter=w.serial(), wiped=True)
            return answer

        def restore_configuration(self):
            super().restore_configuration()
            if not self.evidence.get('error') and not getattr(self, '_s3k_vectors_started', False):
                self._s3k_vectors_started = True
                self.writer = TypedWriter(self)
                try:
                    self.typed_vectors()
                finally:
                    self.writer.close()

        def config_revision(self):
            value = execute.read_scalar(self.comm, self.app.name + '.Status.ConfigRev')
            self.check(type(value) is int, 'live capability revision unavailable')
            return value

        def typed_vectors(self):
            w = self.writer
            # Pure queries: accepted, own reply token, legacy ACK untouched.
            self.typed('query_accepted', mb.QUERY_CONFIG, IntValue=0, DurationMs=0)
            report = self.typed('release_report_accepted', mb.RELEASE_START)
            self.check(1 <= report['Report']['Count'] <= publication.CAPACITY or report['Report']['Released'],
                       'typed release reply must carry the owner report')
            self.config_pair('typed_queries')
            # Serial rules: a backward token is stale and its payload is never sampled.
            serial = w.serial()
            self.typed('backward_serial_stale', mb.QUERY_CONFIG, key=commands.STALE, commit=serial - 1, staged=False)
            self.check(w.serial() == serial, 'stale token moved the forward baseline')
            self.typed('staged_sequence_mismatch', mb.QUERY_CONFIG, key=commands.INVALID,
                       commit=serial + 2, staged=serial + 1)
            # PLC-side resolution keeps the owner's named reasons.
            ordinal, record, member = next(v for v in gen.editable_values(self.candidate)
                if v[1].station_cfg and v[2].kind != 'boolean' and v[2].minimum < v[2].maximum)
            revision = self.config_revision()
            self.typed('stale_revision', mb.WRITE_CONFIG, key=config.CAPTURE_REVISION_KEY, TargetPath=self.app.name,
                       NameValue=member.write_key, IntValue=revision ^ 1, TextValue='0')
            self.typed('foreign_root', mb.WRITE_CONFIG, key=mb.TARGET_KEY, TargetPath=FOREIGN_ROOT,
                       NameValue=member.write_key, IntValue=revision, TextValue='0')
            self.typed('unknown_key_refused_by_owner', mb.WRITE_CONFIG, key=mb.CONFIG_KEY_UNKNOWN_KEY,
                       TargetPath=self.app.name, NameValue=UNKNOWN_KEY, IntValue=revision, TextValue='0')
            self.typed('fractional_value_invalid', mb.WRITE_CONFIG, key=commands.INVALID, TargetPath=self.app.name,
                       NameValue=member.write_key, IntValue=revision, TextValue='1.5')
            self.check(self.config_revision() == revision, 'refused writes changed the capability revision')
            # One accepted typed edit, then the exact original returns.
            tag = record.name + 'Tag.' + member.name
            original = execute.read_scalar(self.comm, tag)
            self.check(type(original) is int, 'configuration fixture original unavailable')
            temporary = original + 1 if original < member.maximum else original - 1
            try:
                self.typed('config_write_accepted', mb.WRITE_CONFIG, TargetPath=self.app.name, NameValue=member.write_key,
                           IntValue=revision, TextValue=f' {temporary}.0 ')
                self.check(execute.read_scalar(self.comm, tag) == temporary, 'typed value did not reach the record')
                self.check(self.config_revision() != revision, 'accepted typed edit must change the revision')
            finally:
                if execute.read_scalar(self.comm, tag) != original:
                    try:
                        self.typed('config_write_restored', mb.WRITE_CONFIG, TargetPath=self.app.name, NameValue=member.write_key,
                                   IntValue=self.config_revision(), TextValue=str(original))
                    finally:
                        # The released legacy path restores the original if the typed one could not.
                        if execute.read_scalar(self.comm, tag) != original:
                            super().command(mb.WRITE_CONFIG, **{mb.CONFIG_ORDINAL_MEMBER: ordinal, mb.CONFIG_VALUE_MEMBER: original})
                self.check(execute.read_scalar(self.comm, tag) == original, 'typed configuration edit not restored')
            self.query_page()
            # Typed logout/login: the credential crosses the payload and is wiped.
            try:
                self.typed('logout_accepted', mb.LOGOUT)
                self.check(projection.read_access(self.comm)['CurrentLevel'] == 0, 'typed logout did not end the session')
                self.typed('login_accepted', mb.LOGIN, User=self.account['user'], Secret=self.account['pin'])
                def settled():
                    state = projection.read_access(self.comm)
                    return state is not None and not state['LoginBusy'] and state['CurrentLevel'] == self.account['level']
                self.wait(settled, 'typed login', timeout=15)
            finally:
                if projection.read_access(self.comm)['CurrentLevel'] != self.account['level']:
                    super().login()
            # Legacy ingress after typed: its own ACK advances, the typed reply does not.
            typed_before = w.reply()['AckSequence']
            self.command(mb.RELEASE_START)
            self.check(w.reply()['AckSequence'] == typed_before, 'legacy request moved the typed reply')
            self.typed_row('legacy_after_typed', typedAck=typed_before & 0xffffffff)
            self.collision()
            self.config_pair('typed_vectors_complete')

        def collision(self):
            """Both commits in one multi-service request: refused together or answered in order."""
            w = self.writer
            token = (w.serial() + 1) & 0xffffffff
            plan = w.plan(token, Kind=mb.QUERY_CONFIG)
            w.send(plan.payload_symbol, plan.payload_request)
            previous_legacy = execute.seed_sequence(self.comm)
            self.check(self.legacy_ack() == previous_legacy, 'legacy mailbox unsettled before collision')
            sequence = (previous_legacy + 1) & 0xffffffff
            writes = mb.command_writes(self.app, mb.RELEASE_START, sequence)
            self.check([t for t, unused in writes] == [w.legacy_frame, w.legacy_commit], 'legacy write plan changed')
            w.write([writes[0]])
            w.write([(w.legacy_commit, writes[1][1]), (w.descriptor['CommitSymbol'], signed(token))])
            typed = w.await_reply(token)
            deadline = time.monotonic() + 4
            while self.legacy_ack() != sequence and time.monotonic() < deadline:
                time.sleep(.02)
            self.check(self.legacy_ack() == sequence, 'legacy collision commit was not acknowledged')
            legacy_accepted = bool(execute.read_scalar(self.comm, mb.response_tag_name(self.app) + '.Accepted'))
            legacy_key = execute.read_scalar(self.comm, mb.response_tag_name(self.app) + '.DiagnosticKey')
            import fraktal_ab_manifest as manifest
            if typed['Accepted'] is False and typed['Diagnostic']['bytes'] == self.key_text(commands.COLLISION):
                outcome = 'collision_refused'
                self.check(not legacy_accepted and legacy_key == manifest.numeric_key(self.app, commands.COLLISION),
                           'collision must refuse both ingresses with one reason')
            else:
                outcome = 'sequential'
                self.check(typed['Accepted'] is True and legacy_accepted, 'separately scanned commits must both be answered')
            self.check(w.wiped(), 'collision transport not wiped')
            time.sleep(.5)
            self.check(w.reply()['AckSequence'] & 0xffffffff == token and self.legacy_ack() == sequence,
                       'a collided request was queued or replayed')
            self.typed_row('collision_observed', outcome=outcome, typedToken=token, legacySequence=sequence)

    return TypedRun


def main(argv=None):
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('--authorization-file', type=__import__('pathlib').Path, required=True)
    parser.add_argument('--expect-acd-sha256', required=True)
    known, rest = parser.parse_known_args(argv)
    authorize(known.authorization_file, known.expect_acd_sha256)
    return genealogy.main(rest, run_type_factory=paired_run, schema='fraktal.ab.s3k-genealogy-fixture',
                          expected_declaration='fraktal_ab_genealogy_s3k_demo')


if __name__ == '__main__': raise SystemExit(main())
