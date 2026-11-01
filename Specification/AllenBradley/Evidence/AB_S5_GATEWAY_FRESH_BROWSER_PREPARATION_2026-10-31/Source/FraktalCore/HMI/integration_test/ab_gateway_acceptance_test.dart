// S5-Q only: compile against a sealed fixture before any Echo download.
// Without the fixture define this test is skipped and opens no connection.
import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';
import 'package:fraktal_hmi/data/opcua_gateway_client_io.dart';
import 'package:fraktal_hmi/data/opcua_repository.dart';
import 'package:fraktal_hmi/data/opcua_session_client.dart';
import 'package:fraktal_hmi/data/reconnecting_opcua_session_client.dart';
import 'package:fraktal_hmi/domain/module_node.dart';
import 'package:fraktal_hmi/domain/types.dart';
import 'package:fraktal_opcua_client/src/cip_namespace.dart';
import 'package:fraktal_opcua_client/src/cip_transport.dart';

const _fixture = String.fromEnvironment('fraktal.ab.gateway.fixture');
const _image =
    '95E1C514A31B06AEF528BDDC07F7D64C2336DDA6910B43663F1C01EBBA586012';

List<ModuleNode> _flatten(Iterable<ModuleNode> roots) => [
      for (final root in roots) ...[root, ..._flatten(root.children)]
    ];

Future<void> _save(Directory directory, String name, Object value) async {
  final file = File('${directory.path}/$name');
  await file.create(exclusive: true);
  await file.writeAsString(jsonEncode(value));
}

Future<void> _wait(FutureOr<bool> Function() predicate, String label,
    {Duration timeout = const Duration(seconds: 30)}) async {
  final clock = Stopwatch()..start();
  while (clock.elapsed < timeout) {
    if (await predicate()) return;
    await Future<void>.delayed(const Duration(milliseconds: 50));
  }
  throw StateError('Timed out: $label');
}

void main() {
  IntegrationTestWidgetsFlutterBinding.ensureInitialized();
  testWidgets('S5 typed gateway qualification', (tester) async {
    await tester.runAsync(() async {
      final file = File(_fixture), directory = file.parent;
      final fixture = jsonDecode(await file.readAsString()) as Map;
      final authorization = jsonDecode(
              await File('${directory.path}/authorization.json').readAsString())
          as Map;
      if (authorization['CurrentOwnerApproved'] != true ||
          authorization['GatewayWritesAuthorized'] != true ||
          authorization['Serial'] != '601FC87B' ||
          authorization['CanonicalSha256'] != _image ||
          fixture['canonicalSha256'] != _image ||
          fixture['root'] != 'Press' ||
          fixture['endpoint'] != 'ws://127.0.0.1:8080/fraktal' ||
          fixture['viewerEndpoint'] != 'ws://127.0.0.1:8081/fraktal')
        throw StateError('Exact S5 fixture authorization required.');
      final account = ((jsonDecode(
              await File(fixture['credentialFile'] as String)
                  .readAsString()) as Map)['users'] as List)
          .cast<Map>()
          .singleWhere((u) => u['level'] == 4);
      final user = account['user'] as String, secret = account['pin'] as String;
      final wrong = secret.isEmpty
          ? '1'
          : '${secret.substring(0, secret.length - 1)}${secret.endsWith('0') ? '1' : '0'}';
      final root = fixture['root'] as String;
      final idleSeconds = fixture['idleProbeSeconds'] as int? ?? 0;
      if (idleSeconds < 0 || idleSeconds > 120) {
        throw StateError('Idle probe must be bounded to 0..120 seconds.');
      }
      final rows = <Map<String, Object?>>[];
      final http = HttpClient();
      OpcUaRepository? repository;
      ReconnectingOpcUaSessionClient? reconnecting;
      IoGatewayOpcUaClient? active, viewer;
      CipSocketTransport? native;
      StreamSubscription? forestSubscription, linkSubscription;
      var forest = <ModuleNode>[], link = LinkState.down;
      final links = <String>[];
      var current = 'initialization';
      String? failure;
      Future<void> record(String id, Map<String, Object?> facts) async {
        rows.add({'case': id, 'passed': true, ...facts});
        await _save(directory, 'gateway_$id.json', rows.last);
      }

      Future<Map> health(int port) async {
        final request =
            await http.getUrl(Uri.parse('http://127.0.0.1:$port/healthz'));
        final response = await request.close();
        expect(response.statusCode, 200);
        return jsonDecode(await utf8.decoder.bind(response).join()) as Map;
      }

      Future<Map<String, Object?>> read(List<String> paths) async =>
          active!.readValues(paths);
      Future<Object?> scalar(String path) async => (await read([path]))[path];
      Future<int> acknowledgement() async =>
          (await CipNamespace.readDint(
              native!, '$root.HmiResponse.AckSequence')) &
          0xffffffff;
      ModuleNode node(String path) =>
          _flatten(forest).singleWhere((n) => n.path == path);
      bool readyToAct() =>
          link == LinkState.live && _flatten(forest).length == 7;
      Future<void> waitForAction() =>
          _wait(readyToAct, 'LIVE forest before operator action');
      List<OpcUaWrite> batch(String target, int kind, int sequence) => [
            OpcUaWrite('$target/HmiRequest/Kind', OpcUaWriteType.int32, kind),
            OpcUaWrite(
                '$target/HmiRequest/Sequence', OpcUaWriteType.uint32, sequence)
          ];
      Future<bool> refused(
          IoGatewayOpcUaClient client, List<OpcUaWrite> writes) async {
        try {
          return !await client.writeBatch(writes);
        } on OpcUaRemoteException {
          return true;
        }
      }

      try {
        // Leave the gateway's upstream connections unused before the first
        // browser-style connection. No request is retried by this test.
        await Future<void>.delayed(Duration(seconds: idleSeconds));
        native = await CipSocketTransport.connect(
            host: '127.0.0.1',
            slot: 0,
            expectSerial: '601FC87B',
            connectionBytes: 4000);
        reconnecting =
            await ReconnectingOpcUaSessionClient.connect(factory: () async {
          final client = await IoGatewayOpcUaClient.connect(
              Uri.parse(fixture['endpoint'] as String));
          active = client;
          return client;
        });
        repository = await OpcUaRepository.connectWithClient(reconnecting);
        forestSubscription = repository.forest().listen((value) {
          forest = value;
        });
        linkSubscription = repository.linkState().listen((value) {
          link = value;
          links.add(value.name);
        });
        current = 'C1';
        await _wait(
            () => link == LinkState.live && _flatten(forest).length == 7,
            'seven LIVE modules');
        final ready =
            await http.getUrl(Uri.parse('http://127.0.0.1:8080/readyz'));
        final readyResponse = await ready.close();
        expect(readyResponse.statusCode, 200);
        await readyResponse.drain<void>();
        expect(((await health(8080))['writeAccess'] as Map)['enabled'], true);
        expect(
            (await active!.snapshot())['contentHash'], fixture['manifestHash']);
        expect(active!.configurationContainersUseHeartbeat, true);
        await waitForAction();
        await record(current, {
          'live': true,
          'modules': _flatten(forest).map((n) => n.path).toList(),
          'writeEnabled': true,
          'gatewayIdleBeforeConnectSeconds': idleSeconds,
        });

        current = 'C2';
        await waitForAction();
        expect(await repository.login(root, user, secret), true);
        await _save(directory, 'gateway_authentication_01.json', {
          'user': user,
          'level': 4,
          'loginResultSequence': await acknowledgement(),
          'correlatedByRepository': true,
        });
        final login = await read([
          '$root/Access/CurrentLevel',
          '$root/Access/LoginBusy',
          '$root/Access/LoginFailed',
          '$root/Access/LoginResultSequence'
        ]);
        expect(login['$root/Access/CurrentLevel'], 4);
        expect(login['$root/Access/LoginBusy'], false);
        expect(login['$root/Access/LoginFailed'], false);
        expect(
            login['$root/Access/LoginResultSequence'], await acknowledgement());
        final privacy = await active!.snapshot();
        expect(
            (privacy['values'] as Map).keys.where((p) =>
                '$p'.endsWith('/HmiRequest/Secret') ||
                '$p'.endsWith('/HmiRequest/TextValue')),
            isEmpty);
        await record(current, {
          'authenticated': true,
          'acknowledgement': await acknowledgement(),
          'inputValuesAbsent': true
        });

        current = 'C3';
        await waitForAction();
        await repository.logout(root);
        await waitForAction();
        expect(await repository.login(root, user, wrong), false);
        final rejected = await read([
          '$root/Access/LoginFailed',
          '$root/Access/CurrentLevel',
          '$root/Access/LoginResultSequence'
        ]);
        expect(rejected['$root/Access/LoginFailed'], true);
        expect(rejected['$root/Access/CurrentLevel'], 0);
        expect(rejected['$root/Access/LoginResultSequence'],
            await acknowledgement());
        await record(current, {
          'providerRefused': true,
          'resultSequence': await acknowledgement(),
          'currentLevel': 0
        });

        current = 'C4';
        await waitForAction();
        expect(await repository.login(root, user, secret), true);
        await _save(directory, 'gateway_authentication_02.json', {
          'user': user,
          'level': 4,
          'loginResultSequence': await acknowledgement(),
          'correlatedByRepository': true,
        });
        final modeAcks = <int>[];
        for (final mode in [UnitMode.auto, UnitMode.manual]) {
          await waitForAction();
          expect(await repository.setMode(root, mode), true);
          await _wait(() => readyToAct() && node(root).modeActive == mode,
              'mode ${mode.name}');
          modeAcks.add(await acknowledgement());
        }
        await record(current,
            {'acknowledgements': modeAcks, 'mode': UnitMode.manual.index});

        current = 'C5';
        final idleLinkStart = links.length;
        for (var i = 0; i < idleSeconds; i++) {
          await Future<void>.delayed(const Duration(seconds: 1));
          // Keep only the independent observation connection alive. The
          // command channel gets no command or keepalive during this wait.
          await acknowledgement();
          expect(readyToAct(), true);
        }
        expect(links.skip(idleLinkStart), everyElement(LinkState.live.name));
        final cm = fixture['cmTarget'] as String,
            path = fixture['cmStatePath'] as String;
        expect(node(cm).commands.map((c) => c.value),
            containsAll([fixture['cmCommand'], fixture['cmRestoreCommand']]));
        final countPath = fixture['cmCountPath'] as String;
        final restoreCountPath = fixture['cmRestoreCountPath'] as String;
        final countBefore = await scalar(countPath) as int;
        final restoreBefore = await scalar(restoreCountPath) as int;
        await waitForAction();
        expect(
            await repository.manualCommand(
                root, cm, fixture['cmCommand'] as int),
            true);
        await _wait(
            () async =>
                await scalar(countPath) == ((countBefore + 1) & 0xffffffff),
            'CM command result');
        expect(await scalar(path),
            anyOf(ExecState.ready.index, ExecState.done.index));
        expect(await scalar('${cm.replaceAll('.', '/')}/Status/FaultActive'),
            false);
        final commandAck = await acknowledgement();
        await waitForAction();
        expect(
            await repository.manualCommand(
                root, cm, fixture['cmRestoreCommand'] as int),
            true);
        await _wait(
            () async =>
                await scalar(restoreCountPath) ==
                ((restoreBefore + 1) & 0xffffffff),
            'CM return command');
        expect(await scalar(path),
            anyOf(ExecState.ready.index, ExecState.done.index));
        expect(await scalar('${cm.replaceAll('.', '/')}/Status/FaultActive'),
            false);
        await record(current, {
          'target': cm,
          'commandIdleBeforeMovementSeconds': idleSeconds,
          'idleWaitLinkTransitions': links.skip(idleLinkStart).toList(),
          'acknowledgement': commandAck,
          'stateObserved': true,
          'returnCommandCompleted': true,
          'completedCount': (countBefore + 1) & 0xffffffff,
          'returnCount': (restoreBefore + 1) & 0xffffffff,
        });

        current = 'C6';
        final key = fixture['configKey'] as String;
        await _wait(() async {
          if (!readyToAct()) return false;
          final capabilities = node(root)
              .config
              .where((f) => f.writeKey == key && f.writable)
              .toList();
          return capabilities.length == 1 &&
              capabilities.single.writeRevision ==
                  await scalar('$root/Status/ConfigRev');
        }, 'current published configuration capability');
        CfgField field() =>
            node(root).config.singleWhere((f) => f.writeKey == key);
        final originalField = field(),
            oldRevision = await scalar('$root/Status/ConfigRev');
        final value = fixture['configValue'] as String;
        expect(value, isNot(originalField.value));
        await waitForAction();
        expect(await repository.writeConfig(root, originalField, value), true);
        await _wait(
            () async =>
                readyToAct() &&
                field().value == value &&
                field().writeRevision == await scalar('$root/Status/ConfigRev'),
            'configuration changed with current published revision');
        final changedRevision = await scalar('$root/Status/ConfigRev');
        expect(changedRevision, isNot(oldRevision));
        await waitForAction();
        expect(await repository.writeConfig(root, field(), originalField.value),
            true);
        await _wait(() => readyToAct() && field().value == originalField.value,
            'exact configuration restoration');
        await record(current, {
          'key': key,
          'capabilityRevision': originalField.writeRevision,
          'original': originalField.value,
          'temporary': value,
          'beforeRevision': oldRevision,
          'changedRevision': changedRevision,
          'restoredRevision': await scalar('$root/Status/ConfigRev'),
          'exactRestoration': true
        });

        current = 'C7';
        final modelCount = await scalar('$root/AvailableModelCount') as int;
        final pages = <Map<String, Object?>>[];
        for (var model = 0; model <= modelCount; model++) {
          final page = await active!.readConfigurationPage(root, model);
          expect(page, isNotNull);
          pages.add({'root': root, 'modelOrdinal': model, 'page': page});
        }
        await _save(directory, 'gateway_configuration_pages.json',
            {'passed': true, 'configurationPages': pages, 'writes': 0});
        await _save(directory, 'gateway_config_oracle_requested.json',
            {'readOnly': true});
        final comparison =
            File('${directory.path}/gateway_configuration_comparison.json');
        await _wait(
            () => comparison.existsSync(), 'independent configuration oracle',
            timeout: const Duration(seconds: 90));
        final compared = jsonDecode(await comparison.readAsString()) as Map;
        expect(compared['passed'], true);
        await record(current, {
          'pages': pages.length,
          'scalarComparisons': compared['scalarComparisons'],
          'oracleValuesAndTypesEqual': true,
        });

        current = 'C8';
        final beforeOutside = await acknowledgement();
        expect(
            await refused(active!,
                batch('OutsideRoot', 0, (beforeOutside + 1) & 0xffffffff)),
            true);
        expect(await acknowledgement(), beforeOutside);
        await record(current, {
          'refusedBeforeController': true,
          'acknowledgement': beforeOutside
        });

        current = 'C9';
        final beforeDuplicate = await acknowledgement();
        for (final sequence in [
          beforeDuplicate,
          (beforeDuplicate - 1) & 0xffffffff
        ]) {
          expect(await refused(active!, batch(root, 0, sequence)), true);
          expect(await acknowledgement(), beforeDuplicate);
        }
        await record(current, {
          'duplicateAndStaleRefused': true,
          'acknowledgement': beforeDuplicate
        });

        current = 'C10';
        viewer = await IoGatewayOpcUaClient.connect(
            Uri.parse(fixture['viewerEndpoint'] as String));
        final beforeViewer = await acknowledgement();
        for (var kind = 0; kind < 39; kind++) {
          expect(
              await refused(
                  viewer, batch(root, kind, (beforeViewer + 1) & 0xffffffff)),
              true);
        }
        expect(await acknowledgement(), beforeViewer);
        expect(((await health(8081))['writeAccess'] as Map)['enabled'], false);
        await record(current, {
          'refusedKinds': 39,
          'acknowledgement': beforeViewer,
          'writeEnabled': false
        });

        current = 'C11';
        final beforeRestart = await acknowledgement();
        links.clear();
        await _save(directory, 'gateway_stop_requested.json',
            {'readOnlyControl': true});
        await _wait(
            () => File('${directory.path}/gateway_stopped.json').existsSync(),
            'gateway stopped');
        await Future<void>.delayed(const Duration(milliseconds: 5200));
        expect(links, contains('stale'));
        expect(link, LinkState.down);
        expect(await repository.setMode(root, UnitMode.auto), false);
        expect(await acknowledgement(), beforeRestart);
        await _save(directory, 'gateway_restart_requested.json',
            {'readOnlyControl': true});
        await _wait(() => link == LinkState.live, 'gateway LIVE after restart');
        expect(await acknowledgement(), beforeRestart);
        await record(current, {
          'links': List<String>.from(links),
          'noReplay': true,
          'acknowledgement': beforeRestart
        });

        current = 'C13';
        await waitForAction();
        expect(await repository.setMode(root, UnitMode.manual), true);
        await waitForAction();
        await repository.logout(root);
        await _wait(() async => await scalar('$root/Access/CurrentLevel') == 0,
            'logout');
        await waitForAction();
        expect(node(root).modeActive, UnitMode.manual);
        expect(node(root).running, false);
        expect(node(root).state, ExecState.ready);
        expect(node(root).faultActive, false);
        await record(
            current, {'loggedOut': true, 'manual': true, 'idle': true});
      } catch (error) {
        failure = error
            .toString()
            .replaceAll(secret, '[redacted]')
            .replaceAll(wrong, '[redacted]');
      } finally {
        await forestSubscription?.cancel();
        await linkSubscription?.cancel();
        repository?.dispose();
        if (repository == null) await reconnecting?.close();
        await viewer?.close();
        await native?.close();
        http.close(force: true);
        await _save(directory, 'gateway_profile_result.json', {
          'passed': failure == null,
          'failedCase': failure == null ? null : current,
          'error': failure,
          'cases': rows,
          'ownerBrowserPending': true,
          'credentialValuesRecorded': false
        });
      }
      if (failure != null)
        throw TestFailure(
            'S5 $current failed; inspect the redacted session report.');
    });
  }, skip: _fixture.isEmpty, timeout: const Timeout(Duration(minutes: 20)));
}
