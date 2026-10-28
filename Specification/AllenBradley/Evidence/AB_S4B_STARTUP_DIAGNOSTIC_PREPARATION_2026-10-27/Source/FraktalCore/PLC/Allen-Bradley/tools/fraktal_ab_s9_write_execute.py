"""Fixed S9 vector, armed only after owner Verify/download of the V3 mailbox.

Exact serial before every primitive write. The vector changes only the session
timeout through its PLC-validated mailbox and restores it and the known session.
No listener, provisioning, movement, I/O/forces, clock, mode or fault writes.
Keep the owner HMI idle: this is the exclusive supervised fixture writer.
"""
import argparse
import asyncio
import json
import tempfile
import time

import fraktal_ab_access as access
import fraktal_ab_gateway as gw
import fraktal_ab_mailbox as mb
import fraktal_ab_mailbox_frame as frame
import fraktal_ab_phase6_access_execute as users
import fraktal_ab_press_execute as px
import fraktal_ab_projection as projection
from fraktal_ab_s16_execute import _normalize_serial, _success, _value

APP = px.APP


class Interruption(OSError):
    pass


def batch(sequence, duration):
    root = APP.name + '/HmiRequest/'
    return {'writes': [dict(path=root + n, valueType=t, value=v)
                      for n, t, v in [('Kind', 'int32', mb.SET_SESSION_TIMEOUT),
                                      ('DurationMs', 'uint32', duration),
                                      ('Sequence', 'uint32', sequence)]]}


async def vector(read_comm, write_comm, serial, directory, evidence):
    accounts = users.credentials(serial)  # consumed from private fixture, never emitted
    before = projection.read_access(read_comm)
    name = bytes(before['UserBytes'][:before['UserLength']]).decode('ascii')
    owner = next((u for u in accounts.values() if u['user'] == name and u['level'] == before['CurrentLevel']), None)
    if before['LoginBusy'] or (before['CurrentLevel'] and owner is None):
        raise ValueError('original session is not restorable; nothing written')
    original = dict(timeout=before['SessionTimeout'], level=before['CurrentLevel'], user=name)
    evidence['original'] = original
    client = users.Client(read_comm, serial, directory)
    guarded = gw._GuardedConnection(write_comm, serial)
    writer = gw.MailboxWriter(write_comm.IPAddress, write_comm.ProcessorSlot, serial, APP, set_store=object())
    rows = []
    evidence['rows'] = rows
    writes = [0]
    original_write = guarded.Write
    def counted(target, value):
        result = original_write(target, value)
        if _success(result):
            writes[0] += 1
        return result
    guarded.Write = counted

    def primitive(target, value):
        if not _success(guarded.Write(target, value)):
            raise ValueError('S9 primitive write failed: ' + target)

    def check(name, observed, passed):
        rows.append(px.row(name, name.replace('_', ' '), observed, 0, passed))

    def state():
        return projection.read_access(read_comm)

    def sequence():
        value = px.read_scalar(read_comm, mb.request_tag_name(APP) + '.Sequence')
        if value is None:
            raise ValueError('native request sequence did not read')
        return value & 0xffffffff

    def gateway(boundary=None):
        fired = [False]
        class Cut:
            def __getattr__(self, name):
                return getattr(guarded, name)
            def Write(self, target, value):
                reply = guarded.Write(target, value)
                cut = ('payload-before-commit' if target == frame.native_path(APP)
                       else 'commit-before-ack' if target.endswith('.Sequence') else None)
                if boundary == cut and not fired[0]:
                    fired[0] = True
                    raise Interruption('fixed S9 interruption')
                return reply
        def write(payload, mailbox):
            result = writer._write_base(Cut(), payload)
            if boundary == 'ack-before-completion' and not fired[0]:
                fired[0] = True
                raise Interruption('fixed S9 interruption')
            return result
        return gw.Gateway(gw.Station(lambda: projection.read_document(read_comm), cache_ttl=0),
                          write_token='isolated-fixture', write_roots=frozenset({APP.name}), write_fn=write)

    actor = gw._ConnState()
    actor.authenticated = True
    cleanup = {}
    seed = sequence()
    try:
        _answer, held = await client.login(accounts[4])
        if not users.authenticated(held, accounts[4]):
            raise ValueError('fixture administrator did not authenticate')
        for index, boundary in enumerate(('payload-before-commit', 'commit-before-ack', 'ack-before-completion')):
            g = gateway(boundary)
            previous = sequence()
            attempted = (previous + 1) & 0xffffffff
            old_timeout = state()['SessionTimeout']
            duration = 600000 + index * 1000
            try:
                await g._write_batch(actor, batch(attempted, duration))
                raise AssertionError('interruption did not fire')
            except Interruption:
                pass
            # Wait for the controller only after the interruption boundary.
            if boundary != 'payload-before-commit':
                px.await_response(read_comm, attempted, 6)
            timeout = state()['SessionTimeout']
            check(boundary, {'sequence': sequence(), 'timeout': timeout},
                  sequence() == (previous if boundary == 'payload-before-commit' else attempted)
                  and timeout == (old_timeout if boundary == 'payload-before-commit' else duration))
            count = writes[0]
            try:
                await g._write_batch(actor, batch(attempted, duration))
                replay_refused = False
            except gw.WriteRefused:
                replay_refused = True
            check(boundary + '_never_replays', {'nativeWrites': writes[0] - count}, replay_refused and writes[0] == count)
            fresh = (attempted + 1) & 0xffffffff
            # Recreate gateway bookkeeping after the first boundary too: a
            # surviving client burns its attempt even if the process lost it.
            if boundary == 'payload-before-commit':
                g = gateway()
            check(boundary + '_fresh_recovery', {'sequence': fresh},
                  await g._write_batch(actor, batch(fresh, 610000)) and state()['SessionTimeout'] == 610000)
        g = gateway()
        stale = sequence()
        count = writes[0]
        try:
            await g._write_batch(actor, batch(stale, 620000))
            refused = False
        except gw.WriteRefused:
            refused = True
        check('reconnect_stale_inflight_refused', {'nativeWrites': writes[0] - count}, refused and writes[0] == count)
        # Deliberately cross both signed storage and uint32 wrap with a benign
        # timeout command. No private last-sequence or audit counters are written.
        for seq in (0x7fffffff, 0x80000000, 0xffffffff, 0):
            for target, value in mb.command_writes(APP, mb.SET_SESSION_TIMEOUT, seq, DurationMs=630000):
                if not _success(guarded.Write(target, value)):
                    raise ValueError('native wrap write failed')
            answer = px.await_response(read_comm, seq, 6)
            check('uint32_' + str(seq), answer, answer['accepted'] and sequence() == seq)
        # Staged partial frame, deliberately premature commit, and late payload.
        next_seq = (sequence() + 1) & 0xffffffff
        words = frame.encode(APP, dict(Kind=mb.SET_SESSION_TIMEOUT, DurationMs=640000, Sequence=next_seq))
        path = frame.native_path(APP)
        primitive(path + '[0]', words[:-1])
        await asyncio.sleep(.03)
        primitive(mb.request_tag_name(APP) + '.Sequence', frame.signed(next_seq))
        answer = px.await_response(read_comm, next_seq, 6)
        primitive(path, words)
        await asyncio.sleep(.03)
        check('early_commit_and_late_payload_do_not_execute', answer,
              not answer['accepted'] and state()['SessionTimeout'] == 630000)
        fresh = (next_seq + 1) & 0xffffffff
        words = frame.encode(APP, dict(Kind=mb.SET_SESSION_TIMEOUT, DurationMs=650000, Sequence=fresh))
        middle = len(words) // 2
        primitive(path + '[' + str(middle) + ']', words[middle:])
        await asyncio.sleep(.03)
        primitive(path + '[0]', words[:middle])
        await asyncio.sleep(.03)
        primitive(mb.request_tag_name(APP) + '.Sequence', frame.signed(fresh))
        answer = px.await_response(read_comm, fresh, 6)
        check('out_of_order_arguments_commit_last', answer, answer['accepted'] and state()['SessionTimeout'] == 650000)
        empty = _value(read_comm.Read(path, count=frame.word_count(APP)))
        check('consumed_native_frame_is_wiped', {'wordCount': len(empty) if isinstance(empty, list) else 0},
              isinstance(empty, list) and empty == [0] * frame.word_count(APP))
    except Exception as exc:
        evidence['error'] = type(exc).__name__
    finally:
        # Rejoin the original small, forward sequence range with an inert query
        # before using the ordinary client for independent restoration attempts.
        try:
            joined = (seed + 128) & 0xffffffff
            for target, value in mb.command_writes(APP, mb.QUERY_CONFIG, joined):
                if not _success(guarded.Write(target, value)):
                    raise ValueError('rejoin failed')
            cleanup['sequence_rejoined'] = px.await_response(read_comm, joined, 6)['accepted']
        except Exception:
            cleanup['sequence_rejoined'] = False
        client = users.Client(read_comm, serial, directory)
        for label, operation in (
            ('timeout', lambda: client.command(mb.SET_SESSION_TIMEOUT, DurationMs=original['timeout'])),
            ('session', lambda: client.login(owner) if owner else client.command(mb.LOGOUT))):
            try:
                result = await operation()
                cleanup[label] = result[0]['accepted'] if isinstance(result, tuple) else result['accepted']
            except Exception:
                cleanup[label] = False
        try:
            held = state()
            restored = dict(timeout=held['SessionTimeout'], level=held['CurrentLevel'],
                            user=bytes(held['UserBytes'][:held['UserLength']]).decode('ascii'))
        except Exception:
            restored = None
            cleanup['readback'] = False
        evidence.update(restored=restored, cleanup=cleanup,
                        cleanupPassed=all(cleanup.values()) and restored == original,
                        guardedNativeWrites=writes[0], frameProfile=frame.profile(APP))
    evidence['rows'] = rows
    evidence['passed'] = 'error' not in evidence and bool(rows) and all(r['passed'] for r in rows) and evidence['cleanupPassed']


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('target')
    parser.add_argument('--expect-serial', required=True, type=_normalize_serial)
    parser.add_argument('--execute-fixture', action='store_true')
    args = parser.parse_args(argv)
    from pylogix import PLC
    evidence = dict(schema='fraktal.ab.s9-write-vector', schemaVersion=1,
                    target=args.target, serial=args.expect_serial, wrote=False, passed=False)
    with PLC() as read_comm, PLC() as write_comm:
        for comm in (read_comm, write_comm):
            comm.IPAddress = args.target
            comm.ProcessorSlot = 0
        read_comm.ConnectionSize = 4000
        write_comm.ConnectionSize = frame.CONNECTION_SIZE
        _serial, matches = projection.verify_serial(read_comm, args.expect_serial)
        if not matches:
            raise ValueError('controller serial mismatch; nothing written')
        fingerprint = px.fingerprint(read_comm)
        doc = projection.read_document(read_comm)
        unit = px.read_unit(read_comm)
        evidence['fingerprint'] = fingerprint
        evidence['ready'] = fingerprint['passed'] and not unit['Running'] and not unit['Error'] and not doc['truncated']
        if not evidence['ready']:
            raise ValueError('S9 fixture fingerprint/stopped state failed; nothing written')
        if args.execute_fixture:
            evidence['wrote'] = True
            with tempfile.TemporaryDirectory(prefix='FraktalS9-') as directory:
                asyncio.run(vector(read_comm, write_comm, args.expect_serial, directory, evidence))
        else:
            evidence['passed'] = True
    print(json.dumps(evidence, indent=2))
    return 0 if evidence['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
