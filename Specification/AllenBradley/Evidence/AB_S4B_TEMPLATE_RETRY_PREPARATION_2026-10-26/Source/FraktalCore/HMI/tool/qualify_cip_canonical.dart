/// Read-only canonical qualification. No declaration, PIN or write service.
import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'package:fraktal_opcua_client/fraktal_opcua_client.dart';
import '../lib/data/opcua_field_tier.dart';

Future<void> main(List<String> arguments) async {
  final args = <String, String>{};
  for (var i = 0; i < arguments.length; i += 2) {
    if (i + 1 >= arguments.length ||
        !arguments[i].startsWith('--') ||
        args.containsKey(arguments[i]))
      throw ArgumentError('Unique option/value pairs required.');
    args[arguments[i]] = arguments[i + 1];
  }
  if (args.keys.any((k) => !const {
            '--endpoint',
            '--output',
            '--samples',
            '--ready-file',
            '--stop-file'
          }.contains(k)) ||
      args['--endpoint'] == null ||
      args['--output'] == null)
    throw ArgumentError('Endpoint and new output required.');
  final endpoint = Uri.parse(args['--endpoint']!),
      output = File(args['--output']!);
  final limit = int.tryParse(args['--samples'] ?? '100');
  if (endpoint.scheme != 'cip' ||
      endpoint.host.isEmpty ||
      endpoint.queryParameters['serial'] == null ||
      output.existsSync() ||
      limit == null ||
      limit < 1 ||
      limit > 10000 ||
      endpoint.queryParametersAll.entries.any((e) =>
          !const {'slot', 'serial'}.contains(e.key) || e.value.length != 1))
    throw ArgumentError(
        'Pinned CIP endpoint, 1..10000 samples and unused output required.');
  final ready =
      args['--ready-file'] == null ? null : File(args['--ready-file']!);
  final stop = args['--stop-file'] == null ? null : File(args['--stop-file']!);
  if (ready?.existsSync() == true || stop?.existsSync() == true)
    throw ArgumentError('New ready/stop paths required.');
  CipSessionClient? client;
  Object? failure;
  final rows = <Map<String, Object?>>[],
      snapshots = <Map<String, Object?>>[],
      pages = <Map<String, Object?>>[];
  final clock = Stopwatch()..start();
  Map<String, Object?>? last;
  String? signature;
  try {
    client = await CipSessionClient.connect(
        host: endpoint.host,
        port: endpoint.hasPort ? endpoint.port : 44818,
        slot: int.parse(endpoint.queryParameters['slot'] ?? '0'),
        expectSerial: endpoint.queryParameters['serial']);
    final paths = await client.discoverPaths(),
        slow = <String>{},
        excluded = <String>{};
    for (final p in paths) {
      if (OpcUaFieldTier.isRequestPayload(p) ||
          p.split('/').any((s) => OpcUaFieldTier.unconsumedContainers
              .contains(s.split('[').first))) {
        excluded.add(p);
        continue;
      }
      switch (OpcUaFieldTier.classify(p)) {
        case FieldTier.slow:
          slow.add(p);
        case FieldTier.onDemand:
          excluded.add(p);
        case FieldTier.config:
        case FieldTier.live:
          break;
      }
    }
    await client.setSlowPaths(slow);
    await client.setExcludedPaths(excluded);
    for (var i = 0;
        i < limit && clock.elapsed < const Duration(minutes: 30);
        i++) {
      final started = clock.elapsedMicroseconds,
          document = await client.snapshot();
      last = document;
      final values = document['values'] as Map,
          samples = document['dataValues'] as Map,
          roots = List<String>.from(document['rootChildren'] as List);
      final identity = {
        for (final e in values.entries)
          if ((e.key as String).endsWith('/Status/Name') ||
              (e.key as String).endsWith('/Status/State') ||
              (e.key as String).endsWith('/ModeActive'))
            e.key as String: e.value
      };
      if (roots.isEmpty ||
          roots.any((r) => values['$r/Status/Name'] != r) ||
          (document['sampleAgeMs'] as num) >= 1000)
        throw const FormatException(
            'Fresh canonical root sample is unavailable.');
      final bad = samples.values
          .where(
              (s) => ((s as Map)['status'] as int) & 0xc0000000 == 0x80000000)
          .length;
      final uncertain = samples.values
          .where(
              (s) => ((s as Map)['status'] as int) & 0xc0000000 == 0x40000000)
          .length;
      rows.add({
        'sample': i,
        'elapsedMs': clock.elapsedMilliseconds,
        'rpcUs': clock.elapsedMicroseconds - started,
        'sampleAgeMs': document['sampleAgeMs'],
        'values': values.length,
        'modules': document['moduleCount'],
        'bad': bad,
        'uncertain': uncertain,
        'state': identity,
        'maximumRowAcquisitionUs': samples.values.fold<int>(
            0,
            (n, s) => ((s as Map)['acquisitionUs'] as int? ?? 0) > n
                ? s['acquisitionUs'] as int
                : n),
        'maximumAcceptedRowWindowUs': samples.values.fold<int>(
            0,
            (n, s) => ((s as Map)['acceptedWindowUs'] as int? ?? 0) > n
                ? s['acceptedWindowUs'] as int
                : n)
      });
      if (bad > 0)
        throw const FormatException('Bad value in cyclic qualification.');
      final current = jsonEncode(identity);
      if (signature != current && snapshots.length < 128) {
        snapshots.add(document);
        signature = current;
      }
      if (ready != null && !ready.existsSync()) {
        await ready.create(exclusive: true);
        await ready.writeAsString(
            jsonEncode({'ready': true, 'readOnly': true, 'sample': i}));
      }
      if (stop?.existsSync() == true) break;
      final remaining = 250000 - (clock.elapsedMicroseconds - started);
      if (remaining > 0)
        await Future<void>.delayed(Duration(microseconds: remaining));
    }
    if (stop != null && !stop.existsSync())
      throw const FormatException(
          'Observer ended before the owning fixture stopped it.');
    if (last == null) throw const FormatException('No complete sample.');
    final values = last['values'] as Map;
    for (final root in List<String>.from(last['rootChildren'] as List)) {
      final bankCount = values.keys
          .where((p) => (p as String).startsWith('$root/AvailableModels['))
          .length;
      for (var bank = 0; bank <= bankCount; bank++) {
        final page = await client.readConfigurationPage(root, bank);
        if (page == null)
          throw const FormatException(
              'Read-only configuration page unavailable.');
        pages.add({'root': root, 'modelOrdinal': bank, 'page': page});
      }
    }
    // Detail reads exercise the same row planner without renewing station age.
    final details = paths
        .where((p) =>
            p.contains('/SequenceSteps[') ||
            p.contains('/SequenceAnnotations['))
        .toList();
    if (details.isNotEmpty) {
      final sample = await client.readDataValues(details);
      if (sample['protocol'] != 'fraktal.opcua.read-values.v1')
        throw const FormatException('Targeted quality envelope differs.');
      snapshots.add({'qualificationDetail': true, ...sample});
    }
  } on Object catch (error) {
    failure = error;
  } finally {
    await client?.close();
  }
  final report = {
    'schema': 'fraktal.ab.s4b-dart-canonical-qualification',
    'readOnly': true,
    'passed': failure == null,
    'error': failure?.toString(),
    'elapsedMs': clock.elapsedMilliseconds,
    'samples': rows,
    'snapshots': snapshots,
    'configurationPages': pages,
    'serial': endpoint.queryParameters['serial'],
    'writes': 0,
    'observationFrameDependency': false
  };
  await output.create(exclusive: true);
  await output.writeAsBytes(gzip.encode(utf8.encode(jsonEncode(report))));
  stdout.writeln(jsonEncode({
    'passed': failure == null,
    'error': failure?.toString(),
    'samples': rows.length,
    'configurationPages': pages.length
  }));
  if (failure != null) exitCode = 1;
}
