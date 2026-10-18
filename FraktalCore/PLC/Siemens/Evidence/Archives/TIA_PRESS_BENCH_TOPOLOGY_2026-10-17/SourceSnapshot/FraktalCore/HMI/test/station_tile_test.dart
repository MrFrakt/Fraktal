// LOCALIZATION §7.5: the station tile's geometry is fixed and its slot
// contents are type-authored. Twelve tiles must read as one table, so a metric
// keeps its column on every tile, an OK badge is neutral (colour means
// abnormal on the overview), and a tile with slots still fits the overview's
// fixed cell.
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:fraktal_hmi/content/content_store.dart';
import 'package:fraktal_hmi/content/module_content_controller.dart';
import 'package:fraktal_hmi/domain/module_node.dart';
import 'package:fraktal_hmi/domain/types.dart';
import 'package:fraktal_hmi/localization/localization_controller.dart';
import 'package:fraktal_hmi/localization/localized_text.dart';
import 'package:fraktal_hmi/ui/app_theme.dart';
import 'package:fraktal_hmi/ui/overview_and_indicators.dart';

const _rate = ModuleControlDefinition(
  id: 'rate',
  kind: ModuleControlKind.value,
  label: 'Rate',
  unit: 'ppm',
  bindings: ['OutImm/Rate'],
);
const _air = ModuleControlDefinition(
  id: 'air',
  kind: ModuleControlKind.shape,
  label: 'Air',
  bindings: ['OutImm/AirOk'],
  rules: [
    ModuleStateRule(
        compare: ModuleCompare.isFalse, token: ModuleStateToken.error)
  ],
  defaultToken: ModuleStateToken.ok,
);
const _profile = ModuleTileProfile(metrics: [_rate], badges: [_air]);

ModuleContentController _controller() => ModuleContentController(
      store: MemoryContentStore(),
      localization: LocalizationController(
          enabledLanguages: {'en'}, activeLanguage: 'en'),
    );

void main() {
  test('a tile holds at most 3 metrics and 2 badges, of the right kinds', () {
    expect(_profile.isValid, isTrue);
    expect(
        const ModuleTileProfile(metrics: [_rate, _rate, _rate, _rate]).isValid,
        isFalse);
    expect(const ModuleTileProfile(metrics: [_air]).isValid, isFalse,
        reason: 'a metric slot is a value, not a shape');
    final restored = ModuleTileProfile.fromJson(_profile.toJson())!;
    expect(restored.metrics.single.unit, 'ppm');
    expect(restored.badges.single.rules.single.token, ModuleStateToken.error);
    expect(
        ModuleTileProfile.fromJson({
          'metrics': [
            _rate.toJson(),
            {'id': 'broken'}
          ],
        }),
        isNull,
        reason: 'refused whole, never shown with a slot missing');
  });

  test('a type tile reaches every station of the type, and travels', () async {
    final content = _controller();
    final scope = ModuleContentController.typeScope('project.moduleType.press');
    await content.publishTile(scope, _profile);
    expect(content.tileFor('PressA', typeKey: 'project.moduleType.press'),
        isNotNull);
    expect(content.tileFor('PressB', typeKey: 'project.moduleType.press'),
        isNotNull);
    expect(content.tileFor('Conveyor', typeKey: 'project.moduleType.belt'),
        isNull);
    await expectLater(
      content.publishTile(
          'PressA', const ModuleTileProfile(badges: [_air, _air, _air])),
      throwsA(isA<FormatException>()),
    );
    final imported = _controller();
    await imported.importBundle(content.exportBundle(),
        availableModulePaths: const ['PressC']);
    expect(
        imported
            .tileFor('PressC', typeKey: 'project.moduleType.press')
            ?.metrics
            .single
            .id,
        'rate');
    await content.publishTile(scope, const ModuleTileProfile());
    expect(
        content.tileFor('PressA', typeKey: 'project.moduleType.press'), isNull,
        reason: 'an empty tile removes the profile');
  });

  Future<void> pumpTile(
      WidgetTester tester, Map<String, Object?> values) async {
    await tester.pumpWidget(LocalizationScope(
      controller: LocalizationController(
          enabledLanguages: {'en'}, activeLanguage: 'en'),
      child: MaterialApp(
        theme: themeAt(0),
        home: Scaffold(
          body: Center(
            // One cell of the overview grid: 340 wide at its 1.7 aspect.
            child: SizedBox(
              width: 340,
              height: 200,
              child: StationCard(
                node: ModuleNode(
                  path: 'PressA',
                  name: 'PressA',
                  type: ModuleType.unit,
                  publishedValues: values,
                ),
                tile: _profile,
              ),
            ),
          ),
        ),
      ),
    ));
    await tester.pump();
  }

  testWidgets('slots render in the fixed cell, OK badge neutral',
      (tester) async {
    await pumpTile(tester, {'OutImm/Rate': 42, 'OutImm/AirOk': true});
    expect(tester.takeException(), isNull, reason: 'no overflow in the cell');
    expect(find.text('42 ppm'), findsOneWidget);
    final context = tester.element(find.byType(StationCard));
    final dot = tester.widget<Icon>(find.byIcon(Icons.circle));
    expect(dot.color, stateTokenColor(context, ModuleStateToken.neutral),
        reason: 'a tile is an operating view: OK is not green');
  });

  testWidgets('an abnormal badge takes its colour; missing data is shown',
      (tester) async {
    await pumpTile(tester, {'OutImm/AirOk': false});
    final context = tester.element(find.byType(StationCard));
    expect(tester.widget<Icon>(find.byIcon(Icons.circle)).color,
        stateTokenColor(context, ModuleStateToken.error));
    expect(find.text('—'), findsOneWidget,
        reason:
            'the Rate tag is missing: the slot says so, it keeps its column');
  });
}
