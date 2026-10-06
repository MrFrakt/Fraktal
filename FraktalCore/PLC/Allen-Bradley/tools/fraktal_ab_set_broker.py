"""Set mailbox broker: arguments, controller validation, host I/O, store receipt.

One external Sequence per request. A load never issues WRITE_CONFIG commands.
The post-save receipt acknowledges host durability without inventing a second
HMI sequence. This executes under Gateway's station mailbox lock.
"""
from __future__ import annotations

import datetime
import re
import time

import fraktal_ab_generate as gen
import fraktal_ab_mailbox as mb
import fraktal_ab_manifest as mf
import fraktal_ab_press_execute as execute
import fraktal_ab_sets as sets


def staging(app, sequence, *, valid=1, document=None, name='', kind=1, operation=mb.LOAD_CONFIG_SET, commit=0):
    out = {m.name: ([m.initial] * m.dimension if m.dimension else m.initial)
           for m in sets.request_members()}
    out.update(Sequence=sequence, Operation=operation, Commit=commit, Valid=valid, RootId=1, SetSchema=1,
               ConfigRev=mf.config_revision(app), Kind=kind)
    name = sets._text(name, sets.NAME_MAX) if name else ''
    out['NameLength'] = len(name)
    out['NameBytes'][:len(name)] = name.encode('ascii')
    if document is None:
        return out
    header = document[0]
    out.update(RootId=1 if header['root'] == app.name else 0,
               SetSchema=header['schema'], ConfigRev=header['configRev'],
               Kind=header['kind'], Count=len(document) - 1)
    addresses = {(app.name, m.write_key): (ordinal, m)
                 for ordinal, _record, m in gen.editable_values(app)}
    for index, record in enumerate(document[1:]):
        address = addresses.get((record['scope'], record['key']))
        out['Ordinal'][index] = address[0] if address else 0
        out['Revision'][index] = record['rev']
        out['RecordKind'][index] = record['kind']
        out['ValueType'][index] = record['type']
        value = record['value']
        if record['type'] == 2 and value.lower() in ('true', 'false'):
            out['Value'][index] = 1 if value.lower() == 'true' else 0
        elif re.fullmatch(r'[+-]?\d+', value):
            candidate = int(value)
            if -2147483648 <= candidate <= 2147483647:
                out['Value'][index] = candidate
            else:
                out['ValueType'][index] = -1
        else:
            # Syntax is translated, not authorized. Invalid numeric text is
            # sent to the PLC as an invalid type, never coerced to zero.
            out['ValueType'][index] = -1
    return out


def snapshot_document(app, name, kind, snapshot, codes=None):
    model = snapshot['ModelOrdinal']
    codes = codes if codes is not None else [m.code for m in app.models]
    model_code = codes[model - 1] if kind == 0 and 1 <= model <= len(codes) else ''
    date, clock = snapshot['Date'], snapshot['Clock']
    stamp = datetime.datetime(date // 10000, (date // 100) % 100, date % 100,
                              clock // 10000000, (clock // 100000) % 100,
                              (clock // 1000) % 100, tzinfo=datetime.timezone.utc)
    records = []
    for ordinal, record, member in gen.editable_values(app):
        if sets.config_kind(record) != kind:
            continue
        value = snapshot['Snapshot'][ordinal - 1]
        text = ('TRUE' if value else 'FALSE') if member.kind == 'boolean' else str(value)
        records.append({'scope': app.name, 'key': member.write_key,
                        'rev': mf.config_revision(app), 'kind': kind,
                        'type': sets.value_type(member), 'value': text})
    if snapshot['Count'] != len(records):
        raise sets.SetRejected('controller snapshot count differs')
    return sets.checked_document([{'set': name, 'root': app.name, 'schema': 1,
              'configRev': mf.config_revision(app), 'kind': kind, 'model': model_code,
              'records': len(records), 'created': int(stamp.timestamp()),
              'clock': int(bool(snapshot['TimeSynchronized']))}, *records])


def read_state(comm, app):
    state = execute.read_layout(comm, sets.state_tag(app), sets.state_members(app))
    if state is None:
        raise sets.SetRejected('controller set state did not read')
    state['Sequence'] &= 0xffffffff
    return state


def wait_response(comm, app, sequence, timeout=6.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        response = execute.read_flat(comm, mb.response_tag_name(app),
                                     tuple(n for n, *_ in mb.RESPONSE_MEMBERS))
        if response is not None and (response['AckSequence'] & 0xffffffff) == sequence:
            response['AckSequence'] &= 0xffffffff
            return response
        time.sleep(.02)
    raise sets.SetRejected('controller set acknowledgement timed out')


def _write(comm, target, value):
    from fraktal_ab_s16_execute import _success
    if target.endswith(('.Sequence', '.StoreAck')):
        from fraktal_ab_mailbox_frame import signed
        value = signed(value)
    reply = comm.Write(target, value)
    if not _success(reply):
        raise sets.SetRejected(f'set staging write failed: {target}')


def process(comm, app, store, session, writes, write_base):
    arguments = {p.rsplit('/', 1)[-1]: v for p, _t, v in writes}
    kind, sequence = arguments['Kind'], arguments['Sequence']
    text = arguments.get('TextValue', '')
    name, document, headers, export = '', None, None, ''
    proposal_kind = arguments.get('IntValue', 0) if kind in (mb.SAVE_CONFIG_SET, mb.EXPORT_CURRENT_CONFIG) else 1
    valid = 1
    if kind != mb.EXPORT_CONFIG_SET:
        session.export_document = None
    if kind != mb.IMPORT_CONFIG_SET:
        session.interrupt()
    try:
        if kind == mb.IMPORT_CONFIG_SET:
            # Header fragments have no name yet. A bounded placeholder labels
            # their controller audit; later pieces carry the parsed set name.
            name = session.document[0]['set'] if session.document else '(import)'
            document = session.piece(text, arguments.get('IntValue', 0) == 1,
                                     bool(arguments.get('BoolValue', False)))
            if session.document:
                name = session.document[0]['set']
            if document:
                name = document[0]['set']
        elif kind == mb.CREATE_MODEL:
            name = sets._text(arguments.get('NameValue', ''), sets.NAME_MAX, nonempty=True)
            proposal_kind = 0
            if arguments.get('BoolValue', False):
                document = store.read(text)
                if document[0]['kind'] != 0:
                    raise sets.SetRejected('creation source must be a model set')
        elif kind == mb.LIST_CONFIG_SETS:
            headers = store.list()
        else:
            name = sets._text(text, sets.NAME_MAX, nonempty=True)
            if kind in (mb.LOAD_CONFIG_SET, mb.EXPORT_CONFIG_SET, mb.DELETE_CONFIG_SET):
                cached = session.export_document
                if kind == mb.EXPORT_CONFIG_SET and arguments.get('IntValue', 0) > 0 and cached and cached[0]['set'] == name:
                    document = cached
                else:
                    document = store.read(name)
            if kind == mb.EXPORT_CONFIG_SET:
                line = arguments.get('IntValue', 0)
                if type(line) is not int or not 0 <= line < len(document):
                    raise sets.SetRejected('export line is outside the document')
                export = sets.render_line(document[line])
            if kind == mb.SAVE_CONFIG_SET:
                headers = store.list()
                if not any(h['set'] == name for h in headers) and len(headers) >= sets.MAX_SETS:
                    raise sets.SetRejected('store is full')
    except (sets.SetRejected, OSError, UnicodeError):
        session.interrupt()
        valid = 0
    # Export is checked by the PLC against every record before any line returns.
    staged_doc = document if kind in (mb.LOAD_CONFIG_SET, mb.EXPORT_CONFIG_SET, mb.CREATE_MODEL) else None
    proposal = staging(app, sequence, valid=valid, document=staged_doc,
                       name=name, kind=proposal_kind, operation=kind, commit=int(bool(arguments.get('BoolValue', False))))
    if kind == mb.CREATE_MODEL:
        proposal['NameLength'] = len(name)
        proposal['NameBytes'] = list(name.encode('ascii')) + [0] * (sets.NAME_MAX - len(name))
    if document and kind != mb.LOAD_CONFIG_SET:
        proposal['Count'] = len(document) - 1
    # The complete payload is planned before the first write. ConfigSet is an
    # appended request member; no other tag gains ExternalAccess Read/Write.
    target = mb.request_tag_name(app) + '.ConfigSet'
    for member in sets.request_members():
        _write(comm, target + '.' + member.name, proposal[member.name])
    if not write_base(comm, writes):
        session.interrupt()
        return False
    session.committed_sequence = sequence
    response = wait_response(comm, app, sequence)
    answer = read_state(comm, app)
    # The root access gate can refuse before set dispatch, leaving the previous
    # set state intact. Its matching mailbox refusal is still authoritative.
    # An acceptance must carry its own set state before any host mutation.
    if response['Accepted'] and answer['Sequence'] != sequence:
        raise sets.SetRejected('set response belongs to another sequence')
    values = session.values
    if kind in (mb.EXPORT_CONFIG_SET, mb.EXPORT_CURRENT_CONFIG):
        values.update({app.name + '/ConfigSetDocument': '', app.name + '/ConfigSetDocumentLine': -1,
                       app.name + '/ConfigSetDocumentLines': 0})
    persist = app.name + '/ConfigPersist/'
    values.update({persist + 'LastRejectScope': '', persist + 'LastRejectKey': ''})
    if not response['Accepted']:
        session.interrupt()
        if document and kind in (mb.LOAD_CONFIG_SET, mb.EXPORT_CONFIG_SET) and answer['Sequence'] == sequence:
            index = answer['RejectIndex']
            if 1 <= index < len(document):
                values[persist + 'LastRejectScope'] = document[index]['scope']
                values[persist + 'LastRejectKey'] = document[index]['key']
            elif document[0]['root'] != app.name:
                values[persist + 'LastRejectScope'] = document[0]['root']
            elif document[0]['kind'] == 0:
                values[persist + 'LastRejectScope'] = document[0]['model']
            else:
                values[persist + 'LastRejectKey'] = name
        else:
            values[persist + 'LastRejectKey'] = name
        # Transport succeeded; HmiResponse is the refusal. Preserve the
        # sequence bookkeeping so the next HMI command uses the next number.
        return True
    durable = kind in (mb.SAVE_CONFIG_SET, mb.DELETE_CONFIG_SET) or (
        kind == mb.IMPORT_CONFIG_SET and bool(arguments.get('BoolValue', False)))
    result = 1
    try:
        if kind in (mb.SAVE_CONFIG_SET, mb.EXPORT_CURRENT_CONFIG):
            import fraktal_ab_models as models
            codes = models.read(comm, app) if app.model_capacity else None
            document = snapshot_document(app, name, proposal_kind, answer, codes)
            if kind == mb.SAVE_CONFIG_SET:
                store.save(document)
            else:
                session.export_document = document
                values.update({app.name + '/ConfigSetDocument': sets.render_line(document[0]),
                               app.name + '/ConfigSetDocumentLine': 0,
                               app.name + '/ConfigSetDocumentLines': len(document) - 1})
        elif kind == mb.DELETE_CONFIG_SET:
            store.delete(name)
        elif kind == mb.IMPORT_CONFIG_SET and document:
            store.save(document)
        elif kind == mb.LIST_CONFIG_SETS:
            values.update(sets.list_values(app.name, headers))
        elif kind == mb.EXPORT_CONFIG_SET:
            values.update({app.name + '/ConfigSetDocument': export,
                           app.name + '/ConfigSetDocumentLine': arguments.get('IntValue', 0),
                           app.name + '/ConfigSetDocumentLines': len(document) - 1})
    except (sets.SetRejected, OSError, ValueError, UnicodeError):
        result = 2
        if kind == mb.EXPORT_CURRENT_CONFIG:
            session.export_document = None
            raise sets.SetRejected('current export snapshot could not be rendered')
    if durable:
        # Data first, matching receipt marker last. It never increments the
        # command Sequence or applies a value. Failure stays visible in PLC.
        _write(comm, target + '.StoreResult', result)
        _write(comm, target + '.StoreAck', sequence)
        deadline = time.monotonic() + 6
        while time.monotonic() < deadline:
            persist_state = execute.read_layout(comm, gen.config_persist_tag(app), gen.config_persist_members())
            if persist_state is not None and not persist_state['Pending']:
                break
            time.sleep(.02)
        else:
            raise sets.SetRejected('controller store receipt timed out')
    return True
