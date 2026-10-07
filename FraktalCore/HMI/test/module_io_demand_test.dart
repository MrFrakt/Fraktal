import 'package:flutter_test/flutter_test.dart';
import 'package:fraktal_hmi/data/opcua_repository.dart';
import 'package:fraktal_hmi/data/opcua_session_client.dart';
import 'package:fraktal_hmi/data/opcua_snapshot_mapper.dart';
import 'package:fraktal_hmi/domain/types.dart';

const topology = 'PLC1/GVL_IO/Topology';
const master = '$topology/Nodes/Nodes[1]';
const ownNode = '$topology/Nodes/Nodes[2]';
const otherNode = '$topology/Nodes/Nodes[3]';
const own = '$ownNode/Channels/Channels[1]';
const other = '$otherNode/Channels/Channels[1]';
const flag = 'PLC1/MAIN/FieldbusViewActive';

// The snapshot carries cached activation identity, as a hydrated manifest does.
// Only dynamic leaves appear in discoverPaths; excluded dynamic fields can be
// obtained only by a targeted read. This isolates I/O scope arbitration from
// the separately tested QUERY_CONFIG mailbox protocol.
class IoDemandClient implements OpcUaBulkReadClient, OpcUaTieredReadClient {
  final excluded = <String>{};
  final readBatches = <List<String>>[];
  final gates = <bool>[];
  bool closed = false;
  Map<String, Object?> get identity => {
        'PLC1/MAIN/Press/Status/Name': 'Press',
        'PLC1/MAIN/Press/Status/ModuleType': ModuleType.unit.index,
        'PLC1/MAIN/Press/Status/State': ExecState.ready.index,
        '$topology/NodeCount': 3,
        for (final (node, name, parent, count) in [
          (master, 'EtherCAT', 0, 0),
          (ownNode, 'DI', 1, 1),
          (otherNode, 'DO', 1, 1)
        ]) ...{
          '$node/Name': name,
          '$node/ParentIdx': parent,
          '$node/ChannelCount': count,
        },
        for (final (base, module, dir) in [
          (own, 'Press.Feeder', 0),
          (other, 'Press.Feeder2', 1)
        ]) ...{
          '$base/Name': base == own ? '_B301' : '_K302',
          '$base/ModulePath': module,
          '$base/Path': '$module.IO',
          '$base/Dir': dir,
          '$base/Kind': 0,
        },
      };
  Map<String, Object?> get dynamicValues => {
        flag: false,
        '$topology/MappingValid': true,
        '$topology/MappingDiagnostic': '',
        for (final node in [master, ownNode, otherNode]) ...{
          '$node/State': 4,
          '$node/LinkOk': true
        },
        for (final base in [own, other]) ...{
          '$base/BoolValue': true,
          '$base/Quality': true,
          '$base/Forced': false,
          '$base/FaultActive': false,
          '$base/Diagnostic': '',
          '$base/Forceable': true,
        },
      };
  @override
  Future<Map<String, Object?>> snapshot() async => {
        'protocol': 'fraktal.opcua.snapshot.v1',
        'truncated': false,
        'paths': dynamicValues.keys.toList(),
        'values': {
          ...identity,
          for (final entry in dynamicValues.entries)
            if (!excluded.contains(entry.key)) entry.key: entry.value
        },
      };
  @override
  Future<Map<String, Object?>> readValues(List<String> paths) async {
    readBatches.add(List.of(paths));
    return {for (final path in paths) path: dynamicValues[path]};
  }

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
  Future<bool> write(String path, OpcUaWriteType type, Object value) async {
    if (path == flag) gates.add(value as bool);
    return true;
  }

  @override
  Future<void> close() async {
    closed = true;
  }
}

void main() {
  test(
      'manual I/O reads exact-assigned channels and ancestor health, then switches and stops',
      () async {
    final client = IoDemandClient();
    final repo = await OpcUaRepository.connectWithClient(client,
        refreshInterval: const Duration(milliseconds: 20));
    addTearDown(repo.dispose);
    await Future<void>.delayed(const Duration(milliseconds: 60));
    expect(client.readBatches, isEmpty);
    repo.setModuleIoViewActive('Press.Feeder');
    await Future<void>.delayed(const Duration(milliseconds: 100));
    expect(
        client.readBatches.last,
        containsAll([
          '$own/Quality',
          '$own/Forced',
          '$master/State',
          '$ownNode/State'
        ]));
    expect(
        client.readBatches.last
            .any((p) => p.startsWith('$other/') || p.startsWith('$otherNode/')),
        isFalse);
    expect(client.readBatches.last, isNot(contains('$own/Forceable')));
    expect(
        client.readBatches.last.toSet().length, client.readBatches.last.length);
    expect(client.gates.last, isTrue);
    final bus = await repo.fieldbus().first;
    expect(bus.first.children.first.channels.first.quality, isTrue);
    repo.setModuleIoViewActive('Press.Feeder2');
    await Future<void>.delayed(const Duration(milliseconds: 100));
    expect(client.readBatches.last, contains('$other/Quality'));
    expect(client.readBatches.last.any((p) => p.startsWith('$own/')), isFalse);
    repo.setModuleIoViewActive(null);
    await Future<void>.delayed(const Duration(milliseconds: 40));
    final settled = client.readBatches.length;
    await Future<void>.delayed(const Duration(milliseconds: 80));
    expect(client.readBatches.length, settled);
    expect(client.gates.last, isFalse);
  });

  test(
      'bus page and module card share demand without withdrawing one another; close releases gate',
      () async {
    final client = IoDemandClient();
    final repo = await OpcUaRepository.connectWithClient(client,
        refreshInterval: const Duration(milliseconds: 20));
    repo.setModuleIoViewActive('Press.Feeder');
    repo.setFieldbusViewActive(true);
    repo.setModuleIoViewActive(null);
    await Future<void>.delayed(const Duration(milliseconds: 90));
    expect(client.gates.last, isTrue);
    expect(client.readBatches.last, contains('$other/Quality'));
    repo.setModuleIoViewActive('Press.Feeder');
    repo.setFieldbusViewActive(false);
    await Future<void>.delayed(const Duration(milliseconds: 80));
    expect(client.gates.last, isTrue);
    expect(client.readBatches.last, isNot(contains('$other/Quality')));
    repo.dispose();
    await Future<void>.delayed(const Duration(milliseconds: 20));
    expect(client.closed, isTrue);
    expect(client.gates.last, isFalse);
  });

  test('an unassigned module does not start a fieldbus scan', () async {
    final client = IoDemandClient();
    final repo = await OpcUaRepository.connectWithClient(client,
        refreshInterval: const Duration(milliseconds: 20));
    addTearDown(repo.dispose);
    repo.setModuleIoViewActive('Press.Unassigned');
    await Future<void>.delayed(const Duration(milliseconds: 80));
    expect(client.gates, isNot(contains(true)));
    expect(
        client.readBatches.expand((p) => p).any((p) => p.contains('/Channels')),
        isFalse);
  });

  test('missing or stale physical values/quality never become healthy OFF', () {
    final source = IoDemandClient();
    final values = {...source.identity, ...source.dynamicValues};
    bool mapped(Map<String, Object?> sample,
            {Map<String, Object?> meta = const {}}) =>
        OpcUaSnapshotMapper()
            .map({'values': sample, 'dataValues': meta})
            .fieldbus
            .first
            .children
            .first
            .channels
            .first
            .quality;
    expect(mapped(values), isTrue);
    expect(mapped({...values, '$own/BoolValue': null}), isFalse);
    expect(mapped({...values, '$own/Quality': null}), isFalse);
    expect(
        mapped(values, meta: {
          '$own/BoolValue': {'status': 0x40000000}
        }),
        isFalse);
    expect(
        mapped(values, meta: {
          '$own/Quality': {'status': 0x80000000}
        }),
        isFalse);
  });
}
