"""Independent, read-only verification of the Dart adapter's live documents.

The V6.8 view supplies keys, kinds, readable values and bank identities. Each
native row has its published proof; the configuration revision brackets the
catalog read. This is configuration verification on a quiescent fixture, not
a whole-station snapshot or a Python keeper. Only Dart writes/applies files.
"""
import time

import fraktal_ab_fixture_reads as fixture
from fraktal_ab_live_medium import FileMedium
from fraktal_ab_canonical_reader import MAX_LEAVES


def expected_documents(reader, root):
    bindings = [r for r in reader._manifest.get('readServices', [])
                if r['RootSymbol'] == root and r['Kind'] == 1 and r['Version'] == 1]
    if len(bindings) != 1:
        raise ValueError('live verification requires one published configuration view')
    prefix = bindings[0]['CanonicalRoot']
    headers = ('SchemaVersion', 'RootIdentity', 'Revision', 'DefinitionCount', 'ValueCount')
    header = reader.read_row(tuple(prefix + '/' + n for n in headers))['values']
    definitions, count = header[prefix + '/DefinitionCount'], header[prefix + '/ValueCount']
    if header[prefix + '/SchemaVersion'] != 1 or header[prefix + '/RootIdentity'] != root \
            or type(definitions) is not int or not 0 < definitions <= 32767 \
            or type(count) is not int or not definitions <= count <= 65535:
        raise ValueError('invalid configuration view identity/counts')
    if 5 + definitions * 5 + count * 6 > MAX_LEAVES:
        raise ValueError('configuration verification exceeds the reader leaf budget')
    def_fields = ('DefinitionIndex', 'WriteKey', 'ConfigKind', 'ValueType', 'ModelScoped')
    val_fields = ('DefinitionIndex', 'ModelOrdinal', 'ModelCode', 'ValueText', 'Readable', 'Revision')
    paths = [*(prefix + '/' + n for n in headers),
             *(f'{prefix}/Definitions[{i}]/{n}' for i in range(definitions) for n in def_fields),
             *(f'{prefix}/Values[{i}]/{n}' for i in range(count) for n in val_fields)]
    values = reader.read_row(paths)['values']
    if any(values[prefix + '/' + n] != header[prefix + '/' + n] for n in headers):
        raise ValueError('configuration changed while planning the verification')
    defs, rows, keys = [], {}, set()
    for i in range(definitions):
        row = {n: values[f'{prefix}/Definitions[{i}]/{n}'] for n in def_fields}
        if row['DefinitionIndex'] != i or not isinstance(row['WriteKey'], str) or not row['WriteKey'] \
                or row['WriteKey'] in keys or type(row['ConfigKind']) is not int or row['ConfigKind'] not in (0, 1, 2) \
                or type(row['ValueType']) is not int \
                or type(row['ModelScoped']) is not bool:
            raise ValueError('invalid or duplicate configuration definition')
        keys.add(row['WriteKey'])
        defs.append(row)
    for i in range(count):
        row = {n: values[f'{prefix}/Values[{i}]/{n}'] for n in val_fields}
        index, bank = row['DefinitionIndex'], row['ModelOrdinal']
        if type(index) is not int or not 0 <= index < definitions or type(bank) is not int or bank < 0 \
                or (index, bank) in rows or row['Revision'] != header[prefix + '/Revision'] \
                or row['Readable'] is not True or not isinstance(row['ValueText'], str):
            raise ValueError('incomplete, masked or inconsistent configuration value')
        rows[index, bank] = row
    model_count = root + '/AvailableModelCount'
    catalog_count = reader.read_row((model_count,))['values'][model_count]
    if type(catalog_count) is not int or not 0 <= catalog_count <= 32767:
        raise ValueError('invalid model catalog count')
    model_path = root + '/Model/ModelCode'
    paths = (model_count, model_path,
             *(f'{root}/AvailableModels[{i}]/ModelCode' for i in range(1, catalog_count + 1)))
    catalog = reader.read_row(paths)['values']
    if catalog[model_count] != catalog_count:
        raise ValueError('model catalog changed')
    codes = [catalog[f'{root}/AvailableModels[{i}]/ModelCode'] for i in range(1, catalog_count + 1)]
    if len(set(codes)) != len(codes) or any(not isinstance(c, str) or not c for c in codes):
        raise ValueError('invalid model identities')
    allowed = {(i, 0) for i in range(definitions)} | {
        (i, bank) for i, d in enumerate(defs) if d['ModelScoped'] for bank in range(1, catalog_count + 1)}
    if set(rows) != allowed:
        raise ValueError('configuration banks are incomplete or exceed the published catalog')
    epoch = root + '/Status/ConfigRev'
    if reader.read_row((epoch,))['values'][epoch] != header[prefix + '/Revision']:
        raise ValueError('configuration changed during the catalog read')
    identity = reader._manifest['legacyContentHash']
    revision = int(identity[:6], 16)  # the published V6.11/O12 document revision
    wanted = [(root + '.station', 1, 0, catalog[model_path])]
    if any(d['ConfigKind'] == 2 for d in defs):
        wanted.append((root + '.line', 2, 0, ''))
    if any(d['ConfigKind'] == 0 for d in defs):
        wanted += [(f'{root}.model{i}', 0, i, code) for i, code in enumerate(codes, 1)]
    result = {}
    for name, kind, bank, code in wanted:
        records = {}
        for i, definition in enumerate(defs):
            if definition['ConfigKind'] != kind:
                continue
            selected = bank if bank and definition['ModelScoped'] else 0
            row = rows.get((i, selected))
            if row is None or row['ModelCode'] != (codes[selected - 1] if selected else ''):
                raise ValueError('configuration bank is incomplete')
            text = row['ValueText']
            if definition['ValueType'] == 2:
                if text.upper() not in ('0', '1', 'TRUE', 'FALSE'):
                    raise ValueError('invalid published boolean value text')
                text = 'TRUE' if text.upper() in ('1', 'TRUE') else 'FALSE'
            records[definition['WriteKey']] = dict(scope=root, key=definition['WriteKey'], rev=revision,
                kind=kind, type=definition['ValueType'], value=text)
        result[name] = dict(header=dict(set='_live', root=root, configRev=revision, kind=kind,
                                       model=code, records=len(records)), records=records)
    return result, header[prefix + '/Revision']


def medium_matches(store, expected):
    medium = FileMedium(store / 'live')
    if set(expected) - set(medium.index()):
        return False
    for key, wanted in expected.items():
        document = medium.read(key)
        if document is None:
            return False
        header = document[0]
        if any(header.get(n) != v for n, v in wanted['header'].items()):
            return False
        rows = {r['key']: r for r in document[1:]}
        if len(rows) != len(document) - 1 or rows != wanted['records']:
            return False
    return True


def ready(comm, app, lease, *, timeout=60, clock=time.monotonic, sleep=time.sleep):
    """Wait for owner restore, then verify every current document on the medium."""
    session = fixture._session(comm, app)
    deadline, expected, epoch = clock() + timeout, None, None
    was_restoring = None
    while clock() < deadline:
        if not lease.guard(serial=session.expected_serial, root=session.root):
            raise ValueError('host adapter failed; ' + lease.failure)
        status = session.reader.host_status(session.root)
        if was_restoring is None:
            was_restoring = bool(status['Restoring'])
        if not status['Restoring']:
            paths = tuple(session.root + '/ConfigPersist/' + n for n in ('RestoreLost', 'Failed', 'Pending'))
            persist = session.reader.read_row(paths)['values']
            if persist[paths[0]] or persist[paths[1]]:
                raise ValueError('configuration restore/store reported a loss or failure')
            if not persist[paths[2]]:
                if expected is None:
                    expected, epoch = expected_documents(session.reader, session.root)
                if medium_matches(lease.store, expected):
                    path = session.root + '/Status/ConfigRev'
                    if session.reader.read_row((path,))['values'][path] != epoch:
                        raise ValueError('configuration changed while waiting for the medium')
                    return dict(wasRestoring=was_restoring, restoring=False, medium=str(lease.store / 'live'),
                                confirmedKeys=sorted(expected), health=dict(lease.health))
        sleep(.05)
    raise TimeoutError('Dart restore/keep did not confirm every current document')


def restore_configuration(comm, app):
    from fraktal_ab_harness_host import bind
    lease = bind(comm, app, require_seed=True)
    return ready(comm, app, lease)
