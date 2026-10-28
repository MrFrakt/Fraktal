/// Panel-host services that differ per platform: closing the application,
/// going fullscreen, and keeping the device awake.
///
/// A machine HMI runs unattended for a shift: the screen must not blank, and a
/// maximized window should fill the panel with no OS chrome. None of this is
/// PLC data, so it stays out of `PlcRepository` (Core O9: minimum surface) and
/// behind this one seam, with a no-op default so an unsupported host degrades
/// quietly rather than crashing.
library;

abstract class PanelPlatform {
  const PanelPlatform();

  /// Whether this host can close the app from inside it. False on Web, where a
  /// script may not close a tab it did not open.
  bool get canCloseApp => false;

  /// Whether fullscreen can be toggled by the app.
  bool get canToggleFullscreen => false;

  /// Whether the operator must trigger fullscreen themselves. Browsers only
  /// grant the Fullscreen API from a user gesture, so Web shows a button while
  /// native follows the window state automatically.
  bool get needsFullscreenGesture => false;

  /// Quit the application (native panels only).
  Future<void> closeApp() async {}

  /// Enter/leave fullscreen. Returns the state actually reached.
  Future<bool> setFullscreen(bool value) async => false;

  Future<bool> isFullscreen() async => false;

  /// Hold a wake lock so the panel does not sleep or blank mid-shift.
  /// Idempotent; safe to call repeatedly.
  Future<void> setKeepAwake(bool value) async {}
}

/// Degrades to no-ops (tests, unsupported hosts).
class NoopPanelPlatform extends PanelPlatform {
  const NoopPanelPlatform();
}
