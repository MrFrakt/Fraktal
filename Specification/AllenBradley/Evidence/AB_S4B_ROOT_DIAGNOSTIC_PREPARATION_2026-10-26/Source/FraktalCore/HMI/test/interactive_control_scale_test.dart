import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:fraktal_hmi/domain/module_node.dart';
import 'package:fraktal_hmi/domain/types.dart';
import 'package:fraktal_hmi/content/module_layout.dart';
import 'package:fraktal_hmi/localization/localization_controller.dart';
import 'package:fraktal_hmi/localization/localized_text.dart';
import 'package:fraktal_hmi/ui/app_theme.dart';
import 'package:fraktal_hmi/ui/config_and_history.dart';
import 'package:fraktal_hmi/ui/image_overlay.dart';
import 'package:fraktal_hmi/ui/language_settings.dart';
import 'package:fraktal_hmi/ui/timing_chart_filters.dart';

Future<void> _pump(
    WidgetTester tester, ControlScale scale, Widget child) async {
  await tester.pumpWidget(ControlScaleScope(
    metrics: UiMetrics.of(scale),
    child: LocalizationScope(
      controller: LocalizationController(
          enabledLanguages: {'en'}, activeLanguage: 'en'),
      child: MaterialApp(
        theme: themeAt(0, scale),
        home: Scaffold(body: Center(child: child)),
      ),
    ),
  ));
  await tester.pumpAndSettle();
}

void main() {
  testWidgets('every interactive chip grows and accepts taps at its outer edge',
      (tester) async {
    List<Size>? previous;
    for (final scale in ControlScale.values) {
      final counts = List.filled(5, 0);
      await _pump(
          tester,
          scale,
          Wrap(spacing: 8, children: [
            PresetChip(
                child: FilterChip(
                    label: const Text('Time type'),
                    selected: true,
                    onSelected: (_) => counts[0]++)),
            PresetChip(
                child: ChoiceChip(
                    label: const Text('Event type'),
                    selected: false,
                    onSelected: (_) => counts[1]++)),
            PresetChip(
                child: ActionChip(
                    label: const Text('Show all'),
                    onPressed: () => counts[2]++)),
            PresetChip(
                child: InputChip(
                    label: const Text('Binding'),
                    deleteIcon: const Icon(Icons.cancel),
                    onPressed: () => counts[3]++,
                    onDeleted: () => counts[4]++)),
          ]));
      final finders = [
        find.byType(FilterChip),
        find.byType(ChoiceChip),
        find.byType(ActionChip),
        find.byType(InputChip),
      ];
      final sizes = finders.map(tester.getSize).toList();
      for (var i = 0; i < finders.length; i++) {
        expect(sizes[i].height,
            greaterThanOrEqualTo(UiMetrics.of(scale).touchTarget));
        if (previous != null) {
          expect(sizes[i].height, greaterThan(previous[i].height));
          expect(sizes[i].width, greaterThan(previous[i].width));
        }
        final rect = tester.getRect(finders[i]);
        await tester.tapAt(Offset(rect.center.dx, rect.top + 2));
      }
      expect(counts.take(4), everyElement(1));
      await tester.tap(find.byIcon(Icons.cancel));
      expect(counts[4], 1);
      previous = sizes;
    }
  });

  testWidgets('time filters and Show all share a row height at every preset',
      (tester) async {
    for (final scale in ControlScale.values) {
      await _pump(
          tester,
          scale,
          TimingChartFilters<int>(
            key: ValueKey(scale),
            options: const [TimingChartOption(0, 'Work', Colors.green)],
            builder: (_, hidden, legend) => legend,
          ));
      final height = tester.getSize(find.byType(FilterChip)).height;
      await tester.tap(find.byType(FilterChip));
      await tester.pumpAndSettle();
      expect(tester.getSize(find.byType(ActionChip)).height, height);
      expect(tester.getSize(find.byType(FilterChip)).height, height);
      expect(height, greaterThanOrEqualTo(UiMetrics.of(scale).touchTarget));
      await tester.tap(find.text('Show all'));
      await tester.pumpAndSettle();
      expect(
          tester.widget<FilterChip>(find.byType(FilterChip)).selected, isTrue);
    }
  });

  testWidgets('actual event filters inherit the preset and still toggle',
      (tester) async {
    double previousHeight = 0;
    for (final scale in ControlScale.values) {
      await _pump(
          tester,
          scale,
          HistoryBrowser(
              key: ValueKey(scale),
              node: const ModuleNode(
                  name: 'Press', path: 'Press', type: ModuleType.unit)));
      final filters = find.byType(FilterChip);
      final height = tester.getSize(filters.first).height;
      expect(height, greaterThanOrEqualTo(UiMetrics.of(scale).touchTarget));
      expect(height, greaterThan(previousHeight));
      await tester.tap(filters.first);
      await tester.pumpAndSettle();
      expect(tester.widget<FilterChip>(filters.first).selected, isFalse);
      previousHeight = height;
    }
  });

  testWidgets('toggle glyphs and their actual hit areas grow together',
      (tester) async {
    for (final scale in ControlScale.values) {
      final values = <bool>[];
      await _pump(
          tester,
          scale,
          PresetToggle(
              child: Checkbox(value: false, onChanged: (v) => values.add(v!))));
      final rect = tester.getRect(find.byType(PresetToggle));
      expect(rect.size, Size.square(UiMetrics.of(scale).touchTarget));
      // A point that was outside the old 48 dp target must be reachable now.
      await tester.tapAt(Offset(rect.left + 2, rect.center.dy));
      expect(values, [true]);
      await tester.sendKeyEvent(LogicalKeyboardKey.tab);
      await tester.sendKeyEvent(LogicalKeyboardKey.space);
      expect(values, [true, true]);
      await _pump(tester, scale,
          const PresetToggle(child: Checkbox(value: false, onChanged: null)));
      await tester.tapAt(Offset(rect.left + 2, rect.center.dy));
      expect(values, [true, true], reason: 'disabled toggle accepted a tap');
    }
  });

  testWidgets('switch rows preserve whole-row, switch and keyboard activation',
      (tester) async {
    for (final scale in ControlScale.values) {
      final values = <bool>[];
      await _pump(
          tester,
          scale,
          PresetSwitchListTile(
              value: false,
              title: const Text('Floating keyboard'),
              onChanged: values.add));
      final tile = find.byType(ListTile);
      expect(tester.getSize(tile).height,
          greaterThanOrEqualTo(UiMetrics.of(scale).touchTarget));
      expect(tester.getSize(find.byType(PresetToggle)).height,
          UiMetrics.of(scale).touchTarget);
      final rect = tester.getRect(find.byType(PresetToggle));
      await tester.tapAt(Offset(rect.right - 2, rect.center.dy));
      await tester.tap(find.text('Floating keyboard'));
      expect(values, [true, true]);
      await tester.sendKeyEvent(LogicalKeyboardKey.tab);
      await tester.sendKeyEvent(LogicalKeyboardKey.enter);
      expect(values, [true, true, true]);
      await _pump(
          tester,
          scale,
          const PresetSwitchListTile(
              value: false, title: Text('Floating keyboard'), onChanged: null));
      await tester.tap(find.text('Floating keyboard'));
      expect(values, [true, true, true]);
    }
  });

  testWidgets('language checkboxes paint at the preset size and remain usable',
      (tester) async {
    for (final scale in ControlScale.values) {
      await _pump(
          tester,
          scale,
          FirstLanguageSelection(
              key: ValueKey(scale),
              controller: LocalizationController(
                  enabledLanguages: {'en'}, activeLanguage: 'en'),
              initialEnabled: const {'en'},
              initialActive: 'en',
              onContinue: (_, language) {}));
      final tile = find.byType(CheckboxListTile).at(1);
      final checkbox =
          find.descendant(of: tile, matching: find.byType(Checkbox));
      // getRect includes the painted transform, not just the 48 dp layout slot.
      expect(tester.getRect(checkbox).height, UiMetrics.of(scale).touchTarget);
      await tester.ensureVisible(tile);
      await tester.tap(tile);
      await tester.pumpAndSettle();
      expect(tester.widget<CheckboxListTile>(tile).value, isTrue);
    }
  });

  testWidgets('picture toolbar keeps sized actions reachable on a narrow layer',
      (tester) async {
    for (final scale in ControlScale.values) {
      var removed = false;
      await _pump(
          tester,
          scale,
          SizedBox(
            width: 240,
            height: 280,
            child: PlacementEditor(
                key: ValueKey(scale),
                image: const Rect.fromLTWH(0, 0, 240, 280),
                controls: const [
                  ModuleControlDefinition(
                      id: 'door',
                      kind: ModuleControlKind.shape,
                      placement:
                          ModulePlacement(x: .1, y: .1, width: .2, height: .2)),
                ],
                render: (_) => const ColoredBox(color: Colors.grey),
                onRemove: (_) => removed = true),
          ));
      await tester.tap(find.byKey(const ValueKey('placed-door')));
      await tester.pumpAndSettle();
      expect(
          tester
              .getSize(find.widgetWithIcon(IconButton, Icons.edit_outlined))
              .height,
          UiMetrics.of(scale).touchTarget);
      await tester.drag(
          find.byType(SingleChildScrollView), const Offset(-400, 0));
      await tester.pumpAndSettle();
      await tester.tap(find.widgetWithIcon(IconButton, Icons.delete_outline));
      expect(removed, isTrue);
      expect(tester.takeException(), isNull);
    }
  });
}
