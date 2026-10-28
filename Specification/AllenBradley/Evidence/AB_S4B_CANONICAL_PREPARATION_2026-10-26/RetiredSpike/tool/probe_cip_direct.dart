// Gateway-less Fraktal/AB spike probe: snapshot over raw EtherNet/IP.
// Usage: dart run tool/probe_cip_direct.dart [host] [port]
//
// Imports the HMI's CIP session client by path so the probe runs without a
// package dependency.
import 'dart:async';

// ignore_for_file: avoid_print

import '../lib/data/cip/cip_session_client.dart';

Future<void> main(List<String> args) async {
  final host = args.isNotEmpty ? args[0] : '127.0.0.1';
  final port = args.length > 1 ? int.parse(args[1]) : 44818;
  final client = await CipSessionClient.connect(host: host, port: port);
  try {

    final raw = await client.readRawConnected('FRK_Press_MfHeader');
  print('MfHeader raw connected reply: ${raw.map((b) => b.toRadixString(16).padLeft(2, '0')).join(' ')}');
  final values = await client.snapshot();
    print('snapshot keys: ${values.length}');
    for (final key in values.keys.toList()..sort()) {
      if (key.contains('/Status/')) continue;
      print('  $key = ${values[key]}');
    }
    final statusKeys =
        values.keys.where((k) => k.endsWith('/Status/State')).toList()..sort();
    for (final key in statusKeys) {
      print('  $key = ${values[key]}');
    }
  } finally {
    await client.close();
  }
}
