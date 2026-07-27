library;

import 'dart:convert';
import 'package:flutter/foundation.dart';
import '../domain/types.dart';
import '../localization/localization_controller.dart';
import 'content_store.dart';
import 'module_layout.dart';

export 'module_layout.dart';

enum ModuleSection {
  information,
  operations,
  diagnostics,
  configuration,
  documentation,
  history,
}

class ModuleDocument {
  final String id;
  final String modulePath;
  final String fileName;
  final String titleKey;
  final String titleDefault;
  final Uint8List bytes;
  final DateTime uploadedAt;
  final String uploadedBy;

  const ModuleDocument({
    required this.id,
    required this.modulePath,
    required this.fileName,
    required this.titleKey,
    required this.titleDefault,
    required this.bytes,
    required this.uploadedAt,
    required this.uploadedBy,
  });

  ModuleDocument copyWith({String? modulePath}) => ModuleDocument(
        id: id,
        modulePath: modulePath ?? this.modulePath,
        fileName: fileName,
        titleKey: titleKey,
        titleDefault: titleDefault,
        bytes: bytes,
        uploadedAt: uploadedAt,
        uploadedBy: uploadedBy,
      );

  Map<String, Object?> toJson() => {
        'id': id,
        'modulePath': modulePath,
        'fileName': fileName,
        'titleKey': titleKey,
        'titleDefault': titleDefault,
        'bytes': base64Encode(bytes),
        'uploadedAt': uploadedAt.toIso8601String(),
        'uploadedBy': uploadedBy,
      };

  static ModuleDocument? fromJson(Object? source) {
    if (source is! Map) return null;
    try {
      return ModuleDocument(
        id: source['id'] as String,
        modulePath: source['modulePath'] as String,
        fileName: source['fileName'] as String,
        titleKey: source['titleKey'] as String,
        titleDefault:
            source['titleDefault'] as String? ?? source['fileName'] as String,
        bytes: base64Decode(source['bytes'] as String),
        uploadedAt: DateTime.parse(source['uploadedAt'] as String),
        uploadedBy: source['uploadedBy'] as String,
      );
    } on Object {
      return null;
    }
  }
}

class CustomizationImportReport {
  final List<String> exactPaths;
  final Map<String, String> remappedPaths;
  final List<String> deferredPaths;

  const CustomizationImportReport({
    this.exactPaths = const [],
    this.remappedPaths = const {},
    this.deferredPaths = const [],
  });
}

class ModuleLayoutRevision {
  final String id;
  final DateTime createdAt;
  final String author;
  final String comment;
  final List<ModuleTabDefinition> tabs;

  const ModuleLayoutRevision({
    required this.id,
    required this.createdAt,
    required this.author,
    required this.comment,
    required this.tabs,
  });

  Map<String, Object?> toJson() => {
        'id': id,
        'createdAt': createdAt.toUtc().toIso8601String(),
        'author': author,
        'comment': comment,
        'tabs': [for (final tab in tabs) tab.toJson()],
      };

  static ModuleLayoutRevision? fromJson(Object? source) {
    if (source is! Map || source['tabs'] is! List) return null;
    try {
      final tabs = <ModuleTabDefinition>[];
      for (final item in source['tabs'] as List) {
        final tab = ModuleTabDefinition.fromJson(item);
        if (tab == null) return null;
        tabs.add(tab);
      }
      if (tabs.isEmpty || tabs.length > 32) return null;
      return ModuleLayoutRevision(
        id: source['id'] as String,
        createdAt: DateTime.parse(source['createdAt'] as String).toUtc(),
        author: source['author'] as String? ?? '',
        comment: source['comment'] as String? ?? '',
        tabs: List.unmodifiable(tabs),
      );
    } on Object {
      return null;
    }
  }
}

class ModuleContentController extends ChangeNotifier {
  static const maxPdfBytes = 20 * 1024 * 1024;
  static const maxImportBytes = 64 * 1024 * 1024;
  static const maxLayoutRevisions = 20;
  final ContentStore store;
  final LocalizationController localization;
  final Map<String, List<ModuleDocument>> _documents = {};
  final Map<String, Map<ModuleSection, AccessLevel>> _policies = {};
  final Map<String, List<ModuleTabDefinition>> _layouts = {};
  final Map<String, List<ModuleLayoutRevision>> _revisions = {};

  ModuleContentController({
    ContentStore? store,
    required this.localization,
  }) : store = store ?? MemoryContentStore();

  Future<void> load() async {
    final data = await store.load();
    _documents.clear();
    _policies.clear();
    _layouts.clear();
    _revisions.clear();
    final docs = data['documents'];
    if (docs is List) {
      for (final source in docs) {
        final document = ModuleDocument.fromJson(source);
        if (document == null) continue;
        localization.registerProjectDefault(
            document.titleKey, document.titleDefault);
        _documents.putIfAbsent(document.modulePath, () => []).add(document);
      }
    }
    final policies = data['policies'];
    if (policies is Map) {
      for (final module in policies.entries) {
        if (module.key is! String || module.value is! Map) continue;
        final sectionPolicy = <ModuleSection, AccessLevel>{};
        for (final item in (module.value as Map).entries) {
          final section = ModuleSection.values
              .where((value) => value.name == item.key)
              .firstOrNull;
          final level = AccessLevel.values
              .where((value) => value.name == item.value)
              .firstOrNull;
          if (section != null && level != null) sectionPolicy[section] = level;
        }
        _policies[module.key as String] = sectionPolicy;
      }
    }
    final layouts = data['layouts'];
    if (layouts is Map) {
      for (final module in layouts.entries) {
        if (module.key is! String || module.value is! List) continue;
        final tabs = <ModuleTabDefinition>[];
        for (final source in module.value as List) {
          final tab = ModuleTabDefinition.fromJson(source);
          if (tab != null) tabs.add(tab);
        }
        if (tabs.isNotEmpty) _layouts[module.key as String] = tabs;
      }
    }
    final revisions = data['layoutRevisions'];
    if (revisions is Map) {
      for (final module in revisions.entries) {
        if (module.key is! String || module.value is! List) continue;
        final parsed = <ModuleLayoutRevision>[];
        for (final source in module.value as List) {
          final revision = ModuleLayoutRevision.fromJson(source);
          if (revision != null) parsed.add(revision);
        }
        parsed.sort((a, b) => b.createdAt.compareTo(a.createdAt));
        if (parsed.isNotEmpty) {
          _revisions[module.key as String] =
              parsed.take(maxLayoutRevisions).toList();
        }
      }
    }
  }

  List<ModuleDocument> documentsFor(String modulePath) =>
      List.unmodifiable(_documents[modulePath] ?? const []);

  AccessLevel requiredLevel(String modulePath, ModuleSection section) =>
      _policies[modulePath]?[section] ?? _defaultLevel(section);

  bool permits(String modulePath, ModuleSection section, AccessLevel current) =>
      current.index >= requiredLevel(modulePath, section).index;

  Future<void> setRequiredLevel(
      String modulePath, ModuleSection section, AccessLevel level) async {
    _policies.putIfAbsent(modulePath, () => {})[section] = level;
    await _persist();
    notifyListeners();
  }

  List<ModuleTabDefinition> tabsFor(
    String modulePath,
    ModuleTabCapabilities capabilities,
  ) {
    final defaults = ModuleTabDefinition.defaults(capabilities);
    final configured = _layouts[modulePath];
    if (configured == null) return List.unmodifiable(defaults);

    final byId = {for (final tab in configured) tab.id: tab};
    final merged = <ModuleTabDefinition>[
      for (final tab in defaults) byId.remove(tab.id) ?? tab,
      // Keep imported specialized/custom tabs even if the current snapshot is
      // temporarily missing that capability. Their access policy and content
      // must not disappear during a device reconnect.
      ...byId.values,
    ];
    return List.unmodifiable(merged);
  }

  Future<void> setTabs(
      String modulePath, List<ModuleTabDefinition> tabs) async {
    _validateTabs(tabs);
    _layouts[modulePath] = List.unmodifiable(tabs);
    await _persist();
    notifyListeners();
  }

  List<ModuleLayoutRevision> revisionsFor(String modulePath) =>
      List.unmodifiable(_revisions[modulePath] ?? const []);

  Future<void> publishTabs(
    String modulePath,
    List<ModuleTabDefinition> tabs,
    ModuleTabCapabilities capabilities, {
    required String author,
    String comment = '',
  }) async {
    _validateTabs(tabs);
    _recordRevision(
      modulePath,
      tabsFor(modulePath, capabilities),
      author: author,
      comment: comment.trim().isEmpty
          ? 'Before published layout change'
          : 'Before: ${comment.trim()}',
    );
    _layouts[modulePath] = List.unmodifiable(tabs);
    await _persist();
    notifyListeners();
  }

  Future<void> restoreRevision(
    String modulePath,
    String revisionId,
    ModuleTabCapabilities capabilities, {
    required String author,
  }) async {
    final revision = (_revisions[modulePath] ?? const [])
        .where((item) => item.id == revisionId)
        .firstOrNull;
    if (revision == null) {
      throw const FormatException('Unknown module layout revision');
    }
    _recordRevision(
      modulePath,
      tabsFor(modulePath, capabilities),
      author: author,
      comment: 'Before restoring revision ${revision.id}',
    );
    _layouts[modulePath] = List.unmodifiable(revision.tabs);
    await _persist();
    notifyListeners();
  }

  void _recordRevision(
    String modulePath,
    List<ModuleTabDefinition> tabs, {
    required String author,
    required String comment,
  }) {
    final revisions = _revisions.putIfAbsent(modulePath, () => []);
    revisions.insert(
      0,
      ModuleLayoutRevision(
        id: DateTime.now().microsecondsSinceEpoch.toRadixString(36),
        createdAt: DateTime.now().toUtc(),
        author: author,
        comment: comment,
        tabs: List.unmodifiable(tabs),
      ),
    );
    if (revisions.length > maxLayoutRevisions) {
      revisions.removeRange(maxLayoutRevisions, revisions.length);
    }
  }

  static void _validateTabs(List<ModuleTabDefinition> tabs) {
    if (tabs.isEmpty || tabs.length > 32) {
      throw const FormatException('Invalid module tab count');
    }
    final ids = <String>{};
    for (final tab in tabs) {
      if (!ids.add(tab.id) || tab.controls.length > 64) {
        throw const FormatException('Invalid or duplicate module tab');
      }
      if (tab.controls.any((control) => !control.bindingsAreValid)) {
        throw const FormatException('Invalid module control bindings');
      }
    }
  }

  Future<void> upsertTab(
    String modulePath,
    ModuleTabDefinition tab,
    ModuleTabCapabilities capabilities,
  ) async {
    final tabs = tabsFor(modulePath, capabilities).toList();
    final index = tabs.indexWhere((item) => item.id == tab.id);
    if (index < 0) {
      tabs.add(tab);
    } else {
      tabs[index] = tab;
    }
    await setTabs(modulePath, tabs);
  }

  Future<void> removeTab(
    String modulePath,
    String tabId,
    ModuleTabCapabilities capabilities,
  ) async {
    final tabs = tabsFor(modulePath, capabilities).toList();
    final tab = tabs.where((item) => item.id == tabId).firstOrNull;
    if (tab == null || tab.builtIn) return;
    tabs.removeWhere((item) => item.id == tabId);
    await setTabs(modulePath, tabs);
  }

  String exportBundle() {
    final bundle = _data()
      ..['schemaVersion'] = 4
      ..['bundleType'] = 'fraktal-hmi-customization'
      ..['localization'] = localization.exportPortableOverrides();
    return const JsonEncoder.withIndent('  ').convert(bundle);
  }

  Future<CustomizationImportReport> importBundle(
    String source, {
    Iterable<String>? availableModulePaths,
  }) async {
    if (utf8.encode(source).length > maxImportBytes) {
      throw const FormatException('HMI content bundle is too large');
    }
    final decoded = jsonDecode(source);
    if (decoded is! Map) {
      throw const FormatException('HMI content bundle must be a JSON object');
    }
    final schema = decoded['schemaVersion'];
    if (schema is! num || schema.toInt() < 1 || schema.toInt() > 4) {
      throw const FormatException('Unsupported HMI content schema');
    }
    if (schema.toInt() >= 3 &&
        decoded['bundleType'] != 'fraktal-hmi-customization') {
      throw const FormatException('Invalid HMI customization bundle');
    }

    final documents = <String, List<ModuleDocument>>{};
    final rawDocuments = decoded['documents'];
    if (rawDocuments is! List) {
      throw const FormatException('Invalid HMI document list');
    }
    for (final source in rawDocuments) {
      final document = ModuleDocument.fromJson(source);
      if (document == null || document.bytes.length > maxPdfBytes) {
        throw const FormatException('Invalid HMI document');
      }
      documents.putIfAbsent(document.modulePath, () => []).add(document);
    }

    final policies = <String, Map<ModuleSection, AccessLevel>>{};
    final rawPolicies = decoded['policies'];
    if (rawPolicies is! Map) {
      throw const FormatException('Invalid HMI access policy');
    }
    for (final module in rawPolicies.entries) {
      if (module.key is! String || module.value is! Map) {
        throw const FormatException('Invalid HMI access policy');
      }
      final sectionPolicy = <ModuleSection, AccessLevel>{};
      for (final item in (module.value as Map).entries) {
        final section = ModuleSection.values
            .where((value) => value.name == item.key)
            .firstOrNull;
        final level = AccessLevel.values
            .where((value) => value.name == item.value)
            .firstOrNull;
        if (section == null || level == null) {
          throw const FormatException('Invalid HMI access policy value');
        }
        sectionPolicy[section] = level;
      }
      policies[module.key as String] = sectionPolicy;
    }

    final layouts = <String, List<ModuleTabDefinition>>{};
    final revisions = <String, List<ModuleLayoutRevision>>{};
    final rawLayouts = decoded['layouts'];
    if (schema.toInt() >= 2 && rawLayouts is! Map) {
      throw const FormatException('Invalid HMI module layouts');
    }

    final localizationProfile = decoded['localization'];
    if (schema.toInt() >= 3 && localizationProfile is! Map) {
      throw const FormatException('Invalid HMI localization profile');
    }
    if (rawLayouts is Map) {
      for (final module in rawLayouts.entries) {
        if (module.key is! String || module.value is! List) {
          throw const FormatException('Invalid HMI module layout');
        }
        final sources = module.value as List;
        if (sources.isEmpty || sources.length > 32) {
          throw const FormatException('Invalid HMI module tab count');
        }
        final tabs = <ModuleTabDefinition>[];
        final ids = <String>{};
        for (final source in sources) {
          final tab = ModuleTabDefinition.fromJson(source);
          if (tab == null || !ids.add(tab.id)) {
            throw const FormatException('Invalid HMI module tab');
          }
          tabs.add(tab);
        }
        layouts[module.key as String] = tabs;
      }
    }

    final rawRevisions = decoded['layoutRevisions'];
    if (schema.toInt() >= 4 && rawRevisions is! Map) {
      throw const FormatException('Invalid HMI module layout revisions');
    }
    if (rawRevisions is Map) {
      for (final module in rawRevisions.entries) {
        if (module.key is! String || module.value is! List) continue;
        final parsed = <ModuleLayoutRevision>[];
        for (final source in module.value as List) {
          final revision = ModuleLayoutRevision.fromJson(source);
          if (revision != null) parsed.add(revision);
        }
        if (parsed.isNotEmpty) {
          parsed.sort((a, b) => b.createdAt.compareTo(a.createdAt));
          revisions[module.key as String] =
              parsed.take(maxLayoutRevisions).toList();
        }
      }
    }

    final sourcePaths = <String>{
      ...documents.keys,
      ...policies.keys,
      ...layouts.keys,
      ...revisions.keys,
    };
    final reconciliation = _reconcileModulePaths(
      sourcePaths,
      availableModulePaths?.toSet(),
    );
    String destination(String path) => reconciliation.remapped[path] ?? path;
    final reconciledDocuments = <String, List<ModuleDocument>>{};
    for (final entry in documents.entries) {
      final target = destination(entry.key);
      reconciledDocuments[target] = [
        for (final document in entry.value)
          document.copyWith(modulePath: target),
      ];
    }
    final reconciledPolicies = <String, Map<ModuleSection, AccessLevel>>{
      for (final entry in policies.entries) destination(entry.key): entry.value,
    };
    final reconciledLayouts = <String, List<ModuleTabDefinition>>{
      for (final entry in layouts.entries) destination(entry.key): entry.value,
    };
    final reconciledRevisions = <String, List<ModuleLayoutRevision>>{
      for (final entry in revisions.entries)
        destination(entry.key): entry.value,
    };

    if (localizationProfile != null) {
      await localization.importPortableOverrides(localizationProfile,
          merge: true);
    }
    for (final entry in reconciledDocuments.entries) {
      final existing = _documents[entry.key] ?? const <ModuleDocument>[];
      final importedIds = entry.value.map((document) => document.id).toSet();
      _documents[entry.key] = [
        ...entry.value,
        for (final document in existing)
          if (!importedIds.contains(document.id)) document,
      ];
    }
    for (final entry in reconciledPolicies.entries) {
      _policies.putIfAbsent(entry.key, () => {}).addAll(entry.value);
    }
    for (final entry in reconciledLayouts.entries) {
      final existing = _layouts[entry.key] ?? const <ModuleTabDefinition>[];
      final importedIds = entry.value.map((tab) => tab.id).toSet();
      _layouts[entry.key] = [
        ...entry.value,
        for (final tab in existing)
          if (!importedIds.contains(tab.id)) tab,
      ];
    }
    for (final entry in reconciledRevisions.entries) {
      final existing = _revisions[entry.key] ?? const <ModuleLayoutRevision>[];
      final importedIds = entry.value.map((revision) => revision.id).toSet();
      final merged = [
        ...entry.value,
        for (final revision in existing)
          if (!importedIds.contains(revision.id)) revision,
      ]..sort((a, b) => b.createdAt.compareTo(a.createdAt));
      _revisions[entry.key] = merged.take(maxLayoutRevisions).toList();
    }
    for (final documents in _documents.values) {
      for (final document in documents) {
        localization.registerProjectDefault(
            document.titleKey, document.titleDefault);
      }
    }
    await _persist();
    notifyListeners();
    return CustomizationImportReport(
      exactPaths: reconciliation.exact.toList()..sort(),
      remappedPaths: Map.unmodifiable(reconciliation.remapped),
      deferredPaths: reconciliation.deferred.toList()..sort(),
    );
  }

  Future<ModuleDocument> addPdf({
    required String modulePath,
    required String fileName,
    required Uint8List bytes,
    required String title,
    required String uploadedBy,
  }) async {
    if (bytes.length > maxPdfBytes) {
      throw const FormatException('PDF too large');
    }
    if (bytes.length < 5 || ascii.decode(bytes.sublist(0, 5)) != '%PDF-') {
      throw const FormatException('Not a PDF');
    }
    final id = DateTime.now().microsecondsSinceEpoch.toString();
    final key = 'project.document.${_keyPart(modulePath)}.$id.title';
    final titleDefault = title.trim().isEmpty ? fileName : title.trim();
    localization.registerProjectDefault(key, titleDefault);
    final document = ModuleDocument(
      id: id,
      modulePath: modulePath,
      fileName: fileName,
      titleKey: key,
      titleDefault: titleDefault,
      bytes: bytes,
      uploadedAt: DateTime.now().toUtc(),
      uploadedBy: uploadedBy,
    );
    _documents.putIfAbsent(modulePath, () => []).add(document);
    await _persist();
    notifyListeners();
    return document;
  }

  Future<void> removeDocument(ModuleDocument document) async {
    _documents[document.modulePath]
        ?.removeWhere((item) => item.id == document.id);
    await _persist();
    notifyListeners();
  }

  Map<String, Object?> _data() => {
        'schemaVersion': 4,
        'documents': [
          for (final documents in _documents.values)
            for (final document in documents) document.toJson(),
        ],
        'policies': {
          for (final module in _policies.entries)
            module.key: {
              for (final policy in module.value.entries)
                policy.key.name: policy.value.name,
            },
        },
        'layouts': {
          for (final module in _layouts.entries)
            module.key: [for (final tab in module.value) tab.toJson()],
        },
        'layoutRevisions': {
          for (final module in _revisions.entries)
            module.key: [
              for (final revision in module.value) revision.toJson(),
            ],
        },
      };

  Future<void> _persist() => store.save(_data());

  static AccessLevel _defaultLevel(ModuleSection section) => switch (section) {
        ModuleSection.information => AccessLevel.none,
        ModuleSection.operations => AccessLevel.operator,
        ModuleSection.diagnostics => AccessLevel.operator,
        ModuleSection.configuration => AccessLevel.engineer,
        ModuleSection.documentation => AccessLevel.operator,
        ModuleSection.history => AccessLevel.technician,
      };

  static String _keyPart(String value) => value
      .replaceAll(RegExp('[^A-Za-z0-9]+'), '_')
      .replaceAll(RegExp('_+'), '_');

  static _PathReconciliation _reconcileModulePaths(
    Set<String> sourcePaths,
    Set<String>? availablePaths,
  ) {
    if (availablePaths == null) {
      return const _PathReconciliation();
    }
    final exact = sourcePaths.intersection(availablePaths);
    final remapped = <String, String>{};
    final claimed = <String>{...exact};
    final unresolved = sourcePaths.difference(exact).toList()
      ..sort((a, b) => _depth(a).compareTo(_depth(b)));
    final sourceRoots =
        sourcePaths.where((path) => !path.contains('.')).toList();
    final targetRoots =
        availablePaths.where((path) => !path.contains('.')).toList();
    if (sourceRoots.length == 1 && targetRoots.length == 1) {
      final sourceRoot = sourceRoots.single;
      final targetRoot = targetRoots.single;
      if (!exact.contains(sourceRoot) && claimed.add(targetRoot)) {
        remapped[sourceRoot] = targetRoot;
      }
    }

    for (final source in unresolved) {
      if (remapped.containsKey(source)) continue;
      final separator = source.lastIndexOf('.');
      if (separator < 0) continue;
      final parent = source.substring(0, separator);
      final local = source.substring(separator + 1);
      final mappedParent =
          remapped[parent] ?? (availablePaths.contains(parent) ? parent : null);
      if (mappedParent == null) continue;
      final candidate = '$mappedParent.$local';
      if (availablePaths.contains(candidate) && claimed.add(candidate)) {
        remapped[source] = candidate;
      }
    }

    for (final source in unresolved) {
      if (remapped.containsKey(source)) continue;
      var bestScore = 0;
      final best = <String>[];
      for (final target in availablePaths) {
        if (claimed.contains(target)) continue;
        final score = _commonSuffixSegments(source, target);
        if (score > bestScore) {
          bestScore = score;
          best
            ..clear()
            ..add(target);
        } else if (score == bestScore && score > 0) {
          best.add(target);
        }
      }
      if (bestScore > 0 && best.length == 1 && claimed.add(best.single)) {
        remapped[source] = best.single;
      }
    }

    // A uniquely remapped descendant also supplies a safe root-rename hint.
    for (final sourceRoot in sourceRoots) {
      if (exact.contains(sourceRoot) || remapped.containsKey(sourceRoot)) {
        continue;
      }
      final inferredTargets = <String>{};
      for (final entry in remapped.entries) {
        if (!entry.key.startsWith('$sourceRoot.')) continue;
        inferredTargets.add(entry.value.split('.').first);
      }
      if (inferredTargets.length == 1) {
        final target = inferredTargets.single;
        if (availablePaths.contains(target) && claimed.add(target)) {
          remapped[sourceRoot] = target;
        }
      }
    }

    return _PathReconciliation(
      exact: exact,
      remapped: remapped,
      deferred: sourcePaths.difference(exact).difference(remapped.keys.toSet()),
    );
  }

  static int _commonSuffixSegments(String left, String right) {
    final a = left.split('.');
    final b = right.split('.');
    var count = 0;
    while (count < a.length &&
        count < b.length &&
        a[a.length - 1 - count] == b[b.length - 1 - count]) {
      count++;
    }
    return count;
  }

  static int _depth(String path) => '.'.allMatches(path).length;
}

class _PathReconciliation {
  final Set<String> exact;
  final Map<String, String> remapped;
  final Set<String> deferred;

  const _PathReconciliation({
    this.exact = const {},
    this.remapped = const {},
    this.deferred = const {},
  });
}
