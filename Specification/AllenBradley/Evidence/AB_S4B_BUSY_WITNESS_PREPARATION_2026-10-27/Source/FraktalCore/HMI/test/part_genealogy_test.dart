import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:fraktal_hmi/data/opcua_snapshot_mapper.dart';
import 'package:fraktal_hmi/domain/types.dart';
import 'package:fraktal_hmi/localization/localization_controller.dart';
import 'package:fraktal_hmi/localization/localized_text.dart';
import 'package:fraktal_hmi/ui/facet_cards.dart';

Widget localized(Widget child) => LocalizationScope(
      controller: LocalizationController(
          enabledLanguages: {'en'}, activeLanguage: 'en'),
      child: child,
    );

void main() {
  test('genealogy uses the current published array across bindings', () {
    const base = 'PLC/Press/Part/Parents';
    for (final leaves in <Map<String, Object?>>[
      {
        base: ['BLANK', 'INSERT', '']
      },
      {'$base[0]': 'BLANK', '$base[1]': 'INSERT', '$base[2]': ''},
      {'$base/1': 'BLANK', '$base/2': 'INSERT', '$base/3': ''},
      {'$base/Parents[1]': 'BLANK', '$base/Parents[2]': 'INSERT'},
      {'$base/Parents/0': 'BLANK', '$base/Parents/1': 'INSERT'},
    ]) {
      final mapper = OpcUaSnapshotMapper();
      Map<String, Object?> values(Map<String, Object?> parents) => {
            'PLC/Press/Status/Name': 'Press',
            'PLC/Press/Status/ModuleType': ModuleType.unit.index,
            'PLC/Press/Part/Uid': 'ASSEMBLY',
            ...parents,
          };
      final part = mapper.map({'values': values(leaves)}).forest.single.part!;
      expect(part.parents, ['BLANK', 'INSERT']);
      final next = mapper.map({'values': values({})}).forest.single.part!;
      expect(next.parents, isEmpty);
    }
  });

  testWidgets('generic Part card displays selectable component identities',
      (tester) async {
    await tester.pumpWidget(localized(const MaterialApp(
      home: Scaffold(
        body: PartCard(
          part: PartFacet(uid: 'ASSEMBLY', parents: ['BLANK', 'INSERT']),
        ),
      ),
    )));
    expect(find.widgetWithText(SelectableText, 'BLANK'), findsOneWidget);
    expect(find.widgetWithText(SelectableText, 'INSERT'), findsOneWidget);
    await tester.pumpWidget(localized(const MaterialApp(
      home: Scaffold(body: PartCard(part: PartFacet(uid: 'NEXT'))),
    )));
    expect(find.text('BLANK'), findsNothing);
    expect(find.text('INSERT'), findsNothing);
  });
}
