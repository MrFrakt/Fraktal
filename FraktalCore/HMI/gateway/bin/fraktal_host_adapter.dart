/// The Fraktal/AB V6.11 host adapter, one process per controller instance.
///
/// It answers the jobs the controller opens on its host-service ingress and
/// keeps and restores its live documents, from published facts alone. Every
/// failure is reported on stdout as one JSON line; discovery is repeated after
/// a pause, and nothing the controller did not acknowledge is ever resent.
library;

import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:fraktal_gateway/host_adapter.dart';
import 'package:fraktal_opcua_client/cip_host_service.dart';

const _usage = '''
fraktal_host_adapter --host ADDRESS --expect-serial XXXXXXXX [options]

  --host ADDRESS          controller address (required)
  --port N                EtherNet/IP port (default 44818)
  --slot N                controller slot (default 0)
  --expect-serial HEX     exact eight-hex controller serial (required)
  --interval-ms N         milliseconds between reply polls (default 20)
  --once                  answer one round, print health, exit
''';

Future<void> main(List<String> arguments) async {
  final options = <String, String>{}, flags = <String>{};
  for (var i = 0; i < arguments.length; i++) {
    final a = arguments[i];
    if (a == '--once' || a == '--help') {
      flags.add(a);
    } else if (a.startsWith('--') && i + 1 < arguments.length) {
      options[a] = arguments[++i];
    } else {
      stderr.write(_usage);
      exit(64);
    }
  }
  final host = options['--host'], serial = options['--expect-serial'];
  final port = int.tryParse(options['--port'] ?? '44818'),
      slot = int.tryParse(options['--slot'] ?? '0'),
      interval = int.tryParse(options['--interval-ms'] ?? '20');
  if (flags.contains('--help') ||
      host == null ||
      serial == null ||
      !RegExp(r'^[0-9A-Fa-f]{8}$').hasMatch(serial) ||
      port == null ||
      port < 1 ||
      port > 65535 ||
      slot == null ||
      slot < 0 ||
      slot > 255 ||
      interval == null ||
      interval < 1) {
    stderr.write(_usage);
    exit(64);
  }
  void report(Map<String, Object?> line) => stdout.writeln(jsonEncode(
      {'utc': DateTime.now().toUtc().toIso8601String(), ...line}));
  while (true) {
    List<CipHostIngress> ports = const [];
    // Discovery walks the whole namespace. After an error (a lost link, a
    // download in progress) it is retried soon; a controller that serves no
    // host services is only looked at again once a minute.
    var pause = const Duration(seconds: 5);
    try {
      ports = await cipHostDiscover(
          host: host, port: port, slot: slot, expectSerial: serial.toUpperCase());
      if (ports.isEmpty) {
        report({'state': 'no host services'});
        if (flags.contains('--once')) return;
        pause = const Duration(minutes: 1);
      } else {
        final services = [
          for (final p in ports)
            RootService(
                p,
                FileStore(directoryFor(p.root, serial.toUpperCase())),
                p.rows.containsKey(CipHost.liveDocuments)
                    ? FileMedium(Directory(
                        '${directoryFor(p.root, serial.toUpperCase()).path}${Platform.pathSeparator}live'))
                    : null)
        ];
        report({'state': 'serving', 'roots': [for (final p in ports) p.root]});
        final last = <String, String>{};
        while (true) {
          for (final service in services) {
            await service.step();
            final health = jsonEncode(service.health.toJson());
            if (last[service.port.root] != health) {
              last[service.port.root] = health;
              report({'root': service.port.root, 'health': service.health.toJson()});
            }
          }
          if (flags.contains('--once')) return;
          await Future<void>.delayed(Duration(milliseconds: interval));
        }
      }
    } on Object catch (error) {
      report({'state': 'unavailable', 'error': '$error'});
      if (flags.contains('--once')) exit(1);
    } finally {
      for (final p in ports) {
        await p.close();
      }
    }
    await Future<void>.delayed(pause);
  }
}
