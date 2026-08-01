// Control-size presets (touch targets for high-density panels / gloves) and the
// two maximum-contrast themes. The compact preset must stay byte-identical to
// what the HMI shipped before presets existed, so an existing panel is unchanged.
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:fraktal_hmi/domain/connection_settings.dart';
import 'package:fraktal_hmi/ui/app_theme.dart';

void main() {
  test('compact preset preserves the original Material sizing', () {
    final compact = UiMetrics.of(ControlScale.compact);
    expect(compact.touchTarget, 48, reason: 'Material baseline, as shipped');
    expect(compact.railWidth, 72);
    // Deliberately taller than Material's 56: a machine panel's bar carries
    // the reset control and must stay reachable at arm's length.
    expect(compact.appBarHeight, 64);
    expect(compact.treeRowHeight, 40);
    expect(compact.textScale, 1.0);
  });

  test('the app bar always clears its own tap targets', () {
    // A toolbar shorter than the buttons inside it clips them — the reason the
    // bar height is part of the preset rather than left at Material's 56.
    for (final m in ControlScale.values.map(UiMetrics.of)) {
      expect(m.appBarHeight, greaterThanOrEqualTo(m.touchTarget),
          reason: 'toolbar must fit a ${m.touchTarget}px action');
    }
  });

  test('the preset drives the generated app-bar theme', () {
    double barHeight(ControlScale s) =>
        themeAt(0, s).appBarTheme.toolbarHeight!;
    expect(barHeight(ControlScale.compact), 64);
    expect(barHeight(ControlScale.large),
        greaterThan(barHeight(ControlScale.compact)));
    // Bar icons scale with it, so actions do not look lost in a taller bar.
    expect(
        themeAt(0, ControlScale.large).appBarTheme.actionsIconTheme?.size,
        greaterThan(themeAt(0, ControlScale.compact)
            .appBarTheme
            .actionsIconTheme!
            .size!));
  });

  test('each preset grows every tap-relevant dimension', () {
    final scales = ControlScale.values.map(UiMetrics.of).toList();
    for (var i = 1; i < scales.length; i++) {
      final prev = scales[i - 1];
      final next = scales[i];
      expect(next.touchTarget, greaterThan(prev.touchTarget));
      expect(next.iconSize, greaterThan(prev.iconSize));
      expect(next.primaryIconSize, greaterThan(prev.primaryIconSize));
      expect(next.railWidth, greaterThan(prev.railWidth));
      expect(next.appBarHeight, greaterThan(prev.appBarHeight));
      expect(next.treeRowHeight, greaterThan(prev.treeRowHeight));
      expect(next.keyboardAlphaHeight, greaterThan(prev.keyboardAlphaHeight));
      expect(next.textScale, greaterThan(prev.textScale));
    }
    // Every preset stays at or above Material's 48 px accessibility floor.
    for (final m in scales) {
      expect(m.touchTarget, greaterThanOrEqualTo(48));
    }
  });

  test('the preset feeds the generated ThemeData button sizing', () {
    Size? minSize(ControlScale scale) {
      final theme = themeAt(0, scale);
      return theme.filledButtonTheme.style?.minimumSize
          ?.resolve(const <WidgetState>{});
    }

    expect(minSize(ControlScale.large)!.height,
        greaterThan(minSize(ControlScale.compact)!.height));
  });

  testWidgets('the Modules/Fieldbus selector grows in BOTH axes',
      (tester) async {
    // A wide-and-short control gets no easier to hit if only its height grows —
    // and SegmentedButton ignores both `minimumSize` and (for icon segments)
    // the themed padding, so this needs visualDensity. Measured, not assumed.
    Future<Size> sizeAt(ControlScale scale) async {
      await tester.pumpWidget(MaterialApp(
        theme: themeAt(0, scale),
        home: Scaffold(
          body: Center(
            child: SegmentedButton<bool>(
              segments: const [
                ButtonSegment(
                    value: false,
                    icon: Icon(Icons.account_tree),
                    label: Text('Modules')),
                ButtonSegment(
                    value: true,
                    icon: Icon(Icons.lan_outlined),
                    label: Text('Fieldbus')),
              ],
              selected: const {false},
              onSelectionChanged: (_) {},
            ),
          ),
        ),
      ));
      await tester.pumpAndSettle();
      return tester.getSize(find.byType(SegmentedButton<bool>));
    }

    final compact = await sizeAt(ControlScale.compact);
    final large = await sizeAt(ControlScale.large);
    expect(large.width, greaterThan(compact.width));
    expect(large.height, greaterThan(compact.height));
    // Compact must stay on Material's 48 dp floor.
    expect(compact.height, greaterThanOrEqualTo(48));
  });

  test('fourteen themes, with the two high-contrast variants last', () {
    expect(kThemes.length, 14);
    expect(kThemes[12].highContrast, isTrue);
    expect(kThemes[13].highContrast, isTrue);
    expect(kThemes[12].brightness, Brightness.light);
    expect(kThemes[13].brightness, Brightness.dark);
    // Index is persisted, so the previously-shipped order must not shift.
    expect(kThemes[0].nameKey, 'std.theme.lightBlue');
    expect(kThemes[11].nameKey, 'std.theme.oledBlack');
  });

  test('high contrast widens the tonal spread versus its normal counterpart',
      () {
    double luminanceGap(int index) {
      final scheme = themeAt(index).colorScheme;
      return (scheme.onSurface.computeLuminance() -
              scheme.surface.computeLuminance())
          .abs();
    }

    // 0 = Light Blue (normal light), 12 = high-contrast light.
    expect(luminanceGap(12), greaterThanOrEqualTo(luminanceGap(0)));
  });

  test('control scale round-trips through persisted settings', () {
    const settings = ConnectionSettings(controlScaleIndex: 2);
    final restored = ConnectionSettings.fromJson(settings.toJson());
    expect(restored!.controlScaleIndex, 2);

    // Absent (settings written before the preset existed) falls back to compact,
    // and an out-of-range value is clamped rather than crashing the boot.
    final legacy = Map<String, Object>.from(settings.toJson())
      ..remove('controlScaleIndex');
    expect(ConnectionSettings.fromJson(legacy)!.controlScaleIndex, 0);
    final bogus = Map<String, Object>.from(settings.toJson())
      ..['controlScaleIndex'] = 99;
    expect(ConnectionSettings.fromJson(bogus)!.controlScaleIndex, 2);
  });
}
