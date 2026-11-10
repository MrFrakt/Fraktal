@Tags(['live'])
library;

// Opt-in: operate the simulated Fraktal/TIA press demo through the native HMI
// repository over the direct S7 Web API link (s7web://, no gateway). Commands
// the PLC; enable only against the isolated PLCSIM press image.
//
// FRAKTAL_TIA_PRESS_LIVE=1, FRAKTAL_TIA_DIRECT_ENDPOINT=s7web://<cpu>?pin=…,
// FRAKTAL_TIA_WEB_USER / FRAKTAL_TIA_WEB_PASSWORD (DPAPI wrapper), optional
// FRAKTAL_TIA_DIRECT_OUTPUT for the JSON record. The simulated plant swaps
// parts by itself; the two-hand requirement is switched off through the
// generic station-config write for the run and restored afterwards.
import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:fraktal_hmi/data/external_repository_factory_native.dart';
import 'package:fraktal_hmi/data/plc_repository.dart';
import 'package:fraktal_hmi/domain/connection_settings.dart';
import 'package:fraktal_hmi/domain/module_node.dart';
import 'package:fraktal_hmi/domain/types.dart';

const _root = 'PressDemo';
const _cycles = 3;

void main() {
  final environment = Platform.environment;
  final live = environment['FRAKTAL_TIA_PRESS_LIVE'] == '1';

  test('TIA press over s7web://: HOME, AUTO cycles, stop at cycle boundary',
      () async {
    final record = <String, Object?>{};
    final events = <Map<String, Object?>>[];
    final watch = Stopwatch()..start();
    void note(String event, [Map<String, Object?> data = const {}]) =>
        events.add({'ms': watch.elapsedMilliseconds, 'event': event, ...data});

    final PlcRepository repository = await createExternalRepository(
        ConnectionSettings(
            transport: ConnectionTransport.gateway,
            endpoint: environment['FRAKTAL_TIA_DIRECT_ENDPOINT']!));
    var forest = const <ModuleNode>[];
    final steps = <int>[];
    final subscription = repository.forest().listen((nodes) {
      forest = nodes;
      final step = nodes
          .where((n) => n.path == _root)
          .map((n) => n.step?.stepNo)
          .firstOrNull;
      if (step != null && (steps.isEmpty || steps.last != step)) {
        steps.add(step);
      }
    });
    ModuleNode root() => forest.singleWhere((n) => n.path == _root);
    Iterable<ModuleNode> walk(List<ModuleNode> nodes) sync* {
      for (final node in nodes) {
        yield node;
        yield* walk(node.children);
      }
    }
    Future<void> until(bool Function() predicate, String what,
        {Duration timeout = const Duration(seconds: 90)}) async {
      final deadline = Stopwatch()..start();
      while (!(forest.isNotEmpty && predicate()) &&
          deadline.elapsed < timeout) {
        await Future<void>.delayed(const Duration(milliseconds: 100));
      }
      note('until', {'what': what, 'ok': forest.isNotEmpty && predicate()});
      expect(forest.isNotEmpty && predicate(), isTrue,
          reason: 'deadline: $what (state=${forest.isEmpty ? '-' : root().state} '
              'mode=${forest.isEmpty ? '-' : root().modeActive} '
              'step=${forest.isEmpty ? '-' : root().step?.stepNo} '
              'message=${forest.isEmpty ? '-' : root().message})');
    }

    CfgField twoHandField() =>
        root().config.singleWhere((f) => f.writeKey.endsWith('requireTwoHandStart'));
    bool truthy(String value) => value.toLowerCase() == 'true';
    Future<void> command(String what, Future<bool> Function() action) async {
      final accepted = await action();
      note('command', {'what': what, 'accepted': accepted});
      expect(accepted, isTrue, reason: 'acknowledged: $what');
    }

    String? restoreTwoHand;
    try {
      await until(() => forest.any((n) => n.path == _root), 'press discovered');
      record['children'] = [for (final c in root().children) c.path];
      record['initial'] = {
        'mode': root().modeActive?.name,
        'state': root().state.name,
        'good': root().goodCount,
      };
      expect(root().children.map((c) => c.path.split('.').last),
          containsAll(['PressRam', 'Door', 'PartSlide', 'TwoHand',
              'PartPresentSensor', 'AirPressureMonitor']));
      // A previous run may have left a chain waiting for the operator.
      if (root().decision?.pending ?? false) {
        await command('settle pending decision', () => repository.setDecisionAnswer(_root, 1));
        await until(() => !root().running, 'pending chain completed');
      }
      if (root().blocking || root().state == ExecState.error) {
        await command('operator reset', () => repository.operatorReset(_root));
        await until(() => !root().blocking && root().state != ExecState.error,
            'reset cleared');
      }
      if (root().modeActive != UnitMode.manual) {
        await command('MANUAL', () => repository.setMode(_root, UnitMode.manual));
        await until(() => root().modeActive == UnitMode.manual, 'MANUAL');
      }

      await until(
          () => root().config.any((f) => f.writeKey.endsWith('requireTwoHandStart')),
          'station config hydrated');
      record['config'] = [for (final f in root().config) '${f.writeKey}=${f.value}'];
      final twoHand = twoHandField();
      if (truthy(twoHand.value)) {
        restoreTwoHand = twoHand.value;
        await command('requireTwoHandStart=false',
            () => repository.writeConfig(_root, twoHand, 'false'));
        await until(() => !truthy(twoHandField().value), 'two-hand off');
      }

      // MANUAL: move the ram out through the published manual command, so
      // HOME has a real motion to undo.
      ModuleNode ram() => walk(forest).singleWhere((n) => n.path == '$_root.PressRam');
      bool flag(ModuleNode node, String key) =>
          node.stateFlags.any((f) => f.key == key && f.value && !f.stale);
      // The ram's manual release requires the guard door closed: refused here.
      final extend = ram().commands.singleWhere((c) => c.label == 'EXTEND');
      final ramAccepted =
          await repository.manualCommand(_root, '$_root.PressRam', extend.value);
      note('command', {'what': 'manual PressRam EXTEND (door open)', 'accepted': ramAccepted});
      expect(ramAccepted, isFalse, reason: 'ram stroke with the guard door open');
      record['manualRamRefusedDoorOpen'] = !ramAccepted;
      ModuleNode door() => walk(forest).singleWhere((n) => n.path == '$_root.Door');
      final close = door().commands.singleWhere((c) => c.label == 'EXTEND');
      await command('manual Door EXTEND',
          () => repository.manualCommand(_root, '$_root.Door', close.value));
      await until(() => flag(door(), 'module.state.extended'), 'door closed');
      record['manualDoorClosed'] = true;

      bool visited(Iterable<int> numbers) => numbers.every((n) =>
          root().sequenceSteps.any((row) => row.stepNo == n && row.visited));
      // As the Sequence tab does: the §3.13 rows are an on-demand read tier.
      repository.setModuleDetailActive(_root, true,
          containers: const {'SequenceSteps', 'SequenceAnnotations', 'Ring'});
      await command('HOME', () => repository.setMode(_root, UnitMode.home));
      await until(() => root().modeActive == UnitMode.home, 'HOME active');
      await command('start HOME', () => repository.start(_root));
      // The PLC records every visited step (§3.13): HOME's three steps are the
      // proof, whatever the poll rate saw of the short BUSY/DONE states.
      await until(() => visited(const [900, 910, 999]) && !root().running &&
          root().state != ExecState.error, 'HOME steps visited');
      record['homeVisited'] = [
        for (final row in root().sequenceSteps)
          if (row.visited) {'step': row.stepNo, 'ms': row.lastDuration.inMilliseconds}
      ];
      record['retractedAfterHome'] = flag(ram(), 'module.state.retracted') &&
          flag(door(), 'module.state.retracted');
      record['homed'] = root().stateFlags
          .where((f) => f.key == 'project.state.pressAtLoadPosition')
          .map((f) => f.value)
          .firstOrNull;

      // CHANGEOVER: SET_MODEL applies STEEL atomically (prepare/commit under
      // the CHANGEOVER release); the chain proves the model, returns to the
      // load position and asks the operator. "Repeat position" (2) must jump
      // back to 810 before "confirm" (1) completes the changeover.
      final initialModel = root().modelCode;
      record['initialModel'] = initialModel;
      record['availableModels'] = root().availableModels;
      await command('CHANGEOVER', () => repository.setMode(_root, UnitMode.changeover));
      await until(() => root().modeActive == UnitMode.changeover, 'CHANGEOVER active');
      await command('model STEEL', () => repository.setModel(_root, 'STEEL'));
      await until(() => root().modelCode == 'STEEL', 'STEEL active');
      await command('start CHANGEOVER', () => repository.start(_root));
      await until(() => root().decision?.pending ?? false, 'confirmation asked');
      record['decision'] = {
        'prompt': root().decision!.prompt,
        'options': root().decision!.options,
      };
      await command('answer: repeat position',
          () => repository.setDecisionAnswer(_root, 2));
      // The jump back through the load position completes within a few scans,
      // faster than any poll; the PLC's own decision audit proves it.
      // TIA's INT_TO_STRING signs the option ("option=+2"); accept either form.
      bool audited(String key) => root().ringEvents.any(
          (e) => e.description == key || e.description == key.replaceFirst('option=', 'option=+'));
      await until(() => audited('std.audit.decisionOperatorResolved option=2') &&
          (root().decision?.pending ?? false), 'repeat resolved and asked again');
      record['repeatAudited'] = true;
      await command('answer: confirm', () => repository.setDecisionAnswer(_root, 1));
      await until(() => audited('std.audit.decisionOperatorResolved option=1') &&
          visited(const [0, 800, 810, 870, 880, 999]) && !root().running &&
          root().state != ExecState.error, 'CHANGEOVER steps visited');
      record['changeoverVisited'] = [
        for (final row in root().sequenceSteps)
          if (row.visited) row.stepNo
      ];
      record['changeoverCompleted'] =
          root().publishedValues['OutCmd/ChangeoverCompleted'];

      steps.clear();
      final good = root().goodCount;
      await command('AUTO', () => repository.setMode(_root, UnitMode.auto));
      await until(() => root().modeActive == UnitMode.auto, 'AUTO active');
      final started = watch.elapsedMilliseconds;
      await command('start AUTO', () => repository.start(_root));
      await until(() => root().goodCount >= good + _cycles, '$_cycles good parts',
          timeout: const Duration(minutes: 3));
      record['autoCycles'] = root().goodCount - good;
      record['autoMs'] = watch.elapsedMilliseconds - started;
      record['lastCycleMs'] = root().lastCycleTime.inMilliseconds;
      final dwell = root().sequenceSteps.where((row) => row.stepNo == 220).firstOrNull;
      record['steelDwellMs'] = dwell?.lastDuration.inMilliseconds;
      expect(dwell?.lastDuration.inMilliseconds ?? 0, greaterThanOrEqualTo(1100),
          reason: 'STEEL seed PressSettleTime 1200 ms drives the dwell');
      record['autoVisited'] = [
        for (final row in root().sequenceSteps)
          if (row.visited) {'step': row.stepNo, 'branch': row.branch, 'ms': row.lastDuration.inMilliseconds}
      ];
      await command('stop', () => repository.stop(_root));
      await until(() => !root().running, 'stopped at the cycle boundary');
      record['autoSteps'] = [...steps];
      record['finalGood'] = root().goodCount;
      record['nok'] = root().nokCount;
      // Leave the station on the model it started with.
      await command('CHANGEOVER (restore)', () => repository.setMode(_root, UnitMode.changeover));
      await until(() => root().modeActive == UnitMode.changeover, 'CHANGEOVER for restore');
      await command('model $initialModel', () => repository.setModel(_root, initialModel));
      await until(() => root().modelCode == initialModel, 'initial model restored');
      await command('MANUAL', () => repository.setMode(_root, UnitMode.manual));
      await until(() => root().modeActive == UnitMode.manual, 'back to MANUAL');
      record['result'] = 'PASS';
    } finally {
      if (forest.any((n) => n.path == _root)) {
        record['rowsAtEnd'] = {
          'enabled': root().sequenceViewEnabled,
          'count': root().sequenceStepCount,
          'rows': [
            for (final row in root().sequenceSteps)
              '${row.branch}/${row.stepNo}:${row.visited ? 'v' : '-'}${row.active ? 'a' : ''}'
          ],
        };
      }
      final previous = restoreTwoHand;
      if (previous != null && forest.isNotEmpty) {
        final restored =
            await repository.writeConfig(_root, twoHandField(), previous);
        note('restore', {'requireTwoHandStart': previous, 'accepted': restored});
      }
      await subscription.cancel();
      repository.dispose();
      record['events'] = events;
      final output = environment['FRAKTAL_TIA_DIRECT_OUTPUT'] ?? '';
      if (output.isNotEmpty) {
        File('$output/press_direct.json')
          ..createSync(recursive: true)
          ..writeAsStringSync(const JsonEncoder.withIndent('  ').convert(record));
      }
    }
  },
      skip: live ? false : 'opt-in: FRAKTAL_TIA_PRESS_LIVE=1',
      timeout: const Timeout(Duration(minutes: 8)));
}
