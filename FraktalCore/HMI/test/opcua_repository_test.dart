import 'dart:async';

import 'package:flutter_test/flutter_test.dart';
import 'package:fraktal_hmi/data/opcua_repository.dart';
import 'package:fraktal_hmi/data/opcua_session_client.dart';
import 'package:fraktal_hmi/domain/types.dart';

void main() {
  test('current export uses one fresh token per complete document', () async {
    final client = _ExportClient();
    final repository = await OpcUaRepository.connectWithClient(client,
        refreshInterval: const Duration(days: 1));
    addTearDown(repository.dispose);
    expect(
        await repository.exportCurrentConfig('PneumaticPress', CfgKind.parCfg),
        'header\nrecord');
    final first = client.requests
        .where((r) => r['Kind'] == 38 || r['Kind'] == 32)
        .toList();
    expect(first, hasLength(2));
    final token = first[0]['NameValue'] as String;
    expect(token, matches(RegExp(r'^[0-9a-f]{32}$')));
    expect(first[1]['NameValue'], token);
    client.requests.clear();
    expect(
        await repository.exportCurrentConfig('PneumaticPress', CfgKind.parCfg),
        'header\nrecord');
    expect(client.requests.first['NameValue'], isNot(token));
    client.requests.clear();
    expect(await repository.exportConfigSet('PneumaticPress', 'saved'),
        'header\nrecord');
    expect(client.requests.every((r) => r['NameValue'] == ''), isTrue);
  });

  test('current export refuses a document with a missing continuation',
      () async {
    final client = _ExportClient()..missingContinuation = true;
    final repository = await OpcUaRepository.connectWithClient(client,
        refreshInterval: const Duration(days: 1));
    addTearDown(repository.dispose);
    expect(
        await repository.exportCurrentConfig('PneumaticPress', CfgKind.parCfg),
        isNull);
  });

  test('deployment polling keeps a full sample during a long interactive ack',
      () async {
    final client = _FreshBlockingModeClient();
    final repository = await OpcUaRepository.connectWithClient(client);
    addTearDown(repository.dispose);
    final request = repository.setMode('PneumaticPress', UnitMode.manual);
    await client.ackStarted.future;
    final before = client.snapshotCalls;
    await Future<void>.delayed(const Duration(milliseconds: 100));
    expect(client.snapshotCalls, greaterThan(before));
    expect(await repository.linkState().first, LinkState.live);
    client.releaseAck.complete();
    expect(await request, isTrue);
  });

  test('deployment polling continues during initial manifest hydration',
      () async {
    final client = _FreshManifestClient();
    final repository = await OpcUaRepository.connectWithClient(client);
    addTearDown(repository.dispose);
    await client.writeStarted.future;
    final before = client.snapshotCalls;
    await Future<void>.delayed(const Duration(milliseconds: 100));
    expect(client.snapshotCalls, greaterThan(before));
    expect(await repository.linkState().first, LinkState.live);
    client.releaseWrite.complete();
  });

  test('interactive bulk command yields polling then refreshes actual mode',
      () async {
    final client = _BlockingModeClient();
    final repository = await OpcUaRepository.connectWithClient(client,
        refreshInterval: const Duration(milliseconds: 10));
    addTearDown(repository.dispose);
    final modes = <UnitMode?>[];
    final subscription = repository.forest().listen((forest) {
      if (forest.isNotEmpty) modes.add(forest.first.modeActive);
    });
    addTearDown(subscription.cancel);
    final request = repository.setMode('PneumaticPress', UnitMode.manual);
    await client.ackStarted.future;
    final before = client.snapshotCalls;
    await Future<void>.delayed(const Duration(milliseconds: 45));
    expect(client.snapshotCalls, before,
        reason: 'periodic snapshots must yield while the command awaits ack');
    expect(modes, isNot(contains(UnitMode.manual)),
        reason: 'a request must not invent the PLC mode');
    client.releaseAck.complete();
    expect(await request, isTrue);
    await client.resultSnapshot.future;
    await Future<void>.delayed(Duration.zero);
    expect(modes, contains(UnitMode.manual));
  });

  test('a set refusal reads its offending record before the next snapshot',
      () async {
    final client = _RefusingSetClient();
    final repository = await OpcUaRepository.connectWithClient(client,
        refreshInterval: const Duration(days: 1));
    try {
      expect(await repository.loadConfigSet('PneumaticPress', 'commissioning'),
          isFalse);
      expect(await repository.configSetRejection('PneumaticPress'),
          'PneumaticPress.Ram / station.pressure');
    } finally {
      repository.dispose();
    }
  });
  test('initial truncated snapshot is rejected before the repository goes live',
      () async {
    final client = _TruncatedClient();

    await expectLater(
      OpcUaRepository.connectWithClient(
        client,
        refreshInterval: const Duration(days: 1),
      ),
      throwsA(
        isA<OpcUaSnapshotException>().having(
          (error) => error.message,
          'message',
          allOf(contains('20000'), contains('publication scope')),
        ),
      ),
    );
    expect(client.closed, isTrue);
  });

  test('mode request shares an in-flight refresh and reads its acknowledgement',
      () async {
    final client = _OverlappingRefreshClient();
    final repository = await OpcUaRepository.connectWithClient(
      client,
      refreshInterval: const Duration(milliseconds: 10),
    );
    addTearDown(repository.dispose);

    await client.refreshStarted.future.timeout(const Duration(seconds: 1));
    final request = repository.setMode('PneumaticPress', UnitMode.manual);
    await client.sequenceWritten.future.timeout(const Duration(seconds: 1));
    client.releaseRefresh.complete();

    expect(await request.timeout(const Duration(seconds: 1)), isTrue);
    expect(client.snapshotCalls, 2);
    expect(client.writes['PLC1/MAIN/PneumaticPress/HmiRequest/IntValue'],
        UnitMode.manual.index);
    expect(await repository.lampTest('PneumaticPress'), isTrue);
    expect(client.committedKinds, [3, 26],
        reason: 'append-only PLC/HMI request ordinals must stay aligned');
  });

  test('login returns the access-provider result, not mailbox consumption',
      () async {
    final rejectedClient = _LoginClient(loginSucceeds: false);
    final rejectedRepository = await OpcUaRepository.connectWithClient(
      rejectedClient,
      refreshInterval: const Duration(days: 1),
    );
    addTearDown(rejectedRepository.dispose);

    expect(
      await rejectedRepository.login('PneumaticPress', 'admin1', 'wrong'),
      isFalse,
    );
    expect(rejectedClient.sequence, 1);

    final acceptedClient = _LoginClient(loginSucceeds: true);
    final acceptedRepository = await OpcUaRepository.connectWithClient(
      acceptedClient,
      refreshInterval: const Duration(days: 1),
    );
    addTearDown(acceptedRepository.dispose);

    expect(
      await acceptedRepository.login('PneumaticPress', 'admin1', '2468'),
      isTrue,
    );
  });

  test('login waits for a background provider even with an existing same user',
      () async {
    for (final succeeds in [false, true]) {
      final client = _PendingLoginClient(loginSucceeds: succeeds);
      final repository = await OpcUaRepository.connectWithClient(client,
          refreshInterval: const Duration(days: 1));
      try {
        expect(await repository.login('PneumaticPress', 'admin1', 'sampled'),
            succeeds);
        expect(client.resultReads, 3,
            reason:
                'the prior session must not authenticate a pending attempt');
      } finally {
        repository.dispose();
      }
    }
  });

  test('login works with bulk providers that do not publish optional LoginBusy',
      () async {
    for (final succeeds in [false, true]) {
      final client = _SynchronousLoginClient(loginSucceeds: succeeds);
      final repository = await OpcUaRepository.connectWithClient(client,
          refreshInterval: const Duration(days: 1));
      try {
        expect(await repository.login('PneumaticPress', 'admin1', 'sampled'),
            succeeds);
      } finally {
        repository.dispose();
      }
    }
  });

  test('login follows the provider budget beyond six seconds', () async {
    final client = _PendingLoginClient(
        loginSucceeds: true,
        loginTimeoutMs: 12000,
        firstResultDelay: const Duration(milliseconds: 6100));
    final repository = await OpcUaRepository.connectWithClient(client,
        refreshInterval: const Duration(days: 1));
    addTearDown(repository.dispose);
    expect(
        await repository.login('PneumaticPress', 'admin1', 'sampled'), isTrue);
    expect(client.resultReads, 3);
  });

  test('login ignores an old failure until its own result sequence arrives',
      () async {
    final client = _CorrelatedLoginClient();
    final repository = await OpcUaRepository.connectWithClient(client,
        refreshInterval: const Duration(days: 1));
    addTearDown(repository.dispose);
    expect(
        await repository.login('PneumaticPress', 'admin1', 'sampled'), isTrue);
    expect(client.resultReads, 3);
  });

  test('a completed login with no remaining session is not a bad PIN',
      () async {
    final client = _CorrelatedLoginClient(sessionExpires: true);
    final repository = await OpcUaRepository.connectWithClient(client,
        refreshInterval: const Duration(days: 1));
    addTearDown(repository.dispose);
    await expectLater(repository.login('PneumaticPress', 'admin1', 'sampled'),
        throwsA(isA<TimeoutException>()));
    expect(client.resultReads, greaterThanOrEqualTo(3));
  });

  test('pending login timeout is unavailable rather than invalid credentials',
      () async {
    final client = _PendingLoginClient(
        loginSucceeds: true, pendingReads: 240, loginTimeoutMs: 90);
    final repository = await OpcUaRepository.connectWithClient(client,
        refreshInterval: const Duration(days: 1));
    addTearDown(repository.dispose);
    await expectLater(repository.login('PneumaticPress', 'admin1', 'sampled'),
        throwsA(isA<TimeoutException>()));
    expect(client.resultReads, lessThan(5));
  });

  test('login deadline also bounds a stalled result read', () async {
    final client = _PendingLoginClient(
        loginSucceeds: true,
        loginTimeoutMs: 90,
        firstResultDelay: const Duration(seconds: 2));
    final repository = await OpcUaRepository.connectWithClient(client,
        refreshInterval: const Duration(days: 1));
    addTearDown(repository.dispose);
    final elapsed = Stopwatch()..start();
    await expectLater(repository.login('PneumaticPress', 'admin1', 'sampled'),
        throwsA(isA<TimeoutException>()));
    expect(elapsed.elapsed, lessThan(const Duration(seconds: 1)));
  });

  test('a missing requested busy field cannot authenticate a prior session',
      () async {
    final client = _IncompleteLoginClient();
    final repository = await OpcUaRepository.connectWithClient(client,
        refreshInterval: const Duration(days: 1));
    addTearDown(repository.dispose);
    await expectLater(repository.login('PneumaticPress', 'admin1', 'sampled'),
        throwsA(isA<TimeoutException>()));
  });

  test('a busy provider refusal is unavailable rather than invalid credentials',
      () async {
    final client = _BusyLoginClient();
    final repository = await OpcUaRepository.connectWithClient(client,
        refreshInterval: const Duration(days: 1));
    addTearDown(repository.dispose);
    await expectLater(repository.login('PneumaticPress', 'admin1', 'sampled'),
        throwsA(isA<StateError>()));
  });

  test('a refused release query reports the PLC reason, not the transport',
      () async {
    // This is what an AB press does: it answers immediately and refuses,
    // because it publishes no release report. Reporting "the transport is
    // unavailable" there is a different and wrong claim - it sends whoever
    // is standing at the machine to look at the network, which is exactly
    // what happened on the bench.
    final client = _RefusingReleaseClient();
    final repository = await OpcUaRepository.connectWithClient(
      client,
      refreshInterval: const Duration(days: 1),
    );
    addTearDown(repository.dispose);

    final report = await repository.releaseReportStart('PneumaticPress');

    expect(report.released, isFalse);
    expect(report.reasons, hasLength(1));
    expect(report.reasons.single.description,
        'project.mailbox.refused.no_release_reports');
    expect(report.reasons.single.description,
        isNot('std.release.transportUnavailable'));
  });

  test('release query maps the complete native OPC UA reason report', () async {
    final client = _ReleaseClient();
    final repository = await OpcUaRepository.connectWithClient(
      client,
      refreshInterval: const Duration(days: 1),
    );
    addTearDown(repository.dispose);

    final report = await repository.releaseReportStart('PneumaticPress');

    expect(report.released, isFalse);
    expect(report.reasons, hasLength(2));
    expect(report.reasons[0].description, 'std.release.unitNotReady');
    expect(report.reasons[0].kind, ReleaseKind.mode);
    expect(report.reasons[0].sourcePath, 'PneumaticPress');
    expect(report.reasons[1].description, 'std.release.controlDomainNotReady');
    expect(report.reasons[1].kind, ReleaseKind.interlock);
    expect(report.reasons[1].reasonCode, 2002);
  });

  test(
      'config manifest hydrates obscured catalogs/topology and refetches on '
      'ConfigRev change', () async {
    final client = _ManifestClient();
    final repository = await OpcUaRepository.connectWithClient(
      client,
      refreshInterval: const Duration(milliseconds: 20),
    );
    addTearDown(repository.dispose);

    // The command catalog is NOT in the published snapshot; it must arrive via
    // the QUERY_CONFIG manifest and surface through the unchanged mapper.
    final hydrated = await repository
        .forest()
        .firstWhere(
            (forest) => forest.isNotEmpty && forest.first.commands.length == 2)
        .timeout(const Duration(seconds: 5));
    expect(hydrated.first.commands[0].value, 11);
    expect(hydrated.first.commands[0].label, 'std.cmd.open');
    expect(hydrated.first.commands[1].label, 'std.cmd.close');
    expect(client.requestedPages, [0, 1]);

    // Fieldbus identity likewise comes only from the manifest.
    final bus = await repository
        .fieldbus()
        .firstWhere(
            (nodes) => nodes.isNotEmpty && nodes.first.name == '=000+S-K010')
        .timeout(const Duration(seconds: 5));
    expect(bus.first.name, '=000+S-K010');

    final configured = await repository
        .forest()
        .firstWhere((forest) => forest.first.config.isNotEmpty)
        .timeout(const Duration(seconds: 5));
    final field = configured.first.config.single;
    expect(await repository.writeConfig('PneumaticPress', field, '2'), isTrue);
    expect(client.writes['PLC1/MAIN/PneumaticPress/HmiRequest/NameValue'],
        'unit.modePolicy.0.shield');
    expect(client.writes['PLC1/MAIN/PneumaticPress/HmiRequest/IntValue'], 1);
    expect(client.writes['PLC1/MAIN/PneumaticPress/HmiRequest/TextValue'], '2');
    // §3.8a - a model index travels only with a model-scoped value: sent for
    // station data, a PLC would take it for "that model" or, older, ignore it.
    expect(field.modelScoped, isFalse);
    expect(
        await repository.writeConfig('PneumaticPress', field, '2',
            modelIndex: 2),
        isTrue);
    expect(client.writes['PLC1/MAIN/PneumaticPress/HmiRequest/DurationMs'], 0);

    // A ConfigRev change (config write / changeover / PLC restart) refetches.
    client.bumpRevision('.v2');
    await repository
        .forest()
        .firstWhere((forest) =>
            forest.isNotEmpty &&
            forest.first.commands.isNotEmpty &&
            forest.first.commands[0].label == 'std.cmd.open.v2')
        .timeout(const Duration(seconds: 5));
    expect(client.requestedPages, [0, 1, 0, 1]);
  });

  test(
      'fieldbus live I/O is excluded from the snapshot and read only while the '
      'fieldbus view is active', () async {
    final client = _OnDemandFieldbusClient();
    final repository = await OpcUaRepository.connectWithClient(
      client,
      refreshInterval: const Duration(milliseconds: 20),
    );
    addTearDown(repository.dispose);

    // Let a few refreshes run with the view INACTIVE.
    await repository.forest().first.timeout(const Duration(seconds: 5));
    await Future<void>.delayed(const Duration(milliseconds: 100));
    // The live channel value must never have been read cyclically.
    expect(client.excludedPaths, contains(_channelValuePath));
    expect(client.readValuesCalls, 0,
        reason: 'no on-demand read until the fieldbus view is active');

    // Activate the fieldbus view -> the excluded live paths get target-read.
    repository.setFieldbusViewActive(true);
    await Future<void>.delayed(const Duration(milliseconds: 120));
    expect(client.readValuesCalls, greaterThan(0));
    expect(client.lastReadPaths, contains(_channelValuePath));

    // Deactivate -> on-demand reads stop.
    repository.setFieldbusViewActive(false);
    await Future<void>.delayed(const Duration(milliseconds: 40));
    final settled = client.readValuesCalls;
    await Future<void>.delayed(const Duration(milliseconds: 80));
    expect(client.readValuesCalls, settled,
        reason: 'no further on-demand reads after the view closes');
  });

  test(
      'module drill-down rings/trends are excluded and read only while that '
      "root's detail is open", () async {
    final client = _OnDemandFieldbusClient();
    final repository = await OpcUaRepository.connectWithClient(
      client,
      refreshInterval: const Duration(milliseconds: 20),
    );
    addTearDown(repository.dispose);
    await repository.forest().first.timeout(const Duration(seconds: 5));
    await Future<void>.delayed(const Duration(milliseconds: 60));

    const historyPath =
        'PLC1/MAIN/PneumaticPress/Profiler/History/History[1]/Total';
    expect(client.excludedPaths, contains(historyPath),
        reason: 'module history is on-demand, excluded from the snapshot');
    expect(client.readValuesCalls, 0);

    // Opening the module detail activates its root scope -> the drill-down reads.
    repository.setModuleDetailActive('PneumaticPress', true);
    await Future<void>.delayed(const Duration(milliseconds: 80));
    expect(client.readValuesCalls, greaterThan(0));
    expect(client.lastReadPaths, contains(historyPath));

    repository.setModuleDetailActive('PneumaticPress', false);
    await Future<void>.delayed(const Duration(milliseconds: 40));
    final settled = client.readValuesCalls;
    await Future<void>.delayed(const Duration(milliseconds: 80));
    expect(client.readValuesCalls, settled);
  });
}

// The channel VALUE is live now (§10.5.1), so the on-demand exemplar for this
// suite is a field that stays gated: `Forced` is per-channel drill-down state.
const _channelValuePath =
    'PLC1/GVL_PressFieldbus/Topology/Nodes/Nodes[1]/Channels/Channels[1]/Forced';

/// A bulk-read + tiered client that models fieldbus live I/O as on-demand data:
/// the snapshot omits the excluded channel-state paths; readValues serves them.
class _OnDemandFieldbusClient
    implements OpcUaBulkReadClient, OpcUaTieredReadClient {
  final List<String> excludedPaths = [];
  int readValuesCalls = 0;
  List<String> lastReadPaths = const [];

  @override
  Future<Map<String, Object?>> snapshot() async {
    const base = 'PLC1/MAIN/PneumaticPress';
    const topo = 'PLC1/GVL_PressFieldbus/Topology';
    // `paths` advertises the full discovered contract INCLUDING the on-demand
    // fieldbus live leaves; `values` omits them (they are excluded from reads).
    return {
      'protocol': 'fraktal.opcua.snapshot.v1',
      'nodeCount': 12,
      'truncated': false,
      'rootChildren': ['4:PLC1(Object)'],
      'namespaces': [
        'http://opcfoundation.org/UA/',
        'urn:BeckhoffAutomation:Ua:PLC1',
      ],
      'paths': [
        '$base/Status/Name',
        '$base/Status/State',
        '$base/Profiler/History/History[1]/Total', // module drill-down (on-demand)
        '$topo/NodeCount',
        '$topo/Nodes/Nodes[1]/State',
        _channelValuePath,
      ],
      'values': {
        '$base/Status/Name': 'PneumaticPress',
        '$base/Status/ModuleType': ModuleType.unit.index,
        '$base/Status/State': ExecState.ready.index,
        '$base/ModeActivePublished': UnitMode.auto.index,
        '$base/SupportedModesPublished': [true, true, true, true],
        // No ConfigRev -> manifest fetch is skipped (isolates the on-demand path).
      },
    };
  }

  @override
  Future<Map<String, Object?>> readValues(List<String> browsePaths) async {
    readValuesCalls++;
    lastReadPaths = browsePaths;
    return {for (final p in browsePaths) p: true};
  }

  @override
  Future<void> setExcludedPaths(Iterable<String> browsePaths) async {
    excludedPaths
      ..clear()
      ..addAll(browsePaths);
  }

  @override
  Future<void> setSlowPaths(Iterable<String> browsePaths) async {}

  @override
  Future<void> refreshSlowPaths() async {}

  @override
  Future<bool> write(String path, OpcUaWriteType type, Object value) async =>
      true;

  @override
  Future<void> close() async {}
}

/// Publishes a root Unit with the §3.10.2 obscured publication (no Catalog,
/// no topology identity in the snapshot) and serves them as a two-page
/// QUERY_CONFIG manifest through the mailbox echo.
class _ManifestClient implements OpcUaSessionClient {
  var sequence = 0;
  var configRev = 1000;
  var labelSuffix = '';
  var _pendingKind = 0;
  var _pendingPage = 0;
  var _ackedKind = 0;
  var _ackedPage = 0;
  final requestedPages = <int>[];
  final writes = <String, Object>{};

  void bumpRevision(String suffix) {
    configRev++;
    labelSuffix = suffix;
  }

  @override
  Future<Map<String, Object?>> snapshot() async {
    const base = 'PLC1/MAIN/PneumaticPress';
    const topology = 'PLC1/GVL_PressFieldbus/Topology';
    final values = <String, Object?>{
      '$base/Status/Name': 'PneumaticPress',
      '$base/Status/ModuleType': ModuleType.unit.index,
      '$base/Status/State': ExecState.ready.index,
      '$base/ModeActivePublished': UnitMode.auto.index,
      '$base/SupportedModesPublished': [true, true, true, true],
      '$base/ConfigRev': configRev,
      '$base/HmiResponse/AckSequence': sequence,
      '$base/HmiResponse/Accepted': sequence != 0,
      '$base/HmiResponse/Diagnostic': '',
      // Live topology state stays published; identity is manifest-only.
      '$topology/NodeCount': 1,
      '$topology/MappingValid': true,
      '$topology/MappingDiagnostic': '',
      '$topology/Nodes/Nodes[1]/State': 4,
      '$topology/Nodes/Nodes[1]/LinkOk': true,
    };
    if (_ackedKind == 23 /* QUERY_CONFIG */) {
      const pageBase = '$base/HmiResponse/ConfigPage';
      values['$pageBase/Revision'] = configRev;
      values['$pageBase/PageIndex'] = _ackedPage;
      values['$pageBase/PageCount'] = 2;
      final entries = _ackedPage == 0
          ? [
              ('PneumaticPress', 'CatalogCount', '2'),
              ('PneumaticPress', 'Catalog/Catalog[1]/Value', '11'),
              (
                'PneumaticPress',
                'Catalog/Catalog[1]/Label',
                'std.cmd.open$labelSuffix'
              ),
            ]
          : [
              ('PneumaticPress', 'Catalog/Catalog[2]/Value', '12'),
              ('PneumaticPress', 'Catalog/Catalog[2]/Label', 'std.cmd.close'),
              ('#Fieldbus', 'Nodes/Nodes[1]/Name', '=000+S-K010'),
              ('#Fieldbus', 'Nodes/Nodes[1]/ParentIdx', '0'),
              ('#Fieldbus', 'Nodes/Nodes[1]/ChannelCount', '0'),
              ('PneumaticPress', 'ModePolicy/ModePolicy[0]/Shield', '1'),
            ];
      values['$pageBase/EntryCount'] = entries.length;
      // Real TF6100 array naming: an ARRAY container then the member browse
      // name repeated per element (Entries/Entries[1]/...).
      for (var i = 0; i < entries.length; i++) {
        values['$pageBase/Entries/Entries[${i + 1}]/Scope'] = entries[i].$1;
        values['$pageBase/Entries/Entries[${i + 1}]/Item'] = entries[i].$2;
        values['$pageBase/Entries/Entries[${i + 1}]/ValueText'] = entries[i].$3;
        if (entries[i].$2 == 'ModePolicy/ModePolicy[0]/Shield') {
          final prefix = '$pageBase/Entries/Entries[${i + 1}]';
          values['$prefix/WriteKey'] = 'unit.modePolicy.0.shield';
          values['$prefix/WriteRevision'] = 1;
          values['$prefix/ConfigKind'] = CfgKind.stationCfg.index;
          values['$prefix/ValueType'] = CfgType.number.index;
          values['$prefix/Writable'] = true;
          values['$prefix/RequiresReady'] = true;
          values['$prefix/HasMinimum'] = true;
          values['$prefix/HasMaximum'] = true;
          values['$prefix/Minimum'] = 0.0;
          values['$prefix/Maximum'] = 2.0;
          values['$prefix/Unit'] = '';
          values['$prefix/LabelKey'] = '';
          values['$prefix/EnumDomain'] = '0|1|2';
        }
      }
    }
    return {
      'protocol': 'fraktal.opcua.snapshot.v1',
      'nodeCount': values.length,
      'truncated': false,
      'rootChildren': ['4:PLC1(Object)'],
      'namespaces': [
        'http://opcfoundation.org/UA/',
        'urn:BeckhoffAutomation:Ua:PLC1',
      ],
      // The discovered contract (bridge emits this once per discovery). The
      // repository derives the topology base from here, so the fieldbus manifest
      // scope resolves even though the live topology members are elsewhere.
      'paths': ['$base/Status/Name', '$topology/NodeCount'],
      'values': values,
    };
  }

  @override
  Future<bool> write(String path, OpcUaWriteType type, Object value) async {
    writes[path] = value;
    if (path.endsWith('/HmiRequest/Kind')) {
      _pendingKind = (value as num).toInt();
    } else if (path.endsWith('/HmiRequest/IntValue')) {
      _pendingPage = (value as num).toInt();
    } else if (path.endsWith('/HmiRequest/Sequence')) {
      sequence = (value as num).toInt();
      _ackedKind = _pendingKind;
      _ackedPage = _pendingPage;
      if (_ackedKind == 23) requestedPages.add(_ackedPage);
    }
    return true;
  }

  @override
  Future<void> close() async {}
}

Map<String, Object?> _freshDocument(Map<String, Object?> document) {
  final values = document['values'] as Map;
  return {
    ...document,
    'freshnessBudget': {
      'schemaVersion': 1,
      'pollPeriodMs': 30,
      'fastGoodMs': 1500,
      'fastExpiryMs': 2500,
      'slowPeriodMs': 1000,
      'slowGoodMs': 1500,
      'slowExpiryMs': 2500,
    },
    'sampleAgeMs': 0,
    'dataValues': {
      for (final item in values.entries)
        '${item.key}': {
          'value': item.value,
          'status': 0,
          'tier': 'fast',
          'ageMs': 0,
        }
    },
  };
}

class _FreshBlockingModeClient extends _BlockingModeClient {
  @override
  Future<Map<String, Object?>> snapshot() async =>
      _freshDocument(await super.snapshot());
}

class _FreshManifestClient extends _ManifestClient {
  var snapshotCalls = 0;
  final writeStarted = Completer<void>(), releaseWrite = Completer<void>();
  @override
  Future<Map<String, Object?>> snapshot() async {
    snapshotCalls++;
    return _freshDocument(await super.snapshot());
  }

  @override
  Future<bool> write(String path, OpcUaWriteType type, Object value) async {
    if (!writeStarted.isCompleted) {
      writeStarted.complete();
      await releaseWrite.future;
    }
    return super.write(path, type, value);
  }
}

class _TruncatedClient implements OpcUaSessionClient {
  bool closed = false;

  @override
  Future<Map<String, Object?>> snapshot() async => {
        'protocol': 'fraktal.opcua.snapshot.v1',
        'nodeCount': 20000,
        'truncated': true,
        'values': {
          'PLC1/MAIN/PneumaticPress/Status/Name': 'PneumaticPress',
          'PLC1/MAIN/PneumaticPress/Status/ModuleType': ModuleType.unit.index,
        },
      };

  @override
  Future<bool> write(String path, OpcUaWriteType type, Object value) async =>
      false;

  @override
  Future<void> close() async {
    closed = true;
  }
}

class _OverlappingRefreshClient implements OpcUaSessionClient {
  final refreshStarted = Completer<void>();
  final releaseRefresh = Completer<void>();
  final sequenceWritten = Completer<void>();
  final Map<String, Object> writes = {};
  final List<int> committedKinds = [];
  var snapshotCalls = 0;
  var sequence = 0;

  @override
  Future<Map<String, Object?>> snapshot() async {
    snapshotCalls++;
    if (snapshotCalls > 1) {
      if (!refreshStarted.isCompleted) refreshStarted.complete();
      await releaseRefresh.future;
    }
    const base = 'PLC1/MAIN/PneumaticPress';
    return {
      'protocol': 'fraktal.opcua.snapshot.v1',
      'nodeCount': 12,
      'truncated': false,
      'rootChildren': ['4:PLC1(Object)'],
      'namespaces': [
        'http://opcfoundation.org/UA/',
        'urn:BeckhoffAutomation:Ua:PLC1',
      ],
      'values': {
        '$base/Status/Name': 'PneumaticPress',
        '$base/Status/ModuleType': ModuleType.unit.index,
        '$base/Status/State': ExecState.ready.index,
        '$base/ModeActivePublished':
            sequence == 0 ? UnitMode.auto.index : UnitMode.manual.index,
        '$base/SupportedModesPublished': [true, true, true, true],
        '$base/HmiResponse/AckSequence': sequence,
        '$base/HmiResponse/Accepted': sequence != 0,
        '$base/HmiResponse/Diagnostic': '',
      },
    };
  }

  @override
  Future<bool> write(String path, OpcUaWriteType type, Object value) async {
    writes[path] = value;
    if (path.endsWith('/HmiRequest/Sequence')) {
      committedKinds.add(
          (writes[path.replaceFirst('/Sequence', '/Kind')] as num).toInt());
      sequence = (value as num).toInt();
      if (!sequenceWritten.isCompleted) sequenceWritten.complete();
    }
    return true;
  }

  @override
  Future<void> close() async {}
}

class _BlockingModeClient extends _OverlappingRefreshClient
    implements OpcUaBulkReadClient {
  final ackStarted = Completer<void>();
  final releaseAck = Completer<void>();
  final resultSnapshot = Completer<void>();

  @override
  Future<Map<String, Object?>> snapshot() async {
    // The parent blocks refreshes to test overlap; this fixture releases those
    // and blocks only the acknowledgement so polling can be observed.
    if (!releaseRefresh.isCompleted) releaseRefresh.complete();
    final document = await super.snapshot();
    if (releaseAck.isCompleted && !resultSnapshot.isCompleted) {
      resultSnapshot.complete();
    }
    return document;
  }

  @override
  Future<Map<String, Object?>> readValues(List<String> paths) async {
    if (!ackStarted.isCompleted) ackStarted.complete();
    await releaseAck.future;
    const base = 'PLC1/MAIN/PneumaticPress';
    final values = <String, Object?>{
      '$base/HmiResponse/AckSequence': sequence,
      '$base/HmiResponse/Accepted': true,
      '$base/HmiResponse/Diagnostic': '',
    };
    return {for (final path in paths) path: values[path]};
  }
}

class _LoginClient implements OpcUaSessionClient {
  final bool loginSucceeds;
  final Map<String, Object> writes = {};
  var sequence = 0;

  _LoginClient({required this.loginSucceeds});

  @override
  Future<Map<String, Object?>> snapshot() async {
    const base = 'PLC1/MAIN/PneumaticPress';
    final attempted = sequence != 0;
    final user = '${writes['$base/HmiRequest/User'] ?? ''}';
    return {
      'protocol': 'fraktal.opcua.snapshot.v1',
      'nodeCount': 16,
      'truncated': false,
      'rootChildren': ['4:PLC1(Object)'],
      'namespaces': [
        'http://opcfoundation.org/UA/',
        'urn:BeckhoffAutomation:Ua:PLC1',
      ],
      'values': {
        '$base/Status/Name': 'PneumaticPress',
        '$base/Status/ModuleType': ModuleType.unit.index,
        '$base/Status/State': ExecState.ready.index,
        '$base/ModeActivePublished': UnitMode.auto.index,
        '$base/SupportedModesPublished': [true, true, true, true],
        '$base/HmiResponse/AckSequence': sequence,
        '$base/HmiResponse/Accepted': attempted,
        '$base/HmiResponse/Diagnostic': '',
        '$base/Access/LoginFailed': attempted && !loginSucceeds,
        '$base/Access/CurrentLevel': attempted && loginSucceeds
            ? AccessLevel.admin.index
            : AccessLevel.none.index,
        '$base/Access/CurrentUser': attempted && loginSucceeds ? user : '',
      },
    };
  }

  @override
  Future<bool> write(String path, OpcUaWriteType type, Object value) async {
    writes[path] = value;
    if (path.endsWith('/HmiRequest/Sequence')) {
      sequence = (value as num).toInt();
    }
    return true;
  }

  @override
  Future<void> close() async {}
}

class _PendingLoginClient extends _LoginClient implements OpcUaBulkReadClient {
  var resultReads = 0;
  final int pendingReads;
  final int? loginTimeoutMs;
  final Duration? firstResultDelay;
  _PendingLoginClient(
      {required super.loginSucceeds,
      this.pendingReads = 3,
      this.loginTimeoutMs,
      this.firstResultDelay});

  @override
  Future<Map<String, Object?>> snapshot() async {
    final document = await super.snapshot();
    (document['values'] as Map<String, Object?>)[
        'PLC1/MAIN/PneumaticPress/Access/LoginBusy'] = false;
    if (loginTimeoutMs != null) {
      (document['values'] as Map<String, Object?>)[
          'PLC1/MAIN/PneumaticPress/Access/LoginTimeoutMs'] = loginTimeoutMs;
    }
    return document;
  }

  @override
  Future<Map<String, Object?>> readValues(List<String> paths) async {
    const base = 'PLC1/MAIN/PneumaticPress';
    if (paths.contains('$base/Access/LoginBusy')) {
      resultReads++;
      if (resultReads == 1 && firstResultDelay != null) {
        await Future<void>.delayed(firstResultDelay!);
      }
    }
    final pending = resultReads < pendingReads;
    final values = <String, Object?>{
      '$base/HmiResponse/AckSequence': sequence,
      '$base/HmiResponse/Accepted': true,
      '$base/HmiResponse/Diagnostic': '',
      '$base/Access/CurrentUser': 'admin1',
      '$base/Access/CurrentLevel': AccessLevel.admin.index,
      '$base/Access/LoginBusy': pending,
      '$base/Access/LoginFailed': !pending && !loginSucceeds,
    };
    return {
      for (final path in paths)
        if (values.containsKey(path)) path: values[path]
    };
  }
}

class _CorrelatedLoginClient extends _PendingLoginClient {
  final bool sessionExpires;
  _CorrelatedLoginClient({this.sessionExpires = false})
      : super(loginSucceeds: true, loginTimeoutMs: sessionExpires ? 180 : null);

  @override
  Future<Map<String, Object?>> snapshot() async {
    final document = await super.snapshot();
    (document['values'] as Map<String, Object?>)[
        'PLC1/MAIN/PneumaticPress/Access/LoginResultSequence'] = 0;
    return document;
  }

  @override
  Future<Map<String, Object?>> readValues(List<String> paths) async {
    final values = await super.readValues(paths);
    const base = 'PLC1/MAIN/PneumaticPress/Access';
    values['$base/LoginBusy'] = false;
    values['$base/LoginFailed'] = resultReads < pendingReads;
    values['$base/LoginResultSequence'] =
        resultReads < pendingReads ? sequence - 1 : sequence;
    if (sessionExpires && resultReads >= pendingReads) {
      values['$base/CurrentUser'] = '';
      values['$base/CurrentLevel'] = AccessLevel.none.index;
    }
    return values;
  }
}

class _BusyLoginClient extends _LoginClient {
  _BusyLoginClient() : super(loginSucceeds: false);

  @override
  Future<Map<String, Object?>> snapshot() async {
    final document = await super.snapshot();
    final values = document['values'] as Map<String, Object?>;
    values['PLC1/MAIN/PneumaticPress/HmiResponse/Accepted'] = false;
    values['PLC1/MAIN/PneumaticPress/HmiResponse/Diagnostic'] =
        'std.error.accessLoginBusy';
    return document;
  }
}

class _IncompleteLoginClient extends _PendingLoginClient {
  _IncompleteLoginClient() : super(loginSucceeds: true, loginTimeoutMs: 90);

  @override
  Future<Map<String, Object?>> readValues(List<String> paths) async {
    final values = await super.readValues(paths);
    values.remove('PLC1/MAIN/PneumaticPress/Access/LoginBusy');
    return values;
  }
}

class _SynchronousLoginClient extends _LoginClient
    implements OpcUaBulkReadClient {
  _SynchronousLoginClient({required super.loginSucceeds});

  @override
  Future<Map<String, Object?>> readValues(List<String> paths) async {
    final values = (await snapshot())['values'] as Map<String, Object?>;
    if (paths.any((path) => !values.containsKey(path))) {
      throw StateError('provider does not publish that path');
    }
    return {for (final path in paths) path: values[path]};
  }
}

/// A station that ANSWERS and refuses, naming its reason - the Allen-Bradley
/// press, which publishes no release report and says so.
class _RefusingReleaseClient implements OpcUaSessionClient {
  var sequence = 0;

  @override
  Future<Map<String, Object?>> snapshot() async {
    const base = 'PLC1/MAIN/PneumaticPress';
    return {
      'protocol': 'fraktal.opcua.snapshot.v1',
      'nodeCount': 8,
      'truncated': false,
      'rootChildren': ['4:PLC1(Object)'],
      'namespaces': ['http://opcfoundation.org/UA/'],
      'values': {
        '$base/Status/Name': 'PneumaticPress',
        '$base/Status/ModuleType': ModuleType.unit.index,
        '$base/Status/State': ExecState.ready.index,
        '$base/ModeActivePublished': UnitMode.auto.index,
        // Acknowledged promptly, refused with a reason. The transport is
        // healthy throughout.
        '$base/HmiResponse/AckSequence': sequence,
        '$base/HmiResponse/Accepted': false,
        '$base/HmiResponse/Diagnostic':
            'project.mailbox.refused.no_release_reports',
      },
    };
  }

  @override
  Future<bool> write(String path, OpcUaWriteType type, Object value) async {
    if (path.endsWith('/HmiRequest/Sequence')) {
      sequence = (value as num).toInt();
    }
    return true;
  }

  @override
  Future<void> close() async {}
}

class _RefusingSetClient extends _RefusingReleaseClient
    implements OpcUaBulkReadClient {
  @override
  Future<Map<String, Object?>> readValues(List<String> browsePaths) async {
    final current = (await snapshot())['values'] as Map<String, Object?>;
    return {
      for (final path in browsePaths)
        path: path.endsWith('/LastRejectScope')
            ? 'PneumaticPress.Ram'
            : path.endsWith('/LastRejectKey')
                ? 'station.pressure'
                : current[path]
    };
  }
}

class _ReleaseClient implements OpcUaSessionClient {
  var sequence = 0;

  @override
  Future<Map<String, Object?>> snapshot() async {
    const base = 'PLC1/MAIN/PneumaticPress';
    return {
      'protocol': 'fraktal.opcua.snapshot.v1',
      'nodeCount': 22,
      'truncated': false,
      'rootChildren': ['4:PLC1(Object)'],
      'namespaces': [
        'http://opcfoundation.org/UA/',
        'urn:BeckhoffAutomation:Ua:PLC1',
      ],
      'values': {
        '$base/Status/Name': 'PneumaticPress',
        '$base/Status/ModuleType': ModuleType.unit.index,
        '$base/Status/State': ExecState.ready.index,
        '$base/ModeActivePublished': UnitMode.home.index,
        '$base/SupportedModesPublished': [true, true, true, true],
        '$base/HmiResponse/AckSequence': sequence,
        '$base/HmiResponse/Accepted': sequence != 0,
        '$base/HmiResponse/Diagnostic': '',
        '$base/HmiResponse/Report/Released': false,
        '$base/HmiResponse/Report/Count': sequence == 0 ? 0 : 2,
        '$base/HmiResponse/Report/Reasons/1/Description':
            'std.release.unitNotReady',
        '$base/HmiResponse/Report/Reasons/1/ReasonCode': 0,
        '$base/HmiResponse/Report/Reasons/1/SourcePath': 'PneumaticPress',
        '$base/HmiResponse/Report/Reasons/1/Kind': ReleaseKind.mode.index,
        '$base/HmiResponse/Report/Reasons/1/Bypassable': false,
        '$base/HmiResponse/Report/Reasons/2/Description':
            'std.release.controlDomainNotReady',
        '$base/HmiResponse/Report/Reasons/2/ReasonCode': 2002,
        '$base/HmiResponse/Report/Reasons/2/SourcePath': 'PneumaticPress',
        '$base/HmiResponse/Report/Reasons/2/Kind': ReleaseKind.interlock.index,
        '$base/HmiResponse/Report/Reasons/2/Bypassable': false,
      },
    };
  }

  @override
  Future<bool> write(String path, OpcUaWriteType type, Object value) async {
    if (path.endsWith('/HmiRequest/Sequence')) {
      sequence = (value as num).toInt();
    }
    return true;
  }

  @override
  Future<void> close() async {}
}

class _ExportClient extends _ReleaseClient implements OpcUaBulkReadClient {
  final requests = <Map<String, Object?>>[];
  final pending = <String, Object?>{};
  bool missingContinuation = false;
  String document = '';

  @override
  Future<Map<String, Object?>> snapshot() async {
    final result = await super.snapshot();
    const base = 'PLC1/MAIN/PneumaticPress';
    result['paths'] = [
      ...(result['values'] as Map<String, Object?>).keys,
      '$base/ConfigSetDocument',
      '$base/ConfigSetDocumentLines',
    ];
    return result;
  }

  @override
  Future<bool> write(String path, OpcUaWriteType type, Object value) async {
    if (path.contains('/HmiRequest/')) {
      pending[path.split('/').last] = value;
      if (path.endsWith('/Sequence')) {
        requests.add(Map.of(pending));
        final header = pending['Kind'] == 38 || pending['IntValue'] == 0;
        document = header ? 'header' : (missingContinuation ? '' : 'record');
      }
    }
    return super.write(path, type, value);
  }

  @override
  Future<Map<String, Object?>> readValues(List<String> paths) async {
    final values = (await snapshot())['values'] as Map<String, Object?>;
    return {
      for (final path in paths)
        path: path.endsWith('/ConfigSetDocument')
            ? document
            : path.endsWith('/ConfigSetDocumentLines')
                ? 1
                : values[path]
    };
  }
}
