// Dumps the live alarm/reset state of a Unit: why a latched fault will not clear.
// Prints the AlarmLog active list (state/reset class/reason per slot), Blocking,
// every module Error/State/ErrorID, and the Start release report reasons, with
// FULL published paths so the owning module of each record stays visible.
//   dart run tool/probe_alarm_state.dart <amsNetId> [port] [pathFilter]
import 'dart:io';
import 'package:fraktal_opcua_client/fraktal_opcua_client.dart';

/// E_AlarmState / E_ResetClass / E_ExecState ordinals are transport contract
/// (HMI lib/domain/types.dart mirrors the same Core DUTs).
const _alarmState = {0: 'CLOSED', 1: 'ACTIVE', 2: 'WAIT_RESET'};
const _resetClass = {0: 'AUTO_RESET', 1: 'MANUAL_RESET'};
const _execState = {
  0: 'READY',
  1: 'BUSY',
  2: 'DONE',
  3: 'ERROR',
  4: 'ABORTED',
};

/// Decode only where the enum is certain from the path. `State` is overloaded
/// across ST_ModuleStatus (E_ExecState), ST_AlarmEvent (E_AlarmState),
/// ST_IoNode (E_NodeState) and the safety-device facet, so a blanket
/// E_ExecState decode would print confident nonsense.
String _decode(String path, Object? value) {
  final leaf = path.split('/').last;
  if (value is! int) return '$value';
  if (leaf == 'State' && path.contains('Active[')) {
    return '$value (${_alarmState[value] ?? '?'})';
  }
  if (leaf == 'ResetClass') return '$value (${_resetClass[value] ?? '?'})';
  if (path.endsWith('/Status/State')) {
    return '$value (${_execState[value] ?? '?'})';
  }
  return '$value';
}

Future<void> main(List<String> a) async {
  if (a.isEmpty) {
    stderr.writeln(
        'usage: dart run tool/probe_alarm_state.dart <amsNetId> [port] [pathFilter]');
    exitCode = 2;
    return;
  }
  final filter = a.length > 2 ? a[2].toLowerCase() : '';
  final c = await AdsSessionClient.connect(
      amsNetId: a[0], amsPort: a.length > 1 ? int.parse(a[1]) : 851);
  try {
    final v = Map<String, Object?>.from(
        (await c.snapshot())['values'] as Map? ?? {});
    void show(String label, bool Function(String path) match) {
      stdout.writeln('-- $label');
      final hits = v.entries.where((e) =>
          match(e.key) && (filter.isEmpty || e.key.toLowerCase().contains(filter)));
      if (hits.isEmpty) {
        stdout.writeln('   <none published>');
        return;
      }
      for (final e in hits) {
        stdout.writeln('   ${e.key} = ${_decode(e.key, e.value)}');
      }
    }

    // Only slots that are not CLOSED matter; print the whole record for those.
    final openSlots = <String>{};
    for (final e in v.entries) {
      if (e.key.contains('Active[') &&
          e.key.endsWith('/State') &&
          e.value is int &&
          e.value != 0) {
        openSlots.add(e.key.substring(0, e.key.length - '/State'.length));
      }
    }
    show('alarm log summary',
        (p) => RegExp(r'/(Blocking|NActive|RingHead|Truncated)$').hasMatch(p));
    stdout.writeln('-- open alarm slots (State <> CLOSED)');
    if (openSlots.isEmpty) {
      stdout.writeln('   <none>');
    } else {
      for (final slot in openSlots) {
        for (final e in v.entries.where((e) => e.key.startsWith('$slot/'))) {
          stdout.writeln('   ${e.key} = ${_decode(e.key, e.value)}');
        }
        stdout.writeln('');
      }
    }
    show('module exec state / error latches',
        (p) =>
            RegExp(r'/(Error|ErrorID|MachineState)$').hasMatch(p) ||
            p.endsWith('/Status/State') ||
            p.endsWith('/Status/FaultActive'));
    // §6.1 handshake: whether the run command is still asserted decides if the
    // inherited Execute-drop reset can clear a latched ERROR at all.
    show(
        'PLCopen handshake surface',
        (p) => RegExp(r'/(Execute|Abort|Busy|Done|Aborted|Running|StopPending)$')
            .hasMatch(p));
    show('first-out diagnostics',
        (p) => p.contains('Diagnostic') || p.contains('Pending'));
    show('current step / release report',
        (p) => p.contains('CurrentStep') || p.contains('Report'));
  } finally {
    await c.close();
  }
}
