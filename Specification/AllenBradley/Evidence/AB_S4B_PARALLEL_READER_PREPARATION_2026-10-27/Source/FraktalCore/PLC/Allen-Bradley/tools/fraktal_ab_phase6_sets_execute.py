"""Phase 6 item 2 fixture, invoked by phase6_execute --sets after owner download.

The parent owns serial/fingerprint, explicit arming and final fixture disarm.
This owns its named host documents and restores every station value it touches.
No listener is started, no credentials read, no existing station sets modified.
"""
from __future__ import annotations

import asyncio
import copy
import datetime
from pathlib import Path
import uuid

import fraktal_ab_gateway as gateway
import fraktal_ab_generate as gen
import fraktal_ab_mailbox as mb
import fraktal_ab_manifest as mf
import fraktal_ab_press_execute as px
import fraktal_ab_press_parity as parity
import fraktal_ab_projection as projection
import fraktal_ab_set_broker as broker
import fraktal_ab_sets as sets

APP = px.APP
FIXTURE_NAMES = ('phase6-station', 'phase6-import', 'phase6-reject', 'phase6-model')


def station_values(comm):
    records = projection.read_records(comm)
    return {m.write_key: records[r.name][m.name] for _o, r, m in gen.editable_values(APP) if r.station_cfg}


def read_rows(comm):
    state = broker.read_state(comm, APP)
    persist = projection.read_persist(comm)
    expected = sets.state_version(APP)
    return [px.row('set_controller_contract_is_present', f'V{expected} bounded transaction and restore status read coherently',
                   {'schema': state['SchemaVersion'], 'auditCapacity': len(state['AuditSequence']),
                    'restoreLost': persist['RestoreLost']}, 0,
                   state['SchemaVersion'] == expected and len(state['AuditSequence']) == sets.AUDIT_CAPACITY
                   and persist['RestoreLost'] == 0)]


class Client:
    def __init__(self, comm, serial, directory):
        self.comm = comm
        self.store = sets.FileStore(directory)
        self.writer = gateway.MailboxWriter(comm.IPAddress, comm.ProcessorSlot, serial, set_store=self.store)
        self.gateway = gateway.Gateway(gateway.Station(lambda: projection.read_document(comm), cache_ttl=0),
            write_fn=self.writer, write_token='phase6-local-fixture', write_roots=frozenset({APP.name}))
        self.state = gateway._ConnState()
        self.state.authenticated = True  # named harness, no real credential or listener

    async def command(self, kind, state=None, **arguments):
        sequence = px.seed_sequence(self.comm) + 1
        root = APP.name + '/HmiRequest'
        supplied = dict(Kind=kind, Sequence=sequence, User='phase6-fixture')
        supplied.update(arguments)
        writes = [{'path': root + '/' + n, 'valueType': 'string' if t == mb.STRING_MEMBER else
                   'uint32' if n == 'Sequence' else 'int32',
                   'value': supplied.get(n, '' if t == mb.STRING_MEMBER else 0)}
                  for n, t, *_ in mb.REQUEST_MEMBERS]
        transport = await self.gateway._write_batch(state or self.state, {'writes': writes})
        if not transport:
            raise RuntimeError('set fixture transport refused')
        return px.await_response(self.comm, sequence, 4)

    async def import_document(self, document):
        answer = None
        for row, value in enumerate(document):
            line = sets.render_line(value)
            pieces = [line[n:n + 255] for n in range(0, len(line), 255)]
            for part, text in enumerate(pieces):
                more = part < len(pieces) - 1
                answer = await self.command(mb.IMPORT_CONFIG_SET, TextValue=text, IntValue=1 if more else 0,
                    BoolValue=int(row == len(document) - 1 and not more))
                if not answer['accepted']:
                    return answer
        return answer

    async def idle(self, settle):
        # Reuse the fixture's owning idle recipe, but route every mailbox
        # command through this same gateway so its sequence stays coherent.
        requests = []
        px._idle(self.comm, settle,
                 command_fn=lambda _comm, kind, **arguments: requests.append((kind, arguments)))
        for kind, arguments in requests:
            await self.command(kind, **arguments)

    async def write_config(self, key, value):
        return await self.command(mb.WRITE_CONFIG, TargetPath=APP.name,
            IntValue=mf.config_revision(APP), NameValue=key, TextValue=str(value), DurationMs=0)

    async def export_document(self, name):
        result = []
        total = 0
        for line in range(sets.MAX_RECORDS + 1):
            answer = await self.command(mb.EXPORT_CONFIG_SET, TextValue=name, IntValue=line)
            if not answer['accepted']:
                raise RuntimeError('export refused: ' + str(answer))
            values = self.state.sets.values
            if values[APP.name + '/ConfigSetDocumentLine'] != line:
                raise RuntimeError('export line cursor differs')
            result.append(sets.parse_line(values[APP.name + '/ConfigSetDocument']))
            total = values[APP.name + '/ConfigSetDocumentLines']
            if line == total:
                return result
        raise RuntimeError('export exceeded capacity')


async def exercise(client, settle, rows):
    comm, ack = client.comm, parity.ack(settle)
    original = station_values(comm)
    await client.idle(ack)
    await client.command(mb.SET_MODE, IntValue=APP.manual_mode)
    saved = await client.command(mb.SAVE_CONFIG_SET, TextValue=FIXTURE_NAMES[0], IntValue=1)
    doc = await client.export_document(FIXTURE_NAMES[0])
    rows.append(px.row('save_export_and_reopen_station_set', 'controller snapshot is portable and the host file survives reopen',
                       {'answer': saved, 'header': doc[0]}, 0,
                       saved['accepted'] and sets.FileStore(client.store.directory).read(FIXTURE_NAMES[0]) == doc
                       and doc[0]['records'] == len(original)))
    await client.command(mb.LIST_CONFIG_SETS)
    values = client.state.sets.values
    rows.append(px.row('list_uses_the_generic_hmi_contract', 'one named set with the controller record count',
                       {'count': values[APP.name + '/ConfigSetCount'],
                        'name': values[APP.name + '/ConfigSets[1]/SetName']}, 0,
                       values[APP.name + '/ConfigSetCount'] == 1
                       and values[APP.name + '/ConfigSets[1]/SetName'] == FIXTURE_NAMES[0]))
    first = next(m for _o, r, m in gen.editable_values(APP) if r.station_cfg and m.kind == 'scalar')
    candidate = first.minimum if original[first.write_key] != first.minimum else first.maximum
    await client.write_config(first.write_key, candidate)
    changed = station_values(comm)[first.write_key]
    answer = await client.command(mb.LOAD_CONFIG_SET, TextValue=FIXTURE_NAMES[0])
    rows.append(px.row('load_restores_the_values_not_just_the_ack', 'the altered station value returns to the saved value',
                       {'changed': changed, 'after': station_values(comm), 'answer': answer}, 0,
                       changed == candidate and candidate != original[first.write_key]
                       and answer['accepted'] and station_values(comm) == original))
    copied = copy.deepcopy(doc)
    copied[0]['set'] = FIXTURE_NAMES[1]
    copied[1]['value'] = str(candidate)
    before = station_values(comm)
    answer = await client.import_document(copied)
    rows.append(px.row('import_only_stores_the_document', 'import cannot apply equipment values', answer, 0,
                       answer['accepted'] and station_values(comm) == before))
    answer = await client.command(mb.LOAD_CONFIG_SET, TextValue=FIXTURE_NAMES[1])
    expected = dict(original, **{first.write_key: candidate})
    rows.append(px.row('imported_station_set_loads_atomically', 'load applies the complete imported record set',
                       {'answer': answer, 'values': station_values(comm)}, 0,
                       answer['accepted'] and station_values(comm) == expected))
    for fault, mutate in (
        ('unknown_key', lambda d: d[-1].update(key='phase6.unknown')),
        ('invalid_last_value', lambda d: d[-1].update(value='2147483647')),
        ('stale_revision', lambda d: d[-1].update(rev=0)),
        ('foreign_root', lambda d: d[0].update(root='Other'))):
        bad = copy.deepcopy(doc)
        bad[0]['set'] = FIXTURE_NAMES[2]
        mutate(bad)
        await client.import_document(bad)
        before = station_values(comm)
        answer = await client.command(mb.LOAD_CONFIG_SET, TextValue=FIXTURE_NAMES[2])
        rejection = {n: client.state.sets.values[APP.name + '/ConfigPersist/LastReject' + n] for n in ('Scope', 'Key')}
        exact = rejection['Scope'] == 'Other' if fault == 'foreign_root' else rejection == {'Scope': bad[-1]['scope'], 'Key': bad[-1]['key']}
        rows.append(px.row('load_refuses_' + fault, 'no value changes; the rejection names the offending identity',
                           {'answer': answer, 'rejection': rejection}, 0,
                           not answer['accepted'] and station_values(comm) == before and exact))
    answer = await client.command(mb.SAVE_CONFIG_SET, TextValue=FIXTURE_NAMES[3], IntValue=0)
    model_doc = await client.export_document(FIXTURE_NAMES[3])
    before = projection.read_records(comm)
    load = await client.command(mb.LOAD_CONFIG_SET, TextValue=FIXTURE_NAMES[3])
    rows.append(px.row('model_load_refuses_as_tc3_does', 'model save/export works; load awaits recipe-store integration',
                       {'save': answer, 'load': load, 'header': model_doc[0]}, 0,
                       answer['accepted'] and model_doc[0]['kind'] == 0 and not load['accepted']
                       and load['diagnosticKey'] == mf.numeric_key(APP, sets.MODEL_KEY)
                       and projection.read_records(comm) == before))
    for tag, value in ((px.PART_PRESENT, 0), (px.AIR_OK, 1), (px.TWO_HAND, 1)):
        px.write(comm, tag, value)
    await client.command(mb.SET_MODE, IntValue=px.MODE_AUTO)
    await client.command(mb.START)
    running, _ = px.await_unit(comm, lambda u: u['Running'] != 0, settle)
    before = station_values(comm)
    answer = await client.command(mb.LOAD_CONFIG_SET, TextValue=FIXTURE_NAMES[0])
    rows.append(px.row('load_checks_root_ready_on_controller', 'a continuously held AUTO run refuses the set',
                       {'running': running, 'answer': answer}, 0,
                       bool(running) and not answer['accepted'] and station_values(comm) == before))
    await client.idle(ack)
    viewer, sequence = gateway._ConnState(), px.seed_sequence(comm)
    refused = False
    try:
        await client.command(mb.LIST_CONFIG_SETS, state=viewer)
    except gateway.WriteRefused:
        refused = True
    rows.append(px.row('sets_retain_the_gateway_write_gate', 'no authenticated actor: no controller commit',
                       {'refused': refused, 'sequence': px.seed_sequence(comm)}, 0,
                       refused and px.seed_sequence(comm) == sequence))
    answer = await client.command(mb.ACK_CONFIG_RESTORE)
    rows.append(px.row('restore_ack_requires_a_reported_loss', 'no restore loss: acknowledgement refuses by TC3 key', answer, 0,
                       not answer['accepted'] and answer['diagnosticKey'] == mf.numeric_key(APP, mb.RESTORE_ACK_REFUSED_KEY)))
    await client.command(mb.DELETE_CONFIG_SET, TextValue=FIXTURE_NAMES[2])
    await client.command(mb.LIST_CONFIG_SETS)
    rows.append(px.row('delete_releases_the_bounded_slot', 'three names remain after deleting one',
                       {'count': client.state.sets.values[APP.name + '/ConfigSetCount']}, 0,
                       client.state.sets.values[APP.name + '/ConfigSetCount'] == 3))


async def restore(client, original, settle, evidence):
    ack = parity.ack(settle)
    result = evidence['sets_restore'] = {}
    try:
        await client.idle(ack)
    except Exception as error:
        result['idle'] = {'accepted': False, 'error': str(error)}
    for key, value in original.items():
        try:
            answer = await client.write_config(key, value)
            result[key] = answer
        except Exception as error:
            result[key] = {'accepted': False, 'error': str(error)}
    for name in FIXTURE_NAMES:
        try:
            if any(h['set'] == name for h in client.store.list()):
                result['delete:' + name] = await client.command(mb.DELETE_CONFIG_SET, TextValue=name)
        except Exception as error:
            result['delete:' + name] = {'accepted': False, 'error': str(error)}
    evidence['sets_restored'] = station_values(client.comm)
    evidence['sets_store_empty'] = client.store.list() == []
    evidence['sets_restore_passed'] = all(v['accepted'] for v in result.values()) and evidence['sets_restored'] == original and evidence['sets_store_empty']


def run(comm, serial, settle, rows, evidence):
    base = Path('C:/work/FraktalPhase6Sets').resolve()
    directory = (base / (datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-' + uuid.uuid4().hex)).resolve()
    if not directory.is_relative_to(base):
        raise ValueError('fixture store escaped its named workspace')
    client = Client(comm, serial, directory)
    original = station_values(comm)
    evidence['sets_original'] = original
    evidence['sets_store_directory'] = str(directory)
    async def guarded():
        try:
            await exercise(client, settle, rows)
        finally:
            await restore(client, original, settle, evidence)
    asyncio.run(guarded())
    return {'tests': len(rows), 'successful': sum(r['passed'] for r in rows),
            'failed': sum(not r['passed'] for r in rows), 'rows': rows,
            'passed': all(r['passed'] for r in rows) and evidence['sets_restore_passed']}
