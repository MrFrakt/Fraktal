/// The adapter's HostEvents delivery against the native capture of session 03.
///
/// On Echo, `capture.py` read the legacy ring, the full canonical S1
/// acquisition and the legacy ring again, on one quiet ring state; the
/// canonical ring equalled the legacy projection leaf for leaf
/// (`Specification/AllenBradley/Evidence/AB_S6_HOST_SESSION_03_RUNTIME_2026-11-04`).
/// Here the declaration-free Dart reader turns that capture's ring bytes into a
/// batch, which must equal the legacy batch read natively. Delivery must write
/// the engineering cursor's and sink's bytes.
@Timeout(Duration(minutes: 5))
library;

import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

import 'package:fraktal_gateway/host_adapter.dart';
import 'package:fraktal_opcua_client/cip_host_service.dart';
// The whole-record projection, for a cross-check only.
import 'package:fraktal_opcua_client/src/cip_publication.dart' show CipPublication;
import 'package:test/test.dart';

const _evidence = '../../../Specification/AllenBradley/Evidence/AB_S6_HOST_SESSION_03_RUNTIME_2026-11-04';
final _tools = Directory('../../PLC/Allen-Bradley/tools');
final _python = Platform.environment['FRAKTAL_PYTHON'] ?? 'python';

String _sha(List<int> bytes) => cipSha256(bytes).toUpperCase();

Uint8List _bytes(String hex) => Uint8List.fromList(
    [for (var i = 0; i < hex.length; i += 2) int.parse(hex.substring(i, i + 2), radix: 16)]);

Object? _plain(Object? v) => jsonDecode(jsonEncode(v));

final class Capture {
  final Map<String, Object?> capture, legacy;
  final CipNamespace namespace;
  final CipManifest manifest;
  final Map<String, Object?> row;
  Capture._(this.capture, this.legacy, this.namespace, this.manifest, this.row);

  static Capture load() {
    final raw = File('test/fixtures/host_events_session03_canonical.json.gz').readAsBytesSync();
    final capture = Map<String, Object?>.from(jsonDecode(utf8.decode(gzip.decode(raw))) as Map);
    final legacy = Map<String, Object?>.from(
        jsonDecode(File('test/fixtures/host_events_session03_legacy.json').readAsStringSync()) as Map);
    final manifest = CipManifest.fromNormalized(Map<String, Object?>.from(capture['manifest'] as Map));
    final row = manifest.rows('hostServiceBindings').singleWhere((r) => r['Service'] == CipHost.hostEvents);
    return Capture._(capture, legacy, CipNamespace.fromCapture(capture), manifest, row);
  }

  Uint8List record(String tag) =>
      _bytes((capture['records'] as List).cast<Map>().singleWhere((r) => r['tag'] == tag)['rawHex'] as String);

  /// The ring structure's own bytes, sliced from the root record at its member offset.
  Uint8List ring(CipHostEventsReader reader) {
    final size = namespace.templates[reader.member.handle]!.byteSize;
    return Uint8List.sublistView(record('Press'), reader.member.offset, reader.member.offset + size);
  }
}

/// A read connection serving the ring structure and a scripted revision.
final class RingWire implements CipReadTransport {
  final Uint8List ring;
  final int structureHandle;
  final List<int> revisions;
  int reads = 0;
  RingWire(this.ring, this.structureHandle, this.revisions);

  @override
  Future<CipReply> request(int service, Uint8List path, [Uint8List? data]) async {
    final symbol = String.fromCharCodes(path.sublist(2, 2 + path[1]));
    if (symbol == 'FRK_Press_HostRingRevision') {
      final value = revisions[reads++ % revisions.length];
      return CipReply(0, const [], Uint8List.fromList([0xc4, 0, ...(ByteData(4)..setInt32(0, value, Endian.little)).buffer.asUint8List()]));
    }
    final header = ByteData(4)
      ..setUint16(0, 0x02a0, Endian.little)
      ..setUint16(2, structureHandle, Endian.little);
    return CipReply(0, const [], Uint8List.fromList([...header.buffer.asUint8List(), ...ring]));
  }

  @override
  Future<void> close() async {}
  @override
  void abort() {}
}

/// The engineering cursor and sink over stdio, for byte parity.
final class Engineering {
  final Process process;
  final StreamIterator<String> lines;
  Engineering._(this.process)
      : lines = StreamIterator(process.stdout.transform(utf8.decoder).transform(const LineSplitter()));

  static Future<Engineering> start() async {
    final process = await Process.start(_python, ['fraktal_ab_host_bench_server.py', 'cursor'],
        workingDirectory: _tools.path);
    process.stderr.transform(utf8.decoder).listen(stderr.write);
    final e = Engineering._(process);
    await e._next();
    return e;
  }

  Future<Map<String, Object?>> _next() async {
    if (!await lines.moveNext()) throw StateError('engineering process ended');
    return Map<String, Object?>.from(jsonDecode(lines.current) as Map);
  }

  Future<Map<String, Object?>> deliver(String directory, Map<String, Object?> batch, {int? accept}) async {
    process.stdin.writeln(jsonEncode({
      'op': 'deliver',
      'directory': directory,
      'station': 'Press',
      'source': source,
      'batch': batch,
      if (accept != null) 'accept': accept
    }));
    return _next();
  }

  Future<void> stop() async {
    await process.stdin.close();
    await process.exitCode;
  }
}

const source = '601FC87B:0DBD9CEA8EE6BC59';

bool get _python3 {
  try {
    return _tools.existsSync() && Process.runSync(_python, ['--version']).exitCode == 0;
  } on ProcessException {
    return false;
  }
}

void main() {
  final c = Capture.load();
  CipHostEventsReader reader(CipReadTransport wire) => CipHostEventsReader(wire, c.namespace, c.manifest, c.row);
  final unused = RingWire(Uint8List(0), 0, [0]);

  group('the sealed session 03 capture', () {
    test('its fixtures are the sealed evidence', () {
      final manifest = jsonDecode(File('$_evidence/artifact_manifest.json').readAsStringSync()) as Map;
      final files = manifest['files'] as Map;
      expect(_sha(File('test/fixtures/host_events_session03_canonical.json.gz').readAsBytesSync()),
          files['Session/capture_canonical.json.gz']);
      expect(_sha(File('test/fixtures/host_events_session03_legacy.json').readAsBytesSync()),
          files['Session/capture_legacy.json']);
    });

    test('the canonical ring decodes to the legacy batch read natively', () {
      final r = reader(unused);
      final batch = batchFromCanonical(r.project(c.ring(r)), 'Press');
      expect((batch['events'] as List), hasLength(16));
      expect(_plain(batch), _plain(c.legacy['first']));
      expect(_plain(batch), _plain(c.legacy['second']));
    });

    test('the ring subtree projects as the whole root record does', () {
      final r = reader(unused);
      final whole = CipPublication(c.namespace, c.manifest).projectRecords({
        for (final row in (c.capture['records'] as List).cast<Map>()) row['tag'] as String: _bytes(row['rawHex'] as String)
      })['values'] as Map;
      final expected = {
        for (final e in whole.entries)
          if ((e.key as String).startsWith('Press/HostEvents/')) (e.key as String).substring(6): e.value
      };
      expect(r.project(c.ring(r)), expected);
      expect(expected, hasLength(220));
    });

    test('a read is kept only between two equal even revisions', () async {
      final structure = c.namespace.templates[reader(unused).member.handle]!.structureHandle;
      final ring = c.ring(reader(unused));
      final good = await reader(RingWire(ring, structure, [290, 290])).read();
      expect(batchFromCanonical(good!, 'Press'), isNotNull);
      expect(await reader(RingWire(ring, structure, [291])).read(), isNull, reason: 'odd: changing');
      expect(await reader(RingWire(ring, structure, [290, 292])).read(), isNull, reason: 'moved: torn');
    });
  });

  group('the batch refuses what it cannot vouch for', () {
    late Map<String, Object?> values;
    setUp(() {
      final r = reader(unused);
      values = r.project(c.ring(r));
    });

    const slot = 'HostEvents/Ring[5]/';
    for (final (name, change) in <(String, void Function(Map<String, Object?>))>[
      ('a discontinuous sequence', (v) => v['${slot}Sequence'] = (v['${slot}Sequence'] as int) + 1),
      ('a foreign station', (v) => v['${slot}StationPath'] = 'Oven'),
      ('an unknown kind', (v) => v['${slot}Kind'] = 11),
      ('a verdict on a non-processed event', (v) {
        if (v['${slot}Kind'] != 3) v['${slot}Verdict'] = 1;
        else v['${slot}Verdict'] = 7;
      }),
      ('a missing leaf', (v) => v.remove('${slot}Stamp')),
      ('an odd data revision', (v) => v['HostEvents/DataRevision'] = 291),
      ('a ring head that disagrees', (v) => v['HostEvents/RingHead'] = 3),
      ('a parent beyond its count', (v) {
        v['${slot}ParentCount'] = 0;
        v['${slot}Parents[1]'] = 'STRAY';
      }),
      ('an unparseable stamp', (v) => v['${slot}Stamp'] = 'yesterday'),
      ('a failed publisher', (v) => v['HostEvents/Failed'] = 1),
    ]) {
      test(name, () {
        change(values);
        expect(() => batchFromCanonical(values, 'Press'), throwsA(isA<HostEventsBad>()));
      });
    }
  });

  group('delivery writes the engineering cursor and sink bytes', () {
    late Engineering python;
    late Directory folder;
    final skip = _python3 ? false : 'needs Python and the Fraktal/AB tools beside the HMI';
    setUpAll(() async {
      if (_python3) python = await Engineering.start();
    });
    tearDownAll(() async {
      if (_python3) await python.stop();
    });
    setUp(() async => folder = await Directory.systemTemp.createTemp('fraktal_host_events_'));
    tearDown(() => folder.delete(recursive: true));

    Map<String, Object?> batch() => Map<String, Object?>.from(_plain(c.legacy['first']) as Map);

    Map<String, Object?> renumbered(int low, int shift) {
      final b = batch();
      final m = Map<String, Object?>.from(b['metadata'] as Map);
      m['EpochLow'] = low;
      m['NewestSequence'] = (m['NewestSequence'] as int) + shift;
      m['Head'] = ((m['NewestSequence'] as int) - 1) % (m['Capacity'] as int) + 1;
      m['DataRevision'] = (m['DataRevision'] as int) + 2;
      b['metadata'] = m;
      b['events'] = [
        for (final e in b['events'] as List) {...(e as Map), 'Sequence': (e['Sequence'] as int) + shift}
      ];
      return b;
    }

    Future<void> both(List<(Map<String, Object?>, int?)> steps) async {
      final dart = Directory('${folder.path}/dart'), py = Directory('${folder.path}/python');
      dart.createSync();
      for (final (b, accept) in steps) {
        final cursor = HostEventsCursor('Press', File('${dart.path}/cursor.json'), source: source);
        Object? mine;
        try {
          var n = 0;
          final sink = jsonlSink(File('${dart.path}/host_events.jsonl'));
          mine = cursor.deliver(b, (r) => accept != null && n >= accept ? false : (n++ >= 0 && sink(r)));
        } on HostEventsBad {
          mine = 'refused';
        }
        final theirs = await python.deliver(py.path, b, accept: accept);
        expect(mine, theirs.containsKey('refused') ? 'refused' : theirs['delivered']);
      }
      for (final name in ['host_events.jsonl', 'cursor.json']) {
        final a = File('${dart.path}/$name'), b = File('${py.path}/$name');
        expect(a.existsSync(), b.existsSync(), reason: name);
        if (b.existsSync()) expect(a.readAsBytesSync(), b.readAsBytesSync(), reason: name);
      }
    }

    test('first delivery: the overwritten interval, then every held event', () async {
      await both([(batch(), null)]);
      final lines = File('${folder.path}/dart/host_events.jsonl').readAsLinesSync();
      expect(lines, hasLength(17));
      expect(jsonDecode(lines.first)['reason'], 'ringOverwritten');
    }, skip: skip);

    test('a repeated batch delivers nothing new; a newer one only its new events', () async {
      await both([(batch(), null), (batch(), null), (renumbered(-1229008737, 3), null)]);
    }, skip: skip);

    test('a publisher epoch change is a loss record', () async {
      await both([(batch(), null), (renumbered(77, 0), null)]);
    }, skip: skip);

    test('a regression within the epoch refuses; a refusing sink stops delivery', () async {
      await both([(renumbered(-1229008737, 5), null), (batch(), null)]);
      await folder.delete(recursive: true);
      folder.createSync();
      await both([(batch(), 4), (batch(), null)]);
    }, skip: skip);
  });
}
