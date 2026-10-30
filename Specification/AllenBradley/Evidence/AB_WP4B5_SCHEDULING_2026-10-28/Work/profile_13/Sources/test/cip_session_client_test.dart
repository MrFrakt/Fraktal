import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:fraktal_opcua_client/src/cip_manifest.dart';
import 'package:fraktal_opcua_client/src/cip_namespace.dart';
import 'package:fraktal_opcua_client/src/cip_read_coherence.dart';
import 'package:fraktal_opcua_client/src/cip_session_client.dart';
import 'package:fraktal_opcua_client/src/cip_transport.dart';

import 'cip_publication_test.dart' as golden;
import 'cip_read_plan_test.dart' as planGolden;

/// A replay wire on the stepped clock the plan tests use, whose publisher
/// counter advances on its own period rather than per read — as the live
/// generation counter does. The shared CaptureWire's parity-based counter
/// locks up once proveProgress consumes an odd number of reads.
class ProgressingCaptureWire extends planGolden.TimedCaptureWire {
  int counterReads = 0;
  void Function(String)? afterDataRead;
  ProgressingCaptureWire(super.capture,
      {super.extraRecords, super.stepUs = 50});

  @override
  Future<CipReply> request(int service, Uint8List encoded,
      [Uint8List? data]) async {
    final root = path(encoded).first.$1;
    if (!raw.containsKey(root)) {
      nowUs += stepUs;
      final token = 2 + 2 * (counterReads++ ~/ 4);
      return CipReply(
          0,
          [],
          Uint8List.fromList([
            0xc4,
            0,
            ...(ByteData(4)..setInt32(0, token, Endian.little))
                .buffer
                .asUint8List()
          ]));
    }
    final reply = await super.request(service, encoded, data);
    afterDataRead?.call(root);
    return reply;
  }
}

/// The manifest record is not among a capture's records (it is carried as the
/// decoded manifest), so a replay wire synthesizes just the members the
/// engine's manifest check reads: Valid and ConfigRevision.
Uint8List canonicalManifestRecord(Map capture, String symbolName) {
  final symbol = (capture['symbols'] as List)
      .cast<Map>()
      .singleWhere((s) => s['name'] == symbolName);
  final template = (capture['templates'] as List)
      .cast<Map>()
      .singleWhere((t) => t['handle'] == symbol['handle']);
  final manifest = capture['manifest'] as Map;
  final bytes = Uint8List(template['byteSize'] as int);
  for (final name in ['Valid', 'ConfigRevision']) {
    final member = (template['members'] as List)
        .cast<Map>()
        .singleWhere((m) => m['name'] == name);
    final value = name == 'Valid'
        ? (manifest['valid'] == true ? 1 : 0)
        : manifest['configRevision'] as int;
    final atomic = (member['code'] as int) & 0xff;
    if (atomic == 0xc1) {
      if (value != 0) {
        bytes[(member['offset'] as int) + (member['info'] as int) ~/ 8] |=
            1 << ((member['info'] as int) % 8);
      }
    } else if (atomic == 0xc4) {
      ByteData.sublistView(bytes)
          .setInt32(member['offset'] as int, value, Endian.little);
    } else {
      throw StateError('Unexpected manifest member type for $name.');
    }
  }
  return bytes;
}

String manifestSymbolName(Map capture) {
  final namespace = CipNamespace.fromCapture(capture);
  return namespace.symbols.values
      .where((s) =>
          s.structured &&
          s.rank == 0 &&
          CipManifest.looksLike(namespace.templates[s.handle]!.members
              .map((m) => m['name'] as String)
              .toSet()))
      .single
      .name;
}

CipSessionEngine replayEngine(Map capture) {
  final symbol = manifestSymbolName(capture);
  final wire = ProgressingCaptureWire(capture,
      extraRecords: {symbol: canonicalManifestRecord(capture, symbol)});
  return CipSessionEngine.fromCapture(capture, wire,
      clockUs: () => wire.nowUs,
      guard: CipReadCoherenceGuard(clockUs: () => wire.nowUs));
}

void main() {
  for (final phase in ['before', 'after']) {
    test('slow acquisition checks manifest validity $phase its native reads',
        () async {
      final capture = golden.fixtures().last['capture'] as Map;
      final symbol = manifestSymbolName(capture);
      final wire = ProgressingCaptureWire(capture,
          extraRecords: {symbol: canonicalManifestRecord(capture, symbol)});
      final engine = CipSessionEngine.fromCapture(capture, wire,
          clockUs: () => wire.nowUs,
          guard: CipReadCoherenceGuard(clockUs: () => wire.nowUs));
      final slow = engine.plan.publication.fields.values
          .firstWhere((f) =>
              !f.commandOnly &&
              !f.member.isStructure &&
              !f.member.isArray &&
              f.path.split('/').length == 2)
          .path;
      engine.plan.slowPaths = {slow};
      await engine.snapshot(fastOnly: true);
      expect(engine.plan.slowAcquisitionDue, true);
      final invalid = canonicalManifestRecord({
        ...capture,
        'manifest': {...capture['manifest'] as Map, 'valid': false}
      }, symbol);
      var bodyRead = false;
      if (phase == 'before') {
        wire.raw[symbol] = invalid;
      } else {
        wire.afterDataRead = (root) {
          if (root != symbol) {
            bodyRead = true;
            wire.raw[symbol] = invalid;
          }
        };
      }
      final before = wire.reads.length;
      await expectLater(engine.acquireSlowChunk(), throwsFormatException);
      expect(wire.closed, true);
      if (phase == 'before') {
        expect(wire.reads.skip(before).every((p) => p.startsWith('$symbol.')),
            true);
      } else {
        expect(bodyRead, true);
      }
    });
  }
  test(
      'the discovered path vector is sent once per engine and re-sent by a new one',
      () async {
    final capture = golden.fixtures().last['capture'] as Map;
    final engine = replayEngine(capture);
    final traces = <Map<String, Object?>>[];
    final first = await engine.snapshot(trace: traces.add);
    final expectedPaths = engine.plan.publication.discoverPaths();
    expect(expectedPaths, isNotEmpty);
    expect(first['paths'], expectedPaths);
    final second = await engine.snapshot(trace: traces.add);
    expect(second['paths'], const []);
    for (var index = 0; index < 3; index++) {
      final later = await engine.snapshot(trace: traces.add);
      expect(later['paths'], const [], reason: 'snapshot ${index + 3}');
    }
    // A new engine is what every reconnect builds; it sends the vector again.
    final reconnected = replayEngine(capture);
    final third = await reconnected.snapshot();
    expect(third['paths'], expectedPaths);
    // The trace carries the expansion cost only on the sending snapshot.
    expect(traces.first.containsKey('pathExpansionUs'), true);
    expect(traces.first.containsKey('pathCount'), true);
    expect(traces.first['pathCount'], expectedPaths.length);
    expect(traces.last.containsKey('pathExpansionUs'), false);
    expect(traces.last.containsKey('pathCount'), false);
    // Each snapshot trace carries the walk summary: due flag, per-phase group
    // counts/durations and the multi-attempt group count (WP4b.3).
    for (final trace in traces) {
      final walk = trace['walk'];
      expect(walk, isA<Map<String, Object?>>());
      expect((walk as Map).containsKey('due'), true);
      expect((walk['phases'] as Map).containsKey('status'), true);
      expect((walk['phases'] as Map).containsKey('main'), true);
      expect(walk.containsKey('multiAttemptGroups'), true);
    }
  });

  test('a replayed snapshot reproduces the golden values and types', () async {
    final fixture = golden.fixtures().last;
    final engine = replayEngine(fixture['capture'] as Map);
    final document = await engine.snapshot();
    final expected = fixture['expected'] as Map;
    expect(document['types'], expected['types']);
    expect(document['values'], expected['values']);
  });
}
