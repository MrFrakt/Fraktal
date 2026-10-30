import 'dart:convert';
import 'dart:io';

import 'package:fraktal_opcua_client/src/cip_read_pool.dart';
import 'package:fraktal_opcua_client/src/cip_session_client.dart';

Future<void> main(List<String> args) async {
  final endpoint = Uri.parse(args[0]), output = File(args[1]);
  if (endpoint.scheme != 'cip' ||
      endpoint.host != '127.0.0.1' ||
      !endpoint.hasPort ||
      endpoint.port == 44818 ||
      output.existsSync()) {
    throw ArgumentError('Only a fresh local rehearsal endpoint is permitted.');
  }
  final wire = await CipReadPool.connect(
    host: endpoint.host,
    port: endpoint.port,
    expectSerial: '601FC87B',
  );
  final outcomes = <Map<String, Object?>>[];
  try {
    final engine = await CipSessionEngine.discover(wire), plan = engine.plan;
    final roots = plan.publication.roots.toList()..sort();
    final prefix = '${roots.first}/Status';
    final selected = <String>{
      for (final key in ['Name', 'ModuleType', 'State', 'ConfigRev', 'TypeKey'])
        if (plan.publication.fields.containsKey('$prefix/$key')) '$prefix/$key',
    };
    if (!await plan.proveProgress())
      throw StateError('Publisher not progressing.');
    for (var i = 0; i < 1000; i++) {
      final clock = Stopwatch()..start();
      await plan.acquire(paths: selected);
      final sample = plan.snapshot(), data = sample['dataValues'] as Map;
      final good = selected.every((p) => (data[p] as Map?)?['status'] == 0);
      outcomes.add({
        'index': i,
        'good': good,
        'elapsedUs': clock.elapsedMicroseconds,
        'acquisition': plan.acquisitions.last,
        if (!good) 'dataValues': data,
      });
      if (!good) break;
    }
    await output.create(exclusive: true);
    await output.writeAsBytes(
      gzip.encode(
        utf8.encode(
          jsonEncode({
            'measurementComplete': true,
            'readOnly': true,
            'controllerAccess': false,
            'controllerChanges': 0,
            'nativeAcceptanceClaim': false,
            'paths': selected.toList(),
            'maxAttempts': plan.guard.maxAttempts,
            'timeoutUs': plan.guard.timeout.inMicroseconds,
            'outcomes': outcomes,
          }),
        ),
      ),
    );
    stdout.writeln(
      jsonEncode({
        'measurementComplete': true,
        'samples': outcomes.length,
        'firstRefused': outcomes.last['good'] == false
            ? outcomes.last['index']
            : null,
      }),
    );
  } finally {
    await wire.close();
  }
}
