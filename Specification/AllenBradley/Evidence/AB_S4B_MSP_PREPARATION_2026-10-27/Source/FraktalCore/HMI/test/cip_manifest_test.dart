import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:fraktal_opcua_client/src/cip_manifest.dart';
import 'package:fraktal_opcua_client/src/cip_template.dart';

List<Map> vectors() => [
      for (final row in (jsonDecode(utf8.decode(gzip.decode(
          File('test/fixtures/cip_publication_goldens.json.gz')
              .readAsBytesSync()))) as Map)['vectors'] as List)
        row as Map
    ];
Map<String, Object?> copy(Map value) =>
    Map<String, Object?>.from(jsonDecode(jsonEncode(value)) as Map);

void main() {
  test('canonical hash uses exact SHA-256 and Python ASCII JSON form', () {
    expect(cipSha256(utf8.encode('abc')),
        'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad');
    expect(cipSha256([]),
        'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855');
    expect(
        cipCanonicalJson({
          'z': 'é😀',
          'a': [true, 1, null]
        }),
        r'{"a":[true,1,null],"z":"\u00e9\ud83d\ude00"}');
    expect(() => cipCanonicalJson(1.5), throwsFormatException);
  });
  test(
      'three accepted native captures validate normalized metadata and exact reconstructed headers',
      () {
    for (final vector in vectors()) {
      final capture = vector['capture'] as Map;
      final manifest =
          CipManifest.fromNormalized(copy(capture['manifest'] as Map));
      final decoder = CipTemplateDecoder.fromCapture(
          List<Object?>.from(capture['templates'] as List));
      final header = vector['physicalManifest'] as Map;
      final hex = header['rawHex'] as String;
      final raw = [
        for (var i = 0; i < hex.length; i += 2)
          int.parse(hex.substring(i, i + 2), radix: 16)
      ];
      final physical = CipManifest.fromPhysical(Map<String, Object?>.from(
          decoder.decode(header['handle'] as int, Uint8List.fromList(raw))
              as Map));
      expect(physical.document, manifest.document,
          reason: vector['name'] as String);
      expect(manifest.contentHash, (capture['manifest'] as Map)['contentHash']);
    }
  });
  test('hash, wire shape, roles and counter metadata fail closed', () {
    final original = vectors().last['capture']['manifest'] as Map;
    for (final change in [
      'hash',
      'period',
      'role',
      'unknown',
      'overlap',
      'type',
      'indices',
      'operation'
    ]) {
      final row = copy(original);
      switch (change) {
        case 'hash':
          row['contentHash'] = List.filled(64, '0').join();
        case 'period':
          (row['readCoherenceBindings'] as List).first['MutationPeriodUs'] = 0;
        case 'role':
          (row['commandBindings'] as List).first['ReadRole'] = 'Live';
        case 'unknown':
          row['unpublishedStationFact'] = 'Press';
        case 'overlap':
          (row['readCoherenceBindings'] as List).last['CanonicalPrefix'] =
              'Press/Other';
        case 'type':
          (row['typeAnnotations'] as List).first['ElementCount'] = true;
        case 'indices':
          (row['pathExceptions'] as List).first['Indices'] = '[1,1]';
        case 'operation':
          (row['commandOperations'] as List).removeLast();
      }
      expect(() => CipManifest.fromNormalized(row), throwsFormatException,
          reason: change);
    }
  });
  test(
      'negotiated nested metadata is immutable and independent of caller input',
      () {
    final row = copy(vectors().last['capture']['manifest'] as Map);
    final manifest = CipManifest.fromNormalized(row);
    (row['readCoherenceBindings'] as List).first['RevisionSymbol'] = 'Wrong';
    expect(manifest.coherence.first.revisionSymbol, isNot('Wrong'));
    expect(() => (manifest.document['readCoherenceBindings'] as List).clear(),
        throwsUnsupportedError);
    expect(
        () => (manifest.document['readCoherenceBindings'] as List)
            .first['Protocol'] = 2,
        throwsUnsupportedError);
  });
}
