import 'dart:async';
import 'dart:math';

import 'package:flutter_test/flutter_test.dart';
import 'package:fraktal_hmi/data/opcua_session_client.dart';
import 'package:fraktal_hmi/data/reconnecting_opcua_session_client.dart';

void main() {
  test('concurrent reconnect snapshots wait for the restored read profile',
      () async {
    final first = _TierSession()..failSnapshotTransportOnce = true;
    final replacement = _TierSession(hold: true);
    final sessions = [first, replacement];
    var calls = 0;
    final client = await ReconnectingOpcUaSessionClient.connect(
      factory: () async => sessions[calls++],
      baseBackoff: const Duration(milliseconds: 1),
      maxBackoff: const Duration(milliseconds: 1),
    );
    addTearDown(client.close);
    expect(client.readTiersAreAtomic, true);
    await client.setReadTiers(['slow'], ['excluded']);
    await expectLater(
        client.snapshot(), throwsA(isA<OpcUaTransportException>()));
    await Future<void>.delayed(const Duration(milliseconds: 3));
    final a = client.snapshot();
    await replacement.restoring.future;
    final b = client.snapshot();
    await Future<void>.delayed(Duration.zero);
    expect(replacement.snapshotCalls, 0);
    // A view may change again while the connection is restoring its profile.
    await client.setSlowPaths(['new-slow']);
    await client.setExcludedPaths(['new-excluded']);
    replacement.release.complete();
    expect(await Future.wait([a, b]),
        [replacement.document, replacement.document]);
    expect(replacement.slow, ['new-slow']);
    expect(replacement.excluded, ['new-excluded']);
    expect(calls, 2);
  });

  test('an unsupported batch tier update does not touch a legacy session',
      () async {
    final legacy = _Session();
    final client = await ReconnectingOpcUaSessionClient.connect(
        factory: () async => legacy);
    addTearDown(client.close);
    expect(client.readTiersAreAtomic, false);
    await expectLater(
        client.setReadTiers(['slow'], ['excluded']), throwsUnsupportedError);
    expect(legacy.closed, false);
    expect(await client.snapshot(), legacy.document);
  });
  test('transport loss reconnects snapshots but never replays a write',
      () async {
    final failed = _Session(failWriteTransport: true);
    final replacement = _Session();
    final sessions = [failed, replacement];
    var factoryCalls = 0;
    final client = await ReconnectingOpcUaSessionClient.connect(
      factory: () async => sessions[factoryCalls++],
      baseBackoff: const Duration(milliseconds: 1),
      maxBackoff: const Duration(milliseconds: 1),
      random: Random(1),
    );
    addTearDown(client.close);

    await expectLater(
      client.write('Unit/HmiRequest/Sequence', OpcUaWriteType.uint32, 1),
      throwsA(isA<OpcUaTransportException>()),
    );
    expect(failed.writeCalls, 1);
    expect(failed.closed, isTrue);
    expect(replacement.writeCalls, 0);

    await Future<void>.delayed(const Duration(milliseconds: 3));
    expect(await client.snapshot(), replacement.document);
    expect(factoryCalls, 2);
    expect(replacement.writeCalls, 0,
        reason: 'an ambiguous command must not be replayed after reconnect');
  });

  test('remote refusal keeps the healthy socket generation', () async {
    final session = _Session(failSnapshotRemoteOnce: true);
    var factoryCalls = 0;
    final client = await ReconnectingOpcUaSessionClient.connect(
      factory: () async {
        factoryCalls++;
        return session;
      },
      baseBackoff: const Duration(milliseconds: 1),
      maxBackoff: const Duration(milliseconds: 1),
    );
    addTearDown(client.close);

    await expectLater(
      client.snapshot(),
      throwsA(isA<OpcUaRemoteException>()),
    );
    expect(await client.snapshot(), session.document);
    expect(factoryCalls, 1);
    expect(session.closed, isFalse);
  });

  test('concurrent reconnect snapshots share one connection attempt', () async {
    final first = _Session(failSnapshotTransportOnce: true);
    final replacement = _Session();
    final connectStarted = Completer<void>();
    final releaseConnect = Completer<void>();
    var factoryCalls = 0;
    final client = await ReconnectingOpcUaSessionClient.connect(
      factory: () async {
        factoryCalls++;
        if (factoryCalls == 1) return first;
        connectStarted.complete();
        await releaseConnect.future;
        return replacement;
      },
      baseBackoff: const Duration(milliseconds: 1),
      maxBackoff: const Duration(milliseconds: 1),
    );
    addTearDown(client.close);
    await expectLater(
      client.snapshot(),
      throwsA(isA<OpcUaTransportException>()),
    );
    await Future<void>.delayed(const Duration(milliseconds: 3));

    final a = client.snapshot();
    await connectStarted.future;
    final b = client.snapshot();
    releaseConnect.complete();
    expect(await Future.wait([a, b]),
        [replacement.document, replacement.document]);
    expect(factoryCalls, 2);
  });
}

class _TierSession extends _Session implements OpcUaReadTierBatchClient {
  final bool hold;
  final restoring = Completer<void>(), release = Completer<void>();
  List<String> slow = [], excluded = [];
  int snapshotCalls = 0;
  _TierSession({this.hold = false});
  @override
  bool get readTiersAreAtomic => true;
  @override
  Future<void> setReadTiers(
      Iterable<String> slowPaths, Iterable<String> excludedPaths) async {
    if (hold && !restoring.isCompleted) {
      restoring.complete();
      await release.future;
    }
    slow = slowPaths.toList();
    excluded = excludedPaths.toList();
  }

  @override
  Future<Map<String, Object?>> snapshot() {
    snapshotCalls++;
    expect(slow, isNotEmpty, reason: 'a default profile must not be exposed');
    return super.snapshot();
  }
}

class _Session implements OpcUaSessionClient {
  final bool failWriteTransport;
  bool failSnapshotRemoteOnce;
  bool failSnapshotTransportOnce;
  int writeCalls = 0;
  bool closed = false;
  final Map<String, Object?> document = {
    'protocol': 'fraktal.opcua.snapshot.v1',
    'values': <String, Object?>{},
  };

  _Session({
    this.failWriteTransport = false,
    this.failSnapshotRemoteOnce = false,
    this.failSnapshotTransportOnce = false,
  });

  @override
  Future<Map<String, Object?>> snapshot() async {
    if (failSnapshotTransportOnce) {
      failSnapshotTransportOnce = false;
      throw const OpcUaTransportException('socket closed');
    }
    if (failSnapshotRemoteOnce) {
      failSnapshotRemoteOnce = false;
      throw const OpcUaRemoteException('PLC rejected snapshot');
    }
    return document;
  }

  @override
  Future<bool> write(String path, OpcUaWriteType type, Object value) async {
    writeCalls++;
    if (failWriteTransport) {
      throw const OpcUaTransportException('write outcome unknown');
    }
    return true;
  }

  @override
  Future<void> close() async {
    closed = true;
  }
}
