// The commissioning step that sets how a panel looks and who may change it.
// Theme and control size depend on the physical screen, so they are chosen at
// the panel; the two access levels are panel-local policy (the PLC keeps its own
// §7.7 gates per root and is never overridden from here).
import 'package:flutter_test/flutter_test.dart';

import 'package:fraktal_hmi/domain/connection_settings.dart';
import 'package:fraktal_hmi/domain/types.dart';
import 'package:fraktal_hmi/state/app_state.dart';
import 'package:fraktal_hmi/data/sim_repository.dart';

void main() {
  test('appearance and access choices round-trip through settings', () {
    const chosen = ConnectionSettings(
      themeIndex: 12, // high-contrast light
      controlScaleIndex: 2, // large
      themeMinLevelIndex: 3, // engineer
      closeAppMinLevelIndex: 4, // admin
      appearanceSetupComplete: true,
    );
    final restored = ConnectionSettings.fromJson(chosen.toJson())!;
    expect(restored.themeIndex, 12);
    expect(restored.controlScaleIndex, 2);
    expect(restored.themeMinLevelIndex, 3);
    expect(restored.closeAppMinLevelIndex, 4);
    expect(restored.appearanceSetupComplete, isTrue);
  });

  test('settings written before this step existed keep working', () {
    // Absent keys must fall back, never reject the file and strand the panel.
    final legacy = Map<String, Object>.from(const ConnectionSettings().toJson())
      ..remove('themeMinLevelIndex')
      ..remove('closeAppMinLevelIndex')
      ..remove('appearanceSetupComplete');
    final restored = ConnectionSettings.fromJson(legacy)!;
    expect(restored.themeMinLevelIndex, 0, reason: 'appearance stays open');
    expect(restored.closeAppMinLevelIndex, 2, reason: 'TECHNICIAN default');
    expect(restored.appearanceSetupComplete, isFalse,
        reason: 'so the step is offered once on an upgraded panel');
  });

  test('a corrupt level index cannot crash the boot', () {
    final bogus = Map<String, Object>.from(const ConnectionSettings().toJson())
      ..['themeMinLevelIndex'] = 99
      ..['closeAppMinLevelIndex'] = -5;
    final restored = ConnectionSettings.fromJson(bogus)!;
    expect(restored.themeMinLevelIndex, inInclusiveRange(0, 4));
    expect(restored.closeAppMinLevelIndex, inInclusiveRange(0, 4));
  });

  group('HMI-local floors can only tighten, never loosen', () {
    // The PLC publishes its own §7.7 policy per root and re-checks every
    // request. A panel-local floor is ANDed with it, so it can add a
    // requirement but must never grant something the PLC denies.
    // permitsLocal takes the session explicitly (the reset fan-out needs it
    // per root), so the PLC side can be varied without touching AppState.
    AccessSession sessionWith(
        AccessLevel userLevel, GatedAction action, AccessLevel plcRequires) {
      final required = List<AccessLevel>.filled(11, AccessLevel.none);
      required[action.index] = plcRequires;
      return AccessSession(level: userLevel, required: required);
    }

    AppState appWithFloor(AccessLevel floor, GatedAction action) => AppState(
          SimRepository(),
          config: action == GatedAction.manual
              ? HmiConfig(manualMinLevel: floor)
              : HmiConfig(alarmResetMinLevel: floor),
        );

    for (final action in [GatedAction.manual, GatedAction.alarmReset]) {
      test('${action.name}: a floor above the PLC restricts', () {
        final app = appWithFloor(AccessLevel.engineer, action);
        addTearDown(app.dispose);
        expect(
            app.permitsLocal(action,
                // PLC would allow anyone; the panel demands ENGINEER.
                forSession: sessionWith(
                    AccessLevel.operator, action, AccessLevel.none)),
            isFalse,
            reason: 'the panel adds a requirement the operator does not meet');
      });

      test('${action.name}: a floor below the PLC cannot grant', () {
        final app =
            appWithFloor(AccessLevel.none, action); // panel adds nothing
        addTearDown(app.dispose);
        expect(
            app.permitsLocal(action,
                // The PLC demands ENGINEER, so an open panel must not help.
                forSession: sessionWith(
                    AccessLevel.operator, action, AccessLevel.engineer)),
            isFalse,
            reason: 'PLC policy is authoritative and still refuses');
      });

      test('${action.name}: both satisfied allows', () {
        final app = appWithFloor(AccessLevel.technician, action);
        addTearDown(app.dispose);
        expect(
            app.permitsLocal(action,
                forSession: sessionWith(
                    AccessLevel.technician, action, AccessLevel.operator)),
            isTrue);
      });
    }
  });

  test('the chosen levels actually gate the app', () {
    // Engineer-only appearance: the sim publishes AccessLevel.none.
    final app = AppState(
      SimRepository(),
      config: const HmiConfig(themeMinLevel: AccessLevel.engineer),
    );
    addTearDown(app.dispose);
    expect(app.setTheme(3), isFalse, reason: 'below the configured level');
    expect(app.themeIndex, 0, reason: 'and nothing changed');
  });
}
