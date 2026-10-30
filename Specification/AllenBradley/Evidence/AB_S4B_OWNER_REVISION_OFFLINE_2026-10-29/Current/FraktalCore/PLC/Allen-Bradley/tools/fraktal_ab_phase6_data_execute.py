"""Guarded item 4: data classes, per-value minima and atomic set permissions.

Run only through phase6_execute --data-classes --execute-fixture after the
owner's download. The parent owns target/fingerprint and fixture disarm.
This fixture owns and restores policy/classes, timeout, the anonymous session,
and station.number/calibration. Its set documents live in a disposable isolated directory.
"""
import asyncio
import tempfile

import fraktal_ab_access as access
import fraktal_ab_data_access as data
import fraktal_ab_mailbox as mb
import fraktal_ab_manifest as mf
import fraktal_ab_phase6_access_execute as users
import fraktal_ab_phase6_sets_execute as sets_fixture
import fraktal_ab_press_execute as px
import fraktal_ab_projection as projection

APP = px.APP
COUNTER = 'station.number'
CALIBRATION = 'station.airPressureMinKpa'
BUILTIN = 'station.ramExtendLimitMs'
SET_NAME = 'phase6-data-classes'


def page_entries(comm):
    values = projection.read_document(comm)['values']
    base = APP.name + '/HmiResponse/ConfigPage/'
    result = {}
    for i in range(1, values[base + 'EntryCount'] + 1):
        prefix = base + f'Entries[{i}]/'
        row = {path[len(prefix):]: value for path, value in values.items() if path.startswith(prefix)}
        result[row['WriteKey']] = row
    return result


def read_rows(comm):
    entries = page_entries(comm)
    policy = users.class_levels(comm)
    raised = entries.get(CALIBRATION, {})
    return [px.row('data_class_contract_present', 'two declared classes; the calibration has immutable ENGINEER write minimum',
                   {'classes': policy, 'calibrationClass': raised.get('ClassId'), 'writeLevel': raised.get('WriteLevel')}, 0,
                   set(policy) == {'public', 'commissioning'} and raised.get('ClassId') == 'commissioning'
                   and raised.get('WriteLevel') == 3),
            px.row('data_fixture_starts_anonymous', 'fresh download starts with no authenticated session',
                   {'level': projection.read_access(comm)['CurrentLevel']}, 0, projection.read_access(comm)['CurrentLevel'] == 0)]


async def fixture(comm, serial, rows, evidence, directory):
    accounts = users.credentials(serial)
    admin, operator, tech = accounts[4], accounts[1], accounts[2]
    held = projection.read_access(comm)
    original = {'Required': held['Required'], 'SessionTimeout': held['SessionTimeout'],
                'station.number': sets_fixture.station_values(comm)[COUNTER], 'classes': users.class_levels(comm),
                'values': {CALIBRATION: sets_fixture.station_values(comm)[CALIBRATION]}}
    evidence['data_original'] = original
    client = users.Client(comm, serial, directory)
    def check(name, observed, passed):
        rows.append(px.row(name, name.replace('_', ' '), observed, 0, passed))
    async def command(kind, **arguments):
        answer = await client.command(kind, **arguments)
        if not answer['accepted']:
            raise ValueError('fixture setup/restoration command refused: ' + str(kind))
        return answer
    try:
        _answer, session = await client.login(admin)
        if not users.authenticated(session, admin):
            raise ValueError('data fixture administrator did not authenticate')
        await command(mb.SET_SESSION_TIMEOUT, DurationMs=0)
        for gate, level in ((0, 3), (1, 3), (11, 0), (8, 4)):
            await command(mb.SET_ACCESS_LEVEL, IntValue=gate, TextValue=str(level))
        await command(mb.SET_CLASS_LEVEL, NameValue='public', IntValue=0, BoolValue=0)
        await command(mb.SET_CLASS_LEVEL, NameValue='public', IntValue=1, BoolValue=1)
        await command(mb.SET_CLASS_LEVEL, NameValue='commissioning', IntValue=0, BoolValue=0)
        await command(mb.SET_CLASS_LEVEL, NameValue='commissioning', IntValue=0, BoolValue=1)
        await client.login(operator)
        await command(mb.QUERY_CONFIG, IntValue=0)
        entries = page_entries(comm)
        check('operator_sees_public_value_and_hidden_builtin_metadata',
              {'public': {k: entries[COUNTER][k] for k in ('ClassId', 'ReadLevel', 'WriteLevel', 'Readable', 'ValueText')},
               'builtin': {k: entries[BUILTIN][k] for k in ('ReadLevel', 'Readable', 'ValueText', 'WriteKey')}},
              entries[COUNTER]['Readable'] and entries[COUNTER]['ValueText'] != ''
              and not entries[BUILTIN]['Readable'] and entries[BUILTIN]['ValueText'] == '' and entries[BUILTIN]['ReadLevel'] == 3)
        before = sets_fixture.station_values(comm)
        answer = await client.write_config(COUNTER, before[COUNTER] + 1)
        changed = sets_fixture.station_values(comm)
        check('operator_public_write_changes_actual_value', {'answer': answer, 'value': changed[COUNTER]},
              answer['accepted'] and changed[COUNTER] == before[COUNTER] + 1)
        answer = client.native(mb.WRITE_CONFIG, IntValue=mb.config_ordinal(APP, BUILTIN), BoolValue=before[BUILTIN], User=admin['user'])
        check('claimed_admin_cannot_bypass_builtin_write_level', answer,
              not answer['accepted'] and answer['diagnosticKey'] == mf.numeric_key(APP, access.DENIED)
              and sets_fixture.station_values(comm)[BUILTIN] == before[BUILTIN])
        answer = await client.command(mb.CAPTURE_CONFIG, NameValue='press.recipe.baselineWorkMs', TargetPath=APP.name,
                                      IntValue=mf.config_revision(APP), TextValue='1')
        check('capture_checks_effective_value_write_level', answer,
              not answer['accepted'] and answer['diagnosticKey'] == mf.numeric_key(APP, access.DENIED))
        policy_before = users.class_levels(comm)
        answer = client.native(mb.SET_CLASS_LEVEL, NameValue='public', IntValue=0, BoolValue=1, User=admin['user'])
        check('operator_cannot_lower_class_policy', answer,
              not answer['accepted'] and users.class_levels(comm) == policy_before)
        await client.login(tech)
        answer = client.native(mb.WRITE_CONFIG, IntValue=mb.config_ordinal(APP, CALIBRATION), BoolValue=before[CALIBRATION], User=admin['user'])
        denied_sequence = answer['sequence']
        check('minimum_engineer_level_refuses_technician', answer,
              not answer['accepted'] and answer['diagnosticKey'] == mf.numeric_key(APP, access.DENIED)
              and sets_fixture.station_values(comm)[CALIBRATION] == before[CALIBRATION])
        await client.login(admin)
        await command(mb.SET_CLASS_LEVEL, NameValue='commissioning', IntValue=1, BoolValue=1)
        entries = page_entries(comm)
        check('lower_class_level_cannot_lower_value_minimum', {'effective': entries[CALIBRATION]['WriteLevel']},
              entries[CALIBRATION]['WriteLevel'] == 3)
        candidate = before[CALIBRATION] + 1 if before[CALIBRATION] < 1000 else before[CALIBRATION] - 1
        answer = await client.write_config(CALIBRATION, candidate)
        check('admin_can_write_guarded_value', {'answer': answer, 'value': sets_fixture.station_values(comm)[CALIBRATION]},
              answer['accepted'] and sets_fixture.station_values(comm)[CALIBRATION] == candidate)
        await command(mb.SET_ACCESS_LEVEL, IntValue=1, TextValue='1')
        await client.login(operator)
        answer = await client.command(mb.SAVE_CONFIG_SET, TextValue=SET_NAME, IntValue=1)
        saved_number = sets_fixture.station_values(comm)[COUNTER]
        check('save_uses_config_set_gate_without_read_write_gate', answer, answer['accepted'])
        await client.write_config(COUNTER, saved_number + 1)
        await client.login(tech)
        before_load = sets_fixture.station_values(comm)
        answer = await client.command(mb.LOAD_CONFIG_SET, TextValue=SET_NAME)
        state = client.state.sets.values
        check('set_load_refuses_before_any_value_changes',
              {'answer': answer, 'rejectKey': state.get(APP.name + '/ConfigPersist/LastRejectKey')},
              not answer['accepted'] and answer['diagnosticKey'] == mf.numeric_key(APP, access.DENIED)
              and state.get(APP.name + '/ConfigPersist/LastRejectKey') == CALIBRATION
              and sets_fixture.station_values(comm) == before_load)
        answer = await client.command(mb.EXPORT_CONFIG_SET, TextValue=SET_NAME, IntValue=0)
        state = client.state.sets.values
        check('export_refuses_before_revealing_even_header',
              {'answer': answer, 'rejectKey': state.get(APP.name + '/ConfigPersist/LastRejectKey'),
               'document': state.get(APP.name + '/ConfigSetDocument')},
              not answer['accepted'] and answer['diagnosticKey'] == mf.numeric_key(APP, access.DENIED)
              and state.get(APP.name + '/ConfigSetDocument') == '')
        await client.login(admin)
        answer = await client.command(mb.LOAD_CONFIG_SET, TextValue=SET_NAME)
        check('admin_load_applies_saved_value', {'answer': answer, 'value': sets_fixture.station_values(comm)[COUNTER]},
              answer['accepted'] and sets_fixture.station_values(comm)[COUNTER] == saved_number)
        answer = await client.command(mb.EXPORT_CONFIG_SET, TextValue=SET_NAME, IntValue=0)
        check('admin_export_returns_document', {'answer': answer},
              answer['accepted'] and bool(client.state.sets.values.get(APP.name + '/ConfigSetDocument')))
        audit = projection.read_access(comm, audit=True)
        slot = next((i for i, sequence in enumerate(audit['Sequence']) if sequence == denied_sequence), None)
        description = ''
        if slot is not None:
            _active, ring = projection.read_alarm_log(comm)
            description = access.audit_status(APP, mf.content(APP), audit, ring).get(f'AlarmLog/Ring[{slot + 1}]/Description', '')
        check('data_denial_audit_names_value_level_and_actual_actor',
              {'slot': slot, 'sequence': denied_sequence, 'description': description},
              slot is not None and audit['Key'][slot] == mf.numeric_key(APP, data.DENIED)
              and audit['DataCapability'][slot] == mb.config_ordinal(APP, CALIBRATION)
              and audit['DataRequiredLevel'][slot] == 3 and f": {tech['user']} [kind=" in description
              and '[value=' + CALIBRATION + ', required=3]' in description)
    finally:
        evidence['data_cleanup_passed'] = await users.restore(client, original, admin, evidence)
        evidence['data_login_timings'] = client.login_timings
    return {'tests': len(rows), 'successful': sum(r['passed'] for r in rows),
            'failed': sum(not r['passed'] for r in rows), 'rows': rows,
            'passed': all(r['passed'] for r in rows) and evidence['data_cleanup_passed']}


def run(comm, serial, settle, rows, evidence):
    with tempfile.TemporaryDirectory(prefix='FraktalPhase6Data-') as directory:
        return asyncio.run(fixture(comm, serial, rows, evidence, directory))
