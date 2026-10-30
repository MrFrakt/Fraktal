/// Independent read-only configuration qualification; no cyclic observer input.
import 'dart:convert';
import 'dart:io';
import 'package:fraktal_opcua_client/fraktal_opcua_client.dart';

Future<List<Map<String, Object?>>> acquireConfigurationPages(
    OpcUaSessionClient client) async {
  if (client is! OpcUaPathDiscoveryClient ||
      client is! OpcUaBulkReadClient ||
      client is! OpcUaReadOnlyConfigurationClient) {
    throw const FormatException(
        'Read-only configuration capabilities required.');
  }
  final paths = await client.discoverPaths();
  final roots = <String>{
    for (final path in paths)
      if (path.split('/').length == 3 && path.endsWith('/Status/Name'))
        path.split('/').first
  }.toList()
    ..sort();
  if (roots.isEmpty)
    throw const FormatException('No discovered root identity.');
  final values = await (client as OpcUaBulkReadClient).readValues([
    for (final root in roots) ...[
      '$root/Status/Name',
      '$root/Status/ModuleType',
      '$root/AvailableModelCount'
    ]
  ]);
  final pages = <Map<String, Object?>>[];
  for (final root in roots) {
    final count = values['$root/AvailableModelCount'];
    final modelIndices = {
      for (final path in paths)
        if (path.startsWith('$root/AvailableModels['))
          path.substring(0, path.indexOf(']') + 1)
    };
    if (values['$root/Status/Name'] != root ||
        values['$root/Status/ModuleType'] != 1 ||
        count is! int ||
        count < 0 ||
        count > modelIndices.length) {
      throw const FormatException(
          'Root identity or published model extent differs.');
    }
    // Core ordinal zero is station/line; ordinals 1..count are model banks,
    // independent of the array's physical or logical index origin.
    for (var ordinal = 0; ordinal <= count; ordinal++) {
      final page = await (client as OpcUaReadOnlyConfigurationClient)
          .readConfigurationPage(root, ordinal);
      if (page == null) {
        throw const FormatException(
            'Read-only configuration page unavailable.');
      }
      pages.add({'root': root, 'modelOrdinal': ordinal, 'page': page});
    }
  }
  return pages;
}

Future<void> main(List<String> arguments) async {
  if (arguments.length != 2) {
    throw ArgumentError('Pinned CIP endpoint and new output required.');
  }
  final endpoint = Uri.parse(arguments[0]), output = File(arguments[1]);
  if (endpoint.scheme != 'cip' ||
      endpoint.host.isEmpty ||
      output.existsSync() ||
      !RegExp(r'^[0-9A-Fa-f]{8}$')
          .hasMatch(endpoint.queryParameters['serial'] ?? '') ||
      endpoint.queryParametersAll.entries.any((e) =>
          !const {'slot', 'serial'}.contains(e.key) || e.value.length != 1)) {
    throw ArgumentError('Pinned CIP endpoint and unused output required.');
  }
  CipSessionClient? client;
  var pages = <Map<String, Object?>>[];
  String? failure;
  try {
    client = await CipSessionClient.connect(
        host: endpoint.host,
        port: endpoint.hasPort ? endpoint.port : 44818,
        slot: int.parse(endpoint.queryParameters['slot'] ?? '0'),
        expectSerial: endpoint.queryParameters['serial']);
    pages = await acquireConfigurationPages(client);
  } catch (error) {
    failure = error.toString();
  } finally {
    await client?.close();
  }
  await output.create(exclusive: true);
  await output.writeAsBytes(gzip.encode(utf8.encode(jsonEncode({
    'passed': failure == null,
    'error': failure,
    'readOnly': true,
    'writes': 0,
    'configurationPages': pages
  }))));
  stdout.writeln(jsonEncode({
    'passed': failure == null,
    'error': failure,
    'pages': pages.length,
    'writes': 0
  }));
  if (failure != null) exitCode = 1;
}
