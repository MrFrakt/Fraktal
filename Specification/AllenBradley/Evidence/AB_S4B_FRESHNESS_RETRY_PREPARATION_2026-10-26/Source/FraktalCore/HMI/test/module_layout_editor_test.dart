import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:fraktal_hmi/content/module_layout.dart';
import 'package:fraktal_hmi/domain/module_node.dart';
import 'package:fraktal_hmi/domain/types.dart';
import 'package:fraktal_hmi/localization/localization_controller.dart';
import 'package:fraktal_hmi/localization/localized_text.dart';
import 'package:fraktal_hmi/ui/module_layout_editor.dart';

void main() {
  testWidgets('chart editor searches and links multiple current-module tags',
      (tester) async {
    await tester.binding.setSurfaceSize(const Size(1280, 1000));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    const node = ModuleNode(
      path: 'Press.Clamp',
      name: 'Clamp',
      type: ModuleType.controlModule,
      publishedValues: {
        'OutImm/Temperature': 31.5,
        'OutImm/Pressure': 5.8,
        'OutImm/Ready': true,
        'OutImm/Result': 'OK',
      },
    );
    ModuleControlDefinition? result;
    final localization = LocalizationController(
      enabledLanguages: {'en'},
      activeLanguage: 'en',
    );

    await tester.pumpWidget(
      LocalizationScope(
        controller: localization,
        child: MaterialApp(
          home: Builder(
            builder: (context) => Center(
              child: FilledButton(
                onPressed: () async {
                  result = await showModuleControlEditor(
                    context,
                    node: node,
                    existing: const ModuleControlDefinition(
                      id: 'trend',
                      kind: ModuleControlKind.chart,
                    ),
                  );
                },
                child: const Text('Open editor'),
              ),
            ),
          ),
        ),
      ),
    );

    await tester.tap(find.text('Open editor'));
    await tester.pumpAndSettle();

    final search = find.byKey(const ValueKey('opcua-binding-search'));
    await tester.enterText(search, 'temperature');
    await tester.pumpAndSettle();
    expect(find.text('OutImm/Temperature'), findsOneWidget);
    await tester.tap(find.text('OutImm/Temperature'));
    await tester.pumpAndSettle();

    await tester.enterText(search, 'pressure');
    await tester.pumpAndSettle();
    expect(find.text('OutImm/Pressure'), findsOneWidget);
    await tester.tap(find.text('OutImm/Pressure'));
    await tester.pumpAndSettle();

    await tester.enterText(search, 'ready');
    await tester.pumpAndSettle();
    expect(find.text('OutImm/Ready'), findsNothing);

    await tester.tap(find.text('Save'));
    await tester.pumpAndSettle();

    expect(result?.linkedBindings, ['OutImm/Temperature', 'OutImm/Pressure']);
  });

  testWidgets('saving a door keeps its state rules, shape and place',
      (tester) async {
    // A save that dropped the fault rule would draw a faulted door green.
    await tester.binding.setSurfaceSize(const Size(1280, 1000));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    const node = ModuleNode(
      path: 'Press.Guard',
      name: 'Guard',
      type: ModuleType.equipmentModule,
      publishedValues: {
        'OutImm/DoorClosed': true,
        'OutImm/DoorFaulted': false,
      },
    );
    const door = ModuleControlDefinition(
      id: 'door1',
      kind: ModuleControlKind.shape,
      label: 'Door 1',
      bindings: ['OutImm/DoorClosed', 'OutImm/DoorFaulted'],
      shape: ModuleShape.rounded,
      rules: [
        ModuleStateRule(
            bindingIndex: 1,
            compare: ModuleCompare.isTrue,
            token: ModuleStateToken.error),
        ModuleStateRule(
            bindingIndex: 0,
            compare: ModuleCompare.isTrue,
            token: ModuleStateToken.ok),
      ],
      defaultToken: ModuleStateToken.warning,
      placement: ModulePlacement(x: 0.1, y: 0.2, width: 0.2, height: 0.4),
    );
    ModuleControlDefinition? result;
    final localization =
        LocalizationController(enabledLanguages: {'en'}, activeLanguage: 'en');
    await tester.pumpWidget(LocalizationScope(
      controller: localization,
      child: MaterialApp(
        home: Builder(
          builder: (context) => Center(
            child: FilledButton(
              onPressed: () async {
                result = await showModuleControlEditor(context,
                    node: node, existing: door);
              },
              child: const Text('Open editor'),
            ),
          ),
        ),
      ),
    ));
    await tester.tap(find.text('Open editor'));
    await tester.pumpAndSettle();
    expect(find.text('State rules'), findsOneWidget);

    await tester.tap(find.text('Save'));
    await tester.pumpAndSettle();

    expect(result, isNotNull);
    expect(result!.shape, ModuleShape.rounded);
    expect(result!.defaultToken, ModuleStateToken.warning);
    expect(result!.placement, door.placement);
    expect(result!.rules.map((rule) => (rule.bindingIndex, rule.token)), [
      (1, ModuleStateToken.error),
      (0, ModuleStateToken.ok),
    ]);
    expect(result!.resolveState([true, true]), ModuleStateToken.error);
  });

  // §7.4 keeps pictures off operating views, but the picker must stay visible: a
  // new tab starts Operating, and hiding the control there read as "background
  // pictures are gone" to an ADMIN.
  testWidgets('the picture picker shows on an operating tab and says what saving does',
      (tester) async {
    await tester.binding.setSurfaceSize(const Size(1280, 1400));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    final localization =
        LocalizationController(enabledLanguages: {'en'}, activeLanguage: 'en');
    ModuleTabDefinition? existing;
    await tester.pumpWidget(LocalizationScope(
      controller: localization,
      child: MaterialApp(
        home: Builder(
          builder: (context) => Center(
            child: FilledButton(
              onPressed: () => showModuleTabEditor(context,
                  existing: existing, allowGuidance: true),
              child: const Text('Open editor'),
            ),
          ),
        ),
      ),
    ));

    await tester.tap(find.text('Open editor'));
    await tester.pumpAndSettle();
    expect(find.text('OPERATING'), findsOneWidget,
        reason: 'a new custom tab starts as an operating view');
    expect(find.text('Choose image'), findsOneWidget,
        reason: 'the picture can still be chosen from here');
    await tester.tap(find.text('Cancel'));
    await tester.pumpAndSettle();

    // A stored operating tab that carries a picture says saving would remove it.
    existing = const ModuleTabDefinition(
      id: 'custom-1',
      title: 'Machine',
      kind: ModuleTabKind.custom,
      declaredClass: ModuleViewClass.operating,
      background: ModuleTabBackground(imageBase64: 'AAAA', imageName: 'cell.png'),
    );
    await tester.tap(find.text('Open editor'));
    await tester.pumpAndSettle();
    expect(
        find.text(
            'Saving as Operating removes the picture: an operating view carries none.'),
        findsOneWidget);
  });

  testWidgets('editing a tab keeps its default flag, layers and budget',
      (tester) async {
    await tester.binding.setSurfaceSize(const Size(1280, 1600));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    final localization =
        LocalizationController(enabledLanguages: {'en'}, activeLanguage: 'en');
    const existing = ModuleTabDefinition(
      id: 'custom-1',
      title: 'Machine',
      kind: ModuleTabKind.custom,
      isDefault: true,
      readBudget: 40,
      layerConditions: {'L': ModuleCondition(binding: 'OutImm/Show')},
      controls: [
        ModuleControlDefinition(
            id: 'c', kind: ModuleControlKind.text, label: 'x', layer: 'L'),
      ],
    );
    ModuleTabDefinition? saved;
    await tester.pumpWidget(LocalizationScope(
      controller: localization,
      child: MaterialApp(
        home: Builder(
          builder: (context) => Center(
            child: FilledButton(
              onPressed: () async => saved = await showModuleTabEditor(context,
                  existing: existing, allowGuidance: true),
              child: const Text('Open editor'),
            ),
          ),
        ),
      ),
    ));
    await tester.tap(find.text('Open editor'));
    await tester.pumpAndSettle();
    await tester.ensureVisible(find.text('Save'));
    await tester.tap(find.text('Save'));
    await tester.pumpAndSettle();
    expect(saved!.isDefault, isTrue,
        reason: 'the default tab stays the default after an edit');
    expect(saved!.readBudget, 40);
    expect(saved!.layerConditions['L']!.binding, 'OutImm/Show',
        reason: 'without a module to pick tags from, the conditions are kept');
  });
}
