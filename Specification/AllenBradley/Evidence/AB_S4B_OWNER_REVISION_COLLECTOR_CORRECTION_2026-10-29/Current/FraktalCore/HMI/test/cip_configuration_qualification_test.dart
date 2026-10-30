import 'package:flutter_test/flutter_test.dart';
import 'package:fraktal_opcua_client/fraktal_opcua_client.dart';
import '../tool/qualify_cip_configuration.dart' as qualification;

class _Client
    implements
        OpcUaSessionClient,
        OpcUaPathDiscoveryClient,
        OpcUaBulkReadClient,
        OpcUaReadOnlyConfigurationClient {
  final paths = <String>[];
  final values = <String, Object?>{};
  final requested = <String>[];
  final pagesRead = <(String, int)>[];
  int writes = 0;
  bool unavailable = false;
  _Client() {
    for (final root in ['Second', 'First']) {
      paths.addAll([
        '$root/Status/Name',
        '$root/Child/Status/Name',
        '$root/AvailableModels[7]/ModelCode',
        '$root/AvailableModels[8]/ModelCode'
      ]);
      values.addAll({
        '$root/Status/Name': root,
        '$root/Status/ModuleType': 1,
        '$root/AvailableModelCount': 2
      });
    }
  }
  @override
  Future<List<String>> discoverPaths() async => paths;
  @override
  Future<Map<String, Object?>> readValues(List<String> paths) async {
    requested.addAll(paths);
    return {for (final path in paths) path: values[path]};
  }

  @override
  Future<Map<String, Object?>?> readConfigurationPage(
      String root, int model) async {
    pagesRead.add((root, model));
    return unavailable
        ? null
        : {'marker': '$root:$model', 'typed': true, 'value': 1.5};
  }

  @override
  Future<bool> write(String path, OpcUaWriteType type, Object value) async {
    writes++;
    throw StateError('qualification must not write');
  }

  @override
  Future<Map<String, Object?>> snapshot() async =>
      throw StateError('no cyclic dependency');
  @override
  Future<void> close() async {}
}

void main() {
  test('all root banks come from published extents without a cyclic observer',
      () async {
    final client = _Client();
    final pages = await qualification.acquireConfigurationPages(client);
    expect(client.pagesRead, [
      ('First', 0),
      ('First', 1),
      ('First', 2),
      ('Second', 0),
      ('Second', 1),
      ('Second', 2)
    ]);
    expect(pages.first, {
      'root': 'First',
      'modelOrdinal': 0,
      'page': {'marker': 'First:0', 'typed': true, 'value': 1.5}
    });
    expect(client.requested.length, 6);
    expect(client.writes, 0);
  });
  test('identity, tier and count mismatches refuse before page acquisition',
      () async {
    for (final change in [
      ('First/Status/Name', 'Other'),
      ('First/Status/ModuleType', 3),
      ('First/AvailableModelCount', 3),
      ('First/AvailableModelCount', -1),
      ('First/AvailableModelCount', 2.0)
    ]) {
      final client = _Client()..values[change.$1] = change.$2;
      await expectLater(qualification.acquireConfigurationPages(client),
          throwsFormatException);
      expect(client.pagesRead, isEmpty);
      expect(client.writes, 0);
    }
  });
  test('an unavailable bank is a failure with no mailbox fallback', () async {
    final client = _Client()..unavailable = true;
    await expectLater(
        qualification.acquireConfigurationPages(client), throwsFormatException);
    expect(client.pagesRead, [('First', 0)]);
    expect(client.writes, 0);
  });
}
