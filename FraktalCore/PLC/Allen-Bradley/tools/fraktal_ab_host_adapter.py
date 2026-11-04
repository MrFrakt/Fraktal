"""WP6.5 declaration-free host adapter: one process per controller instance.

The controller owns every key, every ordinal and every verdict. This process
only answers the jobs the controller opens on its V6.11 host-service ingress,
and opens its own live-document jobs:
- **ConfigSets / ConfigProvider:** it reads and writes the four named set
  documents in `FileStore`, renders a snapshot as a document from published
  facts, keeps an import's parse and a current export's rendering;
- **LiveDocuments:** it keeps every document on `FileMedium` when it changes,
  and restores them after a download while the controller says it restores
  and its own set gate permits the logged-in session.

It discovers the root, its host-service rows and its facts through the S1
reader alone, and imports nothing from the declaration or the generator (a
test asserts that in a fresh process). It writes only through the versioned
host-service endpoints. An unanswered request is never resent: the
controller's job times out, and the operator's command is refused.

`RootService` holds the protocol logic over a `Port`, which a test drives
against the emitted controller code and `CipPort` drives over pylogix.
"""
from __future__ import annotations

import argparse
import json
import re
import time
from dataclasses import dataclass, field

import fraktal_ab_host_service_binding as binding
import fraktal_ab_live_medium as medium
import fraktal_ab_set_documents as documents

# Core E_HmiRequestKind ordinals: binding-neutral, the same on every controller.
SAVE, LOAD, LIST, EXPORT, IMPORT, DELETE, CREATE, EXPORT_CURRENT = 28, 29, 30, 32, 33, 35, 37, 38
DENIED_KEY = 'std.error.accessDenied'
IMPORT_PLACEHOLDER = '(import)'  # the broker's name for an import whose header is not yet complete
SETS, PROVIDER, DOCUMENTS = (binding.SERVICES[n] for n in ('ConfigSets', 'ConfigProvider', 'LiveDocuments'))
KEEP_INTERVAL_S = 2.0
RETRY_S = 10.0


class Unanswered(Exception):
    """A request the controller did not acknowledge: concluded nothing, resent never."""


@dataclass(frozen=True)
class Capability:
    ordinal: int
    key: str
    kind: int
    value_type: int


@dataclass(frozen=True)
class Facts:
    """What the controller publishes about one root: enough to render its documents."""
    root: str
    revision: int
    capabilities: tuple
    codes: tuple
    capacity: int

    @property
    def line(self):
        return any(c.kind == 2 for c in self.capabilities)

    @property
    def models(self):
        return any(c.kind == 0 for c in self.capabilities)


def revision_of(legacy_hash):
    """The configuration revision documents carry: the legacy content hash's first 24 bits."""
    if not isinstance(legacy_hash, str) or not re.fullmatch(r'[0-9A-Fa-f]{6,}', legacy_hash):
        raise ValueError('legacy content hash unavailable')
    return int(legacy_hash[:6], 16)


def render(facts, name, kind, values, model_code, created, clock, revision=None):
    """A snapshot as a set document, from published facts alone."""
    revision = facts.revision if revision is None else revision
    records = [dict(scope=facts.root, key=c.key, rev=revision, kind=kind, type=c.value_type,
                    value=('TRUE' if values[c.ordinal - 1] else 'FALSE') if c.value_type == 2 else str(values[c.ordinal - 1]))
               for c in facts.capabilities if c.kind == kind]
    return documents.checked_document([dict(set=name, root=facts.root, schema=1, configRev=revision, kind=kind,
                                            model=model_code, records=len(records), created=created, clock=clock),
                                       *records])


def _signed(value):
    return value - 0x100000000 if value > 0x7fffffff else value


def document_chunks(document, *, line=None, final=True):
    """A document as request bodies: its header, then up to eight records per scope."""
    header, records = document[0], document[1:]
    chunks = [dict(Kind=binding.HEADER_CHUNK, Count=0, Total=len(records), Scope=header['root'], Name=header['set'],
                   Model=header['model'], SetSchema=header['schema'], ConfigRev=header['configRev'],
                   RecordKind=header['kind'], CreatedSeconds=_signed(header['created']),
                   Synchronized=header['clock'])]
    index = 0
    while index < len(records):
        part = [records[index]]
        while (len(part) < 8 and index + len(part) < len(records)
               and records[index + len(part)]['scope'] == part[0]['scope']):
            part.append(records[index + len(part)])
        types, values = [], []
        for record in part:
            # Syntax is translated, never authorized: anything else reaches the
            # controller as an invalid type, exactly as the broker sent it.
            value, kind = record['value'], record['type']
            if kind == 2 and value.lower() in ('true', 'false'):
                types.append(kind)
                values.append(1 if value.lower() == 'true' else 0)
            elif re.fullmatch(r'[+-]?\d+', value) and -2**31 <= int(value) <= 2**31 - 1:
                types.append(kind)
                values.append(int(value))
            else:
                types.append(-1)
                values.append(0)
        chunks.append(dict(Kind=binding.RECORDS, Count=len(part), Total=len(records), Scope=part[0]['scope'],
                           Keys=[r['key'] for r in part], Revisions=[r['rev'] for r in part],
                           RecordKinds=[r['kind'] for r in part], ValueTypes=types, Values=values))
        index += len(part)
    if line is not None:
        chunks.append(dict(Kind=binding.TEXT, Count=line, Total=len(records),
                           Line=documents.render_line(document[line])))
    return chunks


@dataclass
class Health:
    state: str = 'idle'
    failed: bool = False
    error: str = ''
    losses: list = field(default_factory=list)
    restored_at: str = ''

    def as_dict(self):
        body = dict(state=self.state, failed=self.failed)
        if self.error:
            body['error'] = self.error
        if self.restored_at:
            body['restoredAt'] = self.restored_at
        if self.losses:
            body['losses'] = [dict(key=key, detail=why) for key, why in self.losses]
        return body


class RootService:
    """One root's host services over one port; `step` answers at most one job."""

    def __init__(self, port, store, live_medium=None, *, clock=time.monotonic, wall=time.time,
                 keep_interval=KEEP_INTERVAL_S, retry=RETRY_S):
        self.port, self.store, self.medium = port, store, live_medium
        self.clock, self.wall, self.keep_interval, self.retry = clock, wall, keep_interval, retry
        self.session = documents.Session()
        self.committed = None  # an import's document, saved by its STORE job
        self.export = None     # a current export's rendering, served for its later lines
        self.answered = None
        self.written = None    # live key -> content, loaded from the medium once
        self.keep_next, self.keep_at, self.retry_at = 0, 0.0, 0.0
        self.health = Health()

    # -- transport ------------------------------------------------------------
    def _submit(self, job, body, *, final, status=binding.OK, chunk=None, opening=None):
        envelope = dict(Service=job['JobService'], JobSequence=job['JobSequence'], Operation=job['JobOperation'],
                        Argument=0, Chunk=job['NextChunk'] if chunk is None else chunk, Final=int(final), Status=status)
        if opening is not None:
            envelope.update(opening)
        return self.port.submit(envelope, body)

    def _answer(self, job, chunks, status=binding.OK):
        """Send a job's chunks in order; stop at the first one the controller refuses."""
        reply = job
        for index, body in enumerate(chunks):
            reply = self._submit(reply, body, final=index == len(chunks) - 1,
                                 status=status, chunk=job['NextChunk'] + index)
            if not reply['Accepted']:
                return False
            reply = dict(job, NextChunk=job['NextChunk'] + index + 1)
        return True

    def _status(self, job, status):
        return self._answer(job, [dict(Kind=binding.NONE)], status)

    # -- the loop -------------------------------------------------------------
    def step(self):
        reply = self.port.reply()
        if reply['JobSequence'] == 0:
            self.answered = None
            if self.medium is not None:
                self._live(reply)
            return None
        mark = (reply['JobSequence'], reply['JobService'], reply['JobPhase'], reply['NextChunk'])
        if mark == self.answered:
            return None
        self.answered = mark
        handler = {(SETS, binding.FETCH): self._fetch, (SETS, binding.STORE): self._store,
                   (PROVIDER, binding.PRESENT): self._present}.get((reply['JobService'], reply['JobPhase']))
        if handler is None:
            return None  # a live-document job of ours, answered where it was opened
        if reply['JobOperation'] != IMPORT:
            self.session.interrupt()
        if reply['JobOperation'] not in (EXPORT, EXPORT_CURRENT):
            self.export = None
        try:
            return handler(reply)
        except Unanswered as error:
            self.health.error = str(error)
            return None

    # -- ConfigSets: before the transaction -------------------------------------
    def _fetch(self, job):
        operation, name = job['JobOperation'], job['JobName']
        if operation == IMPORT:
            return self._import(job)
        try:
            if operation == SAVE:
                headers = self.store.list()
                full = not any(h['set'] == name for h in headers) and len(headers) >= documents.MAX_SETS
                return self._status(job, binding.REFUSED if full else binding.OK)
            if operation == DELETE:
                self.store.read(name)
                return self._status(job, binding.OK)
            cached = self.export
            if operation == EXPORT and job['JobInt'] > 0 and cached and cached[0]['set'] == name:
                document = cached
            else:
                document = self.store.read(name)
            if operation == CREATE and document[0]['kind'] != 0:
                raise documents.SetRejected('creation source must be a model set')
            line = None
            if operation == EXPORT:
                line = job['JobInt']
                if not 0 <= line < len(document):
                    raise documents.SetRejected('export line is outside the document')
        except (documents.SetRejected, UnicodeError, FileNotFoundError):
            return self._status(job, binding.REFUSED)
        except OSError:
            return self._status(job, binding.UNAVAILABLE)
        return self._answer(job, document_chunks(document, line=line))

    def _import(self, job):
        name = self.session.document[0]['set'] if self.session.document else IMPORT_PLACEHOLDER
        try:
            document = self.session.piece(job['JobText'], job['JobInt'] == 1, bool(job['JobBool']))
        except (documents.SetRejected, ValueError):
            return self._answer(job, [dict(Kind=binding.HEADER_CHUNK, Name=name, Total=0)], binding.REFUSED)
        if self.session.document:
            name = self.session.document[0]['set']
        if document:
            name, self.committed = document[0]['set'], document
        return self._answer(job, [dict(Kind=binding.HEADER_CHUNK, Name=name,
                                       Total=len(document) - 1 if document else 0)])

    # -- ConfigSets: after the acknowledgement ----------------------------------
    def _store(self, job):
        operation = job['JobOperation']
        try:
            if operation == SAVE:
                snapshot, facts = job['Snapshot'], self.port.facts()
                kind, model = snapshot['Kind'], snapshot['ModelOrdinal']
                code = facts.codes[model - 1] if kind == 0 and 1 <= model <= len(facts.codes) else ''
                self.store.save(render(facts, job['JobName'], kind, snapshot['Values'], code,
                                       documents.created_seconds(snapshot['Date'], snapshot['Clock']),
                                       int(bool(snapshot['Synchronized'])), snapshot['Revision']))
            elif operation == DELETE:
                self.store.delete(job['JobName'])
            elif operation == IMPORT:
                if not self.committed or self.committed[0]['set'] != job['JobName']:
                    raise documents.SetRejected('no committed import of that name')
                self.store.save(self.committed)
                self.committed = None
            else:
                raise documents.SetRejected('no store for this operation')
        except (documents.SetRejected, OSError, ValueError, UnicodeError):
            return self._status(job, binding.FAILED)
        return self._status(job, binding.OK)

    # -- ConfigProvider: before the acknowledgement -------------------------------
    def _present(self, job):
        if job['JobOperation'] == LIST:
            try:
                headers = self.store.list()
            except (documents.SetRejected, OSError, UnicodeError):
                return self._status(job, binding.UNAVAILABLE)
            if not headers:
                return self._status(job, binding.OK)
            return self._answer(job, [dict(Kind=binding.CATALOG, Count=h['records'], Total=len(headers), Scope=h['root'],
                                           Name=h['set'], Model=h['model'], SetSchema=h['schema'],
                                           ConfigRev=h['configRev'], RecordKind=h['kind'],
                                           CreatedSeconds=_signed(h['created']), Synchronized=h['clock'])
                                      for h in headers])
        snapshot, facts = job['Snapshot'], self.port.facts()
        try:
            kind, model = snapshot['Kind'], snapshot['ModelOrdinal']
            code = facts.codes[model - 1] if kind == 0 and 1 <= model <= len(facts.codes) else ''
            document = render(facts, job['JobName'], kind, snapshot['Values'], code,
                              documents.created_seconds(snapshot['Date'], snapshot['Clock']),
                              int(bool(snapshot['Synchronized'])), snapshot['Revision'])
        except (documents.SetRejected, ValueError, IndexError):
            return self._status(job, binding.UNAVAILABLE)
        self.export = document
        return self._answer(job, [dict(Kind=binding.TEXT, Count=0, Total=len(document) - 1,
                                       Line=documents.render_line(document[0]))])

    # -- LiveDocuments ----------------------------------------------------------
    def _live(self, reply):
        if reply['Restoring']:
            if reply['SessionPermits'] and self.clock() >= self.retry_at:
                self.restore()
            return
        if self.clock() >= self.keep_at:
            self.keep_at = self.clock() + self.keep_interval
            self.keep_one()

    def _open(self, operation, body, *, argument=0, status=binding.OK, final=False):
        job = dict(JobService=DOCUMENTS, JobSequence=0, JobOperation=operation, NextChunk=0)
        return self._submit(job, body, final=final, status=status, chunk=0,
                            opening=dict(Argument=argument))

    def _documents(self, facts):
        """(key, kind, index) for every live document this root keeps."""
        out = [(f'{facts.root}.station', 1, 0)]
        if facts.line:
            out.append((f'{facts.root}.line', 2, 0))
        if facts.models:
            out += [(f'{facts.root}.model{i}', 0, i) for i in range(1, len(facts.codes) + 1)]
        return out

    def keep_one(self):
        """Keep the next document in turn; write it only when its content changed."""
        facts = self.port.facts()
        wanted = self._documents(facts)
        key, kind, index = wanted[self.keep_next % len(wanted)]
        self.keep_next += 1
        try:
            if self.written is None:
                self.written = {}
                for k, _kind, _index in wanted:
                    try:
                        known = self.medium.read(k)
                    except medium.DocumentLost:
                        known = None  # rewritten from the controller below
                    if known is not None:
                        self.written[k] = medium.content(known)
        except OSError as error:
            self._fail('failed', error)
            return False
        opened = self._open(EXPORT_CURRENT, dict(Kind=binding.NONE, RecordKind=kind, Count=index))
        if not opened['Accepted']:
            return False  # restoring, busy or preempted: the next turn tries again
        snapshot = opened['Snapshot']
        status = binding.OK
        try:
            code = (facts.codes[snapshot['ModelOrdinal'] - 1]
                    if kind in (0, 1) and 1 <= snapshot['ModelOrdinal'] <= len(facts.codes) else '')
            document = render(facts, medium.LIVE_NAME, kind, snapshot['Values'], code, int(self.wall()), 0,
                              snapshot['Revision'])
            if self.written.get(key) != medium.content(document):
                self.medium.write(key, document)
                self.written[key] = medium.content(document)
            self.health.state, self.health.failed, self.health.error = 'kept', False, ''
        except (OSError, documents.SetRejected, ValueError, IndexError) as error:
            self._fail('failed', error)
            status = binding.FAILED
        self._submit(opened, dict(Kind=binding.NONE), final=True, status=status)
        return status == binding.OK

    def _fail(self, state, error):
        self.health.state, self.health.failed, self.health.error = state, True, str(error)
        self.retry_at = self.clock() + self.retry

    def _restore_document(self, operation, document, *, argument=0, status=binding.OK):
        """One restore job; returns (accepted, key text) or None when not delivered."""
        chunks = document_chunks(document)
        opened = self._open(operation, chunks[0], argument=argument, status=status, final=len(chunks) == 1)
        if not opened['Accepted']:
            return None
        job = opened
        for index, body in enumerate(chunks[1:], 1):
            job = self._submit(job, body, final=index == len(chunks) - 1)
            if not job['Accepted']:
                return None
        for _ in range(50):
            reply = self.port.reply()
            if reply['JobSequence'] == opened['JobSequence'] and reply['JobPhase'] == binding.STORE:
                verdict = (bool(reply['JobBool']), reply['JobInt'])
                self._submit(reply, dict(Kind=binding.NONE), final=True)
                return verdict
            if reply['JobSequence'] != opened['JobSequence']:
                return None
            self.port.wait()
        return None

    def restore(self):
        """One attempt in the medium's order; every outcome but completion retries later."""
        facts = self.port.facts()
        self.health.state = 'restoring'
        losses, models, station, line = [], [], None, None
        try:
            def take(key, kind):
                try:
                    document = self.medium.read(key)
                except medium.DocumentLost as error:
                    losses.append((key, str(error)))
                    return None
                if document is None:
                    return None
                h = document[0]
                if (h['set'], h['root'], h['kind']) != (medium.LIVE_NAME, facts.root, kind):
                    losses.append((key, 'document identity differs'))
                    return None
                return document
            if facts.models:
                for index in range(1, (facts.capacity or len(facts.codes)) + 1):
                    document = take(f'{facts.root}.model{index}', 0)
                    if document is not None:
                        models.append((index, document))
            if facts.line:
                line = take(f'{facts.root}.line', 2)
            station = take(f'{facts.root}.station', 1)
        except medium.MediumUnreadable as error:
            self._fail('unreadable', error)
            return False
        codes = list(facts.codes)
        denied = None

        def send(key, operation, document, **arguments):
            nonlocal denied
            verdict = self._restore_document(operation, document, **arguments)
            if verdict is None:
                raise Unanswered(f'{key}: restore job was not answered')
            accepted, diagnostic = verdict
            if accepted:
                return True
            if self.port.key_text(diagnostic) == DENIED_KEY:
                denied = key
                raise PermissionError(f'{key}: the controller session may not load sets')
            losses.append((key, f'controller refused ({diagnostic})'))
            return False

        try:
            for index, document in models:
                key, code = f'{facts.root}.model{index}', document[0]['model']
                if index <= len(codes) and codes[index - 1] == code:
                    send(key, LOAD, document, argument=index)
                elif index == len(codes) + 1 and index <= facts.capacity:
                    if send(key, CREATE, document):
                        codes.append(code)
                else:
                    losses.append((key, 'the catalog no longer offers this model at its position'))
            if line is not None:
                send(f'{facts.root}.line', LOAD, line)
            if station is None:
                station = documents.checked_document([dict(set=medium.LIVE_NAME, root=facts.root, schema=1,
                                                           configRev=facts.revision, kind=1, model='', records=0,
                                                           created=0, clock=0)])
            active = station[0]['model']
            model = codes.index(active) + 1 if active in codes else 0
            if not send(f'{facts.root}.station', LOAD, station, argument=model,
                        status=binding.LOST if losses else binding.OK):
                self._fail('restoring', 'station load refused')
                return False
        except (PermissionError, Unanswered) as error:
            self._fail('restoring', error)
            return False
        import datetime
        self.health = Health(state='restored', losses=losses,
                             restored_at=datetime.datetime.now(datetime.timezone.utc).isoformat())
        self.written = None  # the restored image becomes the next keep baseline
        return True


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('--host', required=True, help='controller address')
    parser.add_argument('--slot', type=int, default=0)
    parser.add_argument('--expect-serial', required=True, help='exact eight-hex controller serial')
    parser.add_argument('--once', action='store_true', help='answer at most one round, then exit')
    parser.add_argument('--interval', type=float, default=0.02, help='seconds between reply polls')
    args = parser.parse_args(argv)
    if not re.fullmatch(r'[A-Fa-f0-9]{8}', args.expect_serial) or not 0 <= args.slot <= 255:
        parser.error('exact eight-hex serial and valid slot required')
    from fraktal_ab_host_cip import open_services
    from pylogix import PLC
    with PLC(args.host) as comm:
        comm.ProcessorSlot, comm.SocketTimeout = args.slot, 5
        services = open_services(comm, expect_serial=args.expect_serial.upper(), wait=args.interval)
        if not services:
            print(json.dumps(dict(state='no host services')))
            return 0
        while True:
            for service in services:
                service.step()
            if args.once:
                print(json.dumps({s.port.root: s.health.as_dict() for s in services}))
                return 0
            time.sleep(args.interval)


if __name__ == '__main__':
    raise SystemExit(main())
