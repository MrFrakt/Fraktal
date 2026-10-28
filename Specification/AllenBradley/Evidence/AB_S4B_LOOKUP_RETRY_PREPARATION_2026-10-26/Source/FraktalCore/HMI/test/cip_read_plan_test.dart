import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:fraktal_opcua_client/src/cip_read_plan.dart';
import 'package:fraktal_opcua_client/src/cip_read_coherence.dart';
import 'package:fraktal_opcua_client/src/cip_transport.dart';
import 'package:fraktal_opcua_client/src/cip_template.dart';

import 'cip_publication_test.dart' as golden;

/// Independent address resolver over accepted native bytes. It knows no
/// canonical paths, array corrections or manifest annotation semantics.
class CaptureWire implements CipReadTransport {
  final Map capture;
  final Map<String, Uint8List> raw;
  final Map<int, Map> templates;
  final Map<String, Map> symbols;
  final List<String> reads = [];
  final Map<String, int> ticks = {};
  bool closed = false, frozen = false, torn = false;
  CaptureWire(this.capture)
      : raw = golden.records(capture),
        templates = {
          for (final t in capture['templates'] as List)
            t['handle'] as int: t as Map
        },
        symbols = {
          for (final s in capture['symbols'] as List)
            s['name'] as String: s as Map
        };
  List<(String, int?)> path(Uint8List bytes) {
    final out = <(String, int?)>[];
    for (var at = 0; at < bytes.length;) {
      final kind = bytes[at++];
      if (kind == 0x91) {
        final n = bytes[at++];
        out.add((String.fromCharCodes(bytes.sublist(at, at + n)), null));
        at += n + n % 2;
      } else {
        final b = ByteData.sublistView(bytes);
        late int index;
        if (kind == 0x28) {
          index = bytes[at++];
        } else if (kind == 0x29) {
          at++;
          index = b.getUint16(at, Endian.little);
          at += 2;
        } else if (kind == 0x2a) {
          at++;
          index = b.getUint32(at, Endian.little);
          at += 4;
        } else {
          throw FormatException('Unexpected path segment $kind');
        }
        final last = out.removeLast();
        out.add((last.$1, index));
      }
    }
    return out;
  }

  @override
  Future<CipReply> request(int service, Uint8List encoded,
      [Uint8List? data]) async {
    if (closed) throw StateError('closed');
    expect(service, 0x52);
    final parts = path(encoded), root = parts.first.$1;
    reads.add(
        parts.map((p) => p.$1 + (p.$2 == null ? '' : '[${p.$2}]')).join('.'));
    if (!raw.containsKey(root)) {
      expect(parts.length, 1);
      final n = ticks.update(root, (n) => n + 1, ifAbsent: () => 0);
      final token = frozen
          ? 2
          : torn
              ? 2 + 2 * n
              : 2 + 2 * (n ~/ 2);
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
    var handle = symbols[root]!['handle'] as int, offset = 0;
    int? atomic;
    var size = templates[handle]!['byteSize'] as int;
    for (final part in parts.skip(1)) {
      final member = (templates[handle]!['members'] as List)
          .cast<Map>()
          .singleWhere((m) => m['name'] == part.$1);
      final code = member['code'] as int, info = member['info'] as int;
      offset += member['offset'] as int;
      final structure = code & 0x8000 != 0, array = code & 0x6000 != 0;
      if (structure) {
        handle = code & 0xfff;
        size = templates[handle]!['byteSize'] as int;
        atomic = null;
      } else {
        atomic = code & 0xff;
        size = atomic == 0xc1 ? 1 : CipTemplateDecoder.atomicByteSize(atomic);
      }
      if (part.$2 != null) {
        offset += part.$2! * size;
      } else if (array) {
        size *= ByteData.sublistView(data!).getUint16(0, Endian.little);
      }
      if (atomic == 0xc1 && !array) {
        final value = (raw[root]![offset + info ~/ 8] >> (info % 8)) & 1;
        return CipReply(0, [], Uint8List.fromList([0xc1, 0, value]));
      }
    }
    final header = atomic == null
        ? [
            0xa0,
            2,
            ...cipWords([templates[handle]!['structureHandle'] as int? ?? 0])
          ]
        : [atomic, 0];
    final at = ByteData.sublistView(data!).getUint32(2, Endian.little);
    final available = size - at, take = available > 3000 ? 3000 : available;
    return CipReply(
        take < available ? 6 : 0,
        [],
        Uint8List.fromList([
          ...header,
          ...raw[root]!.sublist(offset + at, offset + at + take)
        ]));
  }

  @override
  void abort() => closed = true;
  @override
  Future<void> close() async {
    closed = true;
  }
}

void main() {
  test('tier scopes preserve exact ancestors and array-row boundaries',
      () async {
    final fixture = golden.fixtures().last, capture = fixture['capture'] as Map;
    final pub = golden.publication(capture), wire = CaptureWire(capture);
    final plan = CipReadPlan(pub, wire,
        clockUs: () => 0, guard: CipReadCoherenceGuard(clockUs: () => 0));
    await plan.acquire();
    await plan.acquire();
    final expected = Map<String, Object?>.from(
        (fixture['expected'] as Map)['values'] as Map);
    final root = pub.roots.first;
    final indexed = expected.keys.firstWhere((p) => p.contains('['));
    final array = indexed.substring(0, indexed.indexOf('['));
    final row = indexed.substring(0, indexed.indexOf(']') + 1);
    for (final scopes in [
      {'$root/Status'},
      {array},
      {row},
      {'$root/Stat', '$root/Status/Nam', '${row}0'},
      {'$root/Status/Name', row},
    ]) {
      bool reference(String path) => scopes.any((scope) =>
          path == scope ||
          path.startsWith('$scope/') ||
          path.startsWith('$scope['));
      plan.slowPaths = scopes;
      plan.excludedPaths = scopes;
      final all = plan.snapshot(includeExcluded: true)['dataValues'] as Map;
      for (final entry in all.entries) {
        expect((entry.value as Map)['tier'],
            reference(entry.key as String) ? 'slow' : 'fast',
            reason: '${entry.key}, scopes=$scopes');
      }
      expect(plan.snapshot()['values'], {
        for (final entry in expected.entries)
          if (!reference(entry.key)) entry.key: entry.value
      });
    }
  });
  test(
      'bounded canonical groups reproduce all 4428 oracle paths and types without a frame',
      () async {
    final fixture = golden.fixtures().last, capture = fixture['capture'] as Map;
    final pub = golden.publication(capture), wire = CaptureWire(capture);
    var now = 0;
    final plan = CipReadPlan(pub, wire,
        clockUs: () => now++, guard: CipReadCoherenceGuard(clockUs: () => 0));
    await plan.acquire();
    await plan.acquire();
    final result = plan.snapshot(), expected = fixture['expected'] as Map;
    expect(result['values'], expected['values']);
    expect(result['types'], expected['types']);
    expect(
        wire.reads.any((p) =>
            p.contains('Observe') ||
            p.contains('Frame') ||
            p.contains('Secret') ||
            p.contains('TextValue')),
        false);
    expect(wire.reads.any((p) => pub.records.any((r) => r.source == p)), false,
        reason: 'No full live record acquisition');
    expect(plan.acquisitions.length, greaterThan(100));
  });
  test('torn rows lose payload and targeted reads do not fetch unrelated rows',
      () async {
    final capture = golden.fixtures().last['capture'] as Map,
        pub = golden.publication(capture),
        wire = CaptureWire(capture);
    final plan =
        CipReadPlan(pub, wire, guard: CipReadCoherenceGuard(clockUs: () => 0));
    final wanted = '${pub.roots.first}/Status/Name';
    await plan.acquire(paths: {wanted});
    await plan.acquire(paths: {wanted});
    expect((plan.snapshot()['values'] as Map)[wanted], pub.roots.first);
    expect(wire.reads.any((p) => p.contains('SequenceSteps')), false);
    wire.torn = true;
    await plan.acquire(paths: {wanted});
    expect((plan.snapshot()['values'] as Map).containsKey(wanted), false);
    expect(((plan.snapshot()['dataValues'] as Map)[wanted] as Map)['status'],
        0x40000000);
  });
  test(
      'frozen publisher never produces Good values even with equal even counters',
      () async {
    final capture = golden.fixtures().last['capture'] as Map,
        pub = golden.publication(capture),
        wire = CaptureWire(capture)..frozen = true;
    final plan =
        CipReadPlan(pub, wire, guard: CipReadCoherenceGuard(clockUs: () => 0));
    final wanted = '${pub.roots.first}/Status/Name';
    await plan.acquire(paths: {wanted});
    await plan.acquire(paths: {wanted});
    expect(plan.snapshot()['values'], isEmpty);
    expect((plan.snapshot()['dataValues'] as Map)[wanted],
        containsPair('reason', 'publisher-progress-unproved'));
  });
  test(
      'partial failure invalidates an earlier complete row and never refreshes its age',
      () async {
    final capture = golden.fixtures().last['capture'] as Map,
        pub = golden.publication(capture),
        wire = CaptureWire(capture);
    var now = 0;
    final plan = CipReadPlan(pub, wire,
        clockUs: () => now, guard: CipReadCoherenceGuard(clockUs: () => 0));
    final base = '${pub.roots.first}/Status', name = '$base/Name';
    await plan.acquire(paths: {base});
    await plan.acquire(paths: {base});
    now = 500000;
    wire.torn = true;
    await plan.acquire(paths: {name});
    expect((plan.snapshot()['values'] as Map).containsKey(name), false);
    expect(((plan.snapshot()['dataValues'] as Map)[name] as Map)['ageMs'], 500);
  });
  test(
      'excluded leaves are never read and slow rows keep their original sample age',
      () async {
    final capture = golden.fixtures().last['capture'] as Map,
        pub = golden.publication(capture),
        wire = CaptureWire(capture);
    var now = 0;
    final plan = CipReadPlan(pub, wire,
        clockUs: () => now, guard: CipReadCoherenceGuard(clockUs: () => 0));
    final base = '${pub.roots.first}/Status', name = '$base/Name';
    // Restrict this test to one consumed subtree, then exclude one leaf within
    // it: selecting its siblings must not fetch the entire physical structure.
    plan.excludedPaths = {
      for (final f in pub.fields.values)
        if (!f.path.startsWith('$base/') && f.path != base) f.path,
      name
    };
    await plan.acquire();
    expect(
        wire.reads.any((p) =>
            p == '${pub.roots.first}.Status' || p.endsWith('.Status.Name')),
        false);
    expect((plan.snapshot()['values'] as Map).containsKey(name), false);
    final selected = '$base/State';
    plan.excludedPaths = {};
    plan.slowPaths = {base};
    await plan.acquire(paths: {base});
    await plan.acquire(paths: {base});
    wire.reads.clear();
    now = 1000000;
    // Explicit target requests bypass tiers; an ordinary cached snapshot does
    // not renew the age merely because the caller asks to inspect it.
    final before =
        ((plan.snapshot()['dataValues'] as Map)[selected] as Map)['ageMs'];
    expect(before, 1000);
    expect(wire.reads, isEmpty);
  });
}
