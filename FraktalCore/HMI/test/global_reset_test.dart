// The always-visible fault clear (§8.3(b)) must reach every root Unit this HMI
// shows — and nothing beyond it. The PLC has no super-root to reset (§3.1a is a
// forest of peers), so the fan-out is the client's job and its scope is the HMI's
// assigned root set.
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter/material.dart';

import 'package:fraktal_hmi/data/scoped_plc_repository.dart';
import 'package:fraktal_hmi/data/sim_repository.dart';
import 'package:fraktal_hmi/main.dart';
import 'package:fraktal_hmi/state/app_state.dart';

class _RecordingRepository extends SimRepository {
  final List<String> resets = [];

  @override
  Future<bool> operatorReset(String unitPath) {
    resets.add(unitPath);
    return super.operatorReset(unitPath);
  }
}

void main() {
  testWidgets('one press resets every root shown on this HMI', (tester) async {
    tester.view.physicalSize = const Size(1400, 900);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    final repo = _RecordingRepository();
    final app = AppState(repo);
    await tester.pumpWidget(FraktalHmiApp(app: app));
    await tester.pump(const Duration(seconds: 2));

    final visible = app.visibleRoots.map((root) => root.path).toList();
    expect(visible.length, greaterThan(1),
        reason:
            'the sim publishes a multi-root forest, so fan-out is testable');

    await tester.tap(find.byKey(const Key('global-reset')));
    await tester.pump(const Duration(milliseconds: 100));

    expect(repo.resets, visible,
        reason: 'every visible root gets its own gated OPERATOR_RESET request');
    app.dispose();
  });

  test('the fan-out cannot reach a root outside this HMI scope', () async {
    final repo = _RecordingRepository();
    final scoped = ScopedPlcRepository(
      repo,
      allowedRoots: const ['StationA'],
      configured: true,
    );
    addTearDown(scoped.dispose);

    // Belt and braces: even if a caller passed an unscoped path, the repository
    // clamps it before the request reaches the transport.
    expect(await scoped.operatorReset('ConveyorB'), isFalse);
    expect(repo.resets, isEmpty);
    expect(await scoped.operatorReset('StationA'), isTrue);
    expect(repo.resets, ['StationA']);
  });
}
