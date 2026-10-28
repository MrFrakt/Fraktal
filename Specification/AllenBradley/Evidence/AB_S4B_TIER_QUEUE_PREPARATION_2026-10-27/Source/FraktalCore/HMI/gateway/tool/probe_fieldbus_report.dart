// Commissioning report for the fieldbus node-state pipeline. Prints, side by
// side, the RAW bytes the EtherCAT master returned, how this library decoded
// them, and what ended up published per topology node — so a disagreement with
// XAE is attributable to hardware, indexing, or decode rather than guessed at.
//
//   dart run tool/probe_fieldbus_report.dart <amsNetId> [amsPort]
//   dart run tool/probe_fieldbus_report.dart 5.132.128.188.1.1 851
//
// Needs fraktal_ads.dll in the CWD (the gateway dir). Paste the whole output.
import 'dart:io';

import 'package:fraktal_opcua_client/fraktal_opcua_client.dart';

const _alState = {
  0x01: 'INIT',
  0x02: 'PREOP',
  0x03: 'BOOTSTRAP',
  0x04: 'SAFEOP',
  0x08: 'OP',
};
const _nodeState = {
  0: 'OFFLINE',
  1: 'INIT',
  2: 'PREOP',
  3: 'SAFEOP',
  4: 'OPERATIONAL',
  5: 'FAULT',
};

String _hex(Object? v) {
  final n = (v is num) ? v.toInt() : 0;
  return '0x${n.toRadixString(16).padLeft(2, '0').toUpperCase()}';
}

/// Decodes a deviceState byte the same way the PLC library does, so the report
/// shows whether the PLC's own decode agrees with an independent reading.
String _decodeDevice(Object? v) {
  final n = (v is num) ? v.toInt() : 0;
  if (n == 0) return 'no data (zero)';
  final flags = <String>[
    if (n & 0x10 != 0) 'ERROR',
    if (n & 0x20 != 0) 'INVALID_VPRS',
    if (n & 0x40 != 0) 'INITCMD_ERROR',
    if (n & 0x80 != 0) 'DISABLED',
  ];
  final al = _alState[n & 0x0F] ?? 'AL?(${(n & 0x0F)})';
  return flags.isEmpty ? al : '$al + ${flags.join('+')}';
}

String _decodeLink(Object? v) {
  final n = (v is num) ? v.toInt() : 0;
  if (n == 0) return 'OK';
  return <String>[
    if (n & 0x01 != 0) 'NOT_PRESENT',
    if (n & 0x02 != 0) 'LINK_WITHOUT_COMM',
    if (n & 0x04 != 0) 'MISSING_LINK',
    if (n & 0x08 != 0) 'ADDITIONAL_LINK',
  ].join('+');
}

Object? _pick(Map<String, Object?> v, String suffix) {
  for (final e in v.entries) {
    if (e.key.endsWith(suffix)) return e.value;
  }
  return null;
}

/// Reads `Diag*[i]`, tolerating both `Name/1` and `Name[1]` array spellings.
Object? _elem(Map<String, Object?> v, String name, int i) =>
    _pick(v, '/$name/$name[$i]') ??
    _pick(v, '/$name[$i]') ??
    _pick(v, '/$name/$i');

Future<void> main(List<String> args) async {
  if (args.isEmpty) {
    stderr.writeln('usage: dart run tool/probe_fieldbus_report.dart '
        '<amsNetId> [amsPort]');
    exitCode = 64;
    return;
  }
  final netId = args[0];
  final port = args.length > 1 ? int.parse(args[1]) : 851;

  final client = await AdsSessionClient.connect(amsNetId: netId, amsPort: port);
  try {
    // Two snapshots a moment apart: DiagScanCount must advance if the scanner is
    // actually running. A frozen count is itself the answer.
    final first = await client.snapshot();
    await Future<void>.delayed(const Duration(milliseconds: 1200));
    final second = await client.snapshot();
    final v1 = Map<String, Object?>.from(first['values'] as Map? ?? {});
    final v = Map<String, Object?>.from(second['values'] as Map? ?? {});

    stdout.writeln('=' * 78);
    stdout.writeln('FRAKTAL FIELDBUS REPORT   target ads://$netId:$port');
    stdout.writeln('=' * 78);

    stdout.writeln('\n-- read health -------------------------------------------');
    for (final k in [
      'ReadOk',
      'LastErrorId',
      'SlavesReported',
      'CountMismatch',
      'NetIdMissing',
      'MasterNetId',
      'DiagScanRequested',
      'DiagFirstScanDone',
      'DiagBufferBytes',
      'DiagEntrySize',
    ]) {
      stdout.writeln('  ${k.padRight(20)} ${_pick(v, '/$k')}');
    }
    final c1 = _pick(v1, '/DiagScanCount');
    final c2 = _pick(v, '/DiagScanCount');
    final advancing = (c1 is num && c2 is num) ? (c2 > c1) : false;
    stdout.writeln('  ${'DiagScanCount'.padRight(20)} $c1 -> $c2  '
        '${advancing ? "(SCANNING)" : "(NOT ADVANCING - scanner parked/stuck)"}');

    stdout.writeln('\n-- what the MASTER returned, and how it was decoded -------');
    stdout.writeln('  slot  rawDevice  meaning              rawLink  link      '
        '-> node  decoded');
    for (var i = 1; i <= 8; i++) {
      final dev = _elem(v, 'DiagRawDeviceState', i);
      final link = _elem(v, 'DiagRawLinkState', i);
      final node = _elem(v, 'DiagNodeIndex', i);
      final dec = _elem(v, 'DiagDecodedState', i);
      if (dev == null && node == null) continue;
      if ((node is num) && node.toInt() == 0) continue;
      final decName =
          (dec is num) ? (_nodeState[dec.toInt()] ?? '$dec') : '$dec';
      stdout.writeln('  ${i.toString().padLeft(4)}  '
          '${_hex(dev).padRight(9)}  ${_decodeDevice(dev).padRight(20)} '
          '${_hex(link).padRight(7)}  ${_decodeLink(link).padRight(9)} '
          '-> ${node.toString().padLeft(4)}  $decName');
    }

    stdout.writeln('\n-- what is PUBLISHED per topology node --------------------');
    final count = _pick(v, '/Topology/NodeCount');
    stdout.writeln('  NodeCount = $count');
    for (var i = 1; i <= 8; i++) {
      final name = _elem(v, 'Nodes', i) ??
          _pick(v, '/Topology/Nodes/Nodes[$i]/Name') ??
          _pick(v, '/Topology/Nodes[$i]/Name');
      final st = _pick(v, '/Topology/Nodes/Nodes[$i]/State') ??
          _pick(v, '/Topology/Nodes[$i]/State');
      final lk = _pick(v, '/Topology/Nodes/Nodes[$i]/LinkOk') ??
          _pick(v, '/Topology/Nodes[$i]/LinkOk');
      if (name == null && st == null) continue;
      final stName = (st is num) ? (_nodeState[st.toInt()] ?? '$st') : '$st';
      stdout.writeln('  node ${i.toString().padLeft(2)}  '
          '${name.toString().padRight(20)} state=${stName.padRight(12)} '
          'linkOk=$lk');
    }

    stdout.writeln('\n-- interpretation ----------------------------------------');
    stdout.writeln('  If rawDevice is 0x08 (OP) but the node shows INIT, the bug');
    stdout.writeln('  is in this library. If rawDevice is 0x01 (INIT) while XAE');
    stdout.writeln('  shows OP, the PLC is reading a different master/target than');
    stdout.writeln('  the XAE window is showing.');
    stdout.writeln('=' * 78);
  } finally {
    await client.close();
  }
}
