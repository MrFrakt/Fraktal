import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:fraktal_opcua_client/src/cip_namespace.dart';
import 'package:fraktal_opcua_client/src/cip_transport.dart';

List<Map<String, Object?>> recorded() => [
      for (final t in (jsonDecode(utf8.decode(gzip.decode(
          File('test/fixtures/cip_namespace_goldens.json.gz')
              .readAsBytesSync()))) as Map)['templates'] as List)
        Map<String, Object?>.from(t as Map)
    ];
Uint8List hexBytes(String hex) => Uint8List.fromList([
      for (var i = 0; i < hex.length; i += 2)
        int.parse(hex.substring(i, i + 2), radix: 16)
    ]);
Uint8List u32(int n) =>
    (ByteData(4)..setUint32(0, n, Endian.little)).buffer.asUint8List();

class DefinitionWire implements CipReadTransport {
  final Map<int, Map<String, Object?>> templates = {
    for (final t in recorded()) t['handle'] as int: t
  };
  final int fragmentBytes;
  final List<(int, int, int)> definitionReads = [];
  String? fault;
  DefinitionWire({this.fragmentBytes = 65535, this.fault});
  @override
  Future<CipReply> request(int service, Uint8List path,
      [Uint8List? payload]) async {
    if (service == 0x55) {
      final data = BytesBuilder();
      var instance = 1;
      for (final row in templates.values) {
        final name = utf8.encode('Recorded_${row['handle']}');
        data.add([
          ...u32(instance++),
          ...cipWords([name.length]),
          ...name,
          ...cipWords([0x8000 | (row['handle'] as int)])
        ]);
      }
      return CipReply(0, [], data.takeBytes());
    }
    final handle = path[2] == 0x24
            ? path[3]
            : ByteData.sublistView(path).getUint16(4, Endian.little),
        row = templates[handle]!;
    if (service == 3) {
      expect(payload, cipWords([4, 4, 5, 2, 1]));
      return CipReply(
          0,
          [],
          Uint8List.fromList([
            ...cipWords([4, 4, 0]),
            ...u32(row['definitionWords'] as int),
            ...cipWords([5, 0]),
            ...u32(row['byteSize'] as int),
            ...cipWords([
              2,
              0,
              row['memberCount'] as int,
              1,
              0,
              row['structureHandle'] as int
            ])
          ]));
    }
    expect(service, 0x4c);
    final requested = ByteData.sublistView(payload!),
        offset = requested.getUint32(0, Endian.little),
        count = requested.getUint16(4, Endian.little);
    definitionReads.add((handle, offset, count));
    final raw = hexBytes(row['definitionHex'] as String);
    if (fault == 'empty') return CipReply(6, [], Uint8List(0));
    if (fault == 'overrun') return CipReply(0, [], Uint8List(count + 1));
    if (fault == 'missing-nul' && row['name'] == 'FRK_T_S0S_Page') {
      final start = (row['definitionWords'] as int) * 4 - 23;
      for (var i = start; i < raw.length; i++) raw[i] = 65;
    }
    final available = raw.length - offset;
    final size = count < available ? count : available;
    final take = size < fragmentBytes ? size : fragmentBytes;
    return CipReply(take < size ? 6 : 0, [],
        Uint8List.fromList(raw.sublist(offset, offset + take)));
  }

  @override
  void abort() {}
  @override
  Future<void> close() async {}
}

void main() {
  test(
      'native definitions whose last NUL lies beyond the formula extent require the complete DINT',
      () async {
    final examples = recorded().where(
        (r) => const {'FRK_T_S0S_Page', 'FRK_T_S0S_Block'}.contains(r['name']));
    for (final row in examples) {
      final raw = hexBytes(row['definitionHex'] as String),
          documented = (row['definitionWords'] as int) * 4 - 23;
      expect(raw[documented], 0,
          reason:
              'Native last-member terminator is outside an unrounded request');
      expect(raw.length, documented + 3);
    }
    final wire = DefinitionWire(), ns = await CipNamespace.discover(wire);
    expect(ns.templates.length, 10);
    for (final row in recorded()) {
      final type = ns.templates[row['handle']]!;
      expect(type.name, row['name']);
      expect(type.byteSize, row['byteSize']);
      expect({
        for (final m in type.members) m['name']: m
      }, {
        for (final m in row['expectedMembers'] as List) (m as Map)['name']: m
      });
      final request =
          wire.definitionReads.firstWhere((r) => r.$1 == row['handle']);
      expect(request.$3, hexBytes(row['definitionHex'] as String).length);
    }
  });
  test(
      'fragmented native definition replies preserve every member name and offset',
      () async {
    final wire = DefinitionWire(fragmentBytes: 13),
        ns = await CipNamespace.discover(wire);
    for (final row in recorded()) {
      expect({
        for (final m in ns.templates[row['handle']]!.members) m['name']: m
      }, {
        for (final m in row['expectedMembers'] as List) (m as Map)['name']: m
      });
    }
    expect(wire.definitionReads.any((r) => r.$2 > 0), true);
  });
  test(
      'missing terminator still refuses with bounded Template/offset diagnostics',
      () async {
    await expectLater(
        CipNamespace.discover(DefinitionWire(fault: 'missing-nul')),
        throwsA(isA<FormatException>().having(
            (e) => e.message,
            'diagnostic',
            allOf(contains('0x3e2'), contains('allocation=36'),
                contains('tail=')))));
  });
  test('empty or oversized definition fragments never become partial metadata',
      () async {
    for (final fault in ['empty', 'overrun']) {
      await expectLater(CipNamespace.discover(DefinitionWire(fault: fault)),
          throwsFormatException);
    }
  });
}
