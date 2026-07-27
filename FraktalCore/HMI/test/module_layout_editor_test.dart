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
}
