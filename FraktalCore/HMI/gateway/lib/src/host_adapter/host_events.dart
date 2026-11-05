/// Host events, declaration-free: the canonical ring into the batch the
/// engineering decoder makes, and acknowledged at-least-once delivery.
///
/// The batch is `fraktal_ab_host_events.decode`'s; the cursor, its lock and its
/// loss records are `fraktal_ab_host_cursor`'s, and the JSONL sink writes the
/// engineering collector's bytes. The ring is read-only: delivery acknowledges
/// nothing to the PLC.
library;

import 'dart:io';
import 'dart:math';

import 'package:fraktal_opcua_client/cip_host_service.dart';

import 'python_json.dart';

const _limit = 0x7fffffff;
const meta = [
  'SchemaVersion',
  'Head',
  'Count',
  'Capacity',
  'Wrapped',
  'NewestSequence',
  'DataRevision',
  'EpochLow',
  'EpochHigh',
  'Failed'
];

final class HostEventsBad implements Exception {
  final String message;
  const HostEventsBad(this.message);
  @override
  String toString() => 'HostEventsBad: $message';
}

bool _dint(Object? v) => v is int && v >= -0x80000000 && v <= _limit;

/// `validate_metadata`: capacity, count, head and their arithmetic, an even
/// revision, a live publisher.
(int, int, int, int) validateMetadata(Map<String, Object?> m) {
  if (!meta.every((n) => _dint(m[n])))
    throw const HostEventsBad('invalid host-event metadata or exhausted publisher');
  int i(String n) => m[n] as int;
  final cap = i('Capacity'), count = i('Count'), head = i('Head'), newest = i('NewestSequence');
  if (!const {1, 2, 3, 4, 5}.contains(i('SchemaVersion')) ||
      i('Failed') != 0 ||
      cap < 1 ||
      cap > 64 ||
      count < 0 ||
      count > cap ||
      newest < 0 ||
      count != min(newest, cap) ||
      i('DataRevision') < 0 ||
      i('DataRevision').isOdd ||
      (newest > 0 && i('DataRevision') == 0) ||
      !const {0, 1}.contains(i('Wrapped')) ||
      (count == 0 && (head != 0 || i('Wrapped') != 0)) ||
      (count > 0 && head != (newest - 1) % cap + 1) ||
      i('Wrapped') != (newest > cap ? 1 : 0) ||
      (i('EpochLow') == 0 && i('EpochHigh') == 0))
    throw const HostEventsBad('invalid host-event metadata or exhausted publisher');
  return (cap, count, head, newest);
}

/// The batch of one canonical ring (values keyed `HostEvents/...`). Every active
/// row is validated; no malformed row is dropped to manufacture continuity.
Map<String, Object?> batchFromCanonical(Map<String, Object?> v, String station) {
  Object? at(String key) {
    if (!v.containsKey('HostEvents/$key')) throw HostEventsBad('host-event leaf missing: $key');
    return v['HostEvents/$key'];
  }

  int integer(String key) {
    final x = at(key);
    if (!_dint(x)) throw HostEventsBad('host-event leaf is not a DINT: $key');
    return x as int;
  }

  String text(String key) {
    final x = at(key);
    if (x is! String) throw HostEventsBad('host-event leaf is not text: $key');
    return x;
  }

  final wrapped = at('Wrapped');
  if (wrapped is! bool) throw const HostEventsBad('host-event Wrapped is not a BOOL');
  final metadata = <String, Object?>{
    for (final n in meta) n: n == 'Wrapped' ? (wrapped ? 1 : 0) : integer(n)
  };
  final (cap, count, head, newest) = validateMetadata(metadata);
  if (integer('RingHead') != head) throw const HostEventsBad('ring head differs from its metadata');
  final schema = metadata['SchemaVersion'] as int;
  final genealogy = v.containsKey('HostEvents/GenealogyCapacity') ? integer('GenealogyCapacity') : null;
  if (genealogy != null && (genealogy < 1 || genealogy > 16))
    throw const HostEventsBad('invalid host-event genealogy capacity');
  final events = <Map<String, Object?>>[];
  for (var offset = 0; offset < count; offset++) {
    final slot = (head - count + offset) % cap + 1, p = 'Ring[$slot]/';
    final sequence = integer('${p}Sequence'), kind = integer('${p}Kind');
    final verdict = integer('${p}Verdict'), reason = integer('${p}ReasonCode');
    final synchronized = at('${p}TimeSynchronized');
    final part = text('${p}PartUid'), subject = text('${p}Subject');
    final stamp = text('${p}Stamp');
    if (sequence != newest - count + offset + 1 ||
        kind < 1 ||
        kind > 10 ||
        synchronized is! bool ||
        (kind == 3 && !const {0, 1, 2, 3}.contains(verdict)) ||
        (kind != 3 && verdict != (kind == 10 ? 2 : 0)) ||
        (verdict == 2 && reason == 0) ||
        (kind == 10 && reason == 0) ||
        (!const {3, 4, 10}.contains(kind) && reason != 0))
      throw const HostEventsBad('invalid or discontinuous host-event record');
    if (text('${p}StationPath') != station) throw const HostEventsBad('host-event station differs');
    final resource = schema >= 3 && (kind == 7 || kind == 8);
    if (schema >= 2 && part.isNotEmpty != (kind >= 1 && kind <= 4) ||
        schema < 2 && part.isNotEmpty ||
        subject.isNotEmpty != resource)
      throw const HostEventsBad('part-event identity missing or leaked to non-part event');
    if (!stamp.endsWith('Z') || DateTime.tryParse(stamp) == null)
      throw const HostEventsBad('host-event timestamp unavailable');
    final event = <String, Object?>{
      'Sequence': sequence,
      'Kind': kind,
      'StationPath': station,
      'PartUid': part,
      'Subject': subject,
      'Value': text('${p}Value'),
      'Stamp': stamp,
      'TimeSynchronized': synchronized,
      'Verdict': verdict,
      'ReasonCode': reason
    };
    if (genealogy != null) {
      final parents = integer('${p}ParentCount');
      if (parents < 0 || parents > genealogy || (parents != 0 && (kind < 1 || kind > 4)))
        throw const HostEventsBad('invalid host-event parent count');
      final named = [for (var i = 1; i <= genealogy; i++) text('${p}Parents[$i]')];
      if (named.take(parents).any((n) => n.isEmpty) || named.skip(parents).any((n) => n.isNotEmpty))
        throw const HostEventsBad('host-event parents differ from their count');
      event['Parents'] = named.take(parents).toList();
    }
    events.add(event);
  }
  return {'metadata': metadata, 'events': events, if (genealogy != null) 'genealogyCapacity': genealogy};
}

/// A sink accepts one record durably, or returns false (delivery stops there).
typedef HostEventSink = bool Function(Map<String, Object?> record);

/// `fraktal_ab_host_cursor.Cursor`: per-sink acknowledged state, persisted only
/// after the sink accepts. Delivery is at least once; a sink deduplicates by
/// `idempotencyKey`. A publisher epoch change and an overwritten interval are
/// explicit loss records.
final class HostEventsCursor {
  final String station, source;
  final File? file;
  Map<String, Object?> state;

  HostEventsCursor(this.station, this.file, {this.source = ''})
      : state = {'schema': 1, 'station': station, 'source': source, 'epoch': null, 'sequence': 0} {
    final f = file;
    if (f != null && f.existsSync()) state = _load(f);
  }

  Map<String, Object?> _load(File f) {
    final Object? loaded;
    try {
      loaded = strictJsonDecode(f.readAsStringSync());
    } on FormatException {
      throw const HostEventsBad('invalid acknowledged cursor');
    }
    if (loaded is! Map ||
        loaded['schema'] != 1 ||
        loaded['station'] != station ||
        (loaded['source'] ?? '') != source ||
        !_dint(loaded['sequence']) ||
        (loaded['sequence'] as int) < 0 ||
        loaded['epoch'] is! List ||
        (loaded['epoch'] as List).length != 2 ||
        !(loaded['epoch'] as List).every(_dint))
      throw const HostEventsBad('invalid acknowledged cursor');
    return Map<String, Object?>.from(loaded);
  }

  void _commit(List<int> epoch, int sequence) {
    final next = {'schema': 1, 'station': station, 'source': source, 'epoch': epoch, 'sequence': sequence};
    final f = file;
    if (f != null) {
      // A crash may leave an incomplete temporary; a unique name keeps that
      // orphan from blocking recovery or ever becoming an acknowledgement.
      final temporary = File('${f.path}.${_unique()}.pending');
      try {
        final out = temporary.openSync(mode: FileMode.writeOnly);
        try {
          out.writeStringSync(pythonJsonDumps(next));
          out.flushSync();
        } finally {
          out.closeSync();
        }
        temporary.renameSync(f.path);
      } finally {
        if (temporary.existsSync()) temporary.deleteSync();
      }
    }
    state = next;
  }

  /// Deliver one batch under the cursor's OS lock, from where it stands.
  bool deliver(Map<String, Object?> batch, HostEventSink sink) {
    final f = file;
    if (f == null) return _deliver(batch, sink);
    // The guard file is never unlinked: replacing it could let two writers
    // lock different files. A legacy sentinel lock needs a stopped upgrade.
    final guard = File('${f.path}.guard').openSync(mode: FileMode.append);
    try {
      try {
        guard.lockSync(FileLock.exclusive, 0, 1);
      } on FileSystemException {
        throw const HostEventsBad('host-event cursor has an active writer');
      }
      try {
        if (File('${f.path}.lock').existsSync())
          throw HostEventsBad('legacy cursor lock requires a stopped-collector upgrade: ${f.path}.lock');
        // Another cursor may have advanced while this one was idle.
        if (f.existsSync()) state = _load(f);
        return _deliver(batch, sink);
      } finally {
        guard.unlockSync(0, 1);
      }
    } finally {
      guard.closeSync();
    }
  }

  bool _deliver(Map<String, Object?> batch, HostEventSink sink) {
    final m = Map<String, Object?>.from(batch['metadata'] as Map);
    validateMetadata(m);
    final events = batch['events'];
    if (events is! List || events.length != m['Count'])
      throw const HostEventsBad('invalid delivery batch bounds');
    final newest = m['NewestSequence'] as int;
    for (var i = 0; i < events.length; i++) {
      final e = events[i] as Map;
      if (e['StationPath'] != station || e['Sequence'] != newest - events.length + i + 1)
        throw const HostEventsBad('invalid delivery station or sequence interval');
    }
    final epoch = [m['EpochLow'] as int, m['EpochHigh'] as int];
    var seen = state['sequence'] as int;
    final previous = state['epoch'] as List?;
    if (previous != null && (previous[0] != epoch[0] || previous[1] != epoch[1])) {
      final record = {
        'kind': 'dataLoss',
        'reason': 'publisherEpochChanged',
        'previous': Map<String, Object?>.from(state),
        'epoch': epoch,
        'idempotencyKey': [source, station, ...epoch, 'publisherEpochChanged', ...previous, seen]
      };
      if (sink(record) != true) return false;
      seen = 0;
      _commit(epoch, seen);
    } else if (previous != null && newest < seen) {
      throw const HostEventsBad('publisher sequence regressed within its epoch');
    }
    final oldest = newest - (m['Count'] as int) + 1;
    if (seen + 1 < oldest) {
      final record = {
        'kind': 'dataLoss',
        'reason': 'ringOverwritten',
        'firstMissing': seen + 1,
        'lastMissing': oldest - 1,
        'epoch': epoch,
        'idempotencyKey': [source, station, ...epoch, 'ringOverwritten', seen + 1, oldest - 1]
      };
      if (sink(record) != true) return false;
      seen = oldest - 1;
      _commit(epoch, seen);
    }
    for (final e in events) {
      final event = Map<String, Object?>.from(e as Map);
      if (event['Sequence'] as int <= seen) continue;
      final envelope = {
        'kind': 'event',
        'idempotencyKey': [source, station, ...epoch, event['Sequence']],
        'event': event
      };
      if (sink(envelope) != true) return false;
      seen = event['Sequence'] as int;
      _commit(epoch, seen);
    }
    return true;
  }
}

/// The engineering collector's JSONL sink: one sorted-key line per record,
/// flushed to disk before it counts as accepted. Lines end as Python's text
/// mode ends them (CRLF on Windows), so both collectors write the same bytes.
HostEventSink jsonlSink(File file) => (record) {
      file.parent.createSync(recursive: true);
      final out = file.openSync(mode: FileMode.append);
      try {
        out.writeStringSync('${pythonJsonDumps(record)}${Platform.isWindows ? '\r\n' : '\n'}');
        out.flushSync();
      } finally {
        out.closeSync();
      }
      return true;
    };

/// One root's ring delivered to its sink: read only when its revision moved.
final class HostEventsService {
  final CipHostEventsReader reader;
  final HostEventsCursor cursor;
  final HostEventSink sink;
  int? _delivered;
  String state = 'idle', error = '';
  int deliveredSequence = 0;

  HostEventsService(this.reader, this.cursor, this.sink);

  /// The cursor and sink of a root's ring, in [directory]'s `events` folder.
  factory HostEventsService.inDirectory(CipHostEventsReader reader, Directory directory, String serial) {
    final events = Directory('${directory.path}${Platform.pathSeparator}events')..createSync(recursive: true);
    String path(String name) => '${events.path}${Platform.pathSeparator}$name';
    return HostEventsService(
        reader,
        HostEventsCursor(reader.root, File(path('cursor.json')), source: '$serial:${reader.legacyContentHash}'),
        jsonlSink(File(path('host_events.jsonl'))));
  }

  Map<String, Object?> toJson() => {
        'state': state,
        'sequence': deliveredSequence,
        if (error.isNotEmpty) 'error': error
      };

  Future<void> step() async {
    final revision = await reader.revision();
    if (revision.isOdd || revision == _delivered) return;
    final values = await reader.read();
    if (values == null) return; // torn: the next step reads again
    try {
      final batch = batchFromCanonical(values, reader.root);
      if (cursor.deliver(batch, sink)) {
        _delivered = revision;
        state = 'delivered';
        error = '';
        deliveredSequence = cursor.state['sequence'] as int;
      } else {
        state = 'sinkRefused';
      }
    } on HostEventsBad catch (e) {
      state = 'refused';
      error = e.message;
    }
  }
}

String _unique() =>
    '${DateTime.now().microsecondsSinceEpoch.toRadixString(36)}${Random().nextInt(1 << 32).toRadixString(36)}';
