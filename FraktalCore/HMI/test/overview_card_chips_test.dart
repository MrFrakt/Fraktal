// A station card must not show a chip with nothing in it.
//
// The AB press publishes no `Model/ModelCode` - it has no changeover, which
// is a recorded deferral - so the model chip rendered as an icon with an
// empty label and read as a control that had failed to load. The rule is
// general: a chip is a value, and a station that does not have the value
// should not show the chip at all.
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:fraktal_hmi/domain/module_node.dart';
import 'package:fraktal_hmi/domain/types.dart';
import 'package:fraktal_hmi/localization/localization_controller.dart';
import 'package:fraktal_hmi/localization/localized_text.dart';
import 'package:fraktal_hmi/ui/app_theme.dart';
import 'package:fraktal_hmi/ui/overview_and_indicators.dart';

void main() {
  Future<List<Chip>> pumpCard(WidgetTester tester, ModuleNode node) async {
    await tester.pumpWidget(LocalizationScope(
      controller:
          LocalizationController(enabledLanguages: {'en'}, activeLanguage: 'en'),
      child: MaterialApp(
        theme: themeAt(0),
        home: Scaffold(body: StationCard(node: node)),
      ),
    ));
    await tester.pumpAndSettle();
    return tester.widgetList<Chip>(find.byType(Chip)).toList();
  }

  List<String> emptyLabels(List<Chip> chips) {
    final empty = <String>[];
    for (final chip in chips) {
      final label = chip.label;
      String text = 'n/a';
      if (label is Text) text = label.data ?? '';
      if (label is LText) text = label.data;
      if (text.trim().isEmpty) empty.add('${chip.avatar}');
    }
    return empty;
  }

  const bare = ModuleNode(
    path: 'Press',
    name: 'Press',
    type: ModuleType.unit,
    state: ExecState.ready,
    modeActive: UnitMode.manual,
  );

  testWidgets('a station with no changeover model shows no model chip',
      (tester) async {
    // The reported defect: an icon-only chip with nothing in it, which reads
    // as a control that failed to load rather than as an absent value.
    final chips = await pumpCard(tester, bare);
    expect(bare.modelCode, isEmpty, reason: 'the case under test');
    expect(emptyLabels(chips), isEmpty,
        reason: 'chips rendered with no label');
    expect(chips.any((c) => c.avatar != null), isFalse,
        reason: 'the model chip is the only one with an avatar');
  });

  testWidgets('a station WITH a model still shows it', (tester) async {
    // The other half, so the guard cannot be satisfied by dropping the chip
    // entirely.
    final chips = await pumpCard(
        tester,
        const ModuleNode(
          path: 'Press',
          name: 'Press',
          type: ModuleType.unit,
          state: ExecState.ready,
          modeActive: UnitMode.manual,
          modelCode: 'M-100',
        ));
    expect(emptyLabels(chips), isEmpty);
    final labels = [
      for (final c in chips)
        if (c.label is LText) (c.label as LText).data,
    ];
    expect(labels, contains('M-100'));
  });
}
