import 'dart:async';

import 'package:flutter_test/flutter_test.dart';
import 'package:fraktal_hmi/data/opcua_freshness.dart';
import 'package:fraktal_hmi/data/opcua_repository.dart';
import 'package:fraktal_hmi/data/opcua_session_client.dart';
import 'package:fraktal_hmi/domain/types.dart';
import 'package:fraktal_hmi/domain/module_node.dart';

const budget = <String, Object?>{
  'schemaVersion': 1,
  'pollPeriodMs': 30,
  'fastGoodMs': 150,
  'fastExpiryMs': 300,
  'slowPeriodMs': 50,
  'slowGoodMs': 100,
  'slowExpiryMs': 200,
};
const base = 'PLC1/MAIN/Press';

void main() {
  test('overrunning complete reads resume without a skipped polling boundary',
      () async {
    final client = _SlowSampleClient();
    final repository = await OpcUaRepository.connectWithClient(client);
    addTearDown(repository.dispose);
    final links = <LinkState>[];
    final sub = repository.linkState().listen(links.add);
    addTearDown(sub.cancel);
    await client.fourthRead.future.timeout(const Duration(seconds: 4));
    // Measure the next acquisition from completion of a warmed read. The
    // first pair also includes one-time Dart JIT/discovery work.
    expect(client.starts[2] - client.finishes[1],
        lessThan(const Duration(milliseconds: 90)),
        reason: 'an overrun must renew promptly after completion');
    expect(links, everyElement(LinkState.live));
    expect(client.maximumConcurrent, 1);
  });

  test('transit allowance counts server acquisition once and rejects bad brackets', () {
    final profile = OpcUaFreshnessBudget.parse({'freshnessBudget': budget})!;
    const elapsed = Duration(milliseconds: 85);
    expect(profile.transitAllowance({}, elapsed), elapsed);
    expect(profile.transitAllowance({'responseProcessingMs': 80}, elapsed),
        const Duration(milliseconds: 6));
    for (final invalid in [null, -1, double.nan, double.infinity, '80', 87]) {
      expect(() => profile.transitAllowance(
          {'responseProcessingMs': invalid}, elapsed), throwsFormatException);
    }
    final received = profile.ageDocument({
      'values': {'detail': 1},
      'dataValues': {'detail': {'value': 1, 'status': 0, 'tier': 'slow', 'ageMs': 80}},
    }, profile.transitAllowance({'responseProcessingMs': 80}, elapsed));
    expect(received['values'], {'detail': 1});
    final expired = profile.ageDocument(received, const Duration(milliseconds: 120));
    expect(expired['values'], isEmpty);
  });

  test('budgeted tiers stream only visible detail without targeted sweeps',
      () async {
    final client = _StreamingDetailClient();
    final repository = await OpcUaRepository.connectWithClient(client);
    addTearDown(repository.dispose);
    repository.setModuleDetailActive('Press', true,
        containers: {'History', 'StepStats', 'Timing'});
    await repository.forest().firstWhere((forest) => forest.any((node) =>
        node.path == 'Press' &&
        node.publishedValues.containsKey('Profiler/History[1]/CycleNo')));
    expect(client.slow, unorderedEquals([
      '$base/Profiler/History[1]/CycleNo',
      '$base/Profiler/StepStats[1]/Mean',
      '$base/Ram/Timing/Rows[1]/Last',
    ]));
    expect(client.excluded, containsAll([
      '$base/AlarmLog/Ring[1]/ReasonCode',
      '$base/SequenceSteps[1]/Visited',
      '$base/ConfigSetDocumentLine',
      'PLC1/MAIN/Other/Profiler/History[1]/CycleNo',
    ]));
    expect(client.reads, isEmpty);
    repository.setModuleDetailActive('Press', true, containers: {'Ring'});
    await repository.forest().firstWhere((forest) => forest.any((node) =>
        node.path == 'Press' &&
        node.publishedValues.containsKey('AlarmLog/Ring[1]/ReasonCode')));
    expect(client.slow, {'$base/AlarmLog/Ring[1]/ReasonCode'});
    expect(client.excluded, contains('$base/Profiler/History[1]/CycleNo'));
    repository.setModuleDetailActive('Press', false);
    await Future<void>.delayed(const Duration(milliseconds: 100));
    expect(client.slow, isEmpty);
    expect(client.excluded, contains('$base/AlarmLog/Ring[1]/ReasonCode'));
    expect(client.reads, isEmpty);
    expect(client.overlappingTiers, isFalse);
  });

  test('streamed detail keeps its source age while the station stays live',
      () async {
    final client = _StreamingDetailClient()..detailAge = 200;
    final repository = await OpcUaRepository.connectWithClient(client);
    addTearDown(repository.dispose);
    repository.setModuleDetailActive('Press', true, containers: {'History'});
    final forest = await repository.forest().firstWhere((forest) =>
        forest.any((node) => node.path == 'Press' &&
            node.tagAt('Profiler/History[1]/CycleNo') != null));
    expect(forest.singleWhere((node) => node.path == 'Press')
        .tagAt('Profiler/History[1]/CycleNo')!.quality, PublishedTagQuality.bad);
    expect(await repository.linkState().first, LinkState.live);
    expect(client.reads, isEmpty);
  });

  test('targeted envelope retains source quality and rejects unknown versions', () {
    final source = {'status': 0x40000000, 'ageMs': 1234};
    final result = decodeTargetedDataValues({
      'protocol': 'fraktal.opcua.read-values.v1',
      'values': {'a': null}, 'dataValues': {'a': source},
    });
    expect((result['dataValues'] as Map)['a'], source);
    expect(() => decodeTargetedDataValues({
      'protocol': 'fraktal.opcua.read-values.v2',
      'values': {'a': 1}, 'dataValues': {'a': source},
    }), throwsFormatException);
    expect(() => decodeTargetedDataValues({
      'protocol': 'fraktal.opcua.read-values.v1', 'values': {'a': 1},
    }), throwsFormatException);
    final legacy = decodeTargetedDataValues({'a': 1, 'b': null});
    expect((legacy['dataValues'] as Map)['a'], {'ageMs': 0, 'status': 0});
    expect(((legacy['dataValues'] as Map)['b'] as Map)['status'], 0x80320000);
  });

  for (final age in <num>[200, double.nan]) {
    test('cached/malformed detail age cannot become Good at receipt ($age)',
        () async {
      final client = _CachedDetailClient(age);
      final repository = await OpcUaRepository.connectWithClient(client);
      addTearDown(repository.dispose);
      repository.setModuleDetailActive('Press', true, containers: {'History'});
      final forest = await repository.forest().firstWhere((forest) =>
          forest.any((node) => node.path == 'Press' && node.tagAt(
              'Profiler/History[1]/CycleNo') != null))
          .timeout(const Duration(seconds: 3));
      expect(forest.singleWhere((node) => node.path == 'Press')
          .tagAt('Profiler/History[1]/CycleNo')!.usable,
          isFalse);
      expect(await repository.linkState().first, LinkState.live,
          reason: 'detail does not own the separately fresh station sample');
    });
  }

  test('visible containers include child timing but exclude closed tabs/roots',
      () async {
    final client = _SelectiveDetailClient();
    final repository = await OpcUaRepository.connectWithClient(client);
    addTearDown(repository.dispose);
    repository.setModuleDetailActive('Press', true,
        containers: {'History', 'StepStats', 'Timing'});
    await client.secondRead.future.timeout(const Duration(seconds: 2));
    expect(client.reads.first, unorderedEquals([
      '$base/Profiler/History[1]/CycleNo',
      '$base/Profiler/StepStats[1]/Mean',
      '$base/Ram/Timing/Rows[1]/Last',
    ]));
    final nextRead = client.reads.length;
    repository.setModuleDetailActive('Press', true, containers: {'Ring'});
    await Future<void>.delayed(const Duration(milliseconds: 140));
    expect(client.reads.skip(nextRead).last,
        ['$base/AlarmLog/Ring[1]/ReasonCode']);
    repository.setModuleDetailActive('Press', true, containers: const {});
    await Future<void>.delayed(const Duration(milliseconds: 60));
    final stopped = client.reads.length;
    await Future<void>.delayed(const Duration(milliseconds: 140));
    expect(client.reads.length, stopped);
  });

  test('completed detail sweep renews on its own cadence, without a poll gap',
      () async {
    final client = _SelectiveDetailClient()
      ..profile = {
        ...budget,
        'pollPeriodMs': 1000,
        'fastGoodMs': 2000,
        'fastExpiryMs': 3000,
        'slowPeriodMs': 80,
        'slowGoodMs': 150,
      };
    final repository = await OpcUaRepository.connectWithClient(client);
    addTearDown(repository.dispose);
    repository.setModuleDetailActive('Press', true, containers: {'History'});
    await client.secondRead.future.timeout(const Duration(milliseconds: 600));
    expect(client.snapshotAtRead[1], client.snapshotAtRead[0],
        reason: 'renewal must not wait for another complete snapshot');
    expect(client.startedAt[1] - client.startedAt[0],
        greaterThanOrEqualTo(const Duration(milliseconds: 80)),
        reason: 'fast replies must not cause an unbounded busy loop');
    repository.setModuleDetailActive('Press', false);
    await Future<void>.delayed(const Duration(milliseconds: 60));
    final stopped = client.reads.length;
    await Future<void>.delayed(const Duration(milliseconds: 150));
    expect(client.reads.length, stopped,
        reason: 'closing the view cancels the scheduled continuation');
  });

  test('large detail reads cannot delay complete samples or toggle the link',
      () async {
    final client = _DetailClient();
    final repository = await OpcUaRepository.connectWithClient(client);
    addTearDown(repository.dispose);
    final links = <LinkState>[];
    final subscription = repository.linkState().listen(links.add);
    addTearDown(subscription.cancel);
    repository.setModuleDetailActive('Press', true);
    await client.firstCycleComplete.future.timeout(const Duration(seconds: 3));
    final last = await repository
        .forest()
        .firstWhere((forest) =>
            forest.isNotEmpty &&
            forest.first.publishedValues.containsKey(_detailRelative(2620)))
        .timeout(const Duration(seconds: 3));
    expect(last.first.publishedValues[_detailRelative(2620)], 2620);
    expect(
        last.first.publishedTags[_detailRelative(2620)]!.typeName, 'Integer');
    expect(client.batchSizes.take(6), [512, 512, 512, 512, 512, 61]);
    expect(client.snapshotCalls, greaterThan(5));
    expect(links, everyElement(LinkState.live));
    expect(client.writes, isEmpty);
  });

  test('closing a scope discards its pending detail reply', () async {
    final client = _DetailClient()..holdFirst = true;
    final repository = await OpcUaRepository.connectWithClient(client);
    addTearDown(repository.dispose);
    repository.setModuleDetailActive('Press', true);
    await client.detailStarted.future;
    await Future<void>.delayed(const Duration(milliseconds: 340));
    expect(await repository.linkState().first, LinkState.live);
    repository.setModuleDetailActive('Press', false);
    client.detailRelease.complete();
    await Future<void>.delayed(const Duration(milliseconds: 70));
    final forest = await repository.forest().first;
    expect(forest.first.publishedTags.containsKey(_detailRelative(0)), isFalse);
    expect(client.batchSizes, [512]);
  });

  test('each detail batch expires without renewing it from live snapshots',
      () async {
    final client = _DetailClient()..holdSecond = true;
    final repository = await OpcUaRepository.connectWithClient(client);
    addTearDown(repository.dispose);
    repository.setModuleDetailActive('Press', true);
    final first = await repository
        .forest()
        .firstWhere((forest) =>
            forest.isNotEmpty &&
            forest.first.publishedValues.containsKey(_detailRelative(0)))
        .timeout(const Duration(seconds: 3));
    expect(first.first.publishedValues[_detailRelative(0)], 0);
    await client.detailStarted.future;
    await Future<void>.delayed(const Duration(milliseconds: 240));
    final forest = await repository.forest().first;
    expect(await repository.linkState().first, LinkState.live);
    expect(
        forest.first.publishedValues.containsKey(_detailRelative(0)), isFalse);
    expect(forest.first.publishedTags[_detailRelative(0)]!.quality,
        PublishedTagQuality.bad);
    repository.setModuleDetailActive('Press', false);
    client.detailRelease.complete();
  });

  test('fresh detail replies cannot renew a stalled complete station sample',
      () async {
    final client = _DetailClient()..holdFirst = true;
    final repository = await OpcUaRepository.connectWithClient(client);
    addTearDown(repository.dispose);
    repository.setModuleDetailActive('Press', true);
    await client.detailStarted.future;
    client.blockNextSnapshot = true;
    await client.snapshotBlocked.future;
    client.detailRelease.complete();
    await Future<void>.delayed(const Duration(milliseconds: 340));
    expect(await repository.linkState().first, LinkState.down);
    expect(await repository.forest().first, isEmpty);
    expect(await repository.setMode('Press', UnitMode.manual), isFalse);
    expect(client.writes, isEmpty);
    client.snapshotRelease.complete();
  });

  testWidgets('failed initial sample cancels its expiry timer', (tester) async {
    final client = _Client()..serverAge = 160;
    await expectLater(
        OpcUaRepository.connectWithClient(client), throwsFormatException);
    expect(client.closed, isTrue);
    // The widget harness rejects a pending timer at test exit. A failed first
    // connection must close repository resources as well as the transport.
  });

  test('unknown, missing ages, and invalid budget ordering fail closed', () {
    expect(OpcUaFreshnessBudget.parse({}), isNull);
    for (final changed in [
      {...budget, 'schemaVersion': 2},
      {...budget, 'schemaVersion': 1.0},
      {...budget, 'pollPeriodMs': 0},
      {...budget, 'fastExpiryMs': 150},
    ]) {
      expect(() => OpcUaFreshnessBudget.parse({'freshnessBudget': changed}),
          throwsFormatException);
    }
    for (final age in [null, -1, double.infinity, '0']) {
      expect(() => OpcUaFreshnessBudget.age(age), throwsFormatException);
    }
  });

  test('slow samples lose usability while fast data remains Good', () {
    final profile = OpcUaFreshnessBudget.parse({'freshnessBudget': budget})!;
    final document = {
      'values': {'fast': 1, 'slow': 2, 'bad': 3},
      'dataValues': {
        'fast': {'value': 1, 'status': 0, 'tier': 'fast', 'ageMs': 0},
        'slow': {'value': 2, 'status': 0, 'tier': 'slow', 'ageMs': 100},
        'bad': {'value': 3, 'status': 0x80320000, 'tier': 'fast', 'ageMs': 0},
      },
    };
    var result = profile.ageDocument(document, Duration.zero);
    expect(result['values'], {'fast': 1});
    final late = (result['dataValues'] as Map)['slow'] as Map;
    expect(late['status'], 0x40000000);
    expect(late['qualityReason'], 'read-late');
    result = profile.ageDocument(document, const Duration(milliseconds: 100));
    expect(
        ((result['dataValues'] as Map)['slow'] as Map)['status'], 0x80000000);
    expect(((result['dataValues'] as Map)['bad'] as Map)['status'], 0x80320000);
  });

  test('freshness cannot default missing DataValues to Good', () {
    final profile = OpcUaFreshnessBudget.parse({'freshnessBudget': budget})!;
    final result = profile.ageDocument({
      'values': {'a': 1},
      'dataValues': {}
    }, Duration.zero);
    expect(result['values'], isEmpty);
    expect(((result['dataValues'] as Map)['a'] as Map)['status'], 0x80000000);
  });

  test('stalled RPC withdraws shell and commands before transport timeout',
      () async {
    final client = _Client()..blockSecond = true;
    final repository = await OpcUaRepository.connectWithClient(client);
    addTearDown(repository.dispose);
    final links = <LinkState>[];
    final subscription = repository.linkState().listen(links.add);
    addTearDown(subscription.cancel);
    await client.blocked.future;
    await Future<void>.delayed(const Duration(milliseconds: 340));
    expect(links,
        containsAllInOrder([LinkState.live, LinkState.stale, LinkState.down]));
    expect(client.release.isCompleted, isFalse);
    expect(await repository.forest().first, isEmpty);
    expect(await repository.setMode('Press', UnitMode.manual), isFalse);
    expect(client.writes, isEmpty);
    client.stopAfterSecond = true;
    client.release.complete();
    await Future<void>.delayed(const Duration(milliseconds: 10));
    expect(await repository.linkState().first, LinkState.down,
        reason: 'a delayed reply cannot renew a complete sample');
    final recovered = repository
        .linkState()
        .firstWhere((state) => state == LinkState.live)
        .timeout(const Duration(seconds: 2));
    client.stopAfterSecond = false;
    await recovered;
    expect(await repository.forest().first, isNotEmpty);
  });

  test('server-aged first frame is refused before connecting', () async {
    final client = _Client()..serverAge = 160;
    await expectLater(
        OpcUaRepository.connectWithClient(client), throwsFormatException);
    expect(client.closed, isTrue);
  });

  test('a present malformed profile cannot fall back to a legacy live frame',
      () async {
    final client = _Client()..profile = {...budget, 'schemaVersion': 2};
    await expectLater(
        OpcUaRepository.connectWithClient(client), throwsFormatException);
    expect(client.closed, isTrue);
  });

  test('profile cannot disappear after a validated session', () async {
    final client = _Client()..omitAfterFirst = true;
    final repository = await OpcUaRepository.connectWithClient(client);
    addTearDown(repository.dispose);
    await Future<void>.delayed(const Duration(milliseconds: 70));
    expect(await repository.linkState().first, LinkState.stale);
    expect(await repository.setMode('Press', UnitMode.manual), isFalse);
    expect(client.writes, isEmpty);
  });
}

String _detailRelative(int index) => 'Profiler/History/History[1]/Field$index';

class _SelectiveDetailClient extends _Client
    implements OpcUaBulkReadClient {
  final reads = <List<String>>[];
  final snapshotAtRead = <int>[];
  final startedAt = <Duration>[];
  final clock = Stopwatch()..start();
  final secondRead = Completer<void>();

  @override
  Future<Map<String, Object?>> snapshot() async {
    final doc = await super.snapshot();
    final values = {
      ...doc['values'] as Map<String, Object?>,
      '$base/Ram/Status/Name': 'Press.Ram',
      '$base/Ram/Status/ModuleType': ModuleType.controlModule.index,
      '$base/Ram/Status/State': ExecState.ready.index,
      'PLC1/MAIN/Other/Status/Name': 'Other',
      'PLC1/MAIN/Other/Status/ModuleType': ModuleType.unit.index,
      'PLC1/MAIN/Other/Status/State': ExecState.ready.index,
    };
    return {
      ...doc,
      'values': values,
      'dataValues': {
        for (final item in values.entries)
          item.key: {'value': item.value, 'status': 0, 'tier': 'fast', 'ageMs': 0},
      },
      'paths': [
        ...values.keys,
        '$base/Profiler/History[1]/CycleNo',
        '$base/Profiler/StepStats[1]/Mean',
        '$base/Ram/Timing/Rows[1]/Last',
        '$base/AlarmLog/Ring[1]/ReasonCode',
        '$base/SequenceSteps[1]/Visited',
        '$base/ConfigSetDocumentLine',
        'PLC1/MAIN/Other/Profiler/History[1]/CycleNo',
      ],
    };
  }

  @override
  Future<Map<String, Object?>> readValues(List<String> paths) async {
    reads.add(List.of(paths));
    snapshotAtRead.add(snapshotCalls);
    startedAt.add(clock.elapsed);
    if (reads.length == 2) secondRead.complete();
    await Future<void>.delayed(const Duration(milliseconds: 40));
    return {for (final path in paths) path: 1};
  }

}

class _StreamingDetailClient extends _SelectiveDetailClient
    implements OpcUaTieredReadClient {
  Set<String> slow = {}, excluded = {};
  bool overlappingTiers = false;
  num detailAge = 0;

  @override
  Future<Map<String, Object?>> snapshot() async {
    final doc = await super.snapshot();
    return {
      ...doc,
      'values': {...doc['values'] as Map, for (final path in slow) path: 1},
      'dataValues': {
        ...doc['dataValues'] as Map,
        for (final path in slow)
          path: {'value': 1, 'status': 0, 'tier': 'slow', 'ageMs': detailAge},
      },
    };
  }

  @override
  Future<void> setExcludedPaths(Iterable<String> paths) async {
    excluded = paths.toSet();
    overlappingTiers |= slow.intersection(excluded).isNotEmpty;
  }
  @override
  Future<void> setSlowPaths(Iterable<String> paths) async {
    slow = paths.toSet();
    overlappingTiers |= slow.intersection(excluded).isNotEmpty;
  }
  @override
  Future<void> refreshSlowPaths() async {}
}

class _CachedDetailClient extends _SelectiveDetailClient
    implements OpcUaDataValueReadClient {
  final num sourceAge;
  _CachedDetailClient(this.sourceAge);
  @override
  Future<Map<String, Object?>> readDataValues(List<String> paths) async {
    final values = await super.readValues(paths);
    return {
      'values': values,
      'dataValues': {
        for (final path in paths) path: {'status': 0, 'ageMs': sourceAge},
      },
    };
  }
}

/// The reported deployment has 2,621 detail leaves: six bounded reads. The
/// total detail cycle exceeds the station budget while each full sample stays
/// current. Blocked detail/snapshot RPCs are independent to exercise ownership.
class _DetailClient extends _Client
    implements OpcUaBulkReadClient {
  bool holdFirst = false, holdSecond = false, blockNextSnapshot = false;
  final detailStarted = Completer<void>(), detailRelease = Completer<void>();
  final snapshotBlocked = Completer<void>(),
      snapshotRelease = Completer<void>();
  final firstCycleComplete = Completer<void>();
  final batchSizes = <int>[];

  @override
  Future<Map<String, Object?>> snapshot() async {
    if (blockNextSnapshot) {
      if (!snapshotBlocked.isCompleted) snapshotBlocked.complete();
      await snapshotRelease.future;
    }
    final doc = await super.snapshot();
    return {
      ...doc,
      'paths': [
        ...(doc['values'] as Map).keys,
        for (var i = 0; i < 2621; i++) '$base/${_detailRelative(i)}',
      ]
    };
  }

  @override
  Future<Map<String, Object?>> readValues(List<String> paths) async {
    batchSizes.add(paths.length);
    if ((holdFirst && batchSizes.length == 1) ||
        (holdSecond && batchSizes.length == 2)) {
      detailStarted.complete();
      await detailRelease.future;
    } else {
      // A bulk caller may give the Web client the entire scope; that client
      // serves it as sequential bounded RPCs. Model the whole cost as well as
      // the repository's independently scheduled one-RPC batches.
      final chunks = (paths.length + opcUaTargetReadBatchSize - 1) ~/
          opcUaTargetReadBatchSize;
      await Future<void>.delayed(Duration(milliseconds: 40 * chunks));
    }
    if (batchSizes.length == 6 && !firstCycleComplete.isCompleted) {
      firstCycleComplete.complete();
    }
    return {
      for (final path in paths) path: int.parse(path.split('Field').last)
    };
  }

}

class _SlowSampleClient extends _Client {
  final starts = <Duration>[];
  final finishes = <Duration>[];
  final clock = Stopwatch()..start();
  final fourthRead = Completer<void>();
  int concurrent = 0, maximumConcurrent = 0;
  _SlowSampleClient() {
    profile = {...budget, 'pollPeriodMs': 150, 'fastGoodMs': 500,
      'fastExpiryMs': 800, 'slowPeriodMs': 150, 'slowGoodMs': 500,
      'slowExpiryMs': 800};
  }
  @override
  Future<Map<String, Object?>> snapshot() async {
    starts.add(clock.elapsed);
    concurrent++;
    if (concurrent > maximumConcurrent) maximumConcurrent = concurrent;
    final acquisition = Stopwatch()..start();
    await Future<void>.delayed(const Duration(milliseconds: 180));
    serverAge = acquisition.elapsedMilliseconds;
    final doc = await super.snapshot();
    finishes.add(clock.elapsed);
    concurrent--;
    if (starts.length == 4 && !fourthRead.isCompleted) fourthRead.complete();
    return {...doc, 'responseProcessingMs': acquisition.elapsedMilliseconds};
  }
}

class _Client implements OpcUaSessionClient {
  var snapshotCalls = 0;
  var serverAge = 0;
  var blockSecond = false,
      stopAfterSecond = false,
      closed = false,
      omitAfterFirst = false;
  Map<String, Object?> profile = budget;
  final blocked = Completer<void>(), release = Completer<void>();
  final writes = <Object>[];

  @override
  Future<Map<String, Object?>> snapshot() async {
    snapshotCalls++;
    if (snapshotCalls == 2 && blockSecond) {
      blocked.complete();
      await release.future;
    } else if (snapshotCalls > 2 && stopAfterSecond) {
      throw StateError('fixture still disconnected');
    }
    final values = <String, Object?>{
      '$base/Status/Name': 'Press',
      '$base/Status/ModuleType': ModuleType.unit.index,
      '$base/Status/State': ExecState.ready.index,
      '$base/ModeActivePublished': UnitMode.auto.index,
      '$base/SupportedModesPublished': [true, true, true, true],
      '$base/HmiRequest/Sequence': 0,
      '$base/HmiResponse/AckSequence': 0,
    };
    return {
      'protocol': 'fraktal.opcua.snapshot.v1',
      'truncated': false,
      'nodeCount': values.length,
      'values': values,
      if (!omitAfterFirst || snapshotCalls == 1) 'freshnessBudget': profile,
      'sampleAgeMs': serverAge,
      'dataValues': {
        for (final item in values.entries)
          item.key: {
            'value': item.value,
            'status': 0,
            'tier': 'fast',
            'ageMs': serverAge,
          }
      },
    };
  }

  @override
  Future<bool> write(String path, OpcUaWriteType type, Object value) async {
    writes.add((path, value));
    return true;
  }

  @override
  Future<void> close() async {
    closed = true;
  }
}
