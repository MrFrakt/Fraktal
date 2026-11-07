"""Guarded Phase 6 item 5, invoked only by the explicitly armed parent.

No provisioning, listener, gateway restart, clock or fault-register writes.
The original known session, policy and timeout are restored independently;
the parent restores plant fixture inputs, mode/style and baseline in finally.
"""
import asyncio
import tempfile
import time

import fraktal_ab_access as access
import fraktal_ab_generate as gen
import fraktal_ab_mailbox as mb
import fraktal_ab_manifest as mf
import fraktal_ab_phase6_access_execute as users
import fraktal_ab_press_execute as px
import fraktal_ab_press_parity as parity
import fraktal_ab_projection as projection
import fraktal_ab_shelving as shelf

import fraktal_ab_fixture_reads as views
import fraktal_ab_phase6_sets_execute as sets_fixture

APP = px.APP
STANDING = APP.reasons['CONTROLLER_METRICS_UNAVAILABLE']


class GuardedPLC:
    """Recheck exact target immediately before every primitive fixture write."""
    def __init__(self, comm, serial):
        self._comm, self._serial = comm, serial

    def __getattr__(self, name):
        return getattr(self._comm, name)

    def Write(self, *args, **kwargs):
        _serial, matches = projection.verify_serial(self._comm, self._serial)
        if not matches:
            raise ValueError('controller serial changed before shelving fixture write')
        return self._comm.Write(*args, **kwargs)


def read_alarm_log(comm):
    return views.read_alarm_log(comm, app=APP)


def reason_description(comm, code):
    if not APP.canonical_collapse:
        return projection.reason_description(APP, code)
    active, _ring = read_alarm_log(comm)
    found = set()
    for slot, reason in enumerate(active['ActReasonCode']):
        if reason != code or active['ActState'][slot] == gen.ALARM_CLOSED:
            continue
        prefix = f'{APP.name}/AlarmLog/Active[{slot + 1}]/'
        held = views.values(comm, (prefix + 'ReasonCode', prefix + 'Description'), app=APP)
        if held[prefix + 'ReasonCode'] != code or not held[prefix + 'Description']:
            raise ValueError('active alarm identity changed or has no published description')
        found.add(held[prefix + 'Description'])
    if len(found) != 1:
        raise ValueError('fixture alarm has no unambiguous published description')
    return found.pop()


def public_shelf(comm, active, ring, slot):
    if not APP.canonical_collapse:
        return projection.alarm_log_status(APP, active, ring)[f'AlarmLog/Active[{slot + 1}]/Shelved']
    path = f'{APP.name}/AlarmLog/Active[{slot + 1}]/Shelved'
    return views.values(comm, (path,), app=APP)[path]


def start_report(comm):
    if APP.canonical_collapse:
        return views.surface(comm, 'ReleaseStart', app=APP)
    return px.read_layout(comm, gen.release_report_tag(APP), gen.release_report_members())


def _user(state):
    return bytes(state['UserBytes'][:state['UserLength']]).decode('ascii')


def read_rows(comm):
    active, ring = read_alarm_log(comm)
    state = users.read_access(comm)
    known = not state['CurrentLevel'] or any(u.name == _user(state) and u.level == state['CurrentLevel'] for u in APP.access_users)
    return [px.row('shelving_contract_present', 'V2 active/ring with the registry-shelvable standing metrics event',
                   {'activeSchema': active['SchemaVersion'], 'ringSchema': ring['SchemaVersion'],
                    'standing': STANDING in active['ActReasonCode'], 'shelves': sum(active['ActShelved'])}, 0,
                   active['SchemaVersion'] == gen.ALARM_SCHEMA and ring['SchemaVersion'] == gen.ALARM_SCHEMA
                   and any(code == STANDING and active['ActState'][i] != gen.ALARM_CLOSED for i, code in enumerate(active['ActReasonCode']))
                   and not any(active['ActShelved'][i] for i, state in enumerate(active['ActState']) if state != gen.ALARM_CLOSED)),
            px.row('shelving_session_can_be_restored', 'known owner or anonymous session, no login pending; open bench policy',
                   {'level': state['CurrentLevel'], 'knownSession': known, 'loginBusy': state['LoginBusy'],
                    'required': state['Required'], 'timeout': state['SessionTimeout']}, 0,
                   known and not state['LoginBusy'] and state['Required'] == [0] * 12 and state['SessionTimeout'] == 0)]


async def fixture(comm, serial, settle, rows, evidence, directory):
    with users.Client(comm, serial, directory) as client:
        return await _exercise(client, serial, settle, rows, evidence)


async def _exercise(client, serial, settle, rows, evidence):
    comm = client.comm
    original_records = sets_fixture.read_records(comm) if APP.canonical_collapse else None
    accounts = users.credentials(serial)  # private fixture is consumed, never emitted
    before = users.read_access(comm)
    original = {'Required': before['Required'][:], 'SessionTimeout': before['SessionTimeout'],
                'CurrentLevel': before['CurrentLevel'], 'CurrentUser': _user(before)}
    owner = next((a for a in accounts.values() if a['user'] == original['CurrentUser'] and a['level'] == original['CurrentLevel']), None)
    if original['CurrentLevel'] and owner is None:
        raise ValueError('original session cannot be restored from the private fixture; nothing written')
    evidence['shelving_original'] = original
    admin, operator = accounts[4], accounts[1]
    desc = reason_description(comm, STANDING)
    args = dict(TargetPath=APP.name, TextValue=desc)

    def check(name, observed, passed):
        rows.append(px.row(name, name.replace('_', ' '), observed, 0, passed))

    def current():
        active, ring = read_alarm_log(comm)
        slots = [i for i, code in enumerate(active['ActReasonCode']) if code == STANDING and active['ActState'][i] != gen.ALARM_CLOSED]
        if len(slots) != 1:
            raise ValueError('standing alarm identity is no longer unique')
        return active, ring, slots[0]

    async def command(kind, **arguments):
        answer = await client.command(kind, **arguments)
        if not answer['accepted']:
            raise ValueError('fixture setup/cleanup request refused: ' + str(kind))
        return answer

    cleanup = {}
    try:
        _answer, state = await client.login(admin)
        if not users.authenticated(state, admin):
            raise ValueError('fixture administrator did not authenticate')
        await command(mb.SET_SESSION_TIMEOUT, DurationMs=0)
        await command(mb.SET_ACCESS_LEVEL, IntValue=9, TextValue='4')
        await command(mb.SET_ACCESS_LEVEL, IntValue=7, TextValue='4')
        answer = await client.command(mb.SHELVE_ALARM, DurationMs=60000, **args)
        active, ring, slot = current()
        published_shelved = public_shelf(comm, active, ring, slot)
        check('shelf_changes_published_annunciation_only', {'answer': answer, 'shelved': active['ActShelved'][slot],
              'blocking': active['Blocking'], 'publishedShelved': published_shelved},
              answer['accepted'] and active['ActShelved'][slot] == 1 and active['Blocking'] == 0
              and published_shelved)
        _answer, state = await client.login(operator)
        if not users.authenticated(state, operator):
            raise ValueError('fixture operator did not authenticate')
        for kind in (mb.SHELVE_ALARM, mb.UNSHELVE_ALARM):
            answer = client.native(kind, DurationMs=60000, User=admin['user'], **args)
            active, _ring, slot = current()
            check('native_spoofed_admin_refused_' + str(kind), answer,
                  not answer['accepted'] and answer['diagnosticKey'] == views.numeric_key(comm, access.DENIED, app=APP)
                  and active['ActShelved'][slot] == 1)
        await client.login(admin)
        answer = await client.command(mb.UNSHELVE_ALARM, **args)
        active, _ring, slot = current()
        check('manual_unshelve_restores_annunciation', answer, answer['accepted'] and active['ActShelved'][slot] == 0)
        for name, supplied, key in (
            ('foreign_identity', dict(args, TargetPath='Other'), shelf.IDENTITY),
            ('wrong_description', dict(args, TextValue='std.reason.9999'), shelf.IDENTITY),
            ('zero_duration', args, shelf.REJECTED)):
            answer = client.native(mb.SHELVE_ALARM, DurationMs=0 if name == 'zero_duration' else 60000, **supplied)
            active, _ring, slot = current()
            check(name + '_refused_without_shelf', answer, not answer['accepted']
                  and answer['diagnosticKey'] == views.numeric_key(comm, key, app=APP) and not active['ActShelved'][slot])
        answer = client.native(mb.SHELVE_ALARM, DurationMs=2147483647, **args)
        active, _ring, slot = current()
        check('above_cap_request_is_accepted_as_bounded_shelf', {'answer': answer, 'shelved': active['ActShelved'][slot]},
              answer['accepted'] and active['ActShelved'][slot] == 1)
        await command(mb.UNSHELVE_ALARM, **args)
        started = time.monotonic()
        answer = client.native(mb.SHELVE_ALARM, DurationMs=3000, **args)
        active, _ring, slot = current()
        seen_shelved = bool(active['ActShelved'][slot])
        await command(mb.LOGOUT)
        deadline = started + settle + 3
        while active['ActShelved'][slot] and time.monotonic() < deadline:
            await asyncio.sleep(.03)
            active, _ring, slot = current()
        elapsed = round(time.monotonic() - started, 3)
        audit = users.read_access(comm, audit=True)
        expiry = [i for i, key in enumerate(audit['Key']) if key == views.numeric_key(comm, shelf.UNSHELVED, app=APP)
                  and audit['Sequence'][i] == 0 and audit['UserLength'][i] == 0]
        check('shelf_auto_expires_after_logout_and_logs', {'answer': answer, 'seconds': elapsed, 'expirySlots': expiry},
              answer['accepted'] and seen_shelved and not active['ActShelved'][slot] and 2.5 <= elapsed <= settle + 3 and bool(expiry))
        await client.login(admin)
        # Registry forbids shelving cylinder defects. Prove that refusal with
        # a real adopted simulated-device fault and its still-blocking report.
        parity.select(comm, 'ST')
        px.home(comm, settle)
        px.command(comm, mb.SET_MODE, settle=parity.ack(settle), IntValue=px.MODE_AUTO)
        for tag, value in ((px.PART_PRESENT, 1), (px.AIR_OK, 1), (px.TWO_HAND, 0), (px.FAULT['PartSlide'], 1)):
            if not px.write(comm, tag, value):
                raise ValueError('fixture stimulus write failed')
        px.start_cycle(comm, settle)
        unit, _elapsed = px.await_unit(comm, lambda u: u['Error'] != 0, settle)
        active, _ring = read_alarm_log(comm)
        fault_slot = active['FaultEvt'] - 1
        if unit is None or fault_slot < 0:
            raise ValueError('fixture did not produce an adopted cylinder fault')
        code = active['ActReasonCode'][fault_slot]
        answer = client.native(mb.SHELVE_ALARM, TargetPath=APP.name + '.PartSlide',
                               TextValue=reason_description(comm, code), DurationMs=60000)
        start = client.native(mb.START)
        active, _ring = read_alarm_log(comm)
        report = start_report(comm)
        check('unshelvable_defect_still_blocks_start_and_report', {'shelf': answer, 'start': start, 'reason': code},
              not answer['accepted'] and code == APP.reasons['CYL_NOT_EXTENDED'] and active['Blocking'] == 1
              and not active['ActShelved'][fault_slot] and not start['accepted']
              and views.numeric_key(comm, gen.MANUAL_RESET_KEY, app=APP) in report['Key'][:report['Count']])
        audit = users.read_access(comm, audit=True)
        active, ring = read_alarm_log(comm)
        messages = users.audit_messages(comm, audit)
        check('lifecycle_events_are_controller_history', {'shelves': audit['Key'].count(views.numeric_key(comm, shelf.SHELVED, app=APP)),
              'unshelves': audit['Key'].count(views.numeric_key(comm, shelf.UNSHELVED, app=APP))},
              any(shelf.SHELVED in str(v) for v in messages.values())
              and any(shelf.UNSHELVED in str(v) for v in messages.values()))
    finally:
        try:
            async def attempt(name, operation):
                try:
                    result = await operation()
                    cleanup[name] = {'accepted': bool(result.get('accepted', False))}
                except Exception as error:
                    cleanup[name] = {'accepted': False, 'error': str(error)}
            async def login_admin():
                answer, state = await client.login(admin)
                return {'accepted': answer['accepted'] and users.authenticated(state, admin)}
            await attempt('admin_login', login_admin)
            async def clear_shelf():
                active, _ring, slot = current()
                if not active['ActShelved'][slot]:
                    return {'accepted': True}
                return await client.command(mb.UNSHELVE_ALARM, **args)
            await attempt('unshelve_fixture_alarm', clear_shelf)
            for gate, level in enumerate(original['Required']):
                await attempt('gate_' + str(gate), lambda g=gate, n=level: client.command(mb.SET_ACCESS_LEVEL, IntValue=g, TextValue=str(n)))
            await attempt('timeout', lambda: client.command(mb.SET_SESSION_TIMEOUT, DurationMs=original['SessionTimeout']))
            if owner is None:
                await attempt('original_session', lambda: client.command(mb.LOGOUT))
            else:
                async def restore_owner():
                    answer, state = await client.login(owner)
                    return {'accepted': answer['accepted'] and users.authenticated(state, owner)}
                await attempt('original_session', restore_owner)
            held = users.read_access(comm)
            evidence['shelving_restore'] = cleanup
            evidence['shelving_restored'] = {'Required': held['Required'], 'SessionTimeout': held['SessionTimeout'],
                                             'CurrentLevel': held['CurrentLevel'], 'CurrentUser': _user(held)}
            evidence['shelving_cleanup_passed'] = all(r['accepted'] for r in cleanup.values()) and evidence['shelving_restored'] == original
            evidence['shelving_login_timings'] = client.login_timings
        finally:
            verified = sets_fixture.finish(client, 'shelving', original_records, evidence)
            evidence['shelving_cleanup_passed'] = bool(evidence.get('shelving_cleanup_passed') and verified)
    return {'tests': len(rows), 'successful': sum(r['passed'] for r in rows), 'failed': sum(not r['passed'] for r in rows),
            'rows': rows, 'passed': all(r['passed'] for r in rows) and evidence['shelving_cleanup_passed']}


def run(comm, serial, settle, rows, evidence):
    with tempfile.TemporaryDirectory(prefix='FraktalPhase6Shelf-') as directory:
        return asyncio.run(fixture(comm, serial, settle, rows, evidence, directory))
