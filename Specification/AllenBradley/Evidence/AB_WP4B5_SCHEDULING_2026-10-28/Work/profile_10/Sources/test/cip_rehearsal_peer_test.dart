import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:fraktal_opcua_client/src/cip_manifest.dart';
import 'package:fraktal_opcua_client/src/cip_namespace.dart';
import 'package:fraktal_opcua_client/src/cip_session_client.dart';
import 'package:fraktal_opcua_client/src/cip_transport.dart';
import 'package:fraktal_hmi/data/opcua_field_tier.dart';
import 'package:fraktal_hmi/data/opcua_session_client.dart';

import '../tool/cip_rehearsal_peer.dart' as peer;
import 'cip_publication_test.dart' as golden;

const _sealedCapturePath =
    '../../Specification/AllenBradley/Evidence/AB_S4B_READER_RUNTIME_2026-10-26'
    '/Runtime/generic_capture.json.gz';
const _sealedCaptureSha256 =
    'b0ebfbd06853fbaf1262c3b74549f88f99bd9af37e1585844dc5b9a4291afb4a';

Map _sealed(String name) => jsonDecode(utf8.decode(gzip.decode(File(
        '../../Specification/AllenBradley/Evidence/AB_S4B_READER_RUNTIME_2026-10-26/Runtime/$name')
    .readAsBytesSync()))) as Map;

String _manifestSymbolNameOf(CipNamespace namespace) => namespace.symbols.values
    .where((s) =>
        s.structured &&
        s.rank == 0 &&
        CipManifest.looksLike(namespace.templates[s.handle]!.members
            .map((m) => m['name'] as String)
            .toSet()))
    .single
    .name;

void main() {
  test(
      'sealed physical configuration bytes reconstruct every accepted read-only bank',
      () async {
    final server = await peer.RehearsalPeer.start(
        capturePath: _sealedCapturePath,
        expectSha256: _sealedCaptureSha256,
        delayScale: 0);
    addTearDown(server.close);
    final client = await CipSessionClient.connect(
        host: '127.0.0.1',
        port: server.port,
        slot: 0,
        expectSerial: '601FC87B');
    addTearDown(client.close);
    final report = _sealed('dart_qualification.json.gz');
    for (final expected in (report['configurationPages'] as List).cast<Map>()) {
      final actual = await client.readConfigurationPage(
          expected['root'] as String, expected['modelOrdinal'] as int);
      expect(actual, expected['page']);
    }
    expect(server.refusedServices, 0);
  });
  test('fractional model delays never return before their monotonic deadline',
      () async {
    final server = await peer.RehearsalPeer.start(
        capturePath: _sealedCapturePath,
        expectSha256: _sealedCaptureSha256,
        seed: 7);
    addTearDown(server.close);
    final client = await CipSocketTransport.connect(
        host: '127.0.0.1',
        port: server.port,
        slot: 0,
        expectSerial: '601FC87B');
    addTearDown(client.close);
    for (var i = 0; i < 20; i++) {
      await CipNamespace.readDint(client, server.counters.single);
    }
    expect(server.delayTimingsUs, isNotEmpty);
    expect(server.delayTimingsUs.every((p) => p[0] > 0 && p[1] >= p[0]), true);
    expect(server.refusedServices, 0);
  });
  test('sha256 matches a known vector', () {
    // echo -n "" | sha256sum
    expect(peer.hexOf(peer.sha256Of(Uint8List(0))),
        'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855');
    expect(peer.hexOf(peer.sha256Of(Uint8List.fromList(utf8.encode('abc')))),
        'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad');
    expect(
        peer.hexOf(peer.sha256Of(File(_sealedCapturePath).readAsBytesSync())),
        _sealedCaptureSha256);
  });

  test('a changed capture is refused before opening a listener', () async {
    await expectLater(
        peer.RehearsalPeer.start(
            capturePath: _sealedCapturePath, expectSha256: '0' * 64),
        throwsFormatException);
  });
  test('rehearsal refuses the real controller port and invalid delay scales',
      () async {
    for (final value in [-1.0, double.nan, double.infinity]) {
      await expectLater(
          peer.RehearsalPeer.start(
              capturePath: _sealedCapturePath, delayScale: value),
          throwsFormatException);
    }
    await expectLater(
        peer.RehearsalPeer.start(capturePath: _sealedCapturePath, port: 44818),
        throwsFormatException);
  });

  for (final (name, capture) in [
    ('golden', golden.fixtures().last['capture'] as Map),
    (
      'sealed',
      jsonDecode(utf8.decode(
          gzip.decode(File(_sealedCapturePath).readAsBytesSync()))) as Map
    ),
  ]) {
    test('the re-encoded $name manifest record decodes to the same manifest',
        () {
      final namespace = CipNamespace.fromCapture(capture);
      final symbolName = _manifestSymbolNameOf(namespace);
      final symbol = namespace.symbols[symbolName]!;
      final bytes = peer.encodeManifestRecordFrom(
          namespace, symbolName, capture['manifest'] as Map);
      expect(bytes.length, namespace.templates[symbol.handle]!.byteSize);
      final decoded =
          namespace.decoderFor([symbol.handle]).decode(symbol.handle, bytes);
      final manifest =
          CipManifest.fromPhysical(decoded as Map<String, Object?>);
      // fromPhysical owns a deep copy; compare against the capture manifest
      // re-encoded through the same JSON canonicalization.
      final expected = CipManifest.fromNormalized(Map<String, Object?>.from(
          jsonDecode(jsonEncode(capture['manifest'])) as Map));
      expect(manifest.revision, expected.revision);
      expect(manifest.rows('readCoherenceBindings'),
          expected.rows('readCoherenceBindings'));
      expect(manifest.rows('typeAnnotations').length,
          expected.rows('typeAnnotations').length);
      expect(manifest.rows('bindings'), expected.rows('bindings'));
      expect(
          manifest.rows('services').length, expected.rows('services').length);
      expect(manifest.rows('commandBindings').length,
          expected.rows('commandBindings').length);
    });
  }

  for (final (name, capture, expected) in [
    (
      'golden',
      golden.fixtures().last['capture'] as Map,
      golden.fixtures().last['expected'] as Map
    ),
    (
      'sealed',
      _sealed('generic_capture.json.gz'),
      _sealed('generic_snapshot.json.gz')
    ),
  ]) {
    test('the rehearsal peer serves $name wire discovery and live snapshots',
        () async {
      final temp = Directory.systemTemp.createTempSync('fraktal_peer');
      addTearDown(() => temp.deleteSync(recursive: true));
      final capturePath = '${temp.path}/capture.json';
      File(capturePath).writeAsStringSync(jsonEncode(capture));
      final server = await peer.RehearsalPeer.start(
          capturePath: name == 'sealed' ? _sealedCapturePath : capturePath,
          expectSha256: name == 'sealed' ? _sealedCaptureSha256 : null,
          seed: 1,
          delayScale: 0);
      addTearDown(server.close);
      final client = await CipSessionClient.connect(
          host: '127.0.0.1',
          port: server.port,
          slot: 0,
          expectSerial: '601FC87B',
          timeout: const Duration(seconds: 30));
      addTearDown(client.close);
      final paths = await client.discoverPaths();
      final excluded = <String>{}, slow = <String>{};
      final readServices = [
        for (final row
            in (capture['manifest'] as Map)['readServices'] as List? ?? [])
          (row as Map)['CanonicalRoot'] as String
      ];
      // Production applies view gating before its first acquisition. The full
      // history tree is not a cyclic read or a first-snapshot freshness claim.
      for (final path in paths) {
        if (readServices
                .any((root) => path == root || path.startsWith('$root/')) ||
            OpcUaFieldTier.isRequestPayload(path) ||
            OpcUaFieldTier.isManifestServed(path, hydratedPaths: const {})) {
          excluded.add(path);
        } else {
          switch (OpcUaFieldTier.classify(path)) {
            case FieldTier.onDemand:
              excluded.add(path);
            case FieldTier.slow:
              slow.add(path);
            case FieldTier.config:
            case FieldTier.live:
              break;
          }
        }
      }
      if (name == 'sealed') {
        expect(client.readTiersAreAtomic, true);
        await client.setReadTiers(slow, excluded);
        await expectLater(
            client.setReadTiers([excluded.first], [excluded.first]),
            throwsA(isA<OpcUaTransportException>()));
      } else {
        await client.setSlowPaths(slow);
        await client.setExcludedPaths(excluded);
      }
      var document = await client.snapshot();
      expect(document['paths'], isNotEmpty);
      // The first fast envelope may precede its independently scheduled slow
      // chunks. Bound bootstrap and still require the complete sealed values.
      final expectedCount = (expected['values'] as Map)
          .keys
          .where((path) => !excluded.contains(path))
          .length;
      for (var i = 0;
          i < 5 && (document['values'] as Map).length < expectedCount;
          i++) {
        document = await client.snapshot();
      }
      final refused = {
        for (final entry in (document['dataValues'] as Map).entries)
          if ((entry.value as Map)['status'] != 0)
            entry.key: (entry.value as Map)['reason']
      };
      expect(refused, isEmpty,
          reason: 'Wire rehearsal must prove each golden row.');
      for (final key in ['types', 'values']) {
        expect(document[key], {
          for (final entry in (expected[key] as Map).entries)
            if (!excluded.contains(entry.key)) entry.key: entry.value
        });
      }
      final next = await client.snapshot();
      expect(next['paths'], isEmpty);
      expect(next['types'], document['types']);
      expect(next['values'], document['values']);
      expect(server.readRequests, greaterThan(0));
      expect(server.refusedServices, 0);
    }, timeout: const Timeout(Duration(minutes: 2)));
  }
}
