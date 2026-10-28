"""Guarded Phase 6 item 3 fixture, after owner download and explicit arming.

The parent owns serial/fingerprint, read-only gates and fixture disarm. This
owns the initially anonymous session, policy and one station value. Private
bench PINs are read only from a local fixture file, never put into evidence.
"""
import asyncio
import json
from pathlib import Path
import tempfile
import time

import fraktal_ab_access as access
import fraktal_ab_data_access as data
import fraktal_ab_mailbox as mb
import fraktal_ab_manifest as mf
import fraktal_ab_phase6_sets_execute as sets_fixture
import fraktal_ab_press_execute as px
import fraktal_ab_projection as projection

APP = px.APP
CREDENTIALS = Path('C:/work/fraktal_phase6_access_fixture.json')


def read_rows(comm):
    s = projection.read_access(comm)
    return [px.row('controller_access_contract_present', f'read-only V{access.STATE_SCHEMA} session, twelve gates, anonymous open default',
                   {'schema': s['SchemaVersion'], 'currentLevel': s['CurrentLevel'], 'userLength': s['UserLength'],
                    'required': s['Required'], 'sessionTimeout': s['SessionTimeout'], 'loginTimeoutMs': s['LoginTimeoutMs']}, 0,
                   s['SchemaVersion'] == access.STATE_SCHEMA and s['CurrentLevel'] == 0 and s['UserLength'] == 0
                   and s['LoginTimeoutMs'] == access.login_timeout_ms(APP)
                   and s['Required'] == [0] * 12 and s['SessionTimeout'] == 0 and s['LoginBusy'] == 0)]


def credentials(serial):
    held = json.loads(CREDENTIALS.read_text(encoding='utf-8'))
    if held.get('serial') != serial:
        raise ValueError('local access fixture credentials are for another controller')
    declared = {u.name: u for u in APP.access_users}
    result = {}
    for row in held['users']:
        u = declared.get(row['user'])
        if u is None or u.level != row['level'] or access.pin_hash(bytes.fromhex(u.salt), row['pin'].encode('ascii')).hex() != u.pin_hash:
            raise ValueError('local fixture credentials do not match the committed private registrations')
        result[u.level] = row
    if set(result) != {1, 2, 4}:
        raise ValueError('fixture requires the three declared bench accounts')
    return result


def authenticated(s, account):
    return s['CurrentLevel'] == account['level'] and not s['LoginFailed'] and bytes(s['UserBytes'][:s['UserLength']]).decode('ascii') == account['user']


def class_levels(comm):
    held = projection.read_data_access(comm, policy=True)
    values = data.policy_status(APP, mf.content(APP), held)
    return {values[f'Access/Classes[{i}]/ClassId']: {
                'read': values[f'Access/Classes[{i}]/ReadLevel'],
                'write': values[f'Access/Classes[{i}]/WriteLevel']}
            for i in range(1, values['Access/ClassCount'] + 1)}


class Client(sets_fixture.Client):
    def __init__(self, comm, serial, directory):
        super().__init__(comm, serial, directory)
        self.serial, self.directory = serial, directory
        if not hasattr(self, 'login_timings'):
            self.login_timings = []

    async def login(self, account, pin=None):
        started = time.monotonic()
        answer = await self.command(mb.LOGIN, User=account['user'], Secret=account['pin'] if pin is None else pin)
        consumed_ms = round((time.monotonic() - started) * 1000, 3)
        if not answer['accepted']:
            raise ValueError('controller refused the fixture login request')
        deadline = time.monotonic() + access.login_timeout_ms(APP) / 1000
        while time.monotonic() < deadline:
            state = projection.read_access(self.comm)
            if not state['LoginBusy'] and (state['LoginResultSequence'] & 0xffffffff) == answer['sequence']:
                self.login_timings.append({'sequence': answer['sequence'], 'level': account['level'],
                    'consumedMs': consumed_ms, 'resultMs': round((time.monotonic() - started) * 1000, 3),
                    'authenticated': authenticated(state, account), 'loginFailed': bool(state['LoginFailed'])})
                return answer, state
            await asyncio.sleep(.03)
        raise ValueError('controller login result did not settle')

    def native(self, kind, **arguments):
        # Prove the PLC predicate independent of the gateway. Recreate the
        # local apparatus afterwards so one mailbox sequence owner remains.
        actual, matches = projection.verify_serial(self.comm, self.serial)
        if not matches:
            raise ValueError('serial changed before native fixture request')
        px.seed_sequence(self.comm)
        answer = px.command(self.comm, kind, settle=4, **arguments)
        self.__init__(self.comm, self.serial, self.directory)
        return answer


async def restore(client, original, admin, evidence):
    """Every independent restoration is attempted even if a prior one fails."""
    record = {}
    async def attempt(name, operation):
        try:
            result = await operation()
            record[name] = {'accepted': bool(result.get('accepted', False))}
        except Exception as error:
            record[name] = {'accepted': False, 'error': str(error)}
    async def login_admin():
        answer, s = await client.login(admin)
        return {'accepted': answer['accepted'] and authenticated(s, admin)}
    await attempt('admin_login', login_admin)
    async def stop_timeout():
        return client.native(mb.SET_SESSION_TIMEOUT, DurationMs=0)
    # Immediately after login, before a full snapshot can spend its timeout.
    await attempt('timeout_disabled', stop_timeout)
    for identity, levels in original.get('classes', {}).items():
        for direction, level in levels.items():
            await attempt('class_' + identity + '_' + direction,
                lambda name=identity, n=level, write=direction == 'write': client.command(
                    mb.SET_CLASS_LEVEL, NameValue=name, IntValue=n, BoolValue=int(write)))
    for gate, level in enumerate(original['Required']):
        await attempt('gate_' + str(gate), lambda g=gate, n=level: client.command(mb.SET_ACCESS_LEVEL, IntValue=g, TextValue=str(n)))
    await attempt('station_number', lambda: client.write_config('station.number', original['station.number']))
    for key, value in original.get('values', {}).items():
        await attempt('value_' + key, lambda name=key, n=value: client.write_config(name, n))
    await attempt('timeout', lambda: client.command(mb.SET_SESSION_TIMEOUT, DurationMs=original['SessionTimeout']))
    await attempt('logout', lambda: client.command(mb.LOGOUT))
    held = projection.read_access(client.comm)
    station = sets_fixture.station_values(client.comm)
    evidence['access_restore'] = record
    evidence['access_restored'] = {'Required': held['Required'], 'SessionTimeout': held['SessionTimeout'],
                                   'CurrentLevel': held['CurrentLevel'], 'UserLength': held['UserLength'],
                                   'station.number': station['station.number']}
    if 'classes' in original:
        evidence['access_restored']['classes'] = class_levels(client.comm)
    if 'values' in original:
        evidence['access_restored']['values'] = {key: station[key] for key in original['values']}
    return all(r['accepted'] for r in record.values()) and evidence['access_restored'] == {
        **original, 'CurrentLevel': 0, 'UserLength': 0}


async def fixture(comm, serial, rows, evidence, directory):
    accounts = credentials(serial)
    original_state = projection.read_access(comm)
    original = {'Required': original_state['Required'], 'SessionTimeout': original_state['SessionTimeout'],
                'station.number': sets_fixture.station_values(comm)['station.number'], 'classes': class_levels(comm)}
    evidence['access_original'] = original
    client = Client(comm, serial, directory)
    admin, operator, tech = accounts[4], accounts[1], accounts[2]
    def check(name, description, observed, passed):
        rows.append(px.row(name, description, observed, 0, passed))
    try:
        answer, s = await client.login(admin)
        check('admin_pin_authenticates_on_controller', 'ACK alone is insufficient; published user, level and result agree',
              {'consumed': answer['accepted'], 'level': s['CurrentLevel'], 'loginFailed': s['LoginFailed']}, authenticated(s, admin))
        if not authenticated(s, admin):
            raise ValueError('controller did not authenticate the fixture administrator')
        answer, s = await client.login(admin, pin='intentionally-wrong-fixture-pin')
        check('wrong_pin_consumed_without_replacing_session', 'generic failure preserves prior authenticated user',
              {'consumed': answer['accepted'], 'level': s['CurrentLevel'], 'loginFailed': s['LoginFailed']}, answer['accepted'] and s['LoginFailed'] and s['CurrentLevel'] == 4)
        await client.command(mb.SET_ACCESS_LEVEL, IntValue=access.GATES[mb.WRITE_CONFIG], TextValue='2')
        await client.command(mb.SET_CLASS_LEVEL, NameValue='public', IntValue=2, BoolValue=1)
        await client.command(mb.SET_ACCESS_LEVEL, IntValue=access.GATES[mb.SAVE_CONFIG_SET], TextValue='4')
        await client.command(mb.SET_ACCESS_LEVEL, IntValue=access.GATES[mb.SET_ACCESS_LEVEL], TextValue='4')
        logout = await client.command(mb.LOGOUT)
        logged_out = projection.read_access(comm)
        check('logout_clears_controller_session', 'LOGOUT withdraws the user and level with no pending login',
              {'answer': logout, 'level': logged_out['CurrentLevel'], 'userLength': logged_out['UserLength'],
               'loginBusy': logged_out['LoginBusy']},
              logout['accepted'] and logged_out['CurrentLevel'] == 0 and logged_out['UserLength'] == 0
              and logged_out['LoginBusy'] == 0)
        answer, s = await client.login(operator)
        check('operator_has_its_declared_level', 'a second salted registration gives OPERATOR, not ADMIN',
              {'consumed': answer['accepted'], 'level': s['CurrentLevel']}, authenticated(s, operator))
        before = sets_fixture.station_values(comm)['station.number']
        answer = client.native(mb.WRITE_CONFIG, IntValue=mb.config_ordinal(APP, 'station.number'),
                               BoolValue=before + 1, DurationMs=0, User=admin['user'])
        denied_write = answer.copy()
        after = sets_fixture.station_values(comm)['station.number']
        check('native_mailbox_cannot_spoof_admin', 'the PLC refuses below the value write level; the plant value stays unchanged',
              {'answer': answer, 'before': before, 'after': after}, not answer['accepted'] and after == before
              and answer['diagnosticKey'] == mf.numeric_key(APP, access.DENIED))
        answer = await client.command(mb.SAVE_CONFIG_SET, TextValue='phase6-access-denied', IntValue=1)
        check('set_mutation_rechecks_controller_level', 'OPERATOR cannot save through CONFIG_SET=ADMIN', answer,
              not answer['accepted'] and answer['diagnosticKey'] == mf.numeric_key(APP, access.DENIED))
        answer = await client.command(mb.SET_ACCESS_LEVEL, IntValue=access.GATES[mb.WRITE_CONFIG], TextValue='0')
        check('operator_cannot_lower_locked_policy', 'ACCESS_POLICY=ADMIN is rechecked by the PLC', answer,
              not answer['accepted'] and answer['diagnosticKey'] == mf.numeric_key(APP, access.DENIED))
        await client.command(mb.LOGOUT)
        answer, s = await client.login(tech)
        check('technician_has_its_declared_level', 'the third salted registration gives TECHNICIAN',
              {'consumed': answer['accepted'], 'level': s['CurrentLevel']}, authenticated(s, tech))
        answer = await client.write_config('station.number', before + 1)
        after = sets_fixture.station_values(comm)['station.number']
        check('accepted_authenticated_write_changes_plant', 'DATA_WRITE=TECHNICIAN admits the correct account',
              {'answer': answer, 'value': after}, answer['accepted'] and after == before + 1)
        await client.command(mb.LOGOUT)
        await client.login(admin)
        await client.command(mb.SET_SESSION_TIMEOUT, DurationMs=6000)
        await asyncio.sleep(3)
        accepted = await client.command(mb.SET_MODE, IntValue=px.read_unit(comm)['Mode'])
        await asyncio.sleep(3)
        s = projection.read_access(comm)
        check('accepted_action_rearms_idle_timeout', 'the session survives past its original login deadline',
              {'answer': accepted, 'level': s['CurrentLevel']}, accepted['accepted'] and s['CurrentLevel'] == 4)
        deadline = time.monotonic() + 7
        while time.monotonic() < deadline and projection.read_access(comm)['CurrentLevel']:
            # A targeted background read consumes no operator activity.
            await client.command(mb.RELEASE_ACTION, IntValue=4)
        s = projection.read_access(comm)
        check('background_queries_do_not_keep_session_alive', 'idle timeout clears level and user',
              {'level': s['CurrentLevel'], 'userLength': s['UserLength']}, s['CurrentLevel'] == 0 and s['UserLength'] == 0)
        answer = client.native(mb.SET_ACCESS_LEVEL, IntValue=access.GATES[mb.SET_ACCESS_LEVEL], TextValue='0', User=admin['user'])
        check('expired_session_cannot_edit_policy', 'a claimed user cannot revive expired privilege', answer,
              not answer['accepted'] and answer['diagnosticKey'] == mf.numeric_key(APP, access.DENIED))
        audit = projection.read_access(comm, audit=True)
        slot = next((i for i in range(access.AUDIT_CAPACITY)
                     if audit['Sequence'][i] == denied_write['sequence'] and audit['Kind'][i] == mb.WRITE_CONFIG
                     and not audit['Accepted'][i]), None)
        values = projection.read_document(comm)['values']
        actor = values.get(f'{APP.name}/AlarmLog/Ring[{slot + 1}]/Description', '') if slot is not None else ''
        check('controller_audit_contains_denied_actor_and_action', 'bounded MESSAGE trace records native denial without PINs',
              {'count': audit['Count'], 'sequence': denied_write['sequence'], 'slot': slot, 'description': actor},
              slot is not None and f": {operator['user']} [kind={mb.WRITE_CONFIG}, gate={access.GATES[mb.WRITE_CONFIG]}]" in actor
              and '[value=station.number, required=2]' in actor)
    finally:
        evidence['access_cleanup_passed'] = await restore(client, original, admin, evidence)
        evidence['access_login_timings'] = client.login_timings
    return {'tests': len(rows), 'successful': sum(r['passed'] for r in rows),
            'failed': sum(not r['passed'] for r in rows), 'rows': rows,
            'passed': all(r['passed'] for r in rows) and evidence['access_cleanup_passed']}


def run(comm, serial, settle, rows, evidence):
    # No existing sets are read or touched; the denied SAVE must leave this
    # isolated store empty. No gateway listener or real bearer is created.
    with tempfile.TemporaryDirectory(prefix='FraktalPhase6Access-') as directory:
        return asyncio.run(fixture(comm, serial, rows, evidence, directory))
