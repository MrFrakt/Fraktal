@Tags(['live'])
library;

// Opt-in: the native HMI repository reaches a TIA station directly over the
// S7 Web API (s7web://), with no gateway. Set FRAKTAL_TIA_DIRECT_LIVE=1,
// FRAKTAL_TIA_DIRECT_ENDPOINT=s7web://<cpu>?pin=<sha256>, and the CPU web user
// in FRAKTAL_TIA_WEB_USER / FRAKTAL_TIA_WEB_PASSWORD (use the DPAPI wrapper;
// never type the password on a command line). Optional
// FRAKTAL_TIA_DIRECT_ROOT names a root Unit the forest must contain, and
// FRAKTAL_TIA_DIRECT_OUTPUT a fresh directory for the JSON record;
// FRAKTAL_TIA_DIRECT_EXPECT_LINE=1 also requires published Line configuration.
//
// Read-only unless FRAKTAL_TIA_DIRECT_COMMAND=1, which additionally switches
// that root to MANUAL and back to its starting mode through the mailbox, and
// requires the PLC's acknowledgement for each. Only enable it against an
// isolated simulator.
import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:fraktal_hmi/data/external_repository_factory_native.dart';
import 'package:fraktal_hmi/data/plc_repository.dart';
import 'package:fraktal_hmi/data/s7web_credentials.dart';
import 'package:fraktal_hmi/data/s7web_endpoint.dart';
import 'package:fraktal_hmi/domain/connection_settings.dart';
import 'package:fraktal_hmi/domain/fieldbus.dart';
import 'package:fraktal_hmi/domain/module_node.dart';
import 'package:fraktal_hmi/domain/types.dart';

void main() {
  final environment = Platform.environment;
  final live = environment['FRAKTAL_TIA_DIRECT_LIVE'] == '1';

  test('TIA direct: s7web:// repository discovers and refreshes the forest',
      () async {
    final endpoint = environment['FRAKTAL_TIA_DIRECT_ENDPOINT']!;
    final expectedRoot = environment['FRAKTAL_TIA_DIRECT_ROOT'] ?? '';
    final command = environment['FRAKTAL_TIA_DIRECT_COMMAND'] == '1';
    final record = <String, Object?>{'endpointScheme': Uri.parse(endpoint).scheme};
    final timer = Stopwatch()..start();
    final PlcRepository repository = await createExternalRepository(
        ConnectionSettings(
            transport: ConnectionTransport.gateway, endpoint: endpoint));
    record['connectMs'] = timer.elapsedMilliseconds;
    var forest = const <ModuleNode>[];
    final updates = <DateTime>[];
    final subscription = repository.forest().listen((nodes) {
      forest = nodes;
      updates.add(DateTime.now());
    });
    Future<void> until(bool Function() predicate, String what,
        {Duration timeout = const Duration(minutes: 2)}) async {
      final deadline = Stopwatch()..start();
      while (!predicate() && deadline.elapsed < timeout) {
        await Future<void>.delayed(const Duration(milliseconds: 100));
      }
      expect(predicate(), isTrue, reason: 'deadline: $what');
    }

    Iterable<ModuleNode> walk(List<ModuleNode> nodes) sync* {
      for (final node in nodes) {
        yield node;
        yield* walk(node.children);
      }
    }

    try {
      await until(() => forest.isNotEmpty, 'first forest');
      record['firstForestMs'] = timer.elapsedMilliseconds;
      final roots = [for (final root in forest) root.path];
      record['roots'] = roots;
      record['modules'] = walk(forest).length;
      if (expectedRoot.isNotEmpty) expect(roots, contains(expectedRoot));
      final seen = updates.length;
      await until(() => updates.length >= seen + 3, 'three refreshes');
      record['refreshes'] = updates.length;

      // FRAKTAL_TIA_DIRECT_EXPECT_LINE=1: the root publishes a Line owner's
      // configuration (§3.8e), hydrated from the config manifest.
      List<CfgField> lineFields() => [
            for (final root in forest)
              ...root.config.where((f) => f.kind == CfgKind.lineCfg)
          ];
      if (environment['FRAKTAL_TIA_DIRECT_EXPECT_LINE'] == '1') {
        await until(() => lineFields().isNotEmpty, 'line configuration');
      }
      record['lineConfigFields'] = lineFields().length;
      record['lineConfigSample'] =
          [for (final f in lineFields().take(6)) '${f.writeKey}=${f.value}'];

      // FRAKTAL_TIA_DIRECT_EXPECT_FIELDBUS=1: the station publishes a Core
      // §10.5.1 topology, read on demand exactly as the fieldbus page opens it.
      if (environment['FRAKTAL_TIA_DIRECT_EXPECT_FIELDBUS'] == '1') {
        expect(repository.fieldbusExpected, isTrue,
            reason: 'a topology DB was discovered');
        var bus = const <BusNode>[];
        final busSubscription =
            repository.fieldbus().listen((nodes) => bus = nodes);
        repository.setFieldbusViewActive(true);
        try {
          await until(() => bus.isNotEmpty, 'fieldbus tree');
          Iterable<BusNode> nodes(List<BusNode> level) sync* {
            for (final node in level) {
              yield node;
              yield* nodes(node.children);
            }
          }
          record['fieldbus'] = [
            for (final node in nodes(bus))
              {
                'name': node.name,
                'state': node.state.name,
                'linkOk': node.linkOk,
                'channels': node.channels.length,
                'sample': [
                  for (final c in node.channels.take(3))
                    '${c.name} ${c.address} -> ${c.modulePath}'
                ],
              }
          ];
        } finally {
          repository.setFieldbusViewActive(false);
          await busSubscription.cancel();
        }
      }

      if (command) {
        final rootPath = expectedRoot.isNotEmpty ? expectedRoot : roots.first;
        ModuleNode root() => forest.singleWhere((n) => n.path == rootPath);
        final startMode = root().modeActive;
        record['startMode'] = startMode?.name;
        final target =
            startMode == UnitMode.manual ? UnitMode.auto : UnitMode.manual;
        for (final mode in [target, startMode ?? UnitMode.manual]) {
          final accepted = await repository.setMode(rootPath, mode);
          expect(accepted, isTrue, reason: 'mailbox acknowledgement $mode');
          await until(() => root().modeActive == mode, 'mode $mode');
        }
        record['modeRoundTrip'] = 'PASS';
      }
    } finally {
      await subscription.cancel();
      repository.dispose();
      final output = environment['FRAKTAL_TIA_DIRECT_OUTPUT'] ?? '';
      if (output.isNotEmpty) {
        File('$output/direct_repository.json')
          ..createSync(recursive: true)
          ..writeAsStringSync(
              const JsonEncoder.withIndent('  ').convert(record));
      }
    }
  }, skip: live ? false : 'opt-in: FRAKTAL_TIA_DIRECT_LIVE=1', timeout: const Timeout(Duration(minutes: 6)));

  // A commissioned PLC user (fraktal_tia_users.py): FRAKTAL_TIA_DIRECT_ADMIN_USER
  // and FRAKTAL_TIA_DIRECT_ADMIN_PIN. Logs in and out only; changes no data.
  final adminPin = environment['FRAKTAL_TIA_DIRECT_ADMIN_PIN'] ?? '';
  test('TIA direct: a commissioned PLC user logs in at its level', () async {
    final root = environment['FRAKTAL_TIA_DIRECT_ROOT'] ?? 'PressDemo';
    final user = environment['FRAKTAL_TIA_DIRECT_ADMIN_USER'] ?? 'admin';
    final repository = await createExternalRepository(ConnectionSettings(
        transport: ConnectionTransport.gateway,
        endpoint: environment['FRAKTAL_TIA_DIRECT_ENDPOINT']!));
    var forest = const <ModuleNode>[];
    final subscription = repository.forest().listen((nodes) => forest = nodes);
    ModuleNode? node() => forest.where((n) => n.path == root).firstOrNull;
    Future<void> until(bool Function() predicate, String what) async {
      final deadline = Stopwatch()..start();
      while (!predicate() && deadline.elapsed < const Duration(seconds: 60)) {
        await Future<void>.delayed(const Duration(milliseconds: 100));
      }
      expect(predicate(), isTrue, reason: what);
    }

    final record = <String, Object?>{};
    try {
      await until(() => node()?.access != null, 'root access published');
      record['initialLevel'] = node()!.access!.level.name;
      final wrong = await repository.login(root, user, '${adminPin}0');
      await until(() => node()!.access!.loginFailed, 'wrong PIN reported');
      record['wrongPin'] = {'accepted': wrong, 'level': node()!.access!.level.name};
      expect(node()!.access!.level, AccessLevel.none);
      final right = await repository.login(root, user, adminPin);
      await until(() => node()!.access!.level == AccessLevel.admin, 'admin session');
      record['rightPin'] = {'accepted': right, 'user': node()!.access!.user,
          'level': node()!.access!.level.name};
      await repository.logout(root);
      await until(() => node()!.access!.level == AccessLevel.none, 'logged out');
      record['loggedOut'] = true;
    } finally {
      await subscription.cancel();
      repository.dispose();
      final output = environment['FRAKTAL_TIA_DIRECT_OUTPUT'] ?? '';
      if (output.isNotEmpty) {
        File('$output/admin_login.json')
          ..createSync(recursive: true)
          ..writeAsStringSync(jsonEncode(record));
      }
    }
  },
      skip: live && adminPin.isNotEmpty
          ? false
          : 'opt-in: FRAKTAL_TIA_DIRECT_LIVE=1 with FRAKTAL_TIA_DIRECT_ADMIN_PIN',
      timeout: const Timeout(Duration(minutes: 3)));

  // The operator-entered login (memory only), as the connection screen uses
  // it: run WITHOUT FRAKTAL_TIA_WEB_USER/_PASSWORD and pass the password in
  // FRAKTAL_TIA_DIRECT_ENTERED_PASSWORD. Read-only.
  final entered = environment['FRAKTAL_TIA_DIRECT_ENTERED_PASSWORD'] ?? '';
  test('TIA direct: an entered login is refused when wrong and used when right',
      () async {
    final endpoint = environment['FRAKTAL_TIA_DIRECT_ENDPOINT']!;
    final settings = ConnectionSettings(
        transport: ConnectionTransport.gateway, endpoint: endpoint);
    final target = S7WebEndpoint.parse(Uri.parse(endpoint));
    addTearDown(() => s7WebCredentials.forget(target));
    s7WebCredentials.remember(target, 'fraktal', 'not-the-password');
    await expectLater(
        createExternalRepository(settings),
        throwsA(isA<S7WebLoginRequired>()
            .having((e) => e.rejected, 'rejected', isTrue)));
    expect(s7WebCredentials.lookup(target), isNull);

    s7WebCredentials.remember(target, 'fraktal', entered);
    final repository = await createExternalRepository(settings);
    var forest = const <ModuleNode>[];
    final subscription = repository.forest().listen((nodes) => forest = nodes);
    final deadline = Stopwatch()..start();
    while (forest.isEmpty && deadline.elapsed < const Duration(minutes: 1)) {
      await Future<void>.delayed(const Duration(milliseconds: 100));
    }
    await subscription.cancel();
    repository.dispose();
    expect(forest, isNotEmpty);
    final output = environment['FRAKTAL_TIA_DIRECT_OUTPUT'] ?? '';
    if (output.isNotEmpty) {
      File('$output/entered_login.json')
        ..createSync(recursive: true)
        ..writeAsStringSync(jsonEncode({
          'wrongLogin': 'rejected and forgotten',
          'enteredLogin': 'connected',
          'roots': [for (final root in forest) root.path],
        }));
    }
  },
      skip: live &&
              entered.isNotEmpty &&
              (environment['FRAKTAL_TIA_WEB_USER'] ?? '').isEmpty
          ? false
          : 'opt-in: FRAKTAL_TIA_DIRECT_LIVE=1 with an entered password and no environment login',
      timeout: const Timeout(Duration(minutes: 3)));
}
