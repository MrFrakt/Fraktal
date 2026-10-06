import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:fraktal_hmi/data/opcua_snapshot_mapper.dart';
import 'package:fraktal_hmi/domain/types.dart';
import 'package:fraktal_hmi/ui/facet_cards.dart';
import 'package:fraktal_hmi/localization/localized_text.dart';
import 'package:fraktal_hmi/localization/localization_controller.dart';

Widget app(Widget child) => LocalizationScope(controller: LocalizationController(enabledLanguages: {'en'}, activeLanguage: 'en'),
    child: MaterialApp(home: Scaffold(body: SingleChildScrollView(child: child))));

void main() {
  test('the fifth and later declared shifts use the weekday editor', () {
    for (final index in [1, 5, 12]) {
      final field = CfgField('Days', CfgKind.lineCfg, CfgType.number, '96', labelKey: 'Days', unit: '',
          writeKey: 'line.shift.$index.activeDays', writeRevision: 1);
      expect(field.isWeekdayMask, isTrue);
    }
  });

  test('current and closed targets map independently, old bindings stay absent', () {
    Map<String, Object?> payload(Map<String, Object?> extra) => {
      'protocol': 'fraktal.opcua.snapshot.v1', 'values': {
        'PLC1/MAIN/Press/Status/Name': 'Press',
        'PLC1/MAIN/Press/Status/ModuleType': 1,
        'PLC1/MAIN/Press/CurrentShift': 5,
        'PLC1/MAIN/Press/ShiftHistoryCount': 1,
        'PLC1/MAIN/Press/ShiftHistory[1]/ShiftIndex': 4,
        ...extra,
      },
    };
    final mapper = OpcUaSnapshotMapper();
    final shift = mapper.map(payload({
      'PLC1/MAIN/Press/ShiftProductionTarget': 1300,
      'PLC1/MAIN/Press/ShiftHistory[1]/ProductionTarget': 1200,
      'PLC1/MAIN/Press/ShiftHistory[1]/GoodCount': 1250,
    })).forest.single.shift!;
    expect(shift.productionTarget, 1300);
    expect(shift.history.single.productionTarget, 1200);
    final legacy = mapper.map(payload({})).forest.single.shift!;
    expect(legacy.productionTarget, isNull);
    expect(legacy.history.single.productionTarget, isNull);
  });

  testWidgets('progress uses good parts, allows overachievement and keeps historical goal', (tester) async {
    await tester.pumpWidget(app(const ShiftCard(goodCount: 125, shift: ShiftFacet(currentShift: 5,
        productionTarget: 100, history: [ShiftRecord(shiftIndex: 4,
          productionTarget: 80, good: 60, nok: 20)]))));
    expect(find.text('125 / 100 good parts · 125.0%'), findsOneWidget);
    expect(find.text('80'), findsOneWidget);
    expect(find.text('75.0%'), findsOneWidget);
    expect(tester.widget<LinearProgressIndicator>(find.byType(LinearProgressIndicator)).value, 1);
    expect(tester.takeException(), isNull);
  });

  testWidgets('zero and unsupported targets produce no progress bar', (tester) async {
    for (final target in [null, 0]) {
      await tester.pumpWidget(app(ShiftCard(shift: ShiftFacet(currentShift: 1, productionTarget: target))));
      expect(find.byType(LinearProgressIndicator), findsNothing);
      expect(find.text('No production target configured for this shift.'), target == 0 ? findsOneWidget : findsNothing);
    }
  });
}
