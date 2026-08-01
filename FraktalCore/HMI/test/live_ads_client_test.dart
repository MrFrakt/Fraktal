@Tags(['live'])
library;

// Live: the Dart AdsSessionClient (FFI -> fraktal_ads.dll -> TcAdsDll) reads the
// press demo over ADS and the UNCHANGED mapper renders the forest. No TF6100.
//   flutter build windows --debug
//   set FRAKTAL_ADS_LIBRARY=...\build\windows\x64\runner\Debug\fraktal_ads.dll
//   flutter test --run-skipped -t live test/live_ads_client_test.dart

import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:fraktal_opcua_client/fraktal_opcua_client.dart';
import 'package:fraktal_hmi/data/opcua_snapshot_mapper.dart';

void main() {
  test('ads client: full module tree renders + command latency', () async {
    final dll = File('build/windows/x64/runner/Debug/fraktal_ads.dll');
    expect(dll.existsSync(), isTrue, reason: 'run flutter build windows first');

    final client = await AdsSessionClient.connect(
      amsNetId: '127.0.0.1.1.1',
      amsPort: 854,
    );
    addTearDown(client.close);

    // 1) Snapshot + map -> forest. First call pays one-time discovery + handle
    // creation; measure steady-state (2nd+) separately.
    final sw = Stopwatch()..start();
    final doc = await client.snapshot();
    final snapMs = sw.elapsedMilliseconds;
    final steady = <int>[];
    for (var i = 0; i < 5; i++) {
      final s = Stopwatch()..start();
      await client.snapshot();
      steady.add(s.elapsedMilliseconds);
    }
    steady.sort();
    // ignore: avoid_print
    print('ADS snapshot steady-state: min=${steady.first} '
        'median=${steady[steady.length ~/ 2]}ms (first=$snapMs incl. discovery)');
    final projection = OpcUaSnapshotMapper().map(doc);
    // ignore: avoid_print
    print('ADS snapshot: ${snapMs}ms nodeCount=${doc['nodeCount']} '
        'forest=${projection.forest.length} '
        'roots=${projection.forest.map((r) => r.path).join(",")}');
    expect(projection.forest, isNotEmpty);
    final root = projection.forest.first;
    expect(root.isUnit, isTrue);
    // The forest should include the press demo's child modules (recursive walk).
    // ignore: avoid_print
    print('root ${root.path}: ${root.children.length} children '
        '[${root.children.map((c) => c.name).take(8).join(",")}]');

    // 2) Command latency: write a mailbox field by path (proves the write path).
    final base = 'PLC1/MAIN/${root.path}';
    final wsw = Stopwatch()..start();
    final ok = await client.write(
        '$base/HmiRequest/IntValue', OpcUaWriteType.int32, 1);
    // ignore: avoid_print
    print('ADS write HmiRequest/IntValue: ${wsw.elapsedMilliseconds}ms ok=$ok');
    expect(ok, isTrue);

    // 3) Targeted read (the ack-poll / on-demand path).
    final rsw = Stopwatch()..start();
    final vals = await client.readValues(['$base/Status/State']);
    // ignore: avoid_print
    print('ADS readValues 1 node: ${rsw.elapsedMilliseconds}ms '
        'value=${vals['$base/Status/State']}');
    expect(vals.containsKey('$base/Status/State'), isTrue);
  }, timeout: const Timeout(Duration(seconds: 40)));

  // Reconnect stress: each discovery creates ~2670 server value handles. Before
  // the leak fix, a reconnect orphaned the whole prior set on the PLC symbol
  // server, and a handful of cycles exhausted its handle pool
  // (CAdsWatchServerR0 "no more handles"). Here we reconnect many times on the
  // SAME client/context; every post-reconnect snapshot must still discover and
  // read cleanly, proving handles are released, not leaked.
  test('ads client: repeated reconnects do not exhaust PLC handles', () async {
    final dll = File('build/windows/x64/runner/Debug/fraktal_ads.dll');
    expect(dll.existsSync(), isTrue, reason: 'run flutter build windows first');

    final ep = Platform.environment['FRAKTAL_ADS_ENDPOINT'];
    final host = ep != null ? Uri.parse(ep).host : '127.0.0.1.1.1';
    final port = ep != null && Uri.parse(ep).hasPort ? Uri.parse(ep).port : 854;

    final client =
        await AdsSessionClient.connect(amsNetId: host, amsPort: port);
    addTearDown(client.close);

    const cycles = 6; // ~16k handle-creations if leaked; past a typical pool
    var lastNodeCount = 0;
    for (var i = 0; i < cycles; i++) {
      final sw = Stopwatch()..start();
      await client.reconnect();
      final doc = await client.snapshot(); // triggers a fresh discover()
      final nodeCount = (doc['nodeCount'] as num?)?.toInt() ?? 0;
      // ignore: avoid_print
      print(
          'reconnect cycle $i: nodeCount=$nodeCount ${sw.elapsedMilliseconds}ms');
      expect(nodeCount, greaterThan(0),
          reason: 'reconnect cycle $i produced an empty snapshot '
              '(handle pool likely exhausted)');
      if (i == 0) {
        lastNodeCount = nodeCount;
      } else {
        expect(nodeCount, lastNodeCount,
            reason: 'discovery drifted across reconnects at cycle $i');
      }
    }
    // ignore: avoid_print
    print('ADS reconnect stress: $cycles cycles clean, '
        'stable nodeCount=$lastNodeCount');
  }, timeout: const Timeout(Duration(seconds: 120)));
}
