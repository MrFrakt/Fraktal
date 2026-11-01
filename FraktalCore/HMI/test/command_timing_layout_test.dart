import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:fraktal_hmi/domain/types.dart';
import 'package:fraktal_hmi/localization/localization_controller.dart';
import 'package:fraktal_hmi/localization/localized_text.dart';
import 'package:fraktal_hmi/ui/cycle_trend_view.dart';

const _rows = [
  CommandTiming(1, 'Extend', 3, Duration(seconds: 1),
      Duration(milliseconds: 500), Duration(seconds: 2), Duration(seconds: 1)),
  CommandTiming(2, 'Return', 1, Duration.zero, Duration.zero, Duration.zero,
      Duration.zero),
];

void main() {
  for (final width in [320.0, 394.0, 760.0]) {
    testWidgets('timing table fits a $width pixel card without blank rows',
        (tester) async {
      await tester.pumpWidget(LocalizationScope(
        controller: LocalizationController(
            enabledLanguages: {'en'}, activeLanguage: 'en'),
        child: MaterialApp(
          home: Scaffold(
            body: Align(
              alignment: Alignment.topLeft,
              child: SizedBox(
                width: width,
                child: const SingleChildScrollView(
                  child:
                      CommandTimingView(moduleName: 'PartSlide', rows: _rows),
                ),
              ),
            ),
          ),
        ),
      ));
      await tester.pumpAndSettle();
      expect(tester.takeException(), isNull);
      expect(find.text('Extend'), findsOneWidget);
      expect(find.text('Return'), findsOneWidget);
      expect(
          tester.getSize(find.byType(CommandTimingView)).height, lessThan(200));
      expect(find.text('Count'), findsOneWidget);
      expect(find.text('Max'), findsOneWidget);
      final horizontal = find.byWidgetPredicate((widget) =>
          widget is SingleChildScrollView &&
          widget.scrollDirection == Axis.horizontal);
      if (width < 600) {
        expect(horizontal, findsOneWidget);
        await tester.drag(horizontal, const Offset(-400, 0));
        await tester.pumpAndSettle();
        expect(find.text('Max').hitTestable(), findsOneWidget);
        expect(tester.takeException(), isNull);
      }
    });
  }
}
