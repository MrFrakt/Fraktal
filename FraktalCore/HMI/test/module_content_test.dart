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
      ['overview', 'description', 'motion', 'operator-guidance'],
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
    expect(tabs.first.background?.imageName, 'module-3d.png');
    expect(tabs.first.background?.fit, ModuleBackgroundFit.fitWidth);
    expect(
        tabs.first.background?.position, ModuleBackgroundPosition.bottomRight);
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
      return [
        for (final tab in controller.tabsFor('StationA', capabilities))
          tab.id == 'overview'
              ? tab.copyWith(
                  requiredLevel: level,
                  background: ModuleTabBackground(
                      imageBase64: image, imageName: 'cell.png'))
              : tab,
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
      final current =
          restored.tabsFor('StationA', capabilities).first.background!;
      expect(current.imageBase64, image);
      final withImage = [
        for (final revision in restored.revisionsFor('StationA'))
          if (revision.tabs.first.background?.imageBase64.isNotEmpty ?? false)
            revision.tabs.first.background!.imageBase64,
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
      expect(restored.tabsFor('StationA', capabilities).first.background
          ?.imageBase64, image);
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
