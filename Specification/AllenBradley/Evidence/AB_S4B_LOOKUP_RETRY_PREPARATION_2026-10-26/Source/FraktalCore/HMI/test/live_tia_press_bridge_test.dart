@Tags(['live'])
library;

// Opt-in commissioning observation. Uses the normal repository and CPU Web API
// client; sends no equipment command or configuration change. The bridge's
// physical output wiring gates must remain disabled.
import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:fraktal_opcua_client/fraktal_opcua_client.dart';
import 'package:fraktal_hmi/data/opcua_repository.dart';
import 'package:fraktal_hmi/domain/fieldbus.dart';

void main() {
  final env = Platform.environment;
  test('press bridge: live input tree with unconfirmed physical outputs', () async {
    final connected = env['FRAKTAL_TIA_BRIDGE_EXPECT_CONNECTED'] != '0';
    final expectedState = connected ? NodeState.operational : NodeState.offline;
    const host = '169.254.212.61'; // FraktalBench X2; X1 is 192.168.0.20.
    final transport = HttpsWebApiTransport(
        host: host,
        pinnedCertificate: File(env['FRAKTAL_TIA_BRIDGE_CERT']!).readAsBytesSync());
    final client = await WebApiSessionClient.connect(
        transport: transport,
        user: 'fraktal',
        password: env['FRAKTAL_TIA_WEB_PASSWORD']!);
    final repository = await OpcUaRepository.connectWithClient(client);
    var bus = const <BusNode>[];
    final subscription = repository.fieldbus().listen((nodes) => bus = nodes);
    Iterable<BusNode> walk(List<BusNode> nodes) sync* {
      for (final node in nodes) {
        yield node;
        yield* walk(node.children);
      }
    }

    try {
      expect(repository.fieldbusExpected, isTrue);
      repository.setFieldbusViewActive(true);
      final deadline = Stopwatch()..start();
      while ((walk(bus).length != 3 ||
              !walk(bus).every((n) => n.linkOk == connected && n.state == expectedState)) &&
          deadline.elapsed < const Duration(minutes: 3)) {
        await Future<void>.delayed(const Duration(milliseconds: 100));
      }
      final nodes = walk(bus).toList();
      expect(nodes, hasLength(3));
      expect(nodes.every((n) => n.linkOk == connected && n.state == expectedState), isTrue);
      final channels = nodes.expand((n) => n.channels).toList();
      final inputs = channels.where((c) => c.dir == ChannelDir.input).toList();
      final outputs = channels.where((c) => c.dir == ChannelDir.output).toList();
      expect(inputs, hasLength(14));
      expect(outputs, hasLength(10));
      expect(inputs.every((c) => c.quality == connected), isTrue);
      // The protocol returns DI, not the physical final DQ process image.
      expect(outputs.every((c) => !c.quality), isTrue);
      expect(channels.every((c) => !c.forceable && !c.forced), isTrue);
      final feeder = inputs.singleWhere((c) => c.name == '_101B301A');
      expect(feeder.address, '%I0.0');
      expect(feeder.modulePath, 'PressDemo.PartSlide');
      expect(inputs.any((c) => c.name == '_000K911_Y32'), isTrue);
      expect(inputs.any((c) => c.name == '_000K910A'), isTrue);
      final record = {
        'host': host,
        'expectedConnected': connected,
        'nodes': [for (final n in nodes) {'name': n.name, 'state': n.state.name, 'linkOk': n.linkOk}],
        'channels': [for (final c in channels) {
          'tag': c.name, 'address': c.address, 'module': c.modulePath,
          'dir': c.dir.name, 'value': c.boolValue, 'quality': c.quality,
          'forceable': c.forceable,
        }],
        'equipmentCommands': 0,
        'configurationChanges': 0,
      };
      File(env['FRAKTAL_TIA_BRIDGE_OUTPUT']!)
          .writeAsStringSync(const JsonEncoder.withIndent('  ').convert(record));
    } finally {
      repository.setFieldbusViewActive(false);
      await subscription.cancel();
      repository.dispose();
    }
  },
      skip: env['FRAKTAL_TIA_BRIDGE_LIVE'] == '1'
          ? false
          : 'opt-in: FRAKTAL_TIA_BRIDGE_LIVE=1 on FraktalBench only',
      timeout: const Timeout(Duration(minutes: 6)));
}
