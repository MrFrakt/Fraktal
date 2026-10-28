library;

// Core §7.5.2 — the standing commissioning/engineering-gate annunciation, and
// §10.5.1 rule 1 — the force affordance that must be ABSENT, not greyed, on a
// production build.
//
// These are tested at the widget level on purpose. Every property that matters
// here is a property of what the operator can SEE and DISMISS: an assertion that
// the event exists in a list would pass just as happily against a banner nobody
// renders, or one with a close button.

import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:fraktal_hmi/data/sim_repository.dart';
import 'package:fraktal_hmi/domain/fieldbus.dart';
import 'package:fraktal_hmi/domain/module_node.dart';
import 'package:fraktal_hmi/domain/types.dart';
import 'package:fraktal_hmi/localization/localized_text.dart';
import 'package:fraktal_hmi/state/app_state.dart';
import 'package:fraktal_hmi/ui/fieldbus_tree.dart';
import 'package:fraktal_hmi/ui/overview_and_indicators.dart';

/// The generated code for `E_Reason.COMMISSIONING_GATE_ACTIVE` (Core §8.8).
/// Spelled out once here so a renumbering of the PLC enum fails this test loudly
/// instead of silently making the banner untestable.
const _commissioningGate = 2030;

class _ScriptedRepository extends SimRepository {
  final _forest = StreamController<List<ModuleNode>>.broadcast();
  final _bus = StreamController<List<BusNode>>.broadcast();

  @override
  Stream<List<ModuleNode>> forest() => _forest.stream;

  @override
  Stream<List<BusNode>> fieldbus() => _bus.stream;

  void emitForest(List<ModuleNode> roots) => _forest.add(roots);
  void emitBus(List<BusNode> nodes) => _bus.add(nodes);

  @override
  void dispose() {
    _forest.close();
    _bus.close();
    super.dispose();
  }
}

AlarmEvent _gate(String descriptionKey, {bool shelved = false}) => AlarmEvent(
      severity: Severity.low,
      description: descriptionKey,
      sourcePath: 'StationA',
      resetClass: ResetClass.autoReset,
      state: AlarmState.active,
      comeAt: DateTime(2026, 8, 14),
      reasonCode: _commissioningGate,
      shelved: shelved,
    );

ModuleNode _root(String path, List<AlarmEvent> events) => ModuleNode(
      path: path,
      name: path,
      type: ModuleType.unit,
      modeActive: UnitMode.manual,
      activeEvents: events,
      access: const AccessSession(level: AccessLevel.admin),
    );

List<BusNode> _bus({required bool forceable}) => [
      BusNode(
        name: '=000+S-K010C1',
        typeId: 'Beckhoff EL2809',
        address: 'EtherCAT Box 3',
        channels: [
          IoChannel(
            name: '_101K301A',
            address: '=000+S-K010C1 Ch1',
            path: 'StationA.IO._101K301A',
            modulePath: 'StationA',
            dir: ChannelDir.output,
            kind: ChannelKind.digital,
            forceable: forceable,
          ),
        ],
      ),
    ];

Future<AppState> _pump(WidgetTester tester, _ScriptedRepository repository,
    Widget Function(AppState) body) async {
  final app = AppState(repository);
  await tester.pumpWidget(LocalizationScope(
    controller: app.localization,
    child: MaterialApp(
      home: AnimatedBuilder(
        animation: app,
        builder: (_, __) => Scaffold(body: body(app)),
      ),
    ),
  ));
  return app;
}

Future<void> _teardown(WidgetTester tester, _ScriptedRepository r) async {
  // SimRepository owns a periodic ticker and the binding asserts no timer
  // outlives the tree.
  await tester.pumpWidget(const SizedBox.shrink());
  r.dispose();
  await tester.pumpAndSettle();
}

void main() {
  testWidgets('a production build shows no gate banner at all', (tester) async {
    final repository = _ScriptedRepository();
    await _pump(tester, repository, (app) => EngineeringModeBanner(app: app));
    repository.emitForest([_root('StationA', const [])]);
    await tester.pumpAndSettle();

    expect(find.text('std.engineering.banner'), findsNothing,
        reason: 'an empty §7.5.1 register annunciates nothing');
    await _teardown(tester, repository);
  });

  testWidgets('every active gate is named, once per gate across the forest',
      (tester) async {
    final repository = _ScriptedRepository();
    await _pump(tester, repository, (app) => EngineeringModeBanner(app: app));
    // Both roots raise their own event for the same station-wide gate, and
    // StationA adds one of its own. The operator must see two lines, not three.
    repository.emitForest([
      _root('StationA', [
        _gate('std.engineering.outputForcing'),
        _gate('std.engineering.simulation'),
      ]),
      _root('StationB', [_gate('std.engineering.simulation')]),
    ]);
    await tester.pumpAndSettle();

    expect(find.textContaining('Output forcing enabled'), findsOneWidget);
    expect(find.textContaining('Simulation driver active'), findsOneWidget);
    await _teardown(tester, repository);
  });

  testWidgets('the banner carries no dismiss control', (tester) async {
    final repository = _ScriptedRepository();
    await _pump(tester, repository, (app) => EngineeringModeBanner(app: app));
    repository.emitForest([
      _root('StationA', [_gate('std.engineering.outputForcing')])
    ]);
    await tester.pumpAndSettle();

    // §7.5.2: no operator action closes this. A button, an InkWell or an
    // IconButton anywhere in the banner would hand back exactly the capability
    // the clause removes, so assert on the absence of the affordance itself
    // rather than on any particular label.
    final banner = find.byType(EngineeringModeBanner);
    expect(find.descendant(of: banner, matching: find.byType(IconButton)),
        findsNothing);
    expect(find.descendant(of: banner, matching: find.byType(InkWell)),
        findsNothing);
    expect(find.descendant(of: banner, matching: find.byType(ButtonStyleButton)),
        findsNothing);
    await _teardown(tester, repository);
  });

  testWidgets('shelving cannot silence the gate banner', (tester) async {
    final repository = _ScriptedRepository();
    await _pump(tester, repository, (app) => EngineeringModeBanner(app: app));
    // The reason is rationalized as not suppressible, so the PLC refuses to
    // shelve it; this proves the HMI would not hide it even if one arrived
    // marked shelved — unlike GlobalAlarmBanner, which filters §8.10 correctly.
    repository.emitForest([
      _root('StationA', [_gate('std.engineering.outputForcing', shelved: true)])
    ]);
    await tester.pumpAndSettle();

    expect(find.textContaining('Output forcing enabled'), findsOneWidget);
    await _teardown(tester, repository);
  });

  testWidgets('a non-forceable channel renders no force affordance',
      (tester) async {
    final repository = _ScriptedRepository();
    final app =
        await _pump(tester, repository, (app) => FieldbusTree(app: app));
    repository.emitForest([_root('StationA', const [])]);
    repository.emitBus(_bus(forceable: false));
    await tester.pumpAndSettle();
    await tester.tap(find.text('=000+S-K010C1'));
    await tester.pumpAndSettle();

    // §10.5.1 rule 1 + §3.9: on a production build the capability is FALSE, so
    // the control is ABSENT. A greyed-out button would still tell an operator
    // the machine can be forced, and invite a support call to enable it.
    expect(find.byTooltip(app.localization.resolve('std.fieldbus.forceTitle')),
        findsNothing);
    expect(
        find.byTooltip(
            app.localization.resolve('std.fieldbus.forceWhyBlocked')),
        findsNothing);
    await _teardown(tester, repository);
  });

  testWidgets('a forceable channel offers the force control', (tester) async {
    final repository = _ScriptedRepository();
    final app =
        await _pump(tester, repository, (app) => FieldbusTree(app: app));
    repository.emitForest([_root('StationA', const [])]);
    repository.emitBus(_bus(forceable: true));
    await tester.pumpAndSettle();
    await tester.tap(find.text('=000+S-K010C1'));
    await tester.pumpAndSettle();

    expect(find.byTooltip(app.localization.resolve('std.fieldbus.forceTitle')),
        findsOneWidget);
    await _teardown(tester, repository);
  });
}
