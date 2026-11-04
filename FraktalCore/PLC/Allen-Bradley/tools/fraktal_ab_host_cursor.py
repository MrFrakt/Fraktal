"""Acknowledged, at-least-once delivery of host events, declaration-free.

The ring metadata rules, the per-sink cursor and its OS lock. A batch is
`{metadata, events}`; how it was read (the private ring or the canonical one)
is the reader's concern, never the cursor's.
"""
from __future__ import annotations

import copy
import errno
import json
import os
import tempfile
from contextlib import contextmanager
from pathlib import Path

LIMIT = 2**31 - 1
META = ('SchemaVersion', 'Head', 'Count', 'Capacity', 'Wrapped',
        'NewestSequence', 'DataRevision', 'EpochLow', 'EpochHigh', 'Failed')


class HostEventsBad(ValueError):
    pass


def metadata(raw):
    return {n: raw[n] for n in META}


def validate_metadata(m, expected_capacity=None, expected_schema=None):
    try:
        cap, count, head, newest = (m[n] for n in ('Capacity', 'Count', 'Head', 'NewestSequence'))
        if (any(type(m[n]) is not int or not -2**31 <= m[n] <= LIMIT for n in META)
                or m['SchemaVersion'] not in (1, 2, 3, 4, 5) or m['Failed'] != 0
                or expected_schema is not None and m['SchemaVersion'] != expected_schema
                or (expected_capacity is not None and cap != expected_capacity)
                or not 1 <= cap <= 64 or not 0 <= count <= cap or not 0 <= newest <= LIMIT
                or count != min(newest, cap)
                or not 0 <= m['DataRevision'] <= LIMIT or m['DataRevision'] % 2
                or (newest > 0 and m['DataRevision'] == 0)
                or m['Wrapped'] not in (0, 1)
                or (count == 0 and (head != 0 or m['Wrapped']))
                or (count > 0 and head != (newest - 1) % cap + 1)
                or m['Wrapped'] != int(newest > cap)
                or (m['EpochLow'] == 0 and m['EpochHigh'] == 0)):
            raise HostEventsBad('invalid host-event metadata or exhausted publisher')
        return cap, count, head, newest
    except (KeyError, TypeError) as error:
        raise HostEventsBad('host-event metadata incomplete') from error


@contextmanager
def _cursor_lock(path):
    """Hold an OS lock until close, including release after process termination.

    The persistent guard must never be unlinked: replacing its inode could let
    two writers lock different files. Refuse legacy sentinel locks; an older
    collector must be stopped before upgrading, never guessed dead from a PID.
    """
    legacy = path.with_name(path.name + '.lock')
    with path.with_name(path.name + '.guard').open('a+b') as guard:
        guard.seek(0)
        try:
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(guard.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(guard.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            if exc.errno in (errno.EACCES, errno.EAGAIN, errno.EDEADLK):
                raise BlockingIOError('host-event cursor has an active writer') from exc
            raise
        try:
            if legacy.exists():
                raise FileExistsError('legacy cursor lock requires a stopped-collector upgrade: ' + str(legacy))
            yield
        finally:
            guard.seek(0)
            if os.name == 'nt':
                msvcrt.locking(guard.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(guard.fileno(), fcntl.LOCK_UN)


class Cursor:
    """Per-sink acknowledged cursor. Persist only after the sink accepts.

    Delivery is at least once: a crash after the sink accepts but before the
    local replace can repeat an event. Sinks deduplicate the supplied key.
    An epoch change/reset and an overwritten interval are explicit loss records.
    """
    def __init__(self, station, path=None, *, source=''):
        self.station, self.path = station, Path(path) if path is not None else None
        self.source = source
        self.state = dict(schema=1, station=station, source=source, epoch=None, sequence=0)
        if self.path is not None and self.path.exists():
            loaded = json.loads(self.path.read_text(encoding='utf-8'))
            if (loaded.get('schema') != 1 or loaded.get('station') != station
                    or loaded.get('source', '') != source
                    or type(loaded.get('sequence')) is not int or not 0 <= loaded['sequence'] <= LIMIT
                    or not isinstance(loaded.get('epoch'), list) or len(loaded['epoch']) != 2
                    or any(type(v) is not int or not -2**31 <= v <= LIMIT for v in loaded['epoch'])):
                raise HostEventsBad('invalid acknowledged cursor')
            self.state = loaded

    def _commit(self, epoch, sequence):
        state = dict(schema=1, station=self.station, source=self.source, epoch=epoch, sequence=sequence)
        if self.path is not None:
            # A crash may leave an incomplete temporary. Unique names prevent
            # that orphan from blocking recovery or becoming an acknowledgement.
            fd, name = tempfile.mkstemp(prefix=self.path.name + '.', suffix='.pending',
                                        dir=self.path.parent)
            temporary = Path(name)
            try:
                with os.fdopen(fd, 'w', encoding='utf-8') as out:
                    json.dump(state, out, sort_keys=True)
                    out.flush()
                    os.fsync(out.fileno())
                os.replace(temporary, self.path)
            finally:
                if temporary.exists():
                    temporary.unlink()
        self.state = state

    def deliver(self, batch, sink):
        if self.path is not None:
            with _cursor_lock(self.path):
                # A second Cursor instance may have advanced while idle.
                if self.path.exists():
                    self.state = Cursor(self.station, self.path, source=self.source).state
                return self._deliver(batch, sink)
        return self._deliver(batch, sink)

    def _deliver(self, batch, sink):
        m, events = batch['metadata'], batch['events']
        validate_metadata(m)
        if not isinstance(events, list) or len(events) != m['Count']:
            raise HostEventsBad('invalid delivery batch bounds')
        for index, event in enumerate(events):
            if (event.get('StationPath') != self.station
                    or type(event.get('Sequence')) is not int
                    or event['Sequence'] != m['NewestSequence'] - len(events) + index + 1):
                raise HostEventsBad('invalid delivery station or sequence interval')
        epoch, seen = [m['EpochLow'], m['EpochHigh']], self.state['sequence']
        if self.state['epoch'] is not None and self.state['epoch'] != epoch:
            record = dict(kind='dataLoss', reason='publisherEpochChanged',
                          previous=self.state.copy(), epoch=epoch,
                          idempotencyKey=[self.source, self.station, *epoch,
                              'publisherEpochChanged', *self.state['epoch'], seen])
            if sink(copy.deepcopy(record)) is not True:
                return False
            seen = 0
            self._commit(epoch, seen)
        elif self.state['epoch'] == epoch and m['NewestSequence'] < seen:
            raise HostEventsBad('publisher sequence regressed within its epoch')
        oldest = m['NewestSequence'] - m['Count'] + 1
        if seen + 1 < oldest:
            record = dict(kind='dataLoss', reason='ringOverwritten',
                          firstMissing=seen + 1, lastMissing=oldest - 1, epoch=epoch,
                          idempotencyKey=[self.source, self.station, *epoch,
                              'ringOverwritten', seen + 1, oldest - 1])
            if sink(copy.deepcopy(record)) is not True:
                return False
            seen = oldest - 1
            self._commit(epoch, seen)
        for event in events:
            if event['StationPath'] != self.station:
                raise HostEventsBad('host-event station differs from sink cursor')
            if event['Sequence'] <= seen:
                continue
            envelope = dict(kind='event', idempotencyKey=[self.source, self.station, *epoch, event['Sequence']],
                            event=copy.deepcopy(event))
            if sink(envelope) is not True:
                return False
            seen = event['Sequence']
            self._commit(epoch, seen)
        return True
