#!/usr/bin/env python3
"""Phase 6 item 1 on the press: capture and D5's read-only configuration query.

Serial and fixture first, read-only rows before an explicitly armed fixture.
All requests use the root mailbox, arguments before Sequence; the baseline,
mode and run style are restored in finally, and all fixture inputs cleared.
No gateway listener is started and no credential is read or logged.
"""
from __future__ import annotations
import argparse
import asyncio
import json
from typing import Any

import fraktal_ab_config as config
import fraktal_ab_gateway as gateway
import fraktal_ab_generate as gen
import fraktal_ab_mailbox as mb
import fraktal_ab_manifest as mf
import fraktal_ab_phase5_execute as phase5
import fraktal_ab_press_execute as px
import fraktal_ab_press_parity as parity
import fraktal_ab_projection as projection
from fraktal_ab_s16_execute import _normalize_serial, _status, _success, _value

SCHEMA = 'fraktal.ab.phase6-capture-on-controller'
APP = px.APP
KEY = 'press.recipe.baselineWorkMs'


def configuration(comm):
    return projection.read_records(comm)[APP.records[0].name]


def capture(comm, ack, *, key=KEY, revision=None, scope=None):
    # The same whole-batch translation the browser gateway uses, including
    # the revision carrier; never invent a direct target write for the fixture.
    root = APP.name + '/HmiRequest'
    body = [('Kind', 'int32', mb.CAPTURE_CONFIG), ('TargetPath', 'string', scope or APP.name),
            ('NameValue', 'string', key), ('IntValue', 'int32', mf.config_revision(APP) if revision is None else revision),
            ('BoolValue', 'int32', 999999), ('TextValue', 'string', '999999'),
            ('User', 'string', 'phase6-fixture'), ('Sequence', 'uint32', 0)]
    resolved = mb.resolve_batch(APP, [(root + '/' + m, t, v) for m, t, v in body])
    args = {p.rsplit('/', 1)[-1]: v for p, _t, v in resolved if not p.endswith(('/Kind', '/Sequence'))}
    return px.command(comm, mb.CAPTURE_CONFIG, settle=ack, **args)


def read_rows(comm):
    values = projection.read_document(comm)['values']
    entries = [k for k, v in values.items() if k.endswith('/WriteKey') and v == KEY]
    prefix = entries[0].rsplit('/', 1)[0] if entries else ''
    offered = {'source': values.get(prefix + '/CaptureSource'),
               'canCapture': values.get(prefix + '/CanCapture'),
               'enabled': values.get(APP.name + '/Features/CaptureEnabled')}
    unit = px.read_unit(comm)
    return [px.row('capture_is_registered_beside_its_editable_value',
                   'published source Profiler.LastWork, capturable and enabled', offered, 0,
                   offered == {'source': 'Profiler.LastWork', 'canCapture': True, 'enabled': True}),
            px.row('fixture_starts_stopped', 'the fixture must not interrupt production',
                   {'running': unit['Running'], 'error': unit['Error']}, 0,
                   unit['Running'] == 0 and unit['Error'] == 0)]


async def viewer_rows(comm, serial, ack):
    # Exercise the real gateway route in its read-only posture, pinned to this
    # controller. No server or write root is created. The writer checks serial
    # again immediately before the inert page transaction.
    g = gateway.Gateway(gateway.Station(lambda: projection.read_document(comm), cache_ttl=0),
                        write_fn=gateway.MailboxWriter(comm.IPAddress, 0, serial))
    state = gateway._ConnState()
    responses = []
    async def send(text):
        responses.append(json.loads(text))
    sequence = px.seed_sequence(comm) + 1
    root = APP.name + '/HmiRequest'
    params = {'writes': [{'path': root + '/' + m, 'valueType': t, 'value': v}
                        for m, t, v in [('Kind', 'int32', mb.QUERY_CONFIG), ('IntValue', 'int32', 0),
                                        ('DurationMs', 'uint32', 0), ('Sequence', 'uint32', sequence)]]}
    await g.dispatch(send, state, json.dumps({'protocol': gateway.PROTOCOL, 'id': 1, 'method': 'writeBatch', 'params': params}))
    response = px.await_response(comm, sequence, ack)
    rows = [px.row('read_only_viewer_queries_configuration',
                   'no bearer and no write root: QUERY_CONFIG reaches the page and is acknowledged',
                   {'transport': responses[-1], 'response': response}, 0,
                   responses[-1].get('result') is True and response.get('accepted') is True)]
    params['writes'][0]['value'] = mb.START
    params['writes'][-1]['value'] = sequence + 1
    await g.dispatch(send, state, json.dumps({'protocol': gateway.PROTOCOL, 'id': 2, 'method': 'writeBatch', 'params': params}))
    observed = px.seed_sequence(comm)
    rows.append(px.row('read_only_viewer_cannot_start',
                       'START refused before any controller write; mailbox sequence unchanged',
                       {'transport': responses[-1], 'sequence': observed}, 0,
                       responses[-1].get('ok') is False and observed == sequence))
    return rows


def run(comm, serial, settle, rows):
    ack = parity.ack(settle)
    rows += asyncio.run(viewer_rows(comm, serial, ack))
    px.seed_sequence(comm)
    for tag in (px.PART_PRESENT, px.AIR_OK, px.TWO_HAND):
        px.write(comm, tag, 1)
    px._idle(comm, ack)
    cycle = phase5.auto_cycle(comm, ack, settle)
    work = phase5.profile_raw(comm)['LastWork']
    px._idle(comm, ack)
    px.command(comm, mb.SET_MODE, settle=ack, IntValue=APP.manual_mode)
    answer = capture(comm, ack)
    stored = configuration(comm)['BaselineWorkMs']
    audit = projection.read_config_audit(comm)
    slot = audit['Head'] - 1
    observed = {'cycle': cycle, 'work': work, 'answer': answer, 'stored': stored,
                'audit': {name: audit[name][slot] for name in ('Sequence', 'Kind', 'Value', 'SourceKey', 'Revision')}}
    rows.append(px.row('capture_stores_the_published_machine_value',
                       'last completed cycle WORK, not client candidate 999999, is stored and audited', observed, 0,
                       cycle and work > 0 and answer['accepted'] and stored == work
                       and audit['Value'][slot] == work and audit['Kind'][slot] == mb.CAPTURE_CONFIG
                       and audit['Sequence'][slot] == answer['sequence']
                       and audit['SourceKey'][slot] == mf.numeric_key(APP, 'Profiler.LastWork')))
    before_head = audit['Head']
    for name, args, reason in (
        ('stale_capture_revision', {'revision': mf.config_revision(APP) + 1}, config.CAPTURE_REVISION_KEY),
        ('unregistered_capture', {'key': 'station.number'}, config.CAPTURE_UNAVAILABLE_KEY),
        ('foreign_capture_scope', {'scope': 'Other'}, mb.CONFIG_KEY_UNKNOWN_KEY)):
        answer = capture(comm, ack, **args)
        rows.append(px.row(name, 'refused by name; configuration and accepted-write audit unchanged',
                           answer, 0, not answer['accepted'] and answer['diagnosticKey'] == mf.numeric_key(APP, reason)
                           and configuration(comm)['BaselineWorkMs'] == work
                           and projection.read_config_audit(comm)['Head'] == before_head))
    px.command(comm, mb.SET_MODE, settle=ack, IntValue=px.MODE_AUTO)
    answer = capture(comm, ack)
    rows.append(px.row('capture_requires_setup', 'AUTO is not a capture setup mode', answer, 0,
                       not answer['accepted'] and answer['diagnosticKey'] == mf.numeric_key(APP, config.CAPTURE_SETUP_KEY)))
    px.command(comm, mb.SET_MODE, settle=ack, IntValue=APP.manual_mode)
    px.write(comm, px.AIR_OK, 0)
    px.await_unit(comm, lambda _u: not px.read_module(comm, 'AirPressureMonitor')['OutImm_PressureOk'], settle)
    answer = capture(comm, ack)
    rows.append(px.row('capture_respects_the_release_permissive', 'without air capture is refused', answer, 0,
                       not answer['accepted'] and configuration(comm)['BaselineWorkMs'] == work))
    return {'tests': len(rows), 'successful': sum(r['passed'] for r in rows),
            'failed': sum(not r['passed'] for r in rows), 'rows': rows,
            'passed': all(r['passed'] for r in rows)}


def restore(comm, original, settle, evidence):
    """Attempt every restoration even if an earlier request fails."""
    ack = parity.ack(settle)
    operations = (
        ('air', lambda: px.write(comm, px.AIR_OK, 1)),
        ('idle', lambda: px._idle(comm, ack)),
        ('baseline', lambda: phase5.write_config(comm, KEY, original['baseline'], ack)),
        ('mode', lambda: px.command(comm, mb.SET_MODE, settle=ack, IntValue=original['mode'])),
        ('style', lambda: px.command(comm, mb.SET_RUN_STYLE, settle=ack, IntValue=original['style'])),
    )
    evidence['restore'] = {}
    try:
        for name, operation in operations:
            try:
                result = operation()
                evidence['restore'][name] = result if isinstance(result, dict) else {'accepted': result is not False}
            except Exception as error:
                evidence['restore'][name] = {'accepted': False, 'error': str(error)}
        unit = px.read_unit(comm)
        evidence['restored'] = {'baseline': configuration(comm)['BaselineWorkMs'],
                                'mode': unit['Mode'], 'style': unit['RunStyle']}
    finally:
        evidence['disarm'] = px.disarm(comm)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('target')
    parser.add_argument('--expect-serial', required=True, type=_normalize_serial)
    parser.add_argument('--timeout', type=float, default=15)
    parser.add_argument('--settle', type=float, default=4)
    parser.add_argument('--execute-fixture', action='store_true')
    parser.add_argument('--sets', action='store_true', help='Phase 6 item 2 parameter-set fixture')
    parser.add_argument('--access', action='store_true', help='Phase 6 item 3 controller-user fixture')
    parser.add_argument('--data-classes', action='store_true', help='Phase 6 item 4 per-value permission fixture')
    parser.add_argument('--shelving', action='store_true', help='Phase 6 item 5 alarm-annunciation fixture')
    args = parser.parse_args(argv)
    if sum((args.sets, args.access, args.data_classes, args.shelving)) > 1:
        parser.error('--sets, --access, --data-classes and --shelving are separate fixtures')
    if args.timeout <= 0 or not 0 < args.settle <= 10:
        parser.error('timeout must be positive and settle must be 0..10 seconds')
    from pylogix import PLC
    evidence: dict[str, Any] = {'schema': SCHEMA, 'schema_version': 1, 'target': args.target,
                                'expected_serial': args.expect_serial, 'wrote': False}
    with PLC() as comm:
        comm.IPAddress, comm.SocketTimeout = args.target, args.timeout
        identity = comm.GetModuleProperties(0)
        if not _success(identity):
            evidence['error'] = 'identity read failed: ' + _status(identity)
        else:
            device = _value(identity)
            serial = _normalize_serial(getattr(device, 'SerialNumber', 0))
            evidence['identity'] = {'serial_number': serial, 'product_name': getattr(device, 'ProductName', ''), 'revision': getattr(device, 'Revision', '')}
            evidence['serial_matches'] = serial == args.expect_serial
            if not evidence['serial_matches']:
                evidence['error'] = 'controller serial does not match --expect-serial'
            else:
                evidence['fingerprint'] = px.fingerprint(comm)
                if not evidence['fingerprint']['passed']:
                    evidence['error'] = 'press fingerprint failed; nothing written'
                else:
                    try:
                        rows = read_rows(comm)
                        if args.sets:
                            import fraktal_ab_phase6_sets_execute as set_fixture
                            evidence['schema'] = 'fraktal.ab.phase6-sets-on-controller'
                            rows += set_fixture.read_rows(comm)
                        if args.access:
                            import fraktal_ab_phase6_access_execute as access_fixture
                            evidence['schema'] = 'fraktal.ab.phase6-access-on-controller'
                            rows += access_fixture.read_rows(comm)
                        if args.data_classes:
                            import fraktal_ab_phase6_data_execute as data_fixture
                            evidence['schema'] = 'fraktal.ab.phase6-data-classes-on-controller'
                            rows += data_fixture.read_rows(comm)
                        if args.shelving:
                            import fraktal_ab_phase6_shelving_execute as shelf_fixture
                            evidence['schema'] = 'fraktal.ab.phase6-shelving-on-controller'
                            rows += shelf_fixture.read_rows(comm)
                        evidence['read_only_rows'] = rows.copy()
                        if args.execute_fixture and all(r['passed'] for r in rows):
                            if args.shelving:
                                comm = shelf_fixture.GuardedPLC(comm, serial)
                            original = {'baseline': configuration(comm)['BaselineWorkMs'],
                                        'mode': px.read_unit(comm)['Mode'], 'style': px.read_unit(comm)['RunStyle']}
                            evidence['original'] = original
                            evidence['wrote'] = True
                            evidence['write_surface'] = list(px.WRITABLE) + ['mailbox']
                            if args.sets:
                                evidence['write_surface'] += ['registered StationCfg values', 'isolated fixture set documents']
                            if args.access:
                                evidence['write_surface'] += ['PLC session, access policy, timeout and station.number']
                            if args.data_classes:
                                evidence['write_surface'] += ['PLC session, access/class policy, timeout and registered StationCfg values', 'isolated fixture set documents']
                            if args.shelving:
                                evidence['write_surface'] += ['PLC session, access policy, timeout and alarm-annunciation shelves']
                            try:
                                evidence['result'] = (shelf_fixture.run(comm, serial, args.settle, rows, evidence) if args.shelving else
                                    data_fixture.run(comm, serial, args.settle, rows, evidence) if args.data_classes else
                                    access_fixture.run(comm, serial, args.settle, rows, evidence) if args.access else
                                    set_fixture.run(comm, serial, args.settle, rows, evidence) if args.sets else run(comm, serial, args.settle, rows))
                            finally:
                                restore(comm, original, args.settle, evidence)
                        else:
                            evidence['result'] = {'rows': rows, 'tests': len(rows), 'successful': sum(r['passed'] for r in rows), 'failed': sum(not r['passed'] for r in rows), 'passed': all(r['passed'] for r in rows)}
                    except Exception as error:
                        evidence['error'] = str(error)
    evidence['passed'] = bool(not evidence.get('error') and evidence.get('result', {}).get('passed')
                              and all(s == 'cleared' for s in evidence.get('disarm', {}).values())
                              and (not evidence['wrote'] or (all(r['accepted'] for r in evidence.get('restore', {}).values())
                                   and evidence.get('restored') == evidence['original'])))
    print(json.dumps(evidence, indent=2, sort_keys=True, default=str))
    return 0 if evidence['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
