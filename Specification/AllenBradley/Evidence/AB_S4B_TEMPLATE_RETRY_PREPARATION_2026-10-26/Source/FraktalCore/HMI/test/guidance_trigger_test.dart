// Operator guidance must not take over the screen during a running cycle.
//
// Regression: the shipped guidance tab triggers on `*` (any step), limited only
// to WAIT_OPERATOR steps. A production AUTO cycle waits for the operator all the
// time — the press bench parks AUTO on `pressAwaitTwoHand`, a WAIT_OPERATOR step
// — so simply selecting AUTO threw a fullscreen dialog over the machine view
// before the operator had touched anything. Guidance that interrupts routine
// running teaches the operator to dismiss it, including when it matters.
//
// The trigger is now scoped by Unit mode: the SETUP modes (changeover, home,
// calibration, capability, adjustment) guide; AUTO and MANUAL do not.
import 'package:flutter_test/flutter_test.dart';

import 'package:fraktal_hmi/content/module_layout.dart';
import 'package:fraktal_hmi/domain/types.dart';

ModuleTabDefinition _guidance({
  int stepNo = 0,
  String stepName = '*',
  List<int> modes = const [],
}) =>
    ModuleTabDefinition(
      id: 'operator-guidance',
      title: 'std.module.tab.guidance',
      kind: ModuleTabKind.guidance,
      triggerStepNo: stepNo,
      triggerStepName: stepName,
      triggerModes: modes,
    );

void main() {
  group('mode scoping', () {
    test('a setup-scoped wildcard does not fire in AUTO', () {
      final tab = _guidance(modes: kSetupGuidanceModes);
      expect(
        tab.triggers(100, 'project.step.pressAwaitTwoHand',
            modeIndex: UnitMode.auto.index),
        isFalse,
        reason: 'AUTO parks on a WAIT_OPERATOR step; guidance there interrupts '
            'production the moment the mode is selected',
      );
    });

    test('the same wildcard fires in CHANGEOVER', () {
      final tab = _guidance(modes: kSetupGuidanceModes);
      expect(
        tab.triggers(20, 'project.step.changeoverConfirm',
            modeIndex: UnitMode.changeover.index),
        isTrue,
      );
    });

    test('MANUAL is excluded too — it is not a guided procedure', () {
      final tab = _guidance(modes: kSetupGuidanceModes);
      expect(
          tab.triggers(5, 'anything', modeIndex: UnitMode.manual.index),
          isFalse);
    });

    test('an unknown mode never satisfies a scoped trigger', () {
      // Opening a fullscreen dialog on a guess is the failure being prevented.
      final tab = _guidance(modes: kSetupGuidanceModes);
      expect(tab.triggers(20, 'x', modeIndex: null), isFalse);
    });

    test('an empty scope still means every mode (legacy profiles)', () {
      final tab = _guidance();
      for (final mode in UnitMode.values) {
        expect(tab.triggers(7, 'x', modeIndex: mode.index), isTrue,
            reason: 'an unscoped tab must behave exactly as before');
      }
      expect(tab.triggers(7, 'x', modeIndex: null), isTrue);
    });

    test('an exact step number is still mode-scoped', () {
      final tab = _guidance(stepNo: 42, stepName: '', modes: [
        UnitMode.changeover.index,
      ]);
      expect(tab.triggers(42, 'x', modeIndex: UnitMode.changeover.index),
          isTrue);
      expect(tab.triggers(42, 'x', modeIndex: UnitMode.auto.index), isFalse);
      expect(tab.triggers(41, 'x', modeIndex: UnitMode.changeover.index),
          isFalse);
    });
  });

  group('the shipped default', () {
    ModuleTabDefinition shippedGuidance() =>
        ModuleTabDefinition.defaults(const ModuleTabCapabilities(unit: true))
            .firstWhere((tab) => tab.kind == ModuleTabKind.guidance);

    test('is scoped to the setup modes, not AUTO', () {
      final tab = shippedGuidance();
      expect(tab.triggerModes, isNotEmpty,
          reason: 'an unscoped default is the defect');
      expect(tab.triggerModes, contains(UnitMode.changeover.index));
      expect(tab.triggerModes, isNot(contains(UnitMode.auto.index)));
      expect(tab.triggerModes, isNot(contains(UnitMode.manual.index)));
    });

    test('does not fire on the press bench AUTO two-hand wait', () {
      // The exact live case reported from the panel.
      expect(
        shippedGuidance().triggers(100, 'project.step.pressAwaitTwoHand',
            modeIndex: UnitMode.auto.index),
        isFalse,
      );
    });
  });

  group('persistence', () {
    test('round-trips through JSON', () {
      final tab = _guidance(modes: [
        UnitMode.changeover.index,
        UnitMode.home.index,
      ]);
      final restored = ModuleTabDefinition.fromJson(
          Map<String, Object?>.from(tab.toJson()));
      expect(restored, isNotNull);
      expect(restored!.triggerModes,
          [UnitMode.changeover.index, UnitMode.home.index]);
    });

    test('a profile written before mode scoping still loads', () {
      final legacy = <String, Object?>{
        'id': 'operator-guidance',
        'title': 'std.module.tab.guidance',
        'kind': 'guidance',
        'requiredLevel': 'operator',
        'triggerStepNo': 0,
        'triggerStepName': '*',
      };
      final restored = ModuleTabDefinition.fromJson(legacy);
      expect(restored, isNotNull);
      expect(restored!.triggerModes, isEmpty,
          reason: 'absent scoping must mean "every mode", not "no mode" — '
              'the latter would silently disable an admin\'s guidance');
    });

    test('garbage in the mode list is discarded, not fatal', () {
      final restored = ModuleTabDefinition.fromJson(<String, Object?>{
        'id': 'g',
        'title': 't',
        'kind': 'guidance',
        'requiredLevel': 'operator',
        'triggerModes': [3, 'nonsense', -1, 999, 3],
      });
      expect(restored, isNotNull);
      expect(restored!.triggerModes, [3], reason: 'dedup + range-check');
    });

    test('copyWith preserves the scope', () {
      final tab = _guidance(modes: kSetupGuidanceModes);
      expect(tab.copyWith(title: 'other').triggerModes, kSetupGuidanceModes);
    });
  });
  group('optional vs forced', () {
    // Two distinct jobs. OPTIONAL guidance is reference material the operator
    // may already know — it must never trap them. FORCED guidance is the step
    // genuinely waiting on this person (changeover model selection, confirming
    // it is safe to open the doors before tooling is swapped), where the
    // acknowledgement IS the point.

    test('the default is optional — blocking the panel is opt-in', () {
      const tab = ModuleTabDefinition(
        id: 'g',
        title: 't',
        kind: ModuleTabKind.guidance,
      );
      expect(tab.guidanceMode, GuidanceMode.optional,
          reason: 'a forgotten field must never block the operator');
    });

    test('the shipped guidance tab is optional', () {
      final tab = ModuleTabDefinition.defaults(
              const ModuleTabCapabilities(unit: true))
          .firstWhere((t) => t.kind == ModuleTabKind.guidance);
      expect(tab.guidanceMode, GuidanceMode.optional,
          reason: 'the generic default cannot know a step needs an '
              'acknowledgement; an integrator marks the ones that do');
    });

    test('forced survives a JSON round-trip', () {
      const tab = ModuleTabDefinition(
        id: 'g',
        title: 't',
        kind: ModuleTabKind.guidance,
        guidanceMode: GuidanceMode.forced,
      );
      final restored = ModuleTabDefinition.fromJson(
          Map<String, Object?>.from(tab.toJson()));
      expect(restored!.guidanceMode, GuidanceMode.forced);
    });

    test('optional is not written to JSON, and absence reads as optional', () {
      const tab = ModuleTabDefinition(
        id: 'g',
        title: 't',
        kind: ModuleTabKind.guidance,
      );
      expect(tab.toJson().containsKey('guidanceMode'), isFalse,
          reason: 'the default stays out of the file');
      final restored = ModuleTabDefinition.fromJson(<String, Object?>{
        'id': 'g',
        'title': 't',
        'kind': 'guidance',
        'requiredLevel': 'operator',
      });
      expect(restored!.guidanceMode, GuidanceMode.optional);
    });

    test('an unrecognised mode degrades to optional, never to forced', () {
      // Fail-open on THIS field: a corrupt profile must not be able to lock an
      // operator out of the panel.
      final restored = ModuleTabDefinition.fromJson(<String, Object?>{
        'id': 'g',
        'title': 't',
        'kind': 'guidance',
        'requiredLevel': 'operator',
        'guidanceMode': 'mandatory-ish',
      });
      expect(restored!.guidanceMode, GuidanceMode.optional);
    });

    test('copyWith preserves the mode', () {
      const tab = ModuleTabDefinition(
        id: 'g',
        title: 't',
        kind: ModuleTabKind.guidance,
        guidanceMode: GuidanceMode.forced,
      );
      expect(tab.copyWith(title: 'other').guidanceMode, GuidanceMode.forced);
    });

    test('the mode does not change WHETHER it opens, only how it behaves', () {
      // Scoping and insistence are independent: a forced tab still respects
      // its mode scope, and an optional one still opens.
      const forced = ModuleTabDefinition(
        id: 'g',
        title: 't',
        kind: ModuleTabKind.guidance,
        triggerStepName: '*',
        triggerModes: [3],
        guidanceMode: GuidanceMode.forced,
      );
      expect(forced.triggers(10, 'x', modeIndex: 3), isTrue);
      expect(forced.triggers(10, 'x', modeIndex: 0), isFalse);
    });
  });
}
