"""Core 3.8b parameter-set documents and their host store, declaration-free.

The portable JSON-lines format, its bounds and the file store that keeps four
named documents. Nothing here knows a station: the host adapter and the
engineering code (`fraktal_ab_sets`) share one definition of the format.
"""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path

MAX_SETS = 4  # TC3 PL_Fraktal.MAX_CONFIG_SETS
MAX_RECORDS = 64  # released WriteCapabilities capacity, bounded transaction
LINE_MAX = 480
NAME_MAX = 80
SET_DIR_ENV = 'FRAKTAL_AB_CONFIG_SET_DIR'


def directory_for(root, serial, environ=None):
    """The set store's folder: one per commissioned root and controller serial."""
    environ = os.environ if environ is None else environ
    chosen = environ.get(SET_DIR_ENV)
    if chosen:
        return Path(chosen)
    base = Path(environ.get('LOCALAPPDATA', str(Path.home())))
    return base / 'Fraktal' / 'ConfigSets' / (serial + '-' + root)


def created_seconds(date, clock):
    """A controller date (YYYYMMDD) and clock (HHMMSS and microseconds) as UTC epoch seconds."""
    import datetime
    stamp = datetime.datetime(date // 10000, (date // 100) % 100, date % 100,
                              clock // 10000000, (clock // 100000) % 100,
                              (clock // 1000) % 100, tzinfo=datetime.timezone.utc)
    return int(stamp.timestamp())


class SetRejected(ValueError):
    pass


def _text(value, maximum, *, nonempty=False):
    # The frozen AB StringFamily transport is ASCII. Refuse unsupported text,
    # never shorten it or address another set after character conversion.
    if not isinstance(value, str) or len(value) > maximum or (nonempty and not value):
        raise SetRejected('text width or type')
    if any(ord(c) > 127 or ord(c) == 0 for c in value):
        raise SetRejected('text is outside the frozen ASCII transport')
    return value


def _int(value, low=0, high=2147483647):
    if type(value) is not int or not low <= value <= high:
        raise SetRejected('integer width or type')
    return value


HEADER_FIELDS = ('set', 'root', 'schema', 'configRev', 'kind', 'model', 'records', 'created', 'clock')
RECORD_FIELDS = ('scope', 'key', 'rev', 'kind', 'type', 'value')


def checked_header(header):
    if not isinstance(header, dict) or set(header) != set(HEADER_FIELDS):
        raise SetRejected('header shape')
    h = dict(header)
    for n in ('set', 'root', 'model'):
        _text(h[n], NAME_MAX, nonempty=n != 'model')
    _int(h['schema'], 1, 65535)
    _int(h['configRev'])
    _int(h['kind'], 0, 2)
    _int(h['records'], 0, MAX_RECORDS)
    _int(h['created'], 0, 4294967295)  # TC3 unsigned DT seconds
    _int(h['clock'], 0, 1)
    return h


def checked_record(record):
    if not isinstance(record, dict) or set(record) != set(RECORD_FIELDS):
        raise SetRejected('record shape')
    r = dict(record)
    _text(r['scope'], NAME_MAX)
    _text(r['key'], 160, nonempty=True)
    _text(r['value'], NAME_MAX)
    _int(r['rev'])
    _int(r['kind'], 0, 2)
    _int(r['type'], 0, 3)
    return r


def _pairs(items):
    out = {}
    for key, value in items:
        if key in out:
            raise SetRejected('duplicate JSON member')
        out[key] = value
    return out


def parse_line(line):
    _text(line, LINE_MAX, nonempty=True)
    try:
        value = json.loads(line, object_pairs_hook=_pairs,
                           parse_constant=lambda _: (_ for _ in ()).throw(SetRejected('non-finite JSON')))
    except (ValueError, TypeError) as exc:
        raise SetRejected('invalid JSON line') from exc
    return checked_header(value) if isinstance(value, dict) and 'set' in value else checked_record(value)


def render_line(value):
    header = 'set' in value
    checked = checked_header(value) if header else checked_record(value)
    order = HEADER_FIELDS if header else RECORD_FIELDS
    line = json.dumps({k: checked[k] for k in order}, separators=(',', ':'), ensure_ascii=True)
    return _text(line, LINE_MAX, nonempty=True)


def checked_document(document):
    if not isinstance(document, list) or not document:
        raise SetRejected('empty document')
    h = checked_header(document[0])
    records = [checked_record(r) for r in document[1:]]
    if len(records) != h['records']:
        raise SetRejected('header record count differs')
    result = [h, *records]
    for value in result:
        render_line(value)  # complete bounded export, or no import
    return result


def replace_text(directory, path, text):
    """Atomic ASCII replacement: fsync a sibling temporary, then os.replace."""
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    if path.is_symlink():
        raise SetRejected('store symlink')
    fd, temporary = tempfile.mkstemp(prefix='.pending-', dir=directory)
    try:
        with os.fdopen(fd, 'w', encoding='ascii', newline='\n') as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)  # exact file we just created, never a tree


class FileStore:
    """Four named documents, atomic replacement and explicit I/O failures.

    Names are data, never paths. One directory belongs to one commissioned root
    and controller serial. fsync+replace is host file durability; controller
    power-cycle/download/upgrade retention remains a separate provisional claim.
    """
    def __init__(self, directory):
        self.directory = Path(directory)

    def _path(self, name):
        _text(name, NAME_MAX, nonempty=True)
        digest = hashlib.sha256(name.encode('ascii')).hexdigest()
        return self.directory / (digest + '.jsonl')

    def read(self, name):
        path = self._path(name)
        if path.is_symlink():
            raise SetRejected('store symlink')
        if path.stat().st_size > (MAX_RECORDS + 1) * (LINE_MAX + 1):
            raise SetRejected('document exceeds capacity')
        result = checked_document([parse_line(line) for line in path.read_text(encoding='ascii').splitlines()])
        if result[0]['set'] != name:
            raise SetRejected('stored name differs')
        return result

    def list(self):
        if not self.directory.exists():
            return []
        rows = []
        for path in sorted(self.directory.glob('*.jsonl')):
            if path.is_symlink() or path.stat().st_size > (MAX_RECORDS + 1) * (LINE_MAX + 1):
                raise SetRejected('unsafe or oversized store entry')
            doc = checked_document([parse_line(line) for line in path.read_text(encoding='ascii').splitlines()])
            if path != self._path(doc[0]['set']):
                raise SetRejected('stored identity differs')
            rows.append(doc[0])
            if len(rows) > MAX_SETS:
                raise SetRejected('store exceeds capacity')
        return sorted(rows, key=lambda h: h['set'])

    def save(self, document):
        document = checked_document(document)
        path = self._path(document[0]['set'])
        rows = self.list()
        if not any(h['set'] == document[0]['set'] for h in rows) and len(rows) >= MAX_SETS:
            raise SetRejected('store is full; delete a set first')
        replace_text(self.directory, path, '\n'.join(render_line(v) for v in document) + '\n')

    def delete(self, name):
        self.read(name)  # refuse absent/corrupt entries; never guess a path
        self._path(name).unlink()


class Session:
    """Import framing and export answers belong to the requesting connection."""
    def __init__(self):
        self.partial = ''
        self.document = None
        self.values = {}
        self.committed_sequence = None
        self.export_document = None

    def interrupt(self):
        self.partial = ''
        self.document = None

    def piece(self, text, more, commit):
        try:
            _text(text, 255)
            _text(self.partial + text, LINE_MAX)
            if more:
                if commit:
                    raise SetRejected('commit before the final piece')
                self.partial += text
                return None
            line = self.partial + text
            self.partial = ''
            parsed = parse_line(line)
            if 'set' in parsed:
                self.document = [parsed]
            elif self.document is None:
                raise SetRejected('record before header')
            else:
                self.document.append(parsed)
                if len(self.document) - 1 > MAX_RECORDS:
                    raise SetRejected('import exceeds record capacity')
            if commit:
                result = checked_document(self.document)
                self.document = None
                return result
            return None
        except (SetRejected, ValueError):
            self.interrupt()
            raise


def empty_values(root):
    out = {f'{root}/ConfigSetCount': 0, f'{root}/ConfigSetDocument': '',
           f'{root}/ConfigSetDocumentLine': 0, f'{root}/ConfigSetDocumentLines': 0,
           f'{root}/ConfigPersist/LastRejectScope': '', f'{root}/ConfigPersist/LastRejectKey': ''}
    for index in range(1, MAX_SETS + 1):
        for name, value in (('SetName', ''), ('RootIdentity', ''),
                            ('Kind', 0), ('ModelCode', ''), ('RecordCount', 0),
                            ('ConfigRev', 0), ('CreatedAt', 0),
                            ('TimeSynchronized', False)):
            out[f'{root}/ConfigSets[{index}]/{name}'] = value
    return out


def list_values(root, headers):
    out = empty_values(root)
    out[f'{root}/ConfigSetCount'] = len(headers)
    mapping = {'SetName': 'set', 'RootIdentity': 'root', 'Kind': 'kind', 'ModelCode': 'model',
               'RecordCount': 'records', 'ConfigRev': 'configRev',
               'CreatedAt': 'created', 'TimeSynchronized': 'clock'}
    for i, header in enumerate(headers, 1):
        prefix = f'{root}/ConfigSets[{i}]'
        for name, key in mapping.items():
            out[prefix + '/' + name] = bool(header[key]) if key == 'clock' else header[key]
    return out
