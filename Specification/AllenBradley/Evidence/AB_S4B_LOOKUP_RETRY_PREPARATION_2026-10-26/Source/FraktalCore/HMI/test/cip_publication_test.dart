import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:fraktal_opcua_client/src/cip_manifest.dart';
import 'package:fraktal_opcua_client/src/cip_namespace.dart';
import 'package:fraktal_opcua_client/src/cip_publication.dart';

List<Map> fixtures() => [
      for (final row in (jsonDecode(utf8.decode(gzip.decode(
          File('test/fixtures/cip_publication_goldens.json.gz')
              .readAsBytesSync()))) as Map)['vectors'] as List)
        row as Map
    ];
Uint8List bytes(String hex) => Uint8List.fromList([
      for (var i = 0; i < hex.length; i += 2)
        int.parse(hex.substring(i, i + 2), radix: 16)
    ]);
Map<String, Object?> copied(Map row) =>
    Map<String, Object?>.from(jsonDecode(jsonEncode(row)) as Map);
CipPublication publication(Map capture) => CipPublication(
    CipNamespace.fromCapture(capture),
    CipManifest.fromNormalized(copied(capture['manifest'] as Map)));
Map<String, Uint8List> records(Map capture) => {
      for (final row in capture['records'] as List)
        row['tag'] as String: bytes(row['rawHex'] as String)
    };

void main() {
  test(
      'all paths and types match three independent accepted Python projections',
      () {
    for (final fixture in fixtures()) {
      final capture = fixture['capture'] as Map;
      final output = publication(capture).projectRecords(records(capture));
      final expected = fixture['expected'] as Map;
      expect(output['values'], expected['values'],
          reason: fixture['name'] as String);
      expect(output['types'], expected['types']);
      expect(output['moduleCount'], expected['moduleCount']);
      expect(output['commandArguments'], expected['commandArguments']);
      expect(output['nodeCount'], expected['nodeCount']);
      expect(
          output['readCoherenceBindings'], expected['readCoherenceBindings']);
    }
  });
  test('command-only bytes and unbound records are refused before decode', () {
    final capture = fixtures().last['capture'] as Map,
        p = publication(capture),
        raw = records(capture);
    final endpoint =
        (p.manifest.rows('commandBindings').first)['PayloadSymbol'] as String;
    expect(() => p.projectRecords({...raw, endpoint: Uint8List(1)}),
        throwsFormatException);
    expect(() => p.projectRecords({...raw, 'UnpublishedContext': Uint8List(1)}),
        throwsFormatException);
    raw.remove(raw.keys.first);
    expect(() => p.projectRecords(raw), throwsFormatException);
  });
  test(
      'record extents and root identity cannot be guessed or partially decoded',
      () {
    final capture = fixtures().last['capture'] as Map,
        p = publication(capture),
        raw = records(capture);
    final root = p.roots.first;
    raw[root] = Uint8List(1);
    expect(() => p.projectRecords(raw), throwsFormatException);
    final wrong = records(capture);
    wrong[root] = Uint8List(wrong[root]!.length);
    expect(() => p.projectRecords(wrong), throwsFormatException);
  });
  test('timestamp nanoseconds and signed/unsigned scalars stay exact', () {
    expect(CipPublication.scalar(0xcc, {}, BigInt.from(-1)).$1,
        '1969-12-31T23:59:59.999999999Z');
    expect(CipPublication.scalar(0xcc, {}, BigInt.from(1234567890)).$1,
        '1970-01-01T00:00:01.23456789Z');
    expect(CipPublication.scalar(0xcc, {}, BigInt.zero).$1, 0);
    expect(CipPublication.scalar(0xc9, {}, (BigInt.one << 64) - BigInt.one).$1,
        '18446744073709551615');
    expect(CipPublication.scalar(0xc4, {'logicalType': 'BITSTRING32'}, -1),
        (4294967295, 'UInt32'));
    expect(() => CipPublication.scalar(0xc4, {'logicalType': 'UINT16'}, 65536),
        throwsFormatException);
  });
}
