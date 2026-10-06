import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:fraktal_hmi/domain/types.dart';
import 'package:fraktal_hmi/localization/localization_controller.dart';
import 'package:fraktal_hmi/localization/localized_text.dart';
import 'package:fraktal_hmi/ui/weekday_selector.dart';

void main() {
  test('weekday semantics require the portable Line calendar key', () {
    const field = CfgField('days', CfgKind.lineCfg, CfgType.number, '96',
      writeKey: 'line.shift.1.activeDays', minimum: 0, maximum: 127);
    expect(field.isWeekdayMask, isTrue);
    expect(field.accepts('96'), isTrue);
    expect(field.accepts('128'), isFalse);
    expect(const CfgField('days', CfgKind.stationCfg, CfgType.number, '96',
      writeKey: 'line.shift.1.activeDays').isWeekdayMask, isFalse);
  });

  testWidgets('weekend selection edits bits and disabled controls refuse input', (tester) async {
    var mask = 0;
    var enabled = true;
    late StateSetter rebuild;
    await tester.pumpWidget(LocalizationScope(
      controller: LocalizationController(enabledLanguages: {'en'}, activeLanguage: 'en'),
      child: MaterialApp(home: Scaffold(body: StatefulBuilder(builder: (context, setState) {
        rebuild = setState;
        return WeekdaySelector(mask: mask, enabled: enabled, keyPrefix: 'days',
          onChanged: (value) => setState(() => mask = value));
      }))),
    ));
    await tester.tap(find.text('Sat'));
    await tester.pump();
    await tester.tap(find.text('Sun'));
    await tester.pump();
    expect(mask, 96);
    expect(tester.widget<Checkbox>(find.byKey(const ValueKey('days-0'))).value, isFalse);
    rebuild(() => enabled = false);
    await tester.pump();
    expect(tester.widget<Checkbox>(find.byKey(const ValueKey('days-0'))).onChanged, isNull);
    await tester.tap(find.text('Mon'));
    await tester.pump();
    expect(mask, 96);
  });
}
