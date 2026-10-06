// Static config may be published by a binding without appearing in its pages.
// Tiering must not remove it until its exact replacement has been hydrated.
import 'package:flutter_test/flutter_test.dart';
import 'package:fraktal_hmi/data/opcua_repository.dart';
import 'package:fraktal_hmi/data/opcua_session_client.dart';
import 'package:fraktal_hmi/domain/types.dart';

const _base = 'PLC1/MAIN/Press';
const _model = '$_base/AvailableModels/AvailableModels[2]/ModelCode';

void main() {
  for (final flat in [true, false]) {
    for (final count in [16, 22, 35]) {
      test('configuration page follows published capacity ($count, flat=$flat)',
          () async {
        final client = _SizedConfigClient(flat, count);
        final repo = await OpcUaRepository.connectWithClient(client,
            refreshInterval: const Duration(milliseconds: 10));
        addTearDown(repo.dispose);
        expect(await _configLoaded(repo), isTrue);
        final root = (await repo.forest().first).single;
        expect(root.config, hasLength(count));
        expect(root.config.where((field) => field.kind == CfgKind.lineCfg),
            hasLength(count - 9));
        final other = await repo.queryModelConfig('Press', 4);
        expect(other, hasLength(4));
        expect(other!.every((field) => field.value == '451'), isTrue);
        expect(client.unknownReads, isEmpty);
      });
    }

    for (final invalid in ['overcount', 'hole', 'missing value']) {
      test(
          'incomplete configuration page is unavailable ($invalid, flat=$flat)',
          () async {
        final client = _SizedConfigClient(flat, 16, invalid: invalid);
        final repo = await OpcUaRepository.connectWithClient(client,
            refreshInterval: const Duration(milliseconds: 10));
        addTearDown(repo.dispose);
        expect(await _configLoaded(repo), isFalse);
        expect((await repo.forest().first).single.config, isEmpty);
        expect(await repo.queryModelConfig('Press', 4), isNull);
      });
    }

    test(
        'new model page uses discovered paths and survives cleanup (flat=$flat)',
        () async {
      final client = _StrictConfigClient(flat);
      final repo = await OpcUaRepository.connectWithClient(client,
          refreshInterval: const Duration(milliseconds: 10));
      addTearDown(repo.dispose);
      expect(await _configLoaded(repo), isTrue);
      await Future<void>.delayed(const Duration(milliseconds: 80));
      expect((await repo.forest().first).single.availableModels,
          ['M-100', 'M-200', 'M-050', 'M-101']);
      final other = await repo.queryModelConfig('Press', 4);
      expect(other, isNotNull);
      expect(other, hasLength(1));
      expect(other!.single.value, '451');
      expect(client.unknownReads, isEmpty);
      expect(client.requestedModels, contains(4));
      expect((await repo.forest().first).single.modelCode, 'M-100');
    });

    test(
        'unreadable selected page never uses cached active values (flat=$flat)',
        () async {
      final client = _StrictConfigClient(flat);
      final repo = await OpcUaRepository.connectWithClient(client,
          refreshInterval: const Duration(milliseconds: 10));
      addTearDown(repo.dispose);
      expect(await _configLoaded(repo), isTrue);
      client.failPageReads = true;
      expect(await repo.queryModelConfig('Press', 4), isNull);
      expect((await repo.forest().first).single.modelCode, 'M-100');
    });
  }

  for (final modelsInManifest in [false, true]) {
    test('model selection survives tiering (manifest=$modelsInManifest)',
        () async {
      final client = _ConfigClient(modelsInManifest);
      final repo = await OpcUaRepository.connectWithClient(client,
          refreshInterval: const Duration(milliseconds: 10));
      addTearDown(repo.dispose);
      await repo
          .forest()
          .firstWhere((forest) => forest.first.config.isNotEmpty);
      await Future<void>.delayed(const Duration(milliseconds: 60));
      final root = (await repo.forest().first).single;
      expect(root.availableModels, ['M-100', 'M-200']);
      expect(root.config.single.modelScoped, isTrue);
      expect(client.excluded.contains(_model), modelsInManifest);
      expect(client.excluded,
          contains('$_base/SequenceStepDef/SequenceStepDef[1]/StepName'));
      final other = await repo.queryModelConfig('Press', 2);
      expect(other!.single.value, '200');
      expect(client.requestedModels, contains(2));
      expect((await repo.forest().first).single.modelCode, 'M-100');
    });
  }
}

class _SizedConfigClient extends _StrictConfigClient {
  final int count;
  final String? invalid;
  _SizedConfigClient(super.flat, this.count, {this.invalid});

  @override
  Map<String, Object?> get values {
    final out = super.values;
    const page = '$_base/HmiResponse/ConfigPage';
    final prefix = flat ? '$page/Entries' : '$page/Entries/Entries';
    final template = {
      for (final entry in out.entries)
        if (entry.key.startsWith('$prefix[1]/'))
          entry.key.substring('$prefix[1]/'.length): entry.value,
    };
    out.removeWhere((key, _) => key.startsWith('$prefix['));
    out['$page/EntryCount'] = invalid == 'overcount' ? count + 1 : count;
    // Keep capacity large enough when a middle slot is missing: the legacy
    // zero-based fallback must not duplicate its previous row to fill the hole.
    for (var i = 1; i <= count + (invalid == 'hole' ? 1 : 0); i++) {
      if (invalid == 'hole' && i == 8) continue;
      final entry = {
        ...template,
        'Item': 'Config/Field$i',
        'WriteKey': 'field.$i',
        'ConfigKind': i <= 4 ? 0 : (i <= 9 ? 1 : 2),
        'ModelScoped': i <= 4,
      };
      if (invalid == 'missing value' && i == count) {
        entry.remove('ValueText');
      }
      for (final member in entry.entries) {
        out['$prefix[$i]/${member.key}'] = member.value;
      }
    }
    return out;
  }
}

Future<bool> _configLoaded(OpcUaRepository repo) => repo
    .forest()
    .map((forest) => forest.first.config.isNotEmpty)
    .firstWhere((loaded) => loaded)
    .timeout(const Duration(seconds: 2), onTimeout: () => false);

class _ConfigClient
    implements
        OpcUaBatchSessionClient,
        OpcUaBulkReadClient,
        OpcUaTieredReadClient {
  final bool modelsInManifest;
  _ConfigClient(this.modelsInManifest);
  final excluded = <String>{};
  final requestedModels = <int>[];
  int sequence = 0, model = 0;

  Map<String, Object?> get values {
    final entries = <Map<String, Object?>>[
      {
        'Scope': 'Press',
        'Item': 'Config/Dwell',
        'ValueText': model == 2 ? '200' : '100',
        'WriteKey': 'model.dwell',
        'WriteRevision': 1,
        'ConfigKind': 0,
        'ValueType': 0,
        'Writable': true,
        'ModelScoped': true,
      },
      if (modelsInManifest) ...[
        {
          'Scope': 'Press',
          'Item': 'AvailableModelCount',
          'ValueText': '2',
          'ValueType': 0
        },
        {
          'Scope': 'Press',
          'Item': 'AvailableModels/AvailableModels[1]/ModelCode',
          'ValueText': 'M-100'
        },
        {
          'Scope': 'Press',
          'Item': 'AvailableModels/AvailableModels[2]/ModelCode',
          'ValueText': 'M-200'
        },
      ],
    ];
    const page = '$_base/HmiResponse/ConfigPage';
    return {
      '$_base/Status/Name': 'Press', '$_base/Status/ModuleType': 1,
      '$_base/Status/State': 0, '$_base/Status/ConfigRev': 1,
      '$_base/Model/ModelCode': 'M-100', '$_base/AvailableModelCount': 2,
      '$_base/AvailableModels/AvailableModels[1]/ModelCode': 'M-100',
      _model: 'M-200',
      // This implementation-only definition is re-served under SequenceSteps,
      // so the cyclic reader should never pay for the definition itself.
      '$_base/SequenceStepDef/SequenceStepDef[1]/StepName': 'not a live row',
      '$_base/HmiRequest/Sequence': sequence,
      '$_base/HmiResponse/AckSequence': sequence,
      '$_base/HmiResponse/Accepted': true,
      '$_base/HmiResponse/Diagnostic': '',
      '$page/PageCount': 1, '$page/EntryCount': entries.length,
      for (var i = 0; i < entries.length; i++)
        for (final entry in entries[i].entries)
          '$page/Entries/Entries[${i + 1}]/${entry.key}': entry.value,
    };
  }

  @override
  Future<Map<String, Object?>> snapshot() async {
    final all = values;
    return {
      'protocol': 'fraktal.opcua.snapshot.v1',
      'nodeCount': all.length,
      'truncated': false,
      'paths': all.keys.toList(),
      'values': {
        for (final entry in all.entries)
          if (!excluded.contains(entry.key)) entry.key: entry.value
      },
    };
  }

  @override
  Future<Map<String, Object?>> readValues(List<String> paths) async =>
      {for (final path in paths) path: values[path]};

  @override
  Future<bool> writeBatch(List<OpcUaWrite> writes) async {
    for (final write in writes) {
      if (write.path.endsWith('/DurationMs')) model = write.value as int;
      if (write.path.endsWith('/Sequence')) sequence = write.value as int;
    }
    requestedModels.add(model);
    return true;
  }

  @override
  Future<bool> write(String path, OpcUaWriteType type, Object value) async =>
      true;
  @override
  Future<void> setExcludedPaths(Iterable<String> paths) async {
    excluded
      ..clear()
      ..addAll(paths);
  }

  @override
  Future<void> setSlowPaths(Iterable<String> paths) async {}
  @override
  Future<void> refreshSlowPaths() async {}
  @override
  Future<void> close() async {}
}

class _StrictConfigClient extends _ConfigClient {
  final bool flat;
  _StrictConfigClient(this.flat) : super(false);
  final unknownReads = <String>[];
  bool failPageReads = false;

  @override
  Map<String, Object?> get values {
    final out = <String, Object?>{};
    for (final entry in super.values.entries) {
      final key = flat
          ? entry.key.replaceAll('/Entries/Entries[', '/Entries[')
          : entry.key;
      out[key] = key.endsWith('/ValueText') && model == 4 ? '451' : entry.value;
    }
    out['$_base/AvailableModelCount'] = 4;
    out['$_base/AvailableModels/AvailableModels[3]/ModelCode'] = 'M-050';
    out['$_base/AvailableModels/AvailableModels[4]/ModelCode'] = 'M-101';
    return out;
  }

  @override
  Future<Map<String, Object?>> readValues(List<String> paths) async {
    final all = values;
    final unknown = paths.where((path) => !all.containsKey(path)).toList();
    unknownReads.addAll(unknown);
    if (unknown.isNotEmpty) {
      throw FormatException('Path outside discovery: ${unknown.first}');
    }
    if (failPageReads &&
        paths.any((path) => path.contains('/HmiResponse/ConfigPage/'))) {
      throw StateError('Page payload unavailable');
    }
    return {for (final path in paths) path: all[path]};
  }

  @override
  Future<Map<String, Object?>> snapshot() async {
    final document = await super.snapshot();
    final cached = document['values'] as Map<String, Object?>;
    for (final path in cached.keys.toList()) {
      if (path.endsWith('/ValueText')) cached[path] = '100';
    }
    return document;
  }

  @override
  Future<bool> write(String path, OpcUaWriteType type, Object value) async {
    // A periodic snapshot runs while the inert post-ack cleanup is waiting;
    // excluded page leaves must not erase the reply before its caller parses it.
    await Future<void>.delayed(const Duration(milliseconds: 30));
    return true;
  }
}
