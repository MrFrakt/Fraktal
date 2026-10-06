@Tags(['live'])
library;

// Live end-to-end via the PRODUCTION code path the desktop HMI uses:
// ConnectionSettings(ws://) -> createExternalRepository -> IoGatewayOpcUaClient
// -> OpcUaRepository -> forest. The gateway on the other end is
// FraktalCore/PLC/Allen-Bradley/tools/fraktal_ab_gateway.py serving the
// fraktal_ab_projection of a live Logix controller. Read-only: this test issues
// no command; the gateway would refuse one anyway.
//
//   # in one shell, with the AB venv (pylogix + websockets):
//   python fraktal_ab_gateway.py 192.168.100.89 --expect-serial 7036B510
//   # in another:
//   flutter test --run-skipped -t live test/live_ab_gateway_test.dart
//
// Override the endpoint with FRAKTAL_AB_GATEWAY (e.g. a bench host running the
// gateway). Records what the generic HMI renders and what it shows as absent.

import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:fraktal_hmi/data/external_repository_factory_native.dart';
import 'package:fraktal_hmi/domain/connection_settings.dart';
import 'package:fraktal_hmi/domain/module_node.dart';
import 'package:fraktal_hmi/domain/types.dart';

void _line(String text) {
  // ignore: avoid_print
  print(text);
}

void main() {
  test('ab gateway: the generic HMI renders a live Allen-Bradley controller',
      () async {
    final endpoint = Platform.environment['FRAKTAL_AB_GATEWAY'] ??
        'ws://127.0.0.1:8080/fraktal';
    _line('AB gateway endpoint: $endpoint');

    final repo = await createExternalRepository(ConnectionSettings(
      transport: ConnectionTransport.gateway,
      endpoint: endpoint,
    ));
    addTearDown(repo.dispose);

    final forest = await repo
        .forest()
        .firstWhere((f) => f.isNotEmpty)
        .timeout(const Duration(seconds: 15));

    void dump(ModuleNode n, [String indent = '']) {
      final unit = n.isUnit
          ? ' mode=${n.modeActive?.name} good=${n.goodCount} nok=${n.nokCount}'
              ' step=${n.step?.stepNo ?? '-'}'
              ' stepElapsedMs=${n.currentStepElapsed.inMilliseconds}'
              ' timedOut=${n.currentStepTimedOut}'
          : ' reason=${n.message}';
      _line('$indent- ${n.path}  type=${n.type.name} state=${n.state.name}'
          ' fault=${n.faultActive}$unit  tile=${n.tileEnable}');
      for (final child in n.children) {
        dump(child, '$indent  ');
      }
    }

    _line('=== module tree the operator sees ===');
    for (final root in forest) {
      dump(root);
    }

    final root = forest.first;
    expect(root.isUnit, isTrue, reason: 'the press is the root Unit');
    expect(root.children.length, 3,
        reason: 'the press has three control modules');
    final childNames = root.children.map((c) => c.name).toSet();
    expect(childNames, {'Door', 'PartSlide', 'PressRam'});
    for (final child in root.children) {
      expect(child.type, ModuleType.controlModule);
    }
    // A count that survives a positive read: the tile is enabled because the
    // projection does not zero-fill absent keys (a missing TileEnable defaults
    // true), which is exactly why the absent surfaces below must be named.
    expect(root.tileEnable, isTrue);

    _line('=== what the binding does not publish (honest absence) ===');
    _line('supportedModes=${root.supportedModes.map((m) => m.name).toList()}');
    _line('commands=${root.commands.length} '
        'availableModels=${root.availableModels} '
        'activeEvents=${root.activeEvents.length} '
        'ringEvents=${root.ringEvents.length} '
        'hostEvents=${root.hostEvents.length}');
    _line('access level=${root.access?.level.name} user="${root.access?.user}" '
        'oee=${root.oee} nameplate=${root.nameplate} '
        'cycle=${root.cycle} controlPower=${root.controlPower}');
    for (final child in root.children) {
      _line('${child.path}: ioTag="${child.diagnosticIoTag}" '
          'ioAddress="${child.diagnosticIoAddress}" '
          'commands=${child.commands.length}');
    }

    // Most absent surfaces render as genuine nothing - the honest result. Each
    // assertion is the paired negative of a real key the mapper would populate.
    expect(root.commands, isEmpty,
        reason: 'no §7.6.1 manual-command catalog is published');
    expect(root.availableModels, isEmpty, reason: 'recipes are deferred');
    expect(root.activeEvents, isEmpty, reason: 'the event core is owed work');
    expect(root.hostEvents, isEmpty, reason: 'host events are not published');
    expect(root.oee, isNull, reason: 'OEE is not published');
    expect(root.nameplate, isNull, reason: 'no nameplate is declared');
    for (final child in root.children) {
      expect(child.diagnosticIoTag, isEmpty,
          reason: 'the press demo declares no physical I/O');
    }

    // FINDING (silence renders as data). Two surfaces the projection does not
    // publish are synthesized into defaults by the mapper rather than left
    // blank, so they render as data an operator could misread:
    //  1. No §3.7 _M_Supports set is published, so the mapper offers only the
    //     ACTIVE mode. The mode picker shows just the current mode, not the
    //     controller's real AUTO/MANUAL/HOME set.
    //  2. The mapper always builds an AccessSession, so a binding that publishes
    //     no Access/* still shows a default logged-out session, not a blank
    //     panel. Recorded for a publish-vs-handle-absence decision; not changed
    //     here, since that is a scope call for the user, not a bug to paper over.
    expect(root.supportedModes, [root.modeActive],
        reason: 'lacking _M_Supports, only the active mode is offered');
    expect(root.access, isNotNull,
        reason: 'the mapper synthesizes a default access session');
    expect(root.access!.level, AccessLevel.none,
        reason: 'the synthesized session is logged out');

    _line('=== live scalar mode ordinal (Core E_Mode, published verbatim) ===');
    _line('Press ModeActivePublished ordinal via modeActive index='
        '${root.modeActive?.index}  '
        '(0=AUTO,1=MANUAL,2=HOME under corrected E_Mode; the loaded bench '
        'build may pre-date that correction — confirm before reading meaning)');
  });
}
