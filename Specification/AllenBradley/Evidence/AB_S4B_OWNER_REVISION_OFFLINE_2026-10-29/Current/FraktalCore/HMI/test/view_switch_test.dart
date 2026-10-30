// The view selector, which replaced a SegmentedButton because that widget
// cannot be shaped or sized from the theme: `segmentStyleFor` copies a fixed
// property list onto each segment and hard-codes the segment shape, dropping
// both `shape` and `minimumSize` from the style it was given.
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:fraktal_hmi/localization/localization_controller.dart';
import 'package:fraktal_hmi/localization/localized_text.dart';
import 'package:fraktal_hmi/ui/app_theme.dart';
import 'package:fraktal_hmi/ui/view_switch.dart';

Widget _host(ThemeData theme, ControlScale scale, bool value,
        ValueChanged<bool> onChanged) =>
    LocalizationScope(
      controller: LocalizationController(
          enabledLanguages: {'en'}, activeLanguage: 'en'),
      child: MaterialApp(
        theme: theme,
        home: ControlScaleScope(
          metrics: UiMetrics.of(scale),
          child: Scaffold(
            body: Center(
              child: ViewSwitch<bool>(
                options: const [
                  ViewSwitchOption(
                      value: false, icon: Icons.account_tree, label: 'Modules'),
                  ViewSwitchOption(
                      value: true, icon: Icons.lan_outlined, label: 'Fieldbus'),
                ],
                value: value,
                onChanged: onChanged,
              ),
            ),
          ),
        ),
      ),
    );

void main() {
  testWidgets('it renders both options and reports the one tapped',
      (tester) async {
    bool? picked;
    await tester.pumpWidget(
        _host(themeAt(0), ControlScale.compact, false, (v) => picked = v));
    await tester.pumpAndSettle();
    expect(find.text('Modules'), findsOneWidget);
    expect(find.text('Fieldbus'), findsOneWidget);
    await tester.tap(find.text('Fieldbus'));
    await tester.pumpAndSettle();
    expect(picked, isTrue);
  });

  testWidgets('it keeps one height per preset and never becomes a stadium',
      (tester) async {
    for (final scale in ControlScale.values) {
      await tester.pumpWidget(_host(themeAt(0), scale, false, (_) {}));
      await tester.pumpAndSettle();
      final box = tester.getSize(find.byType(ViewSwitch<bool>));
      expect(box.height, UiMetrics.of(scale).touchTarget,
          reason: '$scale: the switch did not take the preset height');
      // The defect being replaced: a shape whose radius is half the height.
      final container = tester.widget<Container>(
        find
            .descendant(
                of: find.byType(ViewSwitch<bool>),
                matching: find.byType(Container))
            .first,
      );
      final decoration = container.decoration as BoxDecoration;
      final radius = (decoration.borderRadius as BorderRadius).topLeft.x;
      expect(radius, lessThan(box.height / 2),
          reason: '$scale: radius $radius is stadium-shaped');
    }
  });

  testWidgets('the selected half uses a guaranteed scheme pair in every theme',
      (tester) async {
    // Legibility here is the scheme's promise, not a local colour choice, so
    // the contrast scan already covers it - this proves the widget really
    // uses that pair rather than a fill with inherited ink.
    for (var i = 0; i < kThemes.length; i++) {
      final theme = themeAt(i);
      await tester
          .pumpWidget(_host(theme, ControlScale.compact, false, (_) {}));
      await tester.pumpAndSettle();
      final materials = tester
          .widgetList<Material>(find.descendant(
              of: find.byType(ViewSwitch<bool>),
              matching: find.byType(Material)))
          .toList();
      final fills = materials.map((m) => m.color).toList();
      expect(fills, contains(theme.colorScheme.primary),
          reason: '${kThemes[i].nameKey}: selected half is not primary');
      final label = tester.widget<Text>(find.text('Modules'));
      expect(label.style?.color, theme.colorScheme.onPrimary,
          reason: '${kThemes[i].nameKey}: selected label is not onPrimary');
    }
  });
}
