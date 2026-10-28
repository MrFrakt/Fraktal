import 'package:flutter_test/flutter_test.dart';
import 'package:fraktal_hmi/content/module_layout.dart';
import 'package:fraktal_hmi/data/opcua_field_tier.dart';
import 'package:fraktal_hmi/data/opcua_snapshot_mapper.dart';
import 'package:fraktal_hmi/domain/module_node.dart';
import 'package:fraktal_hmi/domain/types.dart';
import 'package:fraktal_hmi/ui/custom_module_tabs.dart';
import 'package:fraktal_hmi/ui/sequence_module_tab.dart';

void main() {
  group('§3.13 sequence flow chart', () {
    test('the PLC decides whether the tab exists, not the module type', () {
      // Keyed on the COUNT, not the rows: the rows are an on-demand subtree read
      // only while the tab is open, so a rows-based capability would deadlock —
      // no tab, so no read, so no rows, so no tab.
      const notYetRead = ModuleNode(
        path: 'Press', name: 'Press', type: ModuleType.unit,
        sequenceViewEnabled: true,
        sequenceStepCount: 12,
      );
      const flagOff = ModuleNode(
        path: 'Press', name: 'Press', type: ModuleType.unit,
        sequenceStepCount: 12,
        sequenceSteps: [SequenceStep(stepNo: 100, stepName: 'a')],
      );
      // A Unit that publishes no steps must not show an empty tab either.
      const noSteps = ModuleNode(
        path: 'Press', name: 'Press', type: ModuleType.unit,
        sequenceViewEnabled: true,
      );
      expect(moduleTabCapabilities(notYetRead).sequence, isTrue);
      expect(moduleTabCapabilities(flagOff).sequence, isFalse);
      expect(moduleTabCapabilities(noSteps).sequence, isFalse);
    });

    test('the flow-chart rows are read on demand, never in the cyclic snapshot',
        () {
      // 128 rows x 17 fields per Unit would dominate the fast read; they only
      // feed this one tab. The signals the rest of the UI needs stay live.
      expect(OpcUaFieldTier.classify('PLC1/MAIN/Press/SequenceSteps/3/StepName'),
          FieldTier.onDemand);
      expect(OpcUaFieldTier.classify('PLC1/MAIN/Press/SequenceSteps[3].StepName'),
          FieldTier.onDemand);
      expect(OpcUaFieldTier.classify('PLC1/MAIN/Press/SequenceStepCount'),
          FieldTier.live);
      expect(OpcUaFieldTier.classify('PLC1/MAIN/Press/SequenceViewEnabled'),
          FieldTier.live);
      expect(OpcUaFieldTier.classify('PLC1/MAIN/Press/CurrentStepElapsed'),
          FieldTier.live);
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

    test('a raised error makes a step click-through to the module that failed',
        () {
      // N200 owns its child's failure, so it declares no Awaits and would not be
      // click-through. Raising the error supplies the link instead.
      const owned = SequenceStep(stepNo: 200);
      const raised = SequenceStep(
        stepNo: 200,
        errorActive: true,
        errorSourcePath: 'Press.PressRam',
      );
      expect(owned.drillsDown, isFalse);
      expect(raised.drillsDown, isTrue);
      expect(raised.linkPath, 'Press.PressRam');
    });

    test('the error link wins over the declared Awaits target', () {
      // The operator wants the module that actually failed, not the one the step
      // nominally commands.
      const step = SequenceStep(
        stepNo: 150,
        awaitsPath: 'Press.PartSlide',
        errorActive: true,
        errorSourcePath: 'Press.PressRam',
      );
      expect(step.linkPath, 'Press.PressRam');
    });

    test('a warning never turns a step into a fault or a drill-down', () {
      // §6.9(e): the warning did not stop the chain, so it must not borrow any of
      // the error path's behaviour - no link, no red, no click-through.
      const step = SequenceStep(
        stepNo: 180,
        warningActive: true,
        warningKey: 'project.warning.twoHandReleasedDuringDoorClose',
      );
      expect(step.errorActive, isFalse);
      expect(step.drillsDown, isFalse);
      expect(step.linkPath, isEmpty);
      expect(step.warningKey, 'project.warning.twoHandReleasedDuringDoorClose');
    });

    test('a reported child failure keeps the step click-through without an error',
        () {
      // Press AUTO N200: the ram did not reach, the chain handles it itself, so
      // nothing faults - but the row still links to the ram that failed.
      const step = SequenceStep(
        stepNo: 200,
        warningActive: true,
        warningKey: 'std.error.cylinderExtendTimeout',
        warningSourcePath: 'Press.PressRam',
      );
      expect(step.errorActive, isFalse);
      expect(step.drillsDown, isTrue);
      expect(step.linkPath, 'Press.PressRam');
    });

    test('an error link still outranks a reported one', () {
      const step = SequenceStep(
        stepNo: 200,
        errorActive: true,
        errorSourcePath: 'Press.Door',
        warningActive: true,
        warningSourcePath: 'Press.PressRam',
      );
      expect(step.linkPath, 'Press.Door');
    });

    test('a parallel step keeps every leg live, each on its own clock', () {
      // §6.12: liveness cannot come from the Unit's single current step once two
      // legs run at once, and a leg times itself because the stall watchdog is
      // singular and follows the main line.
      const node = ModuleNode(
        path: 'Press', name: 'Press', type: ModuleType.unit,
        sequenceViewEnabled: true,
        step: StepInfo(stepNo: 500),
        currentStepElapsed: Duration(milliseconds: 2000),
        currentStepTimedOut: true,
        sequenceSteps: [
          SequenceStep(stepNo: 500, active: true),
          SequenceStep(
              stepNo: 600, branch: 1, active: true,
              elapsed: Duration(milliseconds: 1200)),
          SequenceStep(
              stepNo: 700, branch: 2, active: true,
              elapsed: Duration(milliseconds: 400), timedOut: true),
        ],
      );
      final fork = SequenceRowState.of(node, node.sequenceSteps[0],
          rowsAreLive: true);
      final legA =
          SequenceRowState.of(node, node.sequenceSteps[1], rowsAreLive: true);
      final legB =
          SequenceRowState.of(node, node.sequenceSteps[2], rowsAreLive: true);
      expect([fork.active, legA.active, legB.active], [true, true, true]);
      expect(legA.elapsed, const Duration(milliseconds: 1200));
      expect(legB.elapsed, const Duration(milliseconds: 400));
      // the Unit's stall watchdog marks the MAIN line only; a leg's guard is its own
      expect(fork.timedOut, isTrue);
      expect(legA.timedOut, isFalse);
      expect(legB.timedOut, isTrue);
    });

    test('a runtime that publishes no per-row liveness still draws', () {
      // Pre-§6.12 PLC: no row says it is active, so the chart falls back to the
      // Unit's single current step rather than rendering a dead chart.
      const node = ModuleNode(
        path: 'Press', name: 'Press', type: ModuleType.unit,
        sequenceViewEnabled: true,
        step: StepInfo(stepNo: 200),
        currentStepElapsed: Duration(milliseconds: 700),
        sequenceSteps: [
          SequenceStep(stepNo: 100, lastDuration: Duration(seconds: 3)),
          SequenceStep(stepNo: 200),
        ],
      );
      final past =
          SequenceRowState.of(node, node.sequenceSteps[0], rowsAreLive: false);
      final now =
          SequenceRowState.of(node, node.sequenceSteps[1], rowsAreLive: false);
      expect(past.active, isFalse);
      expect(past.elapsed, const Duration(seconds: 3));
      expect(now.active, isTrue);
      expect(now.elapsed, const Duration(milliseconds: 700));
    });

    test('the per-leg cursor decides which rows are live, and for how long', () {
      // One cursor entry per concurrent leg, indexed by branch: ~10 entries however
      // long the chain is. A leg with RowIdx 0 has no active step.
      const base = 'PLC1/MAIN/Press';
      final projection = OpcUaSnapshotMapper().map({
        'protocol': 'fraktal.opcua.snapshot.v1',
        'values': {
          '$base/Status/Name': 'Press',
          '$base/Status/ModuleType': 1,
          '$base/Status/State': 1,
          '$base/SequenceStepCount': 3,
          '$base/SequenceSteps/1/StepNo': 500,
          '$base/SequenceSteps/2/StepNo': 600,
          '$base/SequenceSteps/3/StepNo': 700,
          // leg 0 idle, leg 1 on row 2, leg 2 on row 3 — a parallel step
          '$base/ActiveSteps/1/RowIdx': 0,
          '$base/ActiveSteps/2/RowIdx': 2,
          '$base/ActiveSteps/2/Elapsed': 1200,
          '$base/ActiveSteps/3/RowIdx': 3,
          '$base/ActiveSteps/3/Elapsed': 400,
          '$base/ActiveSteps/3/TimedOut': true,
        },
      });
      final steps = projection.forest.single.sequenceSteps;
      expect(steps.map((s) => s.active), [false, true, true]);
      expect(steps[1].elapsed, const Duration(milliseconds: 1200));
      expect(steps[2].elapsed, const Duration(milliseconds: 400));
      expect(steps[1].timedOut, isFalse);
      expect(steps[2].timedOut, isTrue);
    });

    test('a marked row with no note keeps its mark', () {
      // The annotation table is small on purpose. If it fills, the PLC keeps the
      // row FLAG and drops only the text, so the chart must still colour the row —
      // reading the flag off the note would silently unmark a real failure.
      const base = 'PLC1/MAIN/Press';
      final projection = OpcUaSnapshotMapper().map({
        'protocol': 'fraktal.opcua.snapshot.v1',
        'values': {
          '$base/Status/Name': 'Press',
          '$base/Status/ModuleType': 1,
          '$base/Status/State': 1,
          '$base/SequenceStepCount': 1,
          '$base/SequenceSteps/1/StepNo': 200,
          '$base/SequenceSteps/1/ErrorActive': true,
          '$base/SequenceAnnotationCount': 0,
        },
      });
      final step = projection.forest.single.sequenceSteps.single;
      expect(step.errorActive, isTrue);
      expect(step.errorSourcePath, isEmpty);
      // nothing to drill into, so it opens the step detail rather than navigating
      expect(step.drillsDown, isFalse);
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
          '$base/SequenceSteps/1/WarningActive': true,
          // §6.9 notes live in their own sparse table, joined by RowIdx
          '$base/SequenceAnnotationCount': 3,
          '$base/SequenceAnnotations/1/RowIdx': 1,
          '$base/SequenceAnnotations/1/IsError': false,
          '$base/SequenceAnnotations/1/Key': 'project.warning.twoHandReleased',
          '$base/SequenceAnnotations/1/SourcePath': '',
          '$base/SequenceAnnotations/2/RowIdx': 2,
          '$base/SequenceAnnotations/2/IsError': true,
          '$base/SequenceAnnotations/2/Key': 'std.error.cylinderExtendTimeout',
          '$base/SequenceAnnotations/2/SourcePath': 'PLC1.MAIN.Press.PressRam',
          // a freed slot inside the count must not become a phantom note
          '$base/SequenceAnnotations/3/RowIdx': 0,
          '$base/SequenceAnnotations/3/Key': 'stale',
          '$base/SequenceSteps/2/StepNo': 200,
          '$base/SequenceSteps/2/StepName': 'std.step.ram',
          '$base/SequenceSteps/2/AwaitsPath': 'PLC1.MAIN.Press.PressRam',
          '$base/SequenceSteps/2/Visited': true,
          '$base/SequenceSteps/2/ErrorActive': true,
          '$base/SequenceSteps/2/Branch': 1,
          // liveness now comes from the per-leg cursor, not the row
          '$base/ActiveSteps/2/RowIdx': 2,
          '$base/ActiveSteps/2/Elapsed': 900,
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
      expect(unit.sequenceSteps[0].warningActive, isTrue);
      expect(unit.sequenceSteps[0].warningKey,
          'project.warning.twoHandReleased');
      expect(unit.sequenceSteps[1].branch, 1);
      expect(unit.sequenceSteps[1].active, isTrue);
      expect(unit.sequenceSteps[1].elapsed,
          const Duration(milliseconds: 900));
      expect(unit.sequenceSteps[1].errorActive, isTrue);
      expect(unit.sequenceSteps[1].linkPath, 'PLC1.MAIN.Press.PressRam');
    });
  });

  group('§10.5.1 fieldbus tiering', () {
    test('a channel value is live; everything around it stays on demand', () {
      // An operator watches an interlock that will not clear without opening the
      // bus page, so the VALUE is live — one leaf per channel. The identity,
      // addressing and diagnostic text around it are large and view-gated.
      const ch = 'PLC1/MAIN/Press/Topology/Nodes/Nodes[3]/Channels/Channels[5]';
      expect(OpcUaFieldTier.classify('$ch/BoolValue'), FieldTier.live);
      expect(OpcUaFieldTier.classify('$ch/AnalogValue'), FieldTier.live);
      expect(OpcUaFieldTier.classify('$ch/Address'), FieldTier.onDemand);
      expect(OpcUaFieldTier.classify('$ch/Diagnostic'), FieldTier.onDemand);
      expect(OpcUaFieldTier.classify('$ch/Forced'), FieldTier.onDemand);
      expect(OpcUaFieldTier.classify('$ch/Quality'), FieldTier.onDemand);
    });
  });

  group('§3.12 derived state flags', () {
    test('the mapper reads them, bounded and skipping unpublished slots', () {
      const base = 'PLC1/MAIN/Press';
      final projection = OpcUaSnapshotMapper().map({
        'protocol': 'fraktal.opcua.snapshot.v1',
        'values': {
          '$base/Status/Name': 'Press',
          '$base/Status/ModuleType': 1,
          '$base/Status/State': 1,
          '$base/StateFlagCount': 3,
          '$base/StateFlags/1/Key': 'project.state.pressAtLoadPosition',
          '$base/StateFlags/1/Value': true,
          '$base/StateFlags/1/Since': '2026-08-04T10:00:00.000Z',
          '$base/StateFlags/2/Key': 'project.state.airOk',
          '$base/StateFlags/2/Value': false,
          '$base/StateFlags/2/Stale': true,
          // index 3 is inside the count but was never published: a gap in the
          // table is not a flag, and must not render as a nameless chip.
          '$base/StateFlags/3/Key': '',
        },
      });
      final unit = projection.forest.single;
      expect(unit.stateFlags.map((f) => f.key),
          ['project.state.pressAtLoadPosition', 'project.state.airOk']);
      expect(unit.stateFlags[0].value, isTrue);
      expect(unit.stateFlags[0].since, isNotNull);
      expect(unit.stateFlags[1].stale, isTrue);
      expect(unit.stateFlags[1].value, isFalse);
    });
  });
}
