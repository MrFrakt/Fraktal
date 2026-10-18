@Tags(['live'])
library;

// Live command proof via the PRODUCTION code path the desktop HMI uses:
// ConnectionSettings(wss://) -> createExternalRepository -> IoGatewayOpcUaClient
// -> OpcUaRepository -> HmiRequest mailbox on a real Logix controller.
//
// This WRITES to a controller. It is run only against the bench test controller
// (serial 7036B510) with nothing wired to it, and the gateway re-checks that
// serial immediately before every write. Each command is proved by reading the
// controller's own acknowledgement back, never by trusting that a write
// returned true.
//
//   # gateway (venv with pylogix + websockets), token from the environment:
//   export FRAKTAL_GATEWAY_WRITE_TOKEN=...
//   python fraktal_ab_gateway.py 192.168.100.89 --expect-serial 7036B510 \
//       --tls-cert cert.pem --tls-key key.pem
//   # HMI side - wss, because a client will not send a bearer over plaintext:
//   export FRAKTAL_GATEWAY_BEARER_TOKEN=...   # same value
//   export FRAKTAL_WSS_TRUSTED_CA=cert.pem
//   flutter test --run-skipped -t live test/live_ab_command_test.dart

import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:fraktal_hmi/data/external_repository_factory_native.dart';
import 'package:fraktal_hmi/data/opcua_gateway_client_io.dart';
import 'package:fraktal_hmi/domain/connection_settings.dart';
import 'package:fraktal_hmi/domain/types.dart';

const _unit = 'Press';
const _seqPath = '$_unit/HmiRequest/Sequence';
const _ackPath = '$_unit/HmiResponse/AckSequence';
const _acceptedPath = '$_unit/HmiResponse/Accepted';
const _diagPath = '$_unit/HmiResponse/Diagnostic';
const _modePath = '$_unit/ModeActivePublished';

void _line(String text) {
  // ignore: avoid_print
  print(text);
}

/// A second, read-only session used to read the controller's answer back. The
/// repository owns its own socket; this keeps the observation independent of
/// the thing being observed.
class _Observer {
  final IoGatewayOpcUaClient _client;

  _Observer(this._client);

  static Future<_Observer> connect(Uri endpoint) async => _Observer(
        await IoGatewayOpcUaClient.connect(
          endpoint,
          security: IoGatewaySecurityOptions(
            trustedCaPath: Platform.environment['FRAKTAL_WSS_TRUSTED_CA'] ?? '',
          ),
        ),
      );

  Future<Map<String, Object?>> mailbox() => _client.readValues(
      const [_seqPath, _ackPath, _acceptedPath, _diagPath, _modePath]);

  Future<void> close() => _client.close();
}

void main() {
  test('ab mailbox: the generic HMI commands a live Allen-Bradley press',
      () async {
    final endpoint = Platform.environment['FRAKTAL_AB_GATEWAY'] ??
        'wss://127.0.0.1:8080/fraktal';
    _line('AB gateway endpoint: $endpoint');
    expect(Platform.environment['FRAKTAL_GATEWAY_BEARER_TOKEN'] ?? '',
        isNotEmpty,
        reason: 'the §14 gate needs a bearer; without it every write is refused');

    final repo = await createExternalRepository(ConnectionSettings(
      transport: ConnectionTransport.gateway,
      endpoint: endpoint,
    ));
    addTearDown(repo.dispose);
    final observer = await _Observer.connect(Uri.parse(endpoint));
    addTearDown(observer.close);

    final forest = await repo
        .forest()
        .firstWhere((f) => f.isNotEmpty)
        .timeout(const Duration(seconds: 15));
    final root = forest.first;
    _line('rendering: ${root.path} mode=${root.modeActive?.name} '
        'state=${root.state.name} children=${root.children.length}');

    final before = await observer.mailbox();
    _line('mailbox as found: seq=${before[_seqPath]} ack=${before[_ackPath]} '
        'accepted=${before[_acceptedPath]} diag="${before[_diagPath]}"');

    /// Issue one command and read the controller's own answer back.
    Future<Map<String, Object?>> issue(
      String label,
      Future<bool> Function() command, {
      required bool expectAccepted,
      String? expectDiagnostic,
    }) async {
      final returned = await command();
      final after = await observer.mailbox();
      _line('$label -> returned=$returned seq=${after[_seqPath]} '
          'ack=${after[_ackPath]} accepted=${after[_acceptedPath]} '
          'diag="${after[_diagPath]}"');
      // The ack is the proof, not the return value: a matching AckSequence is
      // the controller saying it consumed THIS request and the whole answer is
      // present.
      expect(after[_ackPath], after[_seqPath],
          reason: '$label: the controller must acknowledge this sequence');
      expect(after[_acceptedPath], expectAccepted,
          reason: '$label: Accepted must be $expectAccepted');
      expect(returned, expectAccepted,
          reason: '$label: the HMI must report what the controller decided');
      if (expectDiagnostic != null) {
        expect(after[_diagPath], expectDiagnostic,
            reason: '$label: the refusal must name its reason');
      }
      return after;
    }

    _line('\n=== the six kinds this binding routes ===');
    final manual = await issue('SET_MODE(manual)',
        () => repo.setMode(_unit, UnitMode.manual),
        expectAccepted: true);
    expect(manual[_modePath], UnitMode.manual.index,
        reason: 'the mode the operator asked for must be the mode published');

    await issue('START', () => repo.start(_unit), expectAccepted: true);
    await issue('STOP', () => repo.stop(_unit), expectAccepted: true);
    await issue('OPERATOR_RESET', () => repo.operatorReset(_unit),
        expectAccepted: true);
    await issue('DECISION_ANSWER(1)', () => repo.setDecisionAnswer(_unit, 1),
        expectAccepted: true);
    await issue('MANUAL_COMMAND(unaddressed)',
        () => repo.manualCommand(_unit, '', 1),
        expectAccepted: true);

    _line('\n=== refusals: named, not silent and not falsely accepted ===');
    // LAMP_TEST is refused because this press has no signal tower. The HMI must
    // render the reason rather than report a success it did not get.
    await issue('LAMP_TEST (refused)', () => repo.lampTest(_unit),
        expectAccepted: false,
        expectDiagnostic: 'project.mailbox.refused.no_signal_tower');

    // An addressed manual command cannot be honoured: the declared manual chain
    // jogs one module, and jogging the wrong one is worse than refusing.
    await issue('MANUAL_COMMAND(addressed) (refused)',
        () => repo.manualCommand(_unit, 'Press.PressRam', 1),
        expectAccepted: false,
        expectDiagnostic: 'project.mailbox.refused.target_not_addressable');

    // A mode the oracle defines but this application never declared is refused
    // by name rather than clamped into AUTO.
    await issue('SET_MODE(changeover) (refused)',
        () => repo.setMode(_unit, UnitMode.changeover),
        expectAccepted: false,
        expectDiagnostic: 'project.mailbox.refused.mode_not_declared');

    _line('\n=== restore the bench to AUTO ===');
    final restored = await issue('SET_MODE(auto)',
        () => repo.setMode(_unit, UnitMode.auto),
        expectAccepted: true);
    expect(restored[_modePath], UnitMode.auto.index);

    // Every request got its own sequence, and the controller answered each one
    // exactly once: the final ack is well past where it started.
    expect((restored[_ackPath] as num).toInt(),
        greaterThan((before[_ackPath] as num).toInt()),
        reason: 'the mailbox must have advanced across this run');
  }, timeout: const Timeout(Duration(minutes: 3)));
}
