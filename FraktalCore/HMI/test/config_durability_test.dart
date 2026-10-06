library;

// Core §3.8b / HMI_CONTRACT: "Durability is displayed, never assumed."
//
// Transport acknowledgement and Accepted mean a configuration value is LIVE.
// They say nothing about whether it is DURABLE, and a station that cannot
// persist will silently revert at its next restart. The contract requires the
// operator to learn that BEFORE the restart, which makes every property worth
// testing here a property of what is on SCREEN - an assertion that the flag
// arrived in a snapshot would pass just as happily against a banner nobody
// renders.

import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:fraktal_hmi/data/scoped_plc_repository.dart';
import 'package:fraktal_hmi/data/sim_repository.dart';
import 'package:fraktal_hmi/domain/fieldbus.dart';
import 'package:fraktal_hmi/domain/module_node.dart';
import 'package:fraktal_hmi/domain/types.dart';
import 'package:fraktal_hmi/localization/localized_text.dart';
import 'package:fraktal_hmi/state/app_state.dart';
import 'package:fraktal_hmi/ui/overview_and_indicators.dart';

class _ScriptedRepository extends SimRepository {
  final _forest = StreamController<List<ModuleNode>>.broadcast();
  final _bus = StreamController<List<BusNode>>.broadcast();
  final acknowledged = <String>[];

  @override
  Stream<List<ModuleNode>> forest() => _forest.stream;

  @override
  Stream<List<BusNode>> fieldbus() => _bus.stream;

  /// Records the ask and answers yes WITHOUT changing what is published. The
  /// PLC is the authority: the banner must clear because the root stopped
  /// reporting the loss, never because the client decided it had.
  @override
  Future<bool> acknowledgeConfigRestore(String rootPath) async {
    acknowledged.add(rootPath);
    return true;
  }

  void emitForest(List<ModuleNode> roots) => _forest.add(roots);

  @override
  void dispose() {
    _forest.close();
    _bus.close();
    super.dispose();
  }
}

ModuleNode _root(String path, ConfigPersistStatus? persist) => ModuleNode(
      path: path,
      name: path,
      type: ModuleType.unit,
      modeActive: UnitMode.manual,
      access: const AccessSession(level: AccessLevel.admin),
      configPersist: persist,
    );

Future<AppState> _pump(
    WidgetTester tester, _ScriptedRepository repository) async {
  final app = AppState(repository);
  await tester.pumpWidget(LocalizationScope(
    controller: app.localization,
    child: MaterialApp(
      home: AnimatedBuilder(
        animation: app,
        builder: (_, __) => Scaffold(body: ConfigDurabilityBanner(app: app)),
      ),
    ),
  ));
  return app;
}

Future<void> _teardown(WidgetTester tester, _ScriptedRepository r) async {
  await tester.pumpWidget(const SizedBox.shrink());
  r.dispose();
  await tester.pumpAndSettle();
}

void main() {
  testWidgets('a healthy station annunciates nothing', (tester) async {
    final repository = _ScriptedRepository();
    await _pump(tester, repository);
    repository.emitForest([_root('StationA', const ConfigPersistStatus())]);
    await tester.pumpAndSettle();

    expect(find.textContaining('not safely stored'), findsNothing);
    await _teardown(tester, repository);
  });

  testWidgets('a root that publishes no durability at all is not accused',
      (tester) async {
    // A binding that does not claim §3.8b publishes no ConfigPersist subtree.
    // Absence is "nothing pending, nothing lost", never "this station cannot
    // persist" - otherwise every AB station would carry a permanent alarm for
    // a clause it does not claim.
    final repository = _ScriptedRepository();
    await _pump(tester, repository);
    repository.emitForest([_root('StationA', null)]);
    await tester.pumpAndSettle();

    expect(find.textContaining('not safely stored'), findsNothing);
    await _teardown(tester, repository);
  });

  testWidgets('a merely pending write is not annunciated', (tester) async {
    // PENDING is the normal state for the declared window after EVERY accepted
    // write. A strip that appeared on each edit would be noise, and noise is
    // what trains an operator to ignore the strip on the day it matters.
    final repository = _ScriptedRepository();
    await _pump(tester, repository);
    repository.emitForest([
      _root('StationA', const ConfigPersistStatus(pending: true)),
    ]);
    await tester.pumpAndSettle();

    expect(find.textContaining('not safely stored'), findsNothing);
    await _teardown(tester, repository);
  });

  testWidgets('a write that missed its window is annunciated, naming the root',
      (tester) async {
    final repository = _ScriptedRepository();
    await _pump(tester, repository);
    repository.emitForest([
      _root('StationA', const ConfigPersistStatus(failed: true)),
    ]);
    await tester.pumpAndSettle();

    expect(find.textContaining('not safely stored'), findsOneWidget);
    expect(find.textContaining('StationA'), findsOneWidget);
    expect(find.textContaining('lost at the next restart'), findsOneWidget);
    await _teardown(tester, repository);
  });

  testWidgets('a lost image names the module that lost it', (tester) async {
    final repository = _ScriptedRepository();
    await _pump(tester, repository);
    repository.emitForest([
      _root(
          'StationA',
          const ConfigPersistStatus(
              restoreLost: true, lostPath: 'StationA.ClampStation.CylB')),
    ]);
    await tester.pumpAndSettle();

    expect(find.textContaining('StationA.ClampStation.CylB'), findsOneWidget,
        reason:
            'the operator has to know WHICH module to go and re-commission');
    await _teardown(tester, repository);
  });

  testWidgets('an acknowledged loss stops being annunciated', (tester) async {
    final repository = _ScriptedRepository();
    await _pump(tester, repository);
    repository.emitForest([
      _root(
          'StationA',
          const ConfigPersistStatus(
              restoreLost: true, restoreAcknowledged: true)),
    ]);
    await tester.pumpAndSettle();

    expect(find.textContaining('not safely stored'), findsNothing);
    await _teardown(tester, repository);
  });

  testWidgets('only the blocking policy claims the station will not start',
      (tester) async {
    final repository = _ScriptedRepository();
    await _pump(tester, repository);
    repository.emitForest([
      _root('StationA', const ConfigPersistStatus(restoreLost: true)),
    ]);
    await tester.pumpAndSettle();
    expect(find.textContaining('will not start'), findsNothing,
        reason: 'DEFAULTS_AND_ANNUNCIATE runs the station');

    repository.emitForest([
      _root(
          'StationA',
          const ConfigPersistStatus(
              restoreLost: true,
              restorePolicy: ConfigRestorePolicy.blockUntilAcknowledged)),
    ]);
    await tester.pumpAndSettle();
    expect(find.textContaining('will not start'), findsOneWidget);
    await _teardown(tester, repository);
  });

  testWidgets('acknowledging asks the PLC and does not clear the banner itself',
      (tester) async {
    final repository = _ScriptedRepository();
    await _pump(tester, repository);
    repository.emitForest([
      _root('StationA', const ConfigPersistStatus(restoreLost: true)),
    ]);
    await tester.pumpAndSettle();

    await tester.tap(find.textContaining('Acknowledge lost settings'));
    await tester.pumpAndSettle();

    expect(repository.acknowledged, ['StationA']);
    // The scripted repository answered yes but kept publishing the loss. The
    // banner must still be there: it reflects what the ROOT reports, and a
    // client that hid it on its own answer would show a healthy station while
    // the machine still runs on defaults.
    expect(find.textContaining('not safely stored'), findsOneWidget);
    await _teardown(tester, repository);
  });

  testWidgets('a root outside this HMI scope is never annunciated',
      (tester) async {
    final repository = _ScriptedRepository();
    final app = await _pump(tester, repository);
    repository.emitForest([
      _root('StationA', const ConfigPersistStatus()),
      _root('StationB', const ConfigPersistStatus(restoreLost: true)),
    ]);
    await tester.pumpAndSettle();
    // Scoped through the real surface, and AFTER the forest: arriving roots
    // reset a scope whose selection is not visible.
    app.scopeTo('StationA');
    await tester.pumpAndSettle();

    expect(find.textContaining('not safely stored'), findsNothing,
        reason: 'this HMI does not own StationB and could not acknowledge it');
    await _teardown(tester, repository);
  });

  testWidgets('two roots each lose their own image and both are named',
      (tester) async {
    // Deliberately NOT deduplicated the way the §7.5 gate banner is: a gate is
    // one station-wide build constant, a lost image is per root and per store.
    final repository = _ScriptedRepository();
    await _pump(tester, repository);
    repository.emitForest([
      _root('StationA', const ConfigPersistStatus(restoreLost: true)),
      _root('StationB', const ConfigPersistStatus(restoreLost: true)),
    ]);
    await tester.pumpAndSettle();

    expect(find.textContaining('StationA'), findsOneWidget);
    expect(find.textContaining('StationB'), findsOneWidget);
    await _teardown(tester, repository);
  });

  test('a scoped repository refuses an acknowledge outside its scope',
      () async {
    final source = _ScriptedRepository();
    final scoped = ScopedPlcRepository(source,
        allowedRoots: const ['StationA'], configured: true);

    expect(await scoped.acknowledgeConfigRestore('StationA'), isTrue);
    expect(await scoped.acknowledgeConfigRestore('StationB'), isFalse);
    expect(source.acknowledged, ['StationA'],
        reason: 'the out-of-scope ask must never reach the PLC at all');
    source.dispose();
  });
}
