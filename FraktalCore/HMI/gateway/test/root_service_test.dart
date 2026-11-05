/// RootService's restore loop against a scripted port: what it retries, and when.
library;

import 'dart:io';

import 'package:fraktal_gateway/host_adapter.dart';
import 'package:fraktal_opcua_client/cip_host_service.dart';
import 'package:test/test.dart';

/// A restoring controller whose every restore verdict is the access denial.
final class DenyingPort implements CipHostPort {
  int permits = 1, opens = 0, deniedKeyNumber = 99;
  bool _verdictPending = false;

  @override
  String get root => 'Press';

  @override
  Future<Map<String, Object?>> reply() async {
    if (_verdictPending) {
      _verdictPending = false;
      return {'JobSequence': 7, 'JobPhase': CipHost.store, 'JobBool': 0, 'JobInt': deniedKeyNumber,
              'JobService': CipHost.liveDocuments, 'JobOperation': 29, 'NextChunk': 1};
    }
    return {'JobSequence': 0, 'Restoring': 1, 'SessionPermits': permits};
  }

  @override
  Future<Map<String, Object?>> submit(Map<String, Object?> envelope, Map<String, Object?> body) async {
    if (envelope['JobSequence'] == 0) {
      opens++;
      _verdictPending = envelope['Final'] == 1;
    }
    return {'Accepted': 1, 'JobSequence': 7, 'JobService': CipHost.liveDocuments, 'JobOperation': 29,
            'JobPhase': CipHost.restore, 'NextChunk': 1};
  }

  @override
  Future<CipHostFacts> facts() async => const CipHostFacts('Press', 4242, [], [], 0);
  @override
  Future<String> keyText(int numeric) async => numeric == deniedKeyNumber ? deniedKey : '';
  @override
  Future<void> wait() async {}
}

void main() {
  test('a denied restore is not retried until the session permission drops and returns', () async {
    final folder = await Directory.systemTemp.createTemp('fraktal_root_service_');
    addTearDown(() => folder.delete(recursive: true));
    final medium = FileMedium(Directory('${folder.path}/live'));
    medium.write('Press.station', [
      {'set': liveName, 'root': 'Press', 'schema': 1, 'configRev': 4242, 'kind': 1, 'model': '',
       'records': 0, 'created': 0, 'clock': 0}
    ]);
    final port = DenyingPort();
    final service = RootService(port, FileStore(Directory('${folder.path}/sets')), medium,
        clock: () => 0, keepInterval: 0, retry: 0);
    await service.step();
    expect(port.opens, 1);
    expect(service.health.error, contains('may not load sets'));
    for (var i = 0; i < 5; i++) {
      await service.step();
    }
    expect(port.opens, 1, reason: 'no retry under the permission it was denied under');
    port.permits = 0;
    await service.step();
    expect(port.opens, 1, reason: 'no restore without permission');
    port.permits = 1;
    await service.step();
    expect(port.opens, 2, reason: 'a returned permission is a new session');
  });
}
