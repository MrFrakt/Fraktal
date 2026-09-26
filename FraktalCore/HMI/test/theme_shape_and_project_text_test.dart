// Two things reported as still broken after a rebuild, pinned so the answer
// is a measurement rather than an argument about browser caches:
//
//   * the Modules/Fieldbus selector rendering as a lozenge at `large`
//   * `project.module.press` rendering as a raw key
//
// Both are checked against the real theme and the real catalogue.
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:fraktal_hmi/localization/default_catalogs.dart';
import 'package:fraktal_hmi/ui/app_theme.dart';

void main() {
  group('the pressable shape is capped, not a stadium', () {
    test('every preset resolves a bounded corner radius', () {
      for (final scale in ControlScale.values) {
        final style = themeAt(0, scale).segmentedButtonTheme.style;
        final shape = style?.shape?.resolve(const <WidgetState>{});
        expect(shape, isA<RoundedRectangleBorder>(),
            reason: '$scale: segmented button is not a rounded rectangle');
        final radius = ((shape as RoundedRectangleBorder).borderRadius
                as BorderRadius)
            .topLeft
            .x;
        // The defect was a radius that grew with the height until it was a
        // stadium: at `large` the control is 76 px tall, so half-height is 38.
        expect(radius, lessThanOrEqualTo(16.0),
            reason: '$scale: radius $radius is on its way to a stadium');
        expect(radius, greaterThanOrEqualTo(10.0), reason: '$scale: too sharp');
      }
    });

    test('buttons use the same capped shape as the selector', () {
      for (final scale in ControlScale.values) {
        final theme = themeAt(0, scale);
        for (final entry in <String, ButtonStyle?>{
          'filled': theme.filledButtonTheme.style,
          'elevated': theme.elevatedButtonTheme.style,
          'outlined': theme.outlinedButtonTheme.style,
          'text': theme.textButtonTheme.style,
        }.entries) {
          final shape = entry.value?.shape?.resolve(const <WidgetState>{});
          expect(shape, isA<RoundedRectangleBorder>(),
              reason: '$scale/${entry.key} kept the stadium default');
        }
      }
    });

    testWidgets('a rendered selector is not stadium-shaped at large',
        (tester) async {
      // The theme value above proves what we set; this proves the widget
      // actually takes it, which is the half that was in doubt.
      await tester.pumpWidget(MaterialApp(
        theme: themeAt(0, ControlScale.large),
        home: Scaffold(
          body: Center(
            child: SegmentedButton<bool>(
              segments: const [
                ButtonSegment(value: false, label: Text('Modules')),
                ButtonSegment(value: true, label: Text('Fieldbus')),
              ],
              selected: const {false},
              onSelectionChanged: (_) {},
            ),
          ),
        ),
      ));
      await tester.pumpAndSettle();
      final resolved = tester
          .widget<SegmentedButton<bool>>(find.byType(SegmentedButton<bool>));
      // The widget carries no style of its own, so the theme is what decides.
      expect(resolved.style, isNull);
      final themed = Theme.of(tester.element(find.byType(SegmentedButton<bool>)))
          .segmentedButtonTheme
          .style
          ?.shape
          ?.resolve(const <WidgetState>{});
      expect(themed, isA<RoundedRectangleBorder>());
      expect(themed, isNot(isA<StadiumBorder>()));
    });
  });

  group('the AB press has words', () {
    test('module names resolve rather than rendering as keys', () {
      const expected = <String, String>{
        'project.module.press': 'Pneumatic press',
        'project.module.door': 'Access door',
        'project.module.partslide': 'Part slide',
        'project.module.pressram': 'Press ram',
      };
      expected.forEach((key, value) {
        expect(projectEnglish[key], value, reason: '$key is unlocalized');
      });
    });

    test('a channel description and a refusal resolve too', () {
      expect(projectEnglish['project.io.door_closed'], 'Door closed');
      expect(projectEnglish['project.mailbox.refused.force_not_permitted'],
          isNotNull);
    });

    test('no project key is an empty string', () {
      // An empty value renders as nothing at all, which looks like a blank
      // button rather than a missing translation.
      final blank = [
        for (final e in projectEnglish.entries)
          if (e.value.trim().isEmpty) e.key,
      ];
      expect(blank, isEmpty);
    });
  });
}
