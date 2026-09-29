import 'dart:convert';
import 'dart:typed_data';
import 'package:flutter_test/flutter_test.dart';
import 'package:fraktal_hmi/content/content_store.dart';
import 'package:fraktal_hmi/content/module_content_controller.dart';
import 'package:fraktal_hmi/domain/types.dart';
import 'package:fraktal_hmi/localization/catalog_csv.dart';
import 'package:fraktal_hmi/localization/catalog_store.dart';
import 'package:fraktal_hmi/localization/localization_controller.dart';

void main() {
  test('section defaults and admin changes persist per module', () async {
    final store = MemoryContentStore();
    final localization =
        LocalizationController(enabledLanguages: {'en'}, activeLanguage: 'en');
    final first =
        ModuleContentController(store: store, localization: localization);

    expect(first.requiredLevel('StationA', ModuleSection.information),
        AccessLevel.none);
    expect(first.requiredLevel('StationA', ModuleSection.configuration),
        AccessLevel.engineer);
    await first.setRequiredLevel(
        'StationA', ModuleSection.documentation, AccessLevel.technician);

    final restored =
        ModuleContentController(store: store, localization: localization);
    await restored.load();
    expect(restored.requiredLevel('StationA', ModuleSection.documentation),
        AccessLevel.technician);
    expect(
        restored.permits(
            'StationA', ModuleSection.documentation, AccessLevel.operator),
        isFalse);
  });

  test('valid PDF and localizable title survive reload', () async {
    final store = MemoryContentStore();
    final localization =
        LocalizationController(enabledLanguages: {'en'}, activeLanguage: 'en');
    final first =
        ModuleContentController(store: store, localization: localization);
    final document = await first.addPdf(
      modulePath: 'StationA.Clamp',
      fileName: 'manual.pdf',
      bytes: Uint8List.fromList('%PDF-1.7\n%%EOF'.codeUnits),
      title: 'Clamp manual',
      uploadedBy: 'engineer',
    );
    expect(localization.resolve(document.titleKey), 'Clamp manual');

    final restoredLocalization =
        LocalizationController(enabledLanguages: {'en'}, activeLanguage: 'en');
    final restored = ModuleContentController(
        store: store, localization: restoredLocalization);
    await restored.load();
    final loaded = restored.documentsFor('StationA.Clamp').single;
    expect(loaded.bytes, document.bytes);
    expect(restoredLocalization.resolve(loaded.titleKey), 'Clamp manual');
  });

  test('non-PDF payload is rejected without committing', () async {
    final controller = ModuleContentController(
      store: MemoryContentStore(),
      localization: LocalizationController(
          enabledLanguages: {'en'}, activeLanguage: 'en'),
    );
    expect(
      () => controller.addPdf(
        modulePath: 'StationA',
        fileName: 'not.pdf',
        bytes: Uint8List.fromList('hello'.codeUnits),
        title: 'Invalid',
        uploadedBy: 'engineer',
      ),
      throwsFormatException,
    );
    expect(controller.documentsFor('StationA'), isEmpty);
  });

  test('configuration is its own built-in tab, only for a module that has any',
      () {
    final tabs = ModuleTabDefinition.defaults(
        const ModuleTabCapabilities(unit: true, configuration: true));
    expect(tabs.map((tab) => tab.id).take(6), [
      'overview',
      'hardware',
      'statistics',
      'events',
      'description',
      'configuration',
    ]);
    final config = tabs.firstWhere((tab) => tab.id == 'configuration');
    expect(config.kind, ModuleTabKind.configuration);
    expect(config.builtIn, isTrue, reason: 'a built-in tab cannot be deleted');
    expect(
        ModuleTabDefinition.defaults(const ModuleTabCapabilities(unit: true))
            .any((tab) => tab.kind == ModuleTabKind.configuration),
        isFalse);
  });

  test('module tabs include capability defaults and persist admin layout',
      () async {
    final store = MemoryContentStore();
    final localization =
        LocalizationController(enabledLanguages: {'en'}, activeLanguage: 'en');
    final first =
        ModuleContentController(store: store, localization: localization);
    const capabilities = ModuleTabCapabilities(unit: true, motion: true);

    expect(
      first.tabsFor('StationA', capabilities).map((tab) => tab.id),
      [
        'overview',
        'hardware',
        'statistics',
        'events',
        'description',
        'motion',
        'operator-guidance',
      ],
    );
    const custom = ModuleTabDefinition(
      id: 'quality',
      title: 'Quality',
      kind: ModuleTabKind.custom,
      tabIcon: ModuleTabIcon.chart,
      requiredLevel: AccessLevel.technician,
      controls: [
        ModuleControlDefinition(
          id: 'temperature',
          kind: ModuleControlKind.chart,
          label: 'Temperature',
          binding: 'OutImm/Temperature',
          bindings: [
            'OutImm/Temperature',
            'OutImm/TargetTemperature',
          ],
          unit: '°C',
          samplePeriodMs: 500,
          historyPoints: 200,
        ),
      ],
    );
    await first.upsertTab('StationA', custom, capabilities);
    final overview = first.tabsFor('StationA', capabilities).first;
    await first.upsertTab(
      'StationA',
      overview.copyWith(
        requiredLevel: AccessLevel.operator,
        background: ModuleTabBackground(
          imageBase64: base64Encode(const [1, 2, 3]),
          imageName: 'module-3d.png',
          fit: ModuleBackgroundFit.fitWidth,
          position: ModuleBackgroundPosition.bottomRight,
          marginLeft: 24,
          marginBottom: 12,
        ),
      ),
      capabilities,
    );

    final restored =
        ModuleContentController(store: store, localization: localization);
    await restored.load();
    final tabs = restored.tabsFor('StationA', capabilities);
    expect(tabs.first.requiredLevel, AccessLevel.operator);
    expect(tabs.last.id, 'quality');
    expect(tabs.last.controls.single.samplePeriodMs, 500);
    expect(tabs.last.controls.single.linkedBindings, [
      'OutImm/Temperature',
      'OutImm/TargetTemperature',
    ]);
    expect(tabs.last.effectiveIcon, ModuleTabIcon.chart);
    // The Overview is a card view: a picture stored on it is dropped on load.
    expect(tabs.first.background, isNull);
  });

  test('only a custom tab carries a background image', () async {
    expect(
      [
        for (final kind in ModuleTabKind.values)
          if (kind.acceptsBackground) kind,
      ],
      [ModuleTabKind.custom],
    );
    final store = MemoryContentStore();
    final localization =
        LocalizationController(enabledLanguages: {'en'}, activeLanguage: 'en');
    final first =
        ModuleContentController(store: store, localization: localization);
    const capabilities = ModuleTabCapabilities(unit: true);
    await first.publishTabs(
      'StationA',
      [
        ...first.tabsFor('StationA', capabilities),
        ModuleTabDefinition(
          id: 'cell',
          title: 'Cell',
          kind: ModuleTabKind.custom,
          background: ModuleTabBackground(
            imageBase64: base64Encode(const [4, 5, 6]),
            imageName: 'cell.png',
            fit: ModuleBackgroundFit.cover,
          ),
        ),
      ],
      capabilities,
      author: 'admin1',
    );

    final restored =
        ModuleContentController(store: store, localization: localization);
    await restored.load();
    final cell = restored
        .tabsFor('StationA', capabilities)
        .firstWhere((tab) => tab.id == 'cell');
    expect(cell.background?.imageName, 'cell.png');
    expect(cell.background?.fit, ModuleBackgroundFit.cover);
  });

  test('a type layout reaches every instance; an override replaces it whole',
      () async {
    ModuleContentController controller() => ModuleContentController(
          store: MemoryContentStore(),
          localization: LocalizationController(
              enabledLanguages: {'en'}, activeLanguage: 'en'),
        );
    final content = controller();
    const caps = ModuleTabCapabilities();
    const cylinder = 'std.moduleType.cylinder';
    final typeScope = ModuleContentController.typeScope(cylinder);
    const faceplate = ModuleTabDefinition(
        id: 'faceplate', title: 'Faceplate', kind: ModuleTabKind.custom);
    await content.publishTabs(
        typeScope, [...content.tabsFor(typeScope, caps), faceplate], caps,
        author: 'admin1');

    List<String> ids(String path, {String typeKey = cylinder}) => content
        .tabsFor(path, caps, typeKey: typeKey)
        .map((tab) => tab.id)
        .toList();
    // Twenty identical clamps need one layout: both instances get it.
    expect(ids('Press.CylA'), contains('faceplate'));
    expect(ids('Press.CylB'), contains('faceplate'));
    // A module of another type, or of none, does not.
    expect(ids('Press.Door', typeKey: 'std.moduleType.door'),
        isNot(contains('faceplate')));
    expect(ids('Press.Door', typeKey: ''), isNot(contains('faceplate')));

    // An override replaces the type layout WHOLE - no half-inherited merge.
    const own = ModuleTabDefinition(
        id: 'own', title: 'Own', kind: ModuleTabKind.custom);
    await content.publishTabs(
        'Press.CylB', [...ModuleTabDefinition.defaults(caps), own], caps,
        author: 'admin1', typeKey: cylinder);
    // The history says what the module showed before: its type's layout.
    expect(content.revisionsFor('Press.CylB').first.tabs.map((t) => t.id),
        contains('faceplate'));
    expect(ids('Press.CylB'), contains('own'));
    expect(ids('Press.CylB'), isNot(contains('faceplate')));
    expect(ids('Press.CylA'), contains('faceplate'));

    // Dropping the override falls back to the type, and is undoable.
    await content.clearLayout('Press.CylB', caps, author: 'admin1');
    expect(content.hasLayout('Press.CylB'), isFalse);
    expect(ids('Press.CylB'), contains('faceplate'));
    expect(content.revisionsFor('Press.CylB').first.tabs.map((t) => t.id),
        contains('own'));

    // A type scope travels in an export and is never remapped as a path.
    final imported = controller();
    final report = await imported.importBundle(content.exportBundle(),
        availableModulePaths: const ['Other.CylX']);
    expect(report.deferredPaths, isNot(contains(typeScope)));
    expect(
        imported
            .tabsFor('Other.CylX', caps, typeKey: cylinder)
            .map((tab) => tab.id),
        contains('faceplate'));
  });

  test('a view declares its class; operating refuses a picture (§7.4)',
      () async {
    final content = ModuleContentController(
      store: MemoryContentStore(),
      localization:
          LocalizationController(enabledLanguages: {'en'}, activeLanguage: 'en'),
    );
    const caps = ModuleTabCapabilities();
    final picture = ModuleTabBackground(imageBase64: base64Encode(const [1]));
    // Saved before §7.4: derived, so nothing stored becomes invalid.
    expect(
        ModuleTabDefinition(
                id: 'a', title: 'A', kind: ModuleTabKind.custom,
                background: picture)
            .viewClass,
        ModuleViewClass.maintenance);
    expect(
        const ModuleTabDefinition(id: 'b', title: 'B', kind: ModuleTabKind.custom)
            .viewClass,
        ModuleViewClass.operating);

    final operatingWithPicture = ModuleTabDefinition(
      id: 'cell',
      title: 'Cell',
      kind: ModuleTabKind.custom,
      background: picture,
      declaredClass: ModuleViewClass.operating,
    );
    await expectLater(
      content.publishTabs('S',
          [...content.tabsFor('S', caps), operatingWithPicture], caps,
          author: 'admin1'),
      throwsA(isA<FormatException>().having((e) => e.message, 'message',
          'std.module.editor.operatingNoImagery')),
    );

    final maintenance =
        operatingWithPicture.copyWith(declaredClass: ModuleViewClass.maintenance);
    await content.publishTabs(
        'S', [...content.tabsFor('S', caps), maintenance], caps,
        author: 'admin1');
    final restored = ModuleTabDefinition.fromJson(maintenance.toJson())!;
    expect(restored.viewClass, ModuleViewClass.maintenance,
        reason: 'the class is recorded in the export');
  });

  test('a view over its read budget is refused at publish (§7.3)',
      () async {
    final content = ModuleContentController(
      store: MemoryContentStore(),
      localization:
          LocalizationController(enabledLanguages: {'en'}, activeLanguage: 'en'),
    );
    const caps = ModuleTabCapabilities();
    ModuleTabDefinition withReads(int count) => ModuleTabDefinition(
          id: 'big',
          title: 'Big',
          kind: ModuleTabKind.custom,
          controls: [
            for (var c = 0; c * 8 < count; c++)
              ModuleControlDefinition(
                id: 'chart$c',
                kind: ModuleControlKind.chart,
                bindings: [
                  for (var b = 0; b < 8 && c * 8 + b < count; b++)
                    'OutImm/Tag${c * 8 + b}',
                ],
              ),
          ],
        );
    expect(withReads(200).boundReads, 200);
    await content.publishTabs('S', [...content.tabsFor('S', caps),
        withReads(ModuleTabDefinition.maxBoundReads)], caps,
        author: 'admin1');
    await expectLater(
      content.publishTabs('S', [...content.tabsFor('S', caps).where(
          (tab) => tab.id != 'big'), withReads(201)], caps, author: 'admin1'),
      throwsA(isA<FormatException>().having(
          (e) => e.message, 'message', 'std.module.editor.overBudget')),
    );
  });

  test('customization bundle carries localized text and excludes connection',
      () async {
    final sourceCatalog = MemoryCatalogStore();
    final sourceLocalization = LocalizationController(
      store: sourceCatalog,
      enabledLanguages: {'es'},
      activeLanguage: 'es',
    );
    await sourceLocalization.importCsv(
      CatalogScope.project,
      'es',
      CatalogCsv.encode(
        scope: CatalogScope.project,
        locale: 'es',
        values: const {'project.custom.guidance': 'Cambiar la herramienta'},
      ),
    );
    final source = ModuleContentController(
      store: MemoryContentStore(),
      localization: sourceLocalization,
    );
    await source.setRequiredLevel(
        'StationA', ModuleSection.documentation, AccessLevel.engineer);
    await source.upsertTab(
      'StationA',
      const ModuleTabDefinition(
        id: 'instructions',
        title: 'project.custom.guidance',
        kind: ModuleTabKind.guidance,
        triggerStepNo: 80,
      ),
      const ModuleTabCapabilities(unit: true),
    );

    final encoded = source.exportBundle();
    final decoded = jsonDecode(encoded) as Map<String, dynamic>;
    expect(decoded['schemaVersion'], 4);
    expect(decoded['bundleType'], 'fraktal-hmi-customization');
    expect(decoded, contains('localization'));
    expect(decoded, isNot(contains('connection')));
    expect(encoded, isNot(contains('opc.tcp://')));

    final targetLocalization = LocalizationController(
      store: MemoryCatalogStore(),
      enabledLanguages: {'es'},
      activeLanguage: 'es',
    );
    final target = ModuleContentController(
      store: MemoryContentStore(),
      localization: targetLocalization,
    );
    await target.importBundle(encoded);
    expect(targetLocalization.resolve('project.custom.guidance'),
        'Cambiar la herramienta');
    expect(
      target.requiredLevel('StationA', ModuleSection.documentation),
      AccessLevel.engineer,
    );
    expect(
      target
          .tabsFor('StationA', const ModuleTabCapabilities(unit: true))
          .where((tab) => tab.id == 'instructions')
          .single
          .triggers(80, 'Anything'),
      isTrue,
    );
  });

  test('guidance wildcard matches a live step and chart bounds are enforced',
      () {
    const guidance = ModuleTabDefinition(
      id: 'guide',
      title: 'Guide',
      kind: ModuleTabKind.guidance,
      triggerStepName: '*',
    );
    expect(guidance.triggers(10, 'Open door'), isTrue);
    expect(guidance.triggers(0, 'Idle'), isFalse);

    final parsed = ModuleControlDefinition.fromJson({
      'id': 'trend',
      'kind': 'chart',
      'bindings': ['OutImm/Temperature', 'OutImm/Pressure'],
      'width': 'twoThirds',
      'samplePeriodMs': 1,
      'historyPoints': 99999,
    });
    expect(parsed?.samplePeriodMs, ModuleControlDefinition.minSamplePeriodMs);
    expect(parsed?.historyPoints, ModuleControlDefinition.maxHistoryPoints);
    expect(parsed?.linkedBindings, ['OutImm/Temperature', 'OutImm/Pressure']);
    expect(parsed?.width, ModuleControlWidth.twoThirds);
    expect(parsed?.confirmation, ModuleActionConfirmation.confirm,
        reason: 'Imported state-changing controls default fail-safe.');

    final legacy = ModuleControlDefinition.fromJson({
      'id': 'legacy-value',
      'kind': 'value',
      'binding': 'OutImm/Legacy',
    });
    expect(legacy?.linkedBindings, ['OutImm/Legacy']);
    expect(legacy?.toJson()['bindings'], ['OutImm/Legacy']);

    expect(
      ModuleControlDefinition.fromJson({
        'id': 'too-many-values',
        'kind': 'value',
        'bindings': ['OutImm/A', 'OutImm/B'],
      }),
      isNull,
    );
    expect(
      ModuleControlDefinition.fromJson({
        'id': 'too-many-trends',
        'kind': 'chart',
        'bindings': [
          for (var index = 0;
              index <= ModuleControlDefinition.maxChartBindings;
              index++)
            'OutImm/Value$index',
        ],
      }),
      isNull,
    );
  });

  group('embedded images are stored once, not once per revision', () {
    const capabilities = ModuleTabCapabilities(unit: true);
    final image = base64Encode(List<int>.generate(4096, (i) => i % 251));

    List<ModuleTabDefinition> withBackground(
        ModuleContentController controller, AccessLevel level) {
      // The picture rides on an authored tab: only those carry one.
      return [
        for (final tab in controller.tabsFor('StationA', capabilities))
          if (tab.id != 'cell') tab,
        ModuleTabDefinition(
          id: 'cell',
          title: 'Cell',
          kind: ModuleTabKind.custom,
          requiredLevel: level,
          background:
              ModuleTabBackground(imageBase64: image, imageName: 'cell.png'),
        ),
      ];
    }

    test('many publishes of one image write it once and load it shared',
        () async {
      final store = MemoryContentStore();
      final localization = LocalizationController(
          enabledLanguages: {'en'}, activeLanguage: 'en');
      final controller =
          ModuleContentController(store: store, localization: localization);
      for (final level in [
        AccessLevel.operator,
        AccessLevel.technician,
        AccessLevel.engineer,
        AccessLevel.operator,
      ]) {
        await controller.publishTabs(
            'StationA', withBackground(controller, level), capabilities,
            author: 'admin');
      }
      final images = store.value['images'] as Map;
      expect(images, hasLength(1),
          reason: 'one image, however many revisions carry it');
      expect(images.values.single, image);
      expect(jsonEncode(store.value).contains(image), isTrue);
      expect(
          jsonEncode(store.value).indexOf(image),
          jsonEncode(store.value).lastIndexOf(image),
          reason: 'the base64 text appears exactly once on disk');

      final restored =
          ModuleContentController(store: store, localization: localization);
      await restored.load();
      final current = restored
          .tabsFor('StationA', capabilities)
          .firstWhere((tab) => tab.id == 'cell')
          .background!;
      expect(current.imageBase64, image);
      final withImage = [
        for (final revision in restored.revisionsFor('StationA'))
          for (final tab in revision.tabs)
            if (tab.background?.imageBase64.isNotEmpty ?? false)
              tab.background!.imageBase64,
      ];
      expect(withImage, isNotEmpty);
      for (final copy in withImage) {
        expect(identical(copy, current.imageBase64), isTrue,
            reason: 'every reference shares one string instance');
      }
    });

    test('a store written before packing still loads, and is packed on save',
        () async {
      final localization = LocalizationController(
          enabledLanguages: {'en'}, activeLanguage: 'en');
      final writer = ModuleContentController(
          store: MemoryContentStore(), localization: localization);
      await writer.setTabs(
          'StationA', withBackground(writer, AccessLevel.operator));
      // Rebuild the pre-packing (inline) form from the packed one.
      final packed = (writer.store as MemoryContentStore).value;
      final images = packed['images'] as Map;
      Object? inline(Object? node) => node is Map
          ? {
              for (final e in node.entries)
                if (e.key != 'images')
                  (e.key == 'imageRef' ? 'imageBase64' : e.key):
                      e.key == 'imageRef' ? images[e.value] : inline(e.value),
            }
          : node is List
              ? [for (final item in node) inline(item)]
              : node;
      final legacy = MemoryContentStore(
          Map<String, Object?>.from(inline(packed) as Map));
      expect(legacy.value.containsKey('images'), isFalse);

      final restored =
          ModuleContentController(store: legacy, localization: localization);
      await restored.load();
      expect(
          restored
              .tabsFor('StationA', capabilities)
              .firstWhere((tab) => tab.id == 'cell')
              .background
              ?.imageBase64,
          image);
      await restored.setTabs(
          'StationA', withBackground(restored, AccessLevel.technician));
      expect((legacy.value['images'] as Map).values.single, image);
    });

    test('the portable export keeps schema 4 with images inline', () async {
      final localization = LocalizationController(
          enabledLanguages: {'en'}, activeLanguage: 'en');
      final controller = ModuleContentController(
          store: MemoryContentStore(), localization: localization);
      await controller.setTabs(
          'StationA', withBackground(controller, AccessLevel.operator));
      final bundle = jsonDecode(controller.exportBundle()) as Map;
      expect(bundle['schemaVersion'], 4);
      expect(bundle.containsKey('images'), isFalse);
      expect(controller.exportBundle().contains(image), isTrue);
    });
  });

  test('published module layouts retain bounded rollback history', () async {
    final store = MemoryContentStore();
    final localization =
        LocalizationController(enabledLanguages: {'en'}, activeLanguage: 'en');
    final controller =
        ModuleContentController(store: store, localization: localization);
    const capabilities = ModuleTabCapabilities(unit: true);
    final initial = controller.tabsFor('StationA', capabilities);
    final changed = [
      for (final tab in initial)
        tab.id == 'overview'
            ? tab.copyWith(requiredLevel: AccessLevel.technician)
            : tab,
    ];

    await controller.publishTabs(
      'StationA',
      changed,
      capabilities,
      author: 'admin',
      comment: 'Restrict overview',
    );
    final revision = controller.revisionsFor('StationA').single;
    expect(revision.tabs.first.requiredLevel, AccessLevel.none);
    expect(revision.author, 'admin');

    await controller.restoreRevision(
      'StationA',
      revision.id,
      capabilities,
      author: 'admin',
    );
    expect(controller.tabsFor('StationA', capabilities).first.requiredLevel,
        AccessLevel.none);
    expect(controller.revisionsFor('StationA'), hasLength(2));

    final restored =
        ModuleContentController(store: store, localization: localization);
    await restored.load();
    expect(restored.revisionsFor('StationA'), hasLength(2));
  });

  test('import remaps unique structural changes and preserves ambiguous paths',
      () async {
    final source = ModuleContentController(
      store: MemoryContentStore(),
      localization: LocalizationController(
          enabledLanguages: {'en'}, activeLanguage: 'en'),
    );
    await source.upsertTab(
      'OldStation.Tooling.Clamp',
      const ModuleTabDefinition(
        id: 'service',
        title: 'Service',
        kind: ModuleTabKind.custom,
      ),
      const ModuleTabCapabilities(),
    );
    await source.upsertTab(
      'OldStation.Ambiguous',
      const ModuleTabDefinition(
        id: 'ambiguous',
        title: 'Ambiguous',
        kind: ModuleTabKind.custom,
      ),
      const ModuleTabCapabilities(),
    );

    final target = ModuleContentController(
      store: MemoryContentStore(),
      localization: LocalizationController(
          enabledLanguages: {'en'}, activeLanguage: 'en'),
    );
    await target.upsertTab(
      'NewStation.Tooling.Clamp',
      const ModuleTabDefinition(
        id: 'target-only',
        title: 'Target only',
        kind: ModuleTabKind.custom,
      ),
      const ModuleTabCapabilities(),
    );
    final report = await target.importBundle(
      source.exportBundle(),
      availableModulePaths: const [
        'NewStation',
        'NewStation.Tooling',
        'NewStation.Tooling.Clamp',
        'NewStation.Left.Ambiguous',
        'NewStation.Right.Ambiguous',
      ],
    );

    expect(report.remappedPaths['OldStation.Tooling.Clamp'],
        'NewStation.Tooling.Clamp');
    expect(report.deferredPaths, contains('OldStation.Ambiguous'));
    expect(
      target
          .tabsFor('NewStation.Tooling.Clamp', const ModuleTabCapabilities())
          .map((tab) => tab.id),
      containsAll(['service', 'target-only']),
    );
    expect(
      target
          .tabsFor('OldStation.Ambiguous', const ModuleTabCapabilities())
          .map((tab) => tab.id),
      contains('ambiguous'),
    );
  });
}
