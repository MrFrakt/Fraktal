library;

// Regression: the fieldbus detail pane must render LIVE values.
//
// The pane used to hold the selected `BusNode` OBJECT. Every refresh rebuilds
// the projection into new instances, so the captured one never changed — node
// state and channel values froze until the operator selected another node and
// came back (which re-captured a fresh object). Nothing upstream was broken:
// PLC, transport, tier gating and mapper were each verified correct against a
// live PLC, which is exactly why this needs a test rather than an inspection.

import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:fraktal_hmi/data/sim_repository.dart';
import 'package:fraktal_hmi/domain/fieldbus.dart';
import 'package:fraktal_hmi/localization/localized_text.dart';
import 'package:fraktal_hmi/state/app_state.dart';
import 'package:fraktal_hmi/ui/fieldbus_tree.dart';

/// Sim repository whose fieldbus tree is driven by the test, so a refresh can be
/// simulated exactly as the live transport does: by emitting NEW instances.
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

List<BusNode> _tree({required bool inputOn}) => [
      BusNode(
        name: '=000+S-A610-A1',
        typeId: 'Beckhoff CX2030',
        address: 'EtherCAT master',
        state: NodeState.operational,
        linkOk: true,
        children: [
          BusNode(
            name: '=000+S-K010B1',
            typeId: 'Beckhoff EL1809',
            address: 'EtherCAT Box 3',
            state: NodeState.operational,
            linkOk: true,
            channels: [
              IoChannel(
                name: '_101B301A',
                address: '=000+S-K010B1 Ch1',
                path: 'PneumaticPress.IO._101B301A',
                dir: ChannelDir.input,
                kind: ChannelKind.digital,
                boolValue: inputOn,
              ),
            ],
          ),
        ],
      ),
    ];

void main() {
  testWidgets('detail pane follows live updates without re-selecting',
      (tester) async {
    final repository = _ScriptedFieldbusRepository();
    final app = AppState(repository);

    await tester.pumpWidget(LocalizationScope(
      controller: app.localization,
      child: MaterialApp(
        home: AnimatedBuilder(
          animation: app,
          builder: (_, __) => Scaffold(body: FieldbusTree(app: app)),
        ),
      ),
    ));

    repository.emit(_tree(inputOn: false));
    await tester.pumpAndSettle();

    await tester.tap(find.text('=000+S-K010B1'));
    await tester.pumpAndSettle();
    expect(find.textContaining('OFF'), findsWidgets,
        reason: 'the selected channel starts off');

    // A refresh delivers a NEW tree with the input made. The pane must follow
    // it; before the fix it kept rendering the instance captured on tap.
    repository.emit(_tree(inputOn: true));
    await tester.pumpAndSettle();

    expect(find.textContaining('ON'), findsWidgets,
        reason: 'pane must show the new value without re-selecting the node');

    // Dispose inside the test body: SimRepository owns a periodic ticker, and
    // the binding asserts no timer outlives the widget tree.
    await tester.pumpWidget(const SizedBox.shrink());
    repository.dispose();
    await tester.pumpAndSettle();
  });
}
