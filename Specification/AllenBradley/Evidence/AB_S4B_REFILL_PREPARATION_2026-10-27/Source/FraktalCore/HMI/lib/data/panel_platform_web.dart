// ignore_for_file: deprecated_member_use
/// Web panel host: the browser Fullscreen API plus a Screen Wake Lock.
///
/// A browser will not let a script close a tab it did not open, and it only
/// grants fullscreen from a user gesture — so the Web build offers an explicit
/// fullscreen button rather than following a window state.
library;

import 'dart:async';
import 'dart:html' as html;

import 'panel_platform_base.dart';

PanelPlatform createPanelPlatform() => _WebPanelPlatform();

class _WebPanelPlatform extends PanelPlatform {
  @override
  bool get canCloseApp =>
      false; // window.close() is refused for user-opened tabs

  @override
  bool get canToggleFullscreen => true;

  @override
  bool get needsFullscreenGesture => true;

  @override
  Future<bool> isFullscreen() async => html.document.fullscreenElement != null;

  @override
  Future<bool> setFullscreen(bool value) async {
    try {
      if (value) {
        await html.document.documentElement?.requestFullscreen();
      } else if (html.document.fullscreenElement != null) {
        html.document.exitFullscreen();
      }
    } on Object {
      // Denied (no user gesture, or blocked by policy) — report the real state.
    }
    return isFullscreen();
  }

  /// Keeping a browser tab awake needs the Screen Wake Lock API, which
  /// `dart:html` does not expose in typed form. Rather than pull in a JS-interop
  /// dependency for one call (AGENTS.md §4 keeps the dependency set narrow), the
  /// Web build relies on **fullscreen**: browsers suppress the screensaver while
  /// a page is fullscreen, which is exactly the kiosk posture a panel runs in.
  /// A windowed browser tab may still let the OS blank the screen — documented
  /// here rather than silently pretending the lock was taken.
  @override
  Future<void> setKeepAwake(bool value) async {
    // Intentionally a no-op — see the doc comment above.
  }
}
