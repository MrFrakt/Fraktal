"""Core 3.8b live documents: the root's configuration kept on the medium.

TC3 keeps `<root>.station`, the owned line and every catalog model's data as
documents on its persistence medium, rewrites them after every accepted change
and replays them at start through the staged set path (IMPLEMENTATION_NOTES
§163). A Logix download resets every tag to its L5X initial value, so on this
binding the documents live on the gateway's medium and are re-applied after a
download instead of seeding each new image (Part III AB §3.8b).

The controller stays the only validator and the only authority:

* It marks the restore itself. A declaration with live documents leaves the
  StationCfg image at version zero on a first scan that did not find it intact,
  so "restoring" is derived controller state; Start names
  `std.release.configRestoring` and configuration writes are refused until the
  final station load stamps it (`fraktal_ab_generate.config_restoring`).
* Every document travels through the ordinary staged, all-or-nothing
  LOAD_CONFIG_SET (CREATE_MODEL for a model the catalog no longer has), under a
  controller session that the set gate already permits. Nothing here gains a
  write path the logged-in operator does not have.
* A medium that cannot answer is retried and announced, never concluded: the
  restore does not complete, so defaults are never captured over documents.
  A confirmed document that is missing or damaged is a loss, announced under
  its key and raised on the controller with the station load (`StoreResult` 2).

The index records which keys were confirmed. Deleting the whole medium folder,
index included, is indistinguishable from a first commissioning; a lost index
can only miss a loss, as TC3's lost marker can.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path

import fraktal_ab_declaration as decl
import fraktal_ab_sets as sets

LIVE_NAME = '_live'  # TC3's SetName for live documents
INDEX_NAME = 'index.json'
INDEX_SCHEMA = 'fraktal.ab.live-documents'
INDEX_VERSION = 1
STORE_OK, STORE_LOST = 1, 2  # the station load's StoreResult


class MediumUnreadable(OSError):
    """The medium did not answer. Retry; never treat it as "nothing there"."""


class DocumentLost(ValueError):
    """A confirmed document is missing, or a document does not parse."""


def station_key(app):
    return f'{app.name}.station'


def line_key(app):
    return f'{app.name}.line'


def model_key(app, index):
    return f'{app.name}.model{index}'


def live_directory(app, serial, environ=None):
    import fraktal_ab_medium as medium
    return medium.directory(app, serial, environ) / 'live'


@dataclass(frozen=True)
class Capture:
    """The controller's retained configuration as one projection read saw it."""
    restoring: bool
    records: dict
    banks: list
    codes: list
    model_ordinal: int
    level: int = -1
    required: int = -1

    @property
    def authorized(self):
        """The controller's own set-gate rule, read before trying it."""
        import fraktal_ab_access as access
        return (0 <= self.level <= access.ADMIN and 0 <= self.required <= access.ADMIN
                and self.level >= self.required)


def capture(app, unit, records, banks, codes, access_state):
    """None when any part did not answer: a partial read is never kept."""
    import fraktal_ab_generate as gen
    import fraktal_ab_access as access
    import fraktal_ab_mailbox as mb
    station = gen.station_cfg_record(app)
    if unit is None or records is None or banks is None or station.name not in records:
        return None
    if any(r.name not in records for r in app.records) or len(banks) != len(codes):
        return None
    level = required = -1
    if access_state is not None:
        level = access_state.get('CurrentLevel', -1)
        required = access_state.get('Required', [-1] * access.GATE_COUNT)[access.GATES[mb.LOAD_CONFIG_SET]]
    return Capture(restoring=records[station.name][decl.SCHEMA_VERSION_MEMBER] == 0,
                   records=records, banks=list(banks), codes=list(codes),
                   model_ordinal=unit.get('ModelOrdinal', 0), level=level, required=required)


def documents(app, held, created):
    """Every live document this capture implies, rendered once from the walk."""
    import fraktal_ab_generate as gen

    def record_value(_ordinal, record, member):
        return held.records[record.name][member.name]

    active = held.codes[held.model_ordinal - 1] if 1 <= held.model_ordinal <= len(held.codes) else ''
    out = {station_key(app): sets.values_document(app, LIVE_NAME, 1, record_value, active, created, 0)}
    if app.line is not None:
        out[line_key(app)] = sets.values_document(app, LIVE_NAME, 2, record_value, '', created, 0)
    if gen.model_scoped_members(app):
        for index, (code, bank) in enumerate(zip(held.codes, held.banks), 1):
            out[model_key(app, index)] = sets.values_document(
                app, LIVE_NAME, 0, lambda _o, _r, m, bank=bank: bank[m.name], code, created, 0)
    return out


def content(document):
    """What a document says, without when it was written."""
    header = {k: v for k, v in document[0].items() if k not in ('created', 'clock')}
    return json.dumps([header, *document[1:]], sort_keys=True, separators=(',', ':'))


class FileMedium:
    """Keyed live documents in one folder, plus the index of confirmed keys.

    Each document is the existing JSON-lines set document, written atomically
    by the set store's own replacement; the index is written after it, so a
    crash between the two leaves a valid newer document and an older index.
    """
    def __init__(self, directory):
        self.directory = Path(directory)

    def _path(self, key):
        sets._text(key, sets.NAME_MAX, nonempty=True)
        return self.directory / (hashlib.sha256(key.encode('ascii')).hexdigest() + '.jsonl')

    def index(self):
        path = self.directory / INDEX_NAME
        try:
            text = path.read_text(encoding='ascii')
        except FileNotFoundError:
            return {}
        except OSError as error:
            raise MediumUnreadable(f'live document index unreadable: {error}') from error
        try:
            held = json.loads(text)
            if (held.get('schema'), held.get('schemaVersion')) != (INDEX_SCHEMA, INDEX_VERSION):
                raise ValueError('schema')
            confirmed = held['documents']
            if not isinstance(confirmed, dict) or any(
                    not isinstance(v, dict) or type(v.get('generation')) is not int for v in confirmed.values()):
                raise ValueError('documents')
            return confirmed
        except (ValueError, KeyError, AttributeError, UnicodeError) as error:
            # Which keys were confirmed is unknown: a loss could not be told
            # from a first start, so the medium has not answered.
            raise MediumUnreadable('live document index is damaged') from error

    def read(self, key):
        """The document, None if never confirmed, or DocumentLost."""
        confirmed = self.index()
        path = self._path(key)
        try:
            if path.is_symlink():
                raise DocumentLost(f'{key}: store symlink')
            if path.stat().st_size > (sets.MAX_RECORDS + 1) * (sets.LINE_MAX + 1):
                raise DocumentLost(f'{key}: document exceeds capacity')
            text = path.read_text(encoding='ascii')
        except FileNotFoundError:
            if key in confirmed:
                raise DocumentLost(f'{key}: confirmed document is missing') from None
            return None
        except (UnicodeError, ValueError) as error:
            raise DocumentLost(f'{key}: {error}') from error
        except OSError as error:
            raise MediumUnreadable(f'{key}: {error}') from error
        try:
            return sets.checked_document([sets.parse_line(line) for line in text.splitlines()])
        except sets.SetRejected as error:
            raise DocumentLost(f'{key}: {error}') from error

    def write(self, key, document):
        document = sets.checked_document(document)
        text = '\n'.join(sets.render_line(v) for v in document) + '\n'
        confirmed = self.index()
        sets.replace_text(self.directory, self._path(key), text)
        entry = confirmed.get(key, {'generation': 0})
        confirmed[key] = {'generation': entry['generation'] + 1,
                          'sha256': hashlib.sha256(text.encode('ascii')).hexdigest()}
        index = {'schema': INDEX_SCHEMA, 'schemaVersion': INDEX_VERSION, 'documents': confirmed}
        sets.replace_text(self.directory, self.directory / INDEX_NAME,
                          json.dumps(index, sort_keys=True, indent=1) + '\n')


@dataclass
class Plan:
    """What the medium answered for one restore, before anything is sent."""
    models: list = field(default_factory=list)  # (index, document)
    line: list | None = None
    station: list | None = None
    losses: list = field(default_factory=list)  # (key, why)


def plan(app, medium):
    """Read every document first; MediumUnreadable propagates (retry later)."""
    import fraktal_ab_generate as gen
    result = Plan()

    def take(key, kind):
        try:
            document = medium.read(key)
        except DocumentLost as error:
            result.losses.append((key, str(error)))
            return None
        if document is None:
            return None
        h = document[0]
        if (h['set'], h['root'], h['kind']) != (LIVE_NAME, app.name, kind):
            result.losses.append((key, 'document identity differs'))
            return None
        return document

    if gen.model_scoped_members(app):
        for index in range(1, (app.model_capacity or len(app.models)) + 1):
            document = take(model_key(app, index), 0)
            if document is not None:
                result.models.append((index, document))
    if app.line is not None:
        result.line = take(line_key(app), 2)
    result.station = take(station_key(app), 1)
    return result


def empty_station(app):
    import fraktal_ab_manifest as mf
    return sets.checked_document([{'set': LIVE_NAME, 'root': app.name, 'schema': 1,
                                   'configRev': mf.config_revision(app), 'kind': 1, 'model': '',
                                   'records': 0, 'created': 0, 'clock': 0}])


@dataclass
class Outcome:
    complete: bool
    losses: list
    detail: str = ''


def restore(app, held, planned, command):
    """Replay the plan through `command`; the station load answers last.

    `command(kind, document, *, name='', model=0, store_result=0)` performs one
    mailbox transaction and returns the controller's response, or None when
    the transport could not deliver it. An access refusal stops the attempt
    without concluding anything; any other refusal is a loss of that document.
    """
    import fraktal_ab_access as access
    import fraktal_ab_mailbox as mb
    import fraktal_ab_manifest as mf
    denied = mf.numeric_key(app, access.DENIED) if app.access_users is not None else None
    codes, losses = list(held.codes), list(planned.losses)

    def send(key, kind, document, **arguments):
        response = command(kind, document, **arguments)
        if not response:  # None, or the writer's False for a refused identity
            raise MediumUnreadable(f'{key}: controller transaction was not delivered')
        if response['Accepted']:
            return True
        if denied is not None and response['DiagnosticKey'] == denied:
            raise PermissionError(f'{key}: the controller session may not load sets')
        losses.append((key, f'controller refused ({response["DiagnosticKey"]})'))
        return False

    try:
        for index, document in planned.models:
            key, code = model_key(app, index), document[0]['model']
            if index <= len(codes) and codes[index - 1] == code:
                send(key, mb.LOAD_CONFIG_SET, document, model=index)
            elif index == len(codes) + 1 and index <= app.model_capacity:
                if send(key, mb.CREATE_MODEL, document, name=code):
                    codes.append(code)
            else:
                losses.append((key, 'the catalog no longer offers this model at its position'))
        if planned.line is not None:
            send(line_key(app), mb.LOAD_CONFIG_SET, planned.line)
        station = planned.station if planned.station is not None else empty_station(app)
        active = station[0]['model']
        model = codes.index(active) + 1 if active in codes else 0
        result = STORE_LOST if losses else STORE_OK
        if not send(station_key(app), mb.LOAD_CONFIG_SET, station, model=model, store_result=result):
            # The answer itself was refused: still restoring, try again later.
            return Outcome(False, losses, 'station load refused')
    except PermissionError as error:
        return Outcome(False, losses, str(error))
    return Outcome(True, losses)


def write_changed(medium, wanted, written):
    """Write each document whose content changed; returns the keys written."""
    done = []
    for key, document in wanted.items():
        if written.get(key) == content(document):
            continue
        medium.write(key, document)
        written[key] = content(document)
        done.append(key)
    return done


RETRY_S = 10.0  # TC3's LIVE_READ_RETRY / LIVE_RETRY order of magnitude


class Keeper:
    """The gateway's half of live documents, one per controller root.

    Synchronous on purpose: the gateway runs it on a worker thread, under the
    mailbox lock for a restore, and a test drives it directly. It never writes
    a document while the controller is restoring, and a restore that could not
    read the medium never completes, so the documents are never replaced by
    the defaults a fresh image starts on.
    """
    def __init__(self, app, medium, *, clock=None, wall=None):
        import time
        self.app, self.medium = app, medium
        self._clock = clock or time.monotonic
        self._wall = wall or time.time
        self._written = None  # key -> content, loaded from the medium once
        self.state = 'idle'
        self.failed = False
        self.error = ''
        self.losses = []
        self.restored_at = None
        self._retry_at = 0.0

    def _fail(self, state, error):
        self.state, self.failed, self.error = state, True, str(error)
        self._retry_at = self._clock() + RETRY_S

    def keep(self, held):
        """Write what changed since the last write; the controller is the truth."""
        if held is None or held.restoring:
            return []
        if self.failed and self._clock() < self._retry_at:
            return []
        try:
            if self._written is None:
                written = {}
                for key in documents(self.app, held, 0):
                    document = self._known(key)
                    if document is not None:
                        written[key] = content(document)
                self._written = written
            done = write_changed(self.medium, documents(self.app, held, int(self._wall())), self._written)
        except (OSError, sets.SetRejected) as error:
            self._fail('failed', error)
            return []
        self.state, self.failed, self.error = 'kept', False, ''
        return done

    def _known(self, key):
        try:
            return self.medium.read(key)
        except DocumentLost:
            return None  # rewritten from the controller below

    def wants_restore(self, held):
        return (held is not None and held.restoring and held.authorized
                and self._clock() >= self._retry_at)

    def run_restore(self, held, command):
        """One attempt. Every outcome but completion is retried after RETRY_S."""
        self.state = 'restoring'
        try:
            outcome = restore(self.app, held, plan(self.app, self.medium), command)
        except MediumUnreadable as error:
            self._fail('unreadable', error)
            return None
        except Exception as error:  # transport/ack: the controller still says restoring
            self._fail('restoring', error)
            return None
        if not outcome.complete:
            self.error = outcome.detail
            self._retry_at = self._clock() + RETRY_S
            return outcome
        import datetime
        self.state, self.failed, self.error = 'restored', False, ''
        self.losses = outcome.losses
        self.restored_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
        self._written = None  # the restored image becomes the next baseline
        return outcome

    def values(self, current):
        """Overlay for the published §3.8b status: a gateway-side failure is
        shown, never hidden, and a loss names the document it was."""
        root = self.app.name + '/ConfigPersist/'
        out = {}
        if self.failed:
            out[root + 'Failed'] = True
        if self.losses:
            out[root + 'LastRejectScope'] = self.app.name
            out[root + 'LastRejectKey'] = self.losses[0][0]
        return out

    def health(self):
        body = {'state': self.state, 'failed': self.failed}
        if self.error:
            body['error'] = self.error
        if self.restored_at:
            body['restoredAt'] = self.restored_at
        if self.losses:
            body['losses'] = [{'key': key, 'detail': why} for key, why in self.losses]
        return body
