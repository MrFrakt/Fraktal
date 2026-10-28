import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'package:fraktal_opcua_client/fraktal_opcua_client.dart';
import 'file:///C:/Users/SoftIndVM/Fraktal/FraktalCore/HMI/lib/data/opcua_field_tier.dart';

Future<void> main(List<String> args) async {
  if (args.length != 2) throw ArgumentError('Expected hash and new output required');
  final expected = args[0], output = File(args[1]);
  if (output.existsSync()) throw ArgumentError('New output required');
  final samples = <Map<String, Object?>>[], snapshots = <Map<String, Object?>>[];
  final clock = Stopwatch()..start();
  CipSessionClient? client;
  Object? failure;
  try {
    client = await CipSessionClient.connect(host: '127.0.0.1', slot: 0,
        expectSerial: '601FC87B');
    final paths = await client.discoverPaths(), slow = <String>{}, excluded = <String>{};
    for (final path in paths) {
      if (OpcUaFieldTier.isRequestPayload(path) ||
          path.split('/').any((s) => OpcUaFieldTier.unconsumedContainers.contains(s.split('[').first)) ||
          OpcUaFieldTier.classify(path) == FieldTier.onDemand) {
        excluded.add(path);
      } else if (OpcUaFieldTier.classify(path) == FieldTier.slow) {
        slow.add(path);
      }
    }
    await client.setSlowPaths(slow);
    await client.setExcludedPaths(excluded);
    for (var i = 0; i < 40 && clock.elapsed < const Duration(seconds: 120); i++) {
      final document = await client.snapshot();
      if (document['contentHash'] != expected) {
        throw StateError('Pinned publication changed; diagnostic stopped');
      }
      final data = document['dataValues'] as Map;
      final bad = <String, Object?>{}, uncertain = <String, Object?>{};
      for (final item in data.entries) {
        final row = item.value as Map;
        final severity = (row['status'] as int) & 0xc0000000;
        if (severity == 0x80000000) bad[item.key as String] = row;
        if (severity == 0x40000000) uncertain[item.key as String] = row;
      }
      samples.add({'sample': i, 'elapsedMs': clock.elapsedMilliseconds,
        'sampleAgeMs': document['sampleAgeMs'], 'responseProcessingMs': document['responseProcessingMs'],
        'bad': bad, 'uncertain': uncertain});
      if (i == 0 || bad.isNotEmpty || snapshots.length < 4 && uncertain.isNotEmpty) {
        snapshots.add(document);
      }
      if (bad.isNotEmpty) break;
      await Future<void>.delayed(const Duration(milliseconds: 250));
    }
  } on Object catch (error) {
    failure = error;
  } finally {
    await client?.close();
  }
  final report = {'schema': 'fraktal.ab.s4b-readonly-coherence-diagnostic',
    'readOnly': true, 'writes': 0, 'serial': '601FC87B', 'expectedHash': expected,
    'error': failure?.toString(), 'elapsedMs': clock.elapsedMilliseconds,
    'samples': samples, 'snapshots': snapshots};
  await output.create(exclusive: true);
  await output.writeAsBytes(gzip.encode(utf8.encode(jsonEncode(report))));
  stdout.writeln(jsonEncode({'readOnly': true, 'writes': 0, 'samples': samples.length,
    'error': failure?.toString(), 'lastBad': samples.isEmpty ? null : samples.last['bad']}));
  if (failure != null) exitCode = 1;
}
