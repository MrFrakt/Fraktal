// Commanding probe: login + setMode transactions over the connected CIP
// transport. Usage: dart run tool/probe_cip_write.dart [host] [mode]
// (E_Mode ordinal, e.g. 2 = MANUAL on the press declaration.)
//
// The access gates refuse anonymous commands (std.error.accessDenied), so
// the probe logs in first. Credentials come from --login <user> <pin> or
// the local fixture file C:/work/fraktal_echo38_access_fixture.json —
// never from committed code.
//
// Races: another client (the live HMI) commits mailbox requests every few
// seconds and the shared mailbox is one-writer by contract, so the probe
// retries when a concurrent request overruns its response window. LOGIN
// completes asynchronously (257 SHA-256 rounds); its definitive result is
// AccessState.LoginResultSequence/CurrentLevel, never one HmiResponse
// sample.
//
// ignore_for_file: avoid_print
import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

import 'package:fraktal_opcua_client/src/opcua_session_client.dart';

import '../lib/data/cip/cip_session_client.dart';

int dint(Uint8List raw, int offset) =>
    ByteData.sublistView(raw).getInt32(offset, Endian.little);

bool later(int a, int b) => ((a - b) & 0xFFFFFFFF) > 0 && ((a - b) & 0xFFFFFFFF) < 0x80000000;

Future<void> main(List<String> args) async {
  final host = args.isNotEmpty ? args[0] : '127.0.0.1';
  final mode = args.length > 1 ? int.parse(args[1]) : 2;
  final client = await CipSessionClient.connect(host: host);
  try {
    Future<int> mailboxSequence() async {
      final raw = await client.client.connectedRead('FRK_Press_HmiRequest.Sequence');
      return dint(raw, 0);
    }

    Future<(int, int, int)> accessState() async {
      final raw = await client.readRawConnected('FRK_Press_AccessState');
      const o = 6; // addSize(2) + type(2) + instance(2)
      return (dint(raw, o + 4), dint(raw, o + 12), dint(raw, o + 8 + 4 * (6 + 12) + 32 + 12));
    }

    Future<(int, int, int)> response() async {
      final raw = await client.readRawConnected('FRK_Press_HmiResponse');
      const o = 6;
      return (dint(raw, o + 0), dint(raw, o + 4), dint(raw, o + 8));
    }

    Future<bool> commit(List<(String, OpcUaWriteType, Object)> writes) async {
      for (final (path, type, value) in writes) {
        if (!await client.write(path, type, value)) {
          print('  write refused: $path');
          return false;
        }
      }
      return true;
    }

    // LOGIN: poll the access state's result sequence — the hash needs 257
    // scans, so the wait is seconds, not milliseconds.
    var login = args.length > 3 && args[2] == '--login'
        ? (args[3], args[4])
        : null;
    if (login == null) {
      try {
        final fixture = await File('C:/work/fraktal_echo38_access_fixture.json')
            .readAsString();
        final users = (jsonDecode(fixture)['users'] as List).cast<Map>();
        if (users.isNotEmpty) {
          login = (users.first['user'] as String, users.first['pin'] as String);
        }
      } on Object {
        // No local fixture: proceed anonymous and report the refusal.
      }
    }
    // An existing session (a previous probe's login) skips the hash.
    final (currentLevel, _, __) = await accessState();
    if (currentLevel > 0) {
      print('session already live at level $currentLevel, skipping login');
      login = null;
    }
    if (login != null) {
      final (user, pin) = login;
      final seq = (await mailboxSequence()) + 1 & 0xFFFFFFFF;
      print('LOGIN $user (sequence $seq)...');
      if (!await commit([
        ('Press/HmiRequest/Kind', OpcUaWriteType.int32, 1), // LOGIN
        ('Press/HmiRequest/User', OpcUaWriteType.string, user),
        ('Press/HmiRequest/Secret', OpcUaWriteType.string, pin),
        ('Press/HmiRequest/Sequence', OpcUaWriteType.uint32, seq),
      ])) {
        return;
      }
      int level = -1, failed = -1;
      final deadline = DateTime.now().add(const Duration(seconds: 25));
      while (DateTime.now().isBefore(deadline)) {
        await Future.delayed(const Duration(milliseconds: 200));
        final (current, loginFailed, resultSeq) = await accessState();
        if (resultSeq == seq) {
          level = current;
          failed = loginFailed;
          break;
        }
      }
      if (level < 0) {
        print('LOGIN: no result within 12 s (result sequence never matched)');
        return;
      }
      if (level == 0) {
        print('LOGIN: refused by the controller (LoginFailed=$failed)');
        return;
      }
      print('LOGIN: accepted, session level $level');
    }

    // SET_MODE: arguments first, commit word last. A concurrent client's
    // request can overrun the response window — retry with a fresh sequence.
    for (var attempt = 1; attempt <= 3; attempt++) {
      final seq = (await mailboxSequence()) + 1 & 0xFFFFFFFF;
      print('SET_MODE $mode (sequence $seq, attempt $attempt)...');
      if (!await commit([
        ('Press/HmiRequest/Kind', OpcUaWriteType.int32, 3), // SET_MODE
        ('Press/HmiRequest/TargetPath', OpcUaWriteType.string, 'Press'),
        ('Press/HmiRequest/IntValue', OpcUaWriteType.int32, mode),
        ('Press/HmiRequest/BoolValue', OpcUaWriteType.boolean, false),
        ('Press/HmiRequest/DurationMs', OpcUaWriteType.int32, 0),
        ('Press/HmiRequest/Sequence', OpcUaWriteType.uint32, seq),
      ])) {
        return;
      }
      final deadline = DateTime.now().add(const Duration(seconds: 3));
      var settled = false;
      while (DateTime.now().isBefore(deadline)) {
        await Future.delayed(const Duration(milliseconds: 120));
        final (ack, accepted, diagnostic) = await response();
        if (later(ack, seq)) {
          break; // a later request won the window; retry the transaction
        }
        if (ack == seq && (accepted != 0 || diagnostic != 0)) {
          final unit = await client.client.connectedRead('FRK_Press_Unit.Mode');
          print('SET_MODE: accepted=${accepted != 0} '
              'diagnosticKey=$diagnostic mode=${dint(unit, 0)}');
          return;
        }
      }
      if (!settled) {
        final (ack, _, _) = await response();
        if (!later(ack, seq) && ack != seq) {
          continue; // window expired without an answer; retry
        }
      }
    }
    print('SET_MODE: no settled response after 3 attempts (mailbox contention)');
    exitCode = 2;
  } finally {
    await client.close();
  }
}
