@Tags(['live'])
library;

// One-off diagnostic against a LIVE local TF6100 (opc.tcp://127.0.0.1:4840).
// Run explicitly:
//   flutter test --tags live test/live_fieldbus_probe_test.dart
// Requires build\windows\x64\runner\Debug\fraktal_opcua.dll (flutter build).

import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:fraktal_opcua_client/opcua_native_client.dart';
import 'package:fraktal_hmi/data/opcua_repository.dart';
import 'package:fraktal_hmi/domain/fieldbus.dart';

void main() {
  test('live: manifest hydrates and fieldbus tree builds', () async {
    final dll = File('build/windows/x64/runner/Debug/fraktal_opcua.dll');
    expect(dll.existsSync(), isTrue,
        reason: 'run flutter build windows --debug first');

    final client = await NativeOpcUaClient.connect(
      Uri.parse('opc.tcp://127.0.0.1:4840'),
      timeout: const Duration(seconds: 10),
    );
    final repository = await OpcUaRepository.connectWithClient(client);
    addTearDown(repository.dispose);

    // Fieldbus I/O is on-demand: the real UI activates it when the fieldbus page
    // mounts. Do the same so the tree hydrates.
    repository.setFieldbusViewActive(true);

    final sw = Stopwatch()..start();
    var lastLog = '';
    while (sw.elapsed < const Duration(seconds: 90)) {
      final forest = await repository.forest().first;
      final bus = await repository.fieldbus().first;
      // Commands live on child modules (the root Unit's own catalog is empty).
      int countCommands(node) {
        int total = node.commands.length;
        for (final child in node.children) {
          total += countCommands(child);
        }
        return total;
      }

      final commands =
          forest.isEmpty ? -1 : forest.fold<int>(0, (t, n) => t + countCommands(n));
      final log = 'forest=${forest.length} commands=$commands '
          'busRoots=${bus.length} '
          'busNames=${bus.map((n) => n.name).join(",")}';
      if (log != lastLog) {
        // ignore: avoid_print
        print('[probe ${sw.elapsed.inSeconds}s] $log');
        lastLog = log;
      }
      if (bus.isNotEmpty && bus.first.name.isNotEmpty && commands > 0) {
        // Success: dump the tree shape once.
        void dump(BusNode node, String indent) {
          // ignore: avoid_print
          print('$indent${node.name} [${node.typeId}] '
              'ch=${node.channels.length} state=${node.state.name}');
          for (final c in node.children) {
            dump(c, '$indent  ');
          }
        }

        for (final root in bus) {
          dump(root, '  ');
        }
        return;
      }
      await Future<void>.delayed(const Duration(seconds: 1));
    }
    fail('fieldbus tree did not hydrate within 90 s — see probe log above');
  }, timeout: const Timeout(Duration(minutes: 3)));
}
