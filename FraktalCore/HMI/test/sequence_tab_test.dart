import 'package:flutter_test/flutter_test.dart';
import 'package:fraktal_hmi/content/module_layout.dart';
import 'package:fraktal_hmi/data/opcua_snapshot_mapper.dart';
import 'package:fraktal_hmi/domain/module_node.dart';
import 'package:fraktal_hmi/domain/types.dart';
import 'package:fraktal_hmi/ui/custom_module_tabs.dart';

void main() {
  group('§3.13 sequence flow chart', () {
    test('the PLC decides whether the tab exists, not the module type', () {
      const withChart = ModuleNode(
        path: 'Press', name: 'Press', type: ModuleType.unit,
        sequenceViewEnabled: true,
        sequenceSteps: [SequenceStep(stepNo: 100, stepName: 'a')],
      );
      const flagOff = ModuleNode(
        path: 'Press', name: 'Press', type: ModuleType.unit,
        sequenceSteps: [SequenceStep(stepNo: 100, stepName: 'a')],
      );
      // A Unit that publishes no steps must not show an empty tab either.
      const noSteps = ModuleNode(
        path: 'Press', name: 'Press', type: ModuleType.unit,
        sequenceViewEnabled: true,
      );
      expect(moduleTabCapabilities(withChart).sequence, isTrue);
      expect(moduleTabCapabilities(flagOff).sequence, isFalse);
      expect(moduleTabCapabilities(noSteps).sequence, isFalse);
    });

    test('the default tab set follows that capability', () {
      final kinds = ModuleTabDefinition.defaults(
              const ModuleTabCapabilities(unit: true, sequence: true))
          .map((tab) => tab.kind);
      expect(kinds, contains(ModuleTabKind.sequence));
      final without =
          ModuleTabDefinition.defaults(const ModuleTabCapabilities(unit: true))
              .map((tab) => tab.kind);
      expect(without, isNot(contains(ModuleTabKind.sequence)));
    });

    test('drill-down is offered only where the PLC declared a target', () {
      const wired = SequenceStep(stepNo: 200, awaitsPath: 'Press.PressRam');
      // N200 dropped its await to own the ram's failure, so it publishes no
      // path: not click-through, and that must not be guessed around.
      const owned = SequenceStep(stepNo: 200);
      expect(wired.drillsDown, isTrue);
      expect(owned.drillsDown, isFalse);
    });

    test('mapper reads the published rows, bounded by the count', () {
      const base = 'PLC1/MAIN/Press';
      final projection = OpcUaSnapshotMapper().map({
        'protocol': 'fraktal.opcua.snapshot.v1',
        'values': {
          '$base/Status/Name': 'Press',
          '$base/Status/ModuleType': 1,
          '$base/Status/State': 1,
          '$base/SequenceViewEnabled': true,
          '$base/SequenceStepCount': 2,
          '$base/CurrentStepElapsed': 1500,
          '$base/CurrentStepTimedOut': true,
          '$base/SequenceSteps/1/StepNo': 100,
          '$base/SequenceSteps/1/StepName': 'std.step.await',
          '$base/SequenceSteps/1/AwaitsPath': '',
          '$base/SequenceSteps/1/Visited': true,
          '$base/SequenceSteps/2/StepNo': 200,
          '$base/SequenceSteps/2/StepName': 'std.step.ram',
          '$base/SequenceSteps/2/AwaitsPath': 'PLC1.MAIN.Press.PressRam',
          '$base/SequenceSteps/2/Visited': true,
          // A third row exists on the wire but the count says two: the
          // published length wins, so a stale row never reaches the chart.
          '$base/SequenceSteps/3/StepNo': 999,
        },
      });
      final unit = projection.forest.single;
      expect(unit.sequenceViewEnabled, isTrue);
      expect(unit.currentStepTimedOut, isTrue);
      expect(unit.currentStepElapsed, const Duration(milliseconds: 1500));
      expect(unit.sequenceSteps.map((s) => s.stepNo), [100, 200]);
      expect(unit.sequenceSteps[1].awaitsPath, 'PLC1.MAIN.Press.PressRam');
      expect(unit.sequenceSteps[1].drillsDown, isTrue);
      expect(unit.sequenceSteps[0].drillsDown, isFalse);
    });
  });
}
