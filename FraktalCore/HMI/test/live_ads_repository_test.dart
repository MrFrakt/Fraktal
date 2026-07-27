@Tags(['live'])
library;

// Live end-to-end via the PRODUCTION code path: ConnectionSettings(ads://) ->
// createExternalRepository -> AdsSessionClient -> OpcUaRepository -> forest.
// Measures mode-change latency the operator actually feels.
//   flutter build windows --debug
//   set FRAKTAL_ADS_LIBRARY=...\fraktal_ads.dll
//   flutter test --run-skipped -t live test/live_ads_repository_test.dart

import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:fraktal_hmi/data/external_repository_factory_native.dart';
import 'package:fraktal_hmi/domain/connection_settings.dart';
import 'package:fraktal_hmi/domain/fieldbus.dart';
import 'package:fraktal_hmi/domain/types.dart';

void main() {
  test('ads repository: forest live + mode-change latency', () async {
    final dll = File('build/windows/x64/runner/Debug/fraktal_ads.dll');
    expect(dll.existsSync(), isTrue);

    // The real production entry point, with an ads:// endpoint. Override the
    // AmsNetId:port with FRAKTAL_ADS_ENDPOINT (e.g. ads://192.168.1.6.1.1:851)
    // to target a specific runtime; defaults to the loopback runtime.
    final endpoint = Platform.environment['FRAKTAL_ADS_ENDPOINT'] ??
        'ads://127.0.0.1.1.1:854';
    // ignore: avoid_print
    print('ADS endpoint: $endpoint');
    final repo = await createExternalRepository(ConnectionSettings(
      transport: ConnectionTransport.gateway,
      endpoint: endpoint,
    ));
    addTearDown(repo.dispose);

    final forest = await repo
        .forest()
        .firstWhere((f) => f.isNotEmpty)
        .timeout(const Duration(seconds: 15));
    final root = forest.first;
    // ignore: avoid_print
    print('ADS repo forest: ${root.path} children=${root.children.length} '
        'link via forest stream OK');
    expect(root.isUnit, isTrue);
    expect(root.children, isNotEmpty);

    // The mode dropdown is fed by the SupportedModes array — proof that array
    // leaves now expand and map over ADS (the reported "no mode options" bug).
    expect(root.supportedModes, isNotEmpty,
        reason: 'root Unit must publish supported modes (array expansion)');
    // ignore: avoid_print
    print('ADS supportedModes: ${root.supportedModes}');

    // The fieldbus tree fills from the manifest (static node/channel identity)
    // plus the on-demand topology scope (NodeCount + live State/LinkOk/values).
    // Activating that scope reads thousands of leaves; with batch handle
    // resolution it must complete quickly, not stall the worker.
    var bus = <BusNode>[];
    final sub = repo.fieldbus().listen((n) => bus = n);
    addTearDown(sub.cancel);
    repo.setFieldbusViewActive(true);
    addTearDown(() => repo.setFieldbusViewActive(false));
    var stable = 0, last = -1;
    final sw = Stopwatch()..start();
    while (sw.elapsed < const Duration(seconds: 20) && (bus.isEmpty || stable < 4)) {
      await Future<void>.delayed(const Duration(milliseconds: 500));
      stable = (bus.length == last) ? stable + 1 : 0;
      last = bus.length;
    }
    int countNodes(List<BusNode> ns) =>
        ns.fold(0, (n, b) => n + 1 + countNodes(b.children));
    int countChannels(List<BusNode> ns) =>
        ns.fold(0, (n, b) => n + b.channels.length + countChannels(b.children));
    // ignore: avoid_print
    print('ADS fieldbus roots: ${bus.length} totalNodes=${countNodes(bus)} '
        'totalChannels=${countChannels(bus)} '
        'firstNode=${bus.isEmpty ? "-" : bus.first.name} '
        'settleMs=${sw.elapsedMilliseconds}');
    expect(bus, isNotEmpty, reason: 'fieldbus tree must populate over ADS');

    // Steady state (manifest hydrated): mode-change round trips over ADS.
    final latencies = <int>[];
    var mode = UnitMode.auto;
    for (var i = 0; i < 5; i++) {
      mode = mode == UnitMode.auto ? UnitMode.manual : UnitMode.auto;
      final sw = Stopwatch()..start();
      await repo.setMode(root.path, mode);
      latencies.add(sw.elapsedMilliseconds);
      await Future<void>.delayed(const Duration(milliseconds: 200));
    }
    latencies.sort();
    // ignore: avoid_print
    print('ADS mode-change latency ms: min=${latencies.first} '
        'median=${latencies[latencies.length ~/ 2]} max=${latencies.last}');
    expect(latencies[latencies.length ~/ 2], lessThan(200),
        reason: 'ADS command round-trip should be well under 200 ms');
  }, timeout: const Timeout(Duration(minutes: 1)));
}
