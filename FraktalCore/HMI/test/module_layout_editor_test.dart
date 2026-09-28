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
}
