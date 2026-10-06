/// Native panel host (Windows/Linux desktop panels).
///
/// Fullscreen and the wake lock are driven through a [MethodChannel] into the
/// platform runner, so no extra package is pulled in (AGENTS.md §4 keeps the
/// dependency set deliberately narrow). A host that has not implemented the
/// channel simply reports failure and the HMI carries on windowed.
library;

import 'dart:io';

import 'package:flutter/services.dart';

import 'panel_platform_base.dart';

PanelPlatform createPanelPlatform() => _NativePanelPlatform();

class _NativePanelPlatform extends PanelPlatform {
  static const _channel = MethodChannel('fraktal/panel');

  bool get _desktop =>
      Platform.isWindows || Platform.isLinux || Platform.isMacOS;

  @override
  bool get canCloseApp => _desktop;

  @override
  bool get canToggleFullscreen => _desktop;

  /// Native follows the window state automatically (see PanelWindowWatcher), so
  /// no operator gesture is required.
  @override
  bool get needsFullscreenGesture => false;

  @override
  Future<void> closeApp() async {
    try {
      await _channel.invokeMethod<void>('closeApp');
    } on Object {
      // The runner may not implement the channel; exiting directly is the
      // documented fallback for a kiosk panel and still runs Dart finalizers.
      exit(0);
    }
  }

  @override
  Future<bool> isFullscreen() async {
    try {
      return await _channel.invokeMethod<bool>('isFullscreen') ?? false;
    } on Object {
      return false;
    }
  }

  @override
  Future<bool> setFullscreen(bool value) async {
    try {
      return await _channel
              .invokeMethod<bool>('setFullscreen', {'value': value}) ??
          false;
    } on Object {
      return false;
    }
  }

  @override
  Future<void> setKeepAwake(bool value) async {
    try {
      await _channel.invokeMethod<void>('setKeepAwake', {'value': value});
    } on Object {
      // Best effort: a panel that still blanks is a nuisance, not a failure.
    }
  }
}
