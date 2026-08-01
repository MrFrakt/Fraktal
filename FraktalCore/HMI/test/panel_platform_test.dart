// Closing the HMI removes the operator's view of the process, so it is gated by
// an access level (editable per deployment) and confirmed before it happens.
import 'package:flutter_test/flutter_test.dart';

import 'package:fraktal_hmi/data/panel_platform.dart';
import 'package:fraktal_hmi/data/sim_repository.dart';
import 'package:fraktal_hmi/domain/types.dart';
import 'package:fraktal_hmi/state/app_state.dart';

class _FakePanel extends PanelPlatform {
  final bool supportsClose;
  int closes = 0;
  bool? lastKeepAwake;
  bool fullscreen = false;
  _FakePanel({this.supportsClose = true});

  @override
  bool get canCloseApp => supportsClose;
  @override
  bool get canToggleFullscreen => true;
  @override
  Future<void> closeApp() async => closes++;
  @override
  Future<bool> isFullscreen() async => fullscreen;
  @override
  Future<bool> setFullscreen(bool value) async => fullscreen = value;
  @override
  Future<void> setKeepAwake(bool value) async => lastKeepAwake = value;
}

void main() {
  test('closing is refused below the configured level', () async {
    final panel = _FakePanel();
    // The sim publishes AccessLevel.none, below the TECHNICIAN default.
    final app = AppState(SimRepository(), panel: panel);
    addTearDown(app.dispose);

    expect(app.mayCloseApp, isFalse);
    expect(await app.closeApp(), isFalse,
        reason: 'refused calls report failure so the UI can explain');
    expect(panel.closes, 0, reason: 'the host must never be asked');
  });

  test('the required level is configurable per deployment', () async {
    final panel = _FakePanel();
    final app = AppState(
      SimRepository(),
      // A desk station may legitimately leave this open.
      config: const HmiConfig(closeAppMinLevel: AccessLevel.none),
      panel: panel,
    );
    addTearDown(app.dispose);

    expect(app.mayCloseApp, isTrue);
    expect(await app.closeApp(), isTrue);
    expect(panel.closes, 1);
  });

  test('a host that cannot close is never offered it', () async {
    // Web: a browser refuses to close a tab it did not open.
    final panel = _FakePanel(supportsClose: false);
    final app = AppState(
      SimRepository(),
      config: const HmiConfig(closeAppMinLevel: AccessLevel.none),
      panel: panel,
    );
    addTearDown(app.dispose);

    expect(app.mayCloseApp, isFalse);
    expect(await app.closeApp(), isFalse);
    expect(panel.closes, 0);
  });

  test('the real host advertises capabilities without throwing', () {
    // Guards the conditional import: the stub/io/web pick must always resolve.
    final panel = createPanelPlatform();
    expect(panel.canCloseApp, isA<bool>());
    expect(panel.canToggleFullscreen, isA<bool>());
    expect(panel.needsFullscreenGesture, isA<bool>());
  });
}
