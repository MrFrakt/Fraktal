@Tags(['live'])
library;

// End-to-end command latency + fast-tier size against a live TF6100.
//   flutter build windows --debug
//   set FRAKTAL_OPCUA_LIBRARY=...\fraktal_opcua.dll
//   flutter test --run-skipped -t live test/live_command_latency_test.dart

import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:fraktal_opcua_client/opcua_native_client.dart';
import 'package:fraktal_hmi/data/opcua_repository.dart';
import 'package:fraktal_hmi/domain/types.dart';

void main() {
  test('live: mode-change round-trip latency with drill-down data off the poll',
      () async {
    final dll = File('build/windows/x64/runner/Debug/fraktal_opcua.dll');
    expect(dll.existsSync(), isTrue);
    final client = await NativeOpcUaClient.connect(
      Uri.parse('opc.tcp://127.0.0.1:4840'),
      timeout: const Duration(seconds: 10),
    );
    final repository = await OpcUaRepository.connectWithClient(client);
    addTearDown(repository.dispose);

    // Discover the first root and let the tiers + manifest settle.
    final forest =
        await repository.forest().firstWhere((f) => f.isNotEmpty).timeout(
              const Duration(seconds: 10),
            );
    final root = forest.first.path;
    await Future<void>.delayed(const Duration(seconds: 3));

    // Time several mode changes back to back (no drill-down view open).
    final latencies = <int>[];
    var mode = UnitMode.auto;
    for (var i = 0; i < 5; i++) {
      mode = mode == UnitMode.auto ? UnitMode.manual : UnitMode.auto;
      final sw = Stopwatch()..start();
      await repository.setMode(root, mode);
      latencies.add(sw.elapsedMilliseconds);
      await Future<void>.delayed(const Duration(milliseconds: 300));
    }
    latencies.sort();
    // ignore: avoid_print
    print('MODE-CHANGE latency ms: min=${latencies.first} '
        'median=${latencies[latencies.length ~/ 2]} max=${latencies.last}');
    expect(latencies[latencies.length ~/ 2], lessThan(1000),
        reason: 'median command round-trip should be well under 1 s');
  }, timeout: const Timeout(Duration(minutes: 2)));
}
