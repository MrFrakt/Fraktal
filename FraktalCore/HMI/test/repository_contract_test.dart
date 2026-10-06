// One repository contract, executed with TC3 paths and the AB adapter document.
// The AB document is emitted by fraktal_ab_s9_contract.py from generated native
// fixtures through the production projection and gateway. No controller writes.
import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:fraktal_hmi/data/opcua_repository.dart';
import 'package:fraktal_hmi/data/opcua_session_client.dart';
import 'package:fraktal_hmi/domain/module_node.dart';
import 'package:fraktal_hmi/domain/types.dart';

void main() {
  const base = 'PLC1/MAIN/Unit';
  final tc3 = <String, Object?>{
    'protocol': 'fraktal.opcua.snapshot.v1',
    'truncated': false,
    'values': <String, Object?>{
      '$base/Status/Name': 'Unit',
      '$base/Status/ModuleType': ModuleType.unit.index,
      '$base/Status/State': ExecState.ready.index,
      '$base/ModeActivePublished': UnitMode.auto.index,
      '$base/HmiRequest/Sequence': 0,
      '$base/HmiResponse/AckSequence': 0,
      '$base/HmiResponse/Accepted': false,
      '$base/HmiResponse/Diagnostic': '',
    },
  };
  contract('TC3 contract paths', tc3);
  final file = Platform.environment['FRAKTAL_S9_SNAPSHOT'];
  if (file != null) {
    contract(
        'AB production adapter',
        (jsonDecode(File(file).readAsStringSync()) as Map)
            .cast<String, Object?>());
  } else {
    test('AB production adapter requires the offline projection runner', () {},
        skip: 'Run fraktal_ab_s9_contract.py to supply its generated snapshot');
  }
}

void contract(String name, Map<String, Object?> source) {
  group(name, () {
    late _ContractClient client;
    late OpcUaRepository repository;
    setUp(() async {
      client = _ContractClient(source);
      repository = await OpcUaRepository.connectWithClient(client,
          refreshInterval: const Duration(days: 1));
    });
    tearDown(() => repository.dispose());

    test(
        'discovers a root and preserves Good gateway/source timestamp metadata',
        () async {
      final forest = await repository.forest().first;
      final root = forest.single;
      expect(root.type, ModuleType.unit);
      expect(root.path, client.identity);
      final sample = root.tagAt('OutImm/S9Probe');
      expect(sample?.usable, isTrue);
      expect(sample?.value, 42);
      expect(sample?.serverTimestamp?.isUtc, isTrue);
    });

    test('Bad and missing values fail closed', () async {
      final root = (await repository.forest().first).single;
      expect(root.tagAt('OutImm/S9BadProbe')?.quality, PublishedTagQuality.bad);
      expect(root.valueAt('OutImm/S9BadProbe'), isNull);
      expect(root.valueAt('OutImm/S9MissingProbe'), isNull);
      expect(root.tagAt('OutImm/S9UnknownProbe')?.usable, isFalse);
      expect(root.valueAt('OutImm/S9UnknownProbe'), isNull);
    });

    test('complete payload is committed last and refusal stays a refusal',
        () async {
      client.accept = false;
      expect(
          await repository.setMode(client.identity, UnitMode.manual), isFalse);
      final writes = client.batches.last;
      expect(writes.length, 10);
      expect(writes.last.path, '${client.base}/HmiRequest/Sequence');
      expect(writes.last.type, OpcUaWriteType.uint32);
      expect(client.values['${client.base}/HmiResponse/Diagnostic'],
          'std.release.accessDenied');
    });

    test(
        'ambiguous commit is never retried and fresh command uses next sequence',
        () async {
      client.failAfterCommit = true;
      final before = client.batches.where((b) => b.first.value == 3).length;
      expect(
          await repository.setMode(client.identity, UnitMode.manual), isFalse);
      final lost = client.sequence;
      await Future<void>.delayed(const Duration(milliseconds: 30));
      expect(
          client.batches.where((b) => b.first.value == 3).length, before + 1);
      expect(await repository.setMode(client.identity, UnitMode.auto), isTrue);
      expect(client.sequence, (lost + 1) & 0xffffffff);
    });

    test('tier classification never excludes discovery identity or mode state',
        () {
      expect(client.excluded, isNot(contains('${client.base}/Status/Name')));
      expect(client.excluded,
          isNot(contains('${client.base}/ModeActivePublished')));
    });

    test('truncated discovery refuses before LIVE', () async {
      final truncated = _ContractClient({...source, 'truncated': true});
      await expectLater(OpcUaRepository.connectWithClient(truncated),
          throwsA(isA<OpcUaSnapshotException>()));
      expect(truncated.closed, isTrue);
    });
  });

  test('$name uses committed input at wrap, without ordering uint32 counters',
      () async {
    final wrapped = _ContractClient(source);
    wrapped.values['${wrapped.base}/HmiRequest/Sequence'] = 0;
    wrapped.values['${wrapped.base}/HmiResponse/AckSequence'] = 0xffffffff;
    wrapped.sequence = 0;
    final repository = await OpcUaRepository.connectWithClient(wrapped,
        refreshInterval: const Duration(days: 1));
    addTearDown(repository.dispose);
    expect(await repository.setMode(wrapped.identity, UnitMode.manual), isTrue);
    // Initial manifest queries may have used sequences too; none may repeat 0.
    expect(wrapped.batches.first.last.value, 1);
  });
}

class _ContractClient
    implements
        OpcUaBatchSessionClient,
        OpcUaBulkReadClient,
        OpcUaPathDiscoveryClient,
        OpcUaTieredReadClient {
  final Map<String, Object?> document;
  late final Map<String, Object?> values;
  late final String base;
  late final String identity;
  final batches = <List<OpcUaWrite>>[];
  Set<String> excluded = {}, slow = {};
  int sequence = 0;
  bool accept = true, failAfterCommit = false, closed = false;

  _ContractClient(Map<String, Object?> source)
      : document =
            (jsonDecode(jsonEncode(source)) as Map).cast<String, Object?>() {
    values = (document['values'] as Map).cast<String, Object?>();
    document['values'] = values;
    base = values.keys
        .firstWhere((p) =>
            p.endsWith('/Status/ModuleType') &&
            values[p] == ModuleType.unit.index)
        .replaceFirst('/Status/ModuleType', '');
    identity = values['$base/Status/Name'] as String;
    values['$base/HmiRequest/Sequence'] ??= 0;
    values['$base/HmiResponse/AckSequence'] ??= 0;
    values['$base/HmiResponse/Accepted'] ??= false;
    values['$base/HmiResponse/Diagnostic'] ??= '';
    values['$base/OutImm/S9Probe'] = 42;
    values['$base/OutImm/S9BadProbe'] = 99;
    values['$base/OutImm/S9UnknownProbe'] = 88;
    final metadata =
        (document['dataValues'] as Map? ?? {}).cast<String, Object?>();
    metadata['$base/OutImm/S9Probe'] = {
      'value': 42,
      'type': 'Integer',
      'status': 0,
      'ageMs': 0,
      'tier': 'fast',
      'serverTimestampUs': '1784613600123456',
    };
    metadata['$base/OutImm/S9BadProbe'] = {
      'value': 99,
      'type': 'Integer',
      'status': 0x80000000,
      'ageMs': 0,
      'tier': 'fast',
    };
    metadata['$base/OutImm/S9UnknownProbe'] = {'value': 88, 'type': 'Integer'};
    document['dataValues'] = metadata;
    document['paths'] = values.keys.toList();
    document['nodeCount'] = values.length;
  }

  @override
  Future<Map<String, Object?>> snapshot() async => document;
  @override
  Future<List<String>> discoverPaths() async => values.keys.toList();
  @override
  Future<Map<String, Object?>> readValues(List<String> paths) async =>
      {for (final p in paths) p: values[p]};
  @override
  Future<bool> write(String path, OpcUaWriteType type, Object value) async =>
      true;
  @override
  Future<bool> writeBatch(List<OpcUaWrite> writes) async {
    batches.add(List.of(writes));
    for (final write in writes) {
      values[write.path] = write.value;
    }
    sequence = writes.last.value as int;
    values['$base/HmiResponse/AckSequence'] = sequence;
    values['$base/HmiResponse/Accepted'] = accept;
    values['$base/HmiResponse/Diagnostic'] =
        accept ? '' : 'std.release.accessDenied';
    if (failAfterCommit && writes.first.value == 3) {
      failAfterCommit = false;
      throw const OpcUaTransportException('fixture: ambiguous commit');
    }
    return true;
  }

  @override
  Future<void> setSlowPaths(Iterable<String> paths) async =>
      slow = paths.toSet();
  @override
  Future<void> setExcludedPaths(Iterable<String> paths) async =>
      excluded = paths.toSet();
  @override
  Future<void> refreshSlowPaths() async {}
  @override
  Future<void> close() async => closed = true;
}
