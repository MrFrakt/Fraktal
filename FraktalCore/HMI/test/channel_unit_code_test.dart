library;

// Core 0.26 - a fieldbus channel publishes its unit as a CODE (ST_IoChannel.UnitCode),
// read the same way as a configuration value's: the HMI shows its own translated
// symbol, and the legacy Unit text stands only when no code was published.

import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:fraktal_hmi/data/opcua_snapshot_mapper.dart';
import 'package:fraktal_hmi/data/sim_repository.dart';
import 'package:fraktal_hmi/domain/fieldbus.dart';
import 'package:fraktal_hmi/domain/types.dart';
import 'package:fraktal_hmi/localization/localized_text.dart';
import 'package:fraktal_hmi/state/app_state.dart';
import 'package:fraktal_hmi/ui/app_theme.dart';
import 'package:fraktal_hmi/ui/fieldbus_tree.dart';

class _ScriptedFieldbusRepository extends SimRepository {
  final _controller = StreamController<List<BusNode>>.broadcast();

  @override
  Stream<List<BusNode>> fieldbus() => _controller.stream;

  void emit(List<BusNode> nodes) => _controller.add(nodes);

  @override
  void dispose() {
    _controller.close();
    super.dispose();
  }
}

const _node = 'PLC1/GVL_Fieldbus/Topology/Nodes/Nodes[1]';

Map<String, Object?> _channel(int index, String tag, String unit,
        {Object? unitCode}) =>
    {
      '$_node/Channels/Channels[$index]/Name': tag,
      '$_node/Channels/Channels[$index]/Address': 'EL3062 Ch$index',
      '$_node/Channels/Channels[$index]/Path': 'Unit.IO.$tag',
      '$_node/Channels/Channels[$index]/ModulePath': 'Unit.SupplyPressure',
      '$_node/Channels/Channels[$index]/Dir': 0,
      '$_node/Channels/Channels[$index]/Kind': 1,
      '$_node/Channels/Channels[$index]/Unit': unit,
      if (unitCode != null) '$_node/Channels/Channels[$index]/UnitCode': unitCode,
    };

List<BusNode> _tree() => const [
      BusNode(
        name: '=000+S-K020A1',
        typeId: 'Beckhoff EL3062',
        address: 'EtherCAT Box 4',
        channels: [
          IoChannel(
            name: '_101B301',
            path: 'Unit.IO._101B301',
            dir: ChannelDir.input,
            kind: ChannelKind.analog,
            analogValue: 2.5,
            unit: 'um', // what F_EngUnitSymbol derives on the PLC
            unitCode: EngUnit.micrometer,
          ),
          IoChannel(
            name: '_101B302',
            path: 'Unit.IO._101B302',
            dir: ChannelDir.input,
            kind: ChannelKind.analog,
            analogValue: 4,
            unit: 'mA', // a unit the vocabulary lacks: text only
          ),
        ],
      ),
    ];

void main() {
  test('a published code wins; absent, NONE or newer codes keep the legacy text',
      () {
    final projection = OpcUaSnapshotMapper().map({
      'protocol': 'fraktal.opcua.snapshot.v1',
      'values': {
        'PLC1/GVL_Fieldbus/Topology/NodeCount': 1,
        'PLC1/GVL_Fieldbus/Topology/MappingValid': true,
        '$_node/ParentIdx': 0,
        '$_node/Name': 'EL3062',
        '$_node/TypeId': 'EL3062',
        '$_node/Address': '1004',
        '$_node/State': 4,
        '$_node/LinkOk': true,
        '$_node/ChannelCount': 4,
        ..._channel(1, '_101B301', 'bar', unitCode: EngUnit.bar.index),
        ..._channel(2, '_101B302', 'mA'),
        ..._channel(3, '_101B303', 'kWh', unitCode: 9999),
        ..._channel(4, '_101B304', 'mA', unitCode: EngUnit.none.index),
      },
    });

    final channels = projection.fieldbus.single.channels;
    expect(channels[0].unitCode, EngUnit.bar);
    expect(channels[0].unitKey, 'std.unit.bar');
    expect(channels[1].unitCode, isNull, reason: 'no code is exported for NONE');
    expect(channels[1].unitKey, 'mA');
    expect(channels[2].unitCode, isNull,
        reason: 'a code newer than this HMI falls back to the derived text');
    expect(channels[2].unitKey, 'kWh');
    expect(channels[3].unitCode, isNull,
        reason: 'a binding that publishes the whole struct sends NONE');
    expect(channels[3].unitKey, 'mA', reason: 'and NONE means the text is the source');
  });

  for (var i = 0; i < kThemes.length; i++) {
    testWidgets(
        'the channel row shows the translated unit or the legacy text '
        '(${kThemes[i].nameKey})', (tester) async {
      final repository = _ScriptedFieldbusRepository();
      final app = AppState(repository);

      await tester.pumpWidget(LocalizationScope(
        controller: app.localization,
        child: MaterialApp(
          theme: themeAt(i),
          home: AnimatedBuilder(
            animation: app,
            builder: (_, __) => Scaffold(body: FieldbusTree(app: app)),
          ),
        ),
      ));

      repository.emit(_tree());
      await tester.pumpAndSettle();
      await tester.tap(find.text('=000+S-K020A1'));
      await tester.pumpAndSettle();

      expect(find.text('2.50 µm'), findsOneWidget,
          reason: "the HMI's own symbol, not the PLC's ASCII 'um'");
      expect(find.text('4.00 mA'), findsOneWidget,
          reason: 'without a code the catalog text is shown as it is');

      await tester.pumpWidget(const SizedBox.shrink());
      repository.dispose();
      await tester.pumpAndSettle();
    });
  }
}
