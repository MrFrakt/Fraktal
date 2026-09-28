// A value is edited in the control its type calls for: a flag is a checkbox,
// a fixed set of values is a dropdown of TRANSLATED labels, and a number shows
// its unit - translated from the code the PLC publishes - or nothing when the
// unit is NONE. Nobody types TRUE, FALSE or an ordinal by hand.
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:fraktal_hmi/data/opcua_config_manifest.dart';
import 'package:fraktal_hmi/data/sim_repository.dart';
import 'package:fraktal_hmi/domain/types.dart';
import 'package:fraktal_hmi/localization/localization_controller.dart';
import 'package:fraktal_hmi/localization/localized_text.dart';
import 'package:fraktal_hmi/state/app_state.dart';
import 'package:fraktal_hmi/ui/config_and_history.dart';

void main() {
  group('unit keys', () {
    test('a code wins, NONE shows nothing, an older PLC keeps its text', () {
      const coded = CfgField('a', CfgKind.stationCfg, CfgType.number, '1',
          unit: 'ms', unitCode: EngUnit.millimeter);
      expect(coded.unitKey, 'std.unit.millimeter');
      const none = CfgField('b', CfgKind.stationCfg, CfgType.number, '1',
          unit: 'ms', unitCode: EngUnit.none);
      expect(none.unitKey, '');
      const legacy =
          CfgField('c', CfgKind.stationCfg, CfgType.number, '1', unit: 'bar');
      expect(legacy.unitKey, 'bar');
    });

    test('the PLC code maps by ordinal; an unknown one shows no unit', () {
      List<CfgField> fields(int code) => configFieldsFromManifest([
            ConfigManifestEntry('Press', 'StationCfg/X', '1',
                writeKey: 'x',
                writeRevision: 1,
                valueType: 0,
                writable: true,
                unitCode: code),
          ])['Press']!;
      expect(fields(6).single.unitCode, EngUnit.millimeter);
      expect(fields(999).single.unitCode, EngUnit.none);
    });
  });

  testWidgets('flag is a checkbox, choice a translated dropdown, unit beside',
      (tester) async {
    tester.view.physicalSize = const Size(1200, 1400);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    final repo = SimRepository();
    final app = AppState(repo);
    final localization =
        LocalizationController(enabledLanguages: {'en'}, activeLanguage: 'en');
    await tester.pumpWidget(LocalizationScope(
      controller: localization,
      child: MaterialApp(
        home: Scaffold(
          body: ListenableBuilder(
            listenable: app,
            builder: (context, _) {
              final node = app.forest
                  .where((root) => root.path == 'StationA')
                  .firstOrNull;
              return node == null
                  ? const SizedBox()
                  : SingleChildScrollView(
                      child: ConfigEditor(app: app, node: node));
            },
          ),
        ),
      ),
    ));
    await tester.pump(const Duration(seconds: 2));
    expect(await repo.login('StationA', 'admin1', '2468'), isTrue);
    await tester.pump(const Duration(seconds: 2));

    // Each kind of data is its own group, and a value sits inside its group.
    final station = find.byKey(const ValueKey('cfg-group-stationCfg'));
    expect(station, findsOneWidget, reason: 'station config is its own group');
    expect(find.text('Station configuration'), findsOneWidget);

    final flag = find.byKey(const ValueKey('cfg-flag-Require two-hand start'));
    expect(find.descendant(of: station, matching: flag), findsOneWidget,
        reason: 'a station value is drawn inside the station group');
    expect(flag, findsOneWidget,
        reason: 'a flag is a checkbox, not TRUE/FALSE');
    expect(tester.widget<Checkbox>(flag).value, isTrue);
    await tester.tap(flag);
    await tester.pump();
    expect(tester.widget<Checkbox>(flag).value, isFalse);

    expect(find.text('Confirm first – the HMI asks before switching'),
        findsOneWidget,
        reason: 'the choice shows its translated label, not the ordinal 1');
    expect(find.byWidgetPredicate((w) => w is DropdownButtonFormField<String>),
        findsOneWidget);

    Text unitOf(String name) =>
        tester.widget<Text>(find.byKey(ValueKey('cfg-unit-$name')));
    expect(unitOf('Clamp settle time').data, 'ms');
    expect(unitOf('MES port').data, '', reason: 'no unit: no unit text');
    // The unit FOLLOWS the value (English/Spanish reading order).
    final unitBox = tester
        .getRect(find.byKey(const ValueKey('cfg-unit-Clamp settle time')));
    final fieldBox = tester.getRect(find
        .ancestor(
            of: find.byKey(const ValueKey('cfg-unit-Clamp settle time')),
            matching: find.byType(Row))
        .first);
    expect(unitBox.left, greaterThan(fieldBox.left + fieldBox.width / 2),
        reason: 'the unit sits to the right of the value field');
    app.dispose(); // stops the simulator's timer
  });
}
