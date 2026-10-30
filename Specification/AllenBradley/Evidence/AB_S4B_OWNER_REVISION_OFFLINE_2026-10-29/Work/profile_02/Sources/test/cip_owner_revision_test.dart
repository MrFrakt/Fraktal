import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:fraktal_opcua_client/src/cip_manifest.dart';
import 'package:fraktal_opcua_client/src/cip_namespace.dart';
import 'package:fraktal_opcua_client/src/cip_read_plan.dart';
import 'package:fraktal_opcua_client/src/cip_read_coherence.dart';
import 'package:fraktal_opcua_client/src/cip_session_client.dart';
import 'package:fraktal_opcua_client/src/cip_transport.dart';

import '../tool/cip_rehearsal_peer.dart' as peer;
import 'cip_publication_test.dart' as golden;
import 'cip_read_plan_test.dart' show CaptureWire;

Map fixture() => jsonDecode(utf8.decode(gzip.decode(
    File('test/fixtures/cip_owner_apparatus_v610.json.gz')
        .readAsBytesSync()))) as Map;

/// Independent address resolver retains sealed native product bytes. Owner
/// tokens are stable; scan progress is controlled separately by each case.
class OwnerWire extends CaptureWire {
  int nowUs = 0, progress = 2;
  bool invalid = false;
  final Set<String> owners;
  OwnerWire(Map capture)
      : owners = {
          for (final r in capture['manifest']['ownerReadBindings'] as List)
            r['RevisionSymbol'] as String
        },
        super(capture);
  @override
  Future<CipReply> request(int service, Uint8List encoded,
      [Uint8List? data]) async {
    nowUs += 300;
    final name = path(encoded).singleOrNull?.$1;
    if (name != null && !raw.containsKey(name)) {
      reads.add(name);
      final token = invalid
          ? -1
          : owners.contains(name)
              ? 2
              : progress;
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
    return super.request(service, encoded, data);
  }
}

Map<String, Object?> rehashed(Map source) {
  final d = golden.copied(source);
  final body = Map<String, Object?>.from(d)
    ..remove('valid')
    ..remove('truncated')
    ..remove('contentHash')
    ..remove('configRevision')
    ..remove('fragmentRevision');
  final hash = cipSha256(utf8.encode(cipCanonicalJson(body))).toUpperCase();
  d['contentHash'] = hash;
  final revision = int.parse(hash.substring(0, 7), radix: 16);
  d['configRevision'] = revision == 0 ? 1 : revision;
  return d;
}

void main() {
  test('V6.10 peer discovers owner symbols and serves read-only configuration',
      () async {
    final server = await peer.RehearsalPeer.start(
        capturePath: 'test/fixtures/cip_owner_apparatus_v610.json.gz',
        delayScale: 0);
    addTearDown(server.close);
    final wire = await CipSocketTransport.connect(
        host: '127.0.0.1', port: server.port, expectSerial: '601FC87B');
    addTearDown(wire.close);
    final name = server.ownerCounters.first;
    expect(await CipNamespace.readDint(wire, name), 2);
    await Future<void>.delayed(const Duration(milliseconds: 20));
    expect(await CipNamespace.readDint(wire, name), 2);
    final client = await CipSessionClient.connect(
        host: '127.0.0.1',
        port: server.port,
        slot: 0,
        expectSerial: '601FC87B');
    addTearDown(client.close);
    final page = await client.readConfigurationPage('Press', 0);
    expect(page, isNotNull);
    expect(server.refusedServices, 0);
  }, timeout: const Timeout(Duration(minutes: 2)));

  test(
      'synthetic metadata preserves all sealed native product bytes and values',
      () {
    final c = fixture();
    expect(c['apparatus']['nativeCapture'], false);
    final original = jsonDecode(utf8.decode(gzip.decode(File(
            '../../Specification/AllenBradley/Evidence/AB_S4B_READER_RUNTIME_2026-10-26/Runtime/generic_capture.json.gz')
        .readAsBytesSync()))) as Map;
    expect(c['records'], original['records']);
    final actual = golden.publication(c).projectRecords(golden.records(c));
    final old =
        golden.publication(original).projectRecords(golden.records(original));
    expect(actual['values'], old['values']);
    expect(actual['types'], old['types']);
    expect(actual['nodeCount'], 5407);
    final ns = CipNamespace.fromCapture(c);
    final symbol = ns.symbols.values.singleWhere((s) =>
        s.structured &&
        CipManifest.looksLike(ns.templates[s.handle]!.members
            .map((m) => m['name'] as String)
            .toSet()));
    final physical = ns.decoderFor([symbol.handle]).decode(
        symbol.handle,
        peer.encodeManifestRecordFrom(
            ns, symbol.name, c['manifest'] as Map)) as Map;
    expect(
        CipManifest.fromPhysical(Map<String, Object?>.from(physical)).document,
        golden.publication(c).manifest.document);
  });

  test('correctly rehashed but forged owner selections and scan aliases refuse',
      () {
    final c = fixture();
    expect(
        CipManifest.fromNormalized(rehashed(c['manifest'] as Map)).minor, 10);
    for (final change in [
      'scan-alias',
      'missing',
      'extra',
      'wrong-symbol-type',
      'member'
    ]) {
      final bad = golden.copied(c);
      final rows = (bad['manifest'] as Map)['ownerReadBindings'] as List;
      switch (change) {
        case 'scan-alias':
          rows.first['RevisionSymbol'] = rows.first['ProgressSymbol'];
        case 'missing':
          rows.removeLast();
        case 'extra':
          rows.first['CanonicalPrefix'] = 'Press/Other/Status';
        case 'wrong-symbol-type':
          (bad['symbols'] as List).singleWhere(
                  (s) => s['name'] == rows.first['RevisionSymbol'])['atomic'] =
              0xc3;
        case 'member':
          rows.first['MembersJson'] = '["Name","ModuleType","State"]';
      }
      bad['manifest'] = rehashed(bad['manifest'] as Map);
      expect(() => golden.publication(bad), throwsFormatException,
          reason: change);
    }
  });

  test(
      'mixed Status owners partition, preserve read-start age, and cannot hide frozen progress',
      () async {
    final c = fixture(), pub = golden.publication(c), wire = OwnerWire(c);
    final plan = CipReadPlan(pub, wire,
        clockUs: () => wire.nowUs,
        guard:
            CipReadCoherenceGuard(maxAttempts: 20, clockUs: () => wire.nowUs));
    await plan.refreshProgress();
    wire.progress = 4;
    final start = wire.nowUs;
    await plan.acquire(paths: {'Press/Status'});
    var samples = plan.snapshot()['dataValues'] as Map;
    expect(samples['Press/Status/Name']['status'], 0);
    expect(samples['Press/Status/FaultActive']['status'], 0);
    expect(
        wire.reads, contains(pub.manifest.ownerCoherence.first.revisionSymbol));
    expect(wire.reads, contains(pub.manifest.coherence.first.revisionSymbol));
    expect(samples['Press/Status/Name']['ageMs'], greaterThan(0));
    expect(wire.nowUs, greaterThan(start));
    wire.nowUs += 1100000;
    await plan.acquire(paths: {'Press/Status/Name'});
    samples = plan.snapshot()['dataValues'] as Map;
    expect(samples['Press/Status/Name']['status'], 0x40000000);
    expect(samples['Press/Status/Name'].containsKey('value'), false);
    expect((plan.snapshot()['values'] as Map).containsKey('Press/Status/Name'),
        false);
    wire.progress = 6;
    await plan.acquire(paths: {'Press/Status/Name'});
    expect(
        (plan.snapshot()['dataValues'] as Map)['Press/Status/Name']['status'],
        0);
  });

  test('invalid independent progress retires the transport before body reads',
      () async {
    final c = fixture(), wire = OwnerWire(c)..invalid = true;
    final plan =
        CipReadPlan(golden.publication(c), wire, clockUs: () => wire.nowUs);
    await expectLater(
        plan.acquire(paths: {'Press/Status/Name'}), throwsFormatException);
    expect(wire.closed, true);
    expect(wire.reads.every((p) => !p.contains('.Status')), true);
  });
}
