/// Keeps the panel behaving like a machine terminal rather than a desktop app:
///
///  * **Maximized ⇒ fullscreen.** An operator who maximizes the window wants the
///    whole panel, not a title bar and taskbar. Restoring the window leaves
///    fullscreen again, so this never traps anyone in a chromeless screen.
///  * **Never sleep while live.** A screen that blanks mid-shift hides machine
///    state, so a wake lock is held for as long as the HMI is running.
///
/// Both are best-effort: a host that does not implement them degrades to a
/// normal window (see [PanelPlatform]).
library;

import 'package:flutter/widgets.dart';

import '../data/panel_platform.dart';

class PanelWindowWatcher extends StatefulWidget {
  final Widget child;
  final PanelPlatform platform;
  const PanelWindowWatcher({
    super.key,
    required this.child,
    required this.platform,
  });

  @override
  State<PanelWindowWatcher> createState() => _PanelWindowWatcherState();
}

class _PanelWindowWatcherState extends State<PanelWindowWatcher>
    with WidgetsBindingObserver {
  bool _fullscreen = false;
  Size? _lastSize;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    // Hold the wake lock for the whole session, not just while in fullscreen:
    // a windowed panel showing an alarm must stay lit too.
    widget.platform.setKeepAwake(true);
    WidgetsBinding.instance.addPostFrameCallback((_) => _syncFullscreen());
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    widget.platform.setKeepAwake(false);
    super.dispose();
  }

  @override
  void didChangeMetrics() {
    super.didChangeMetrics();
    _syncFullscreen();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    super.didChangeAppLifecycleState(state);
    // Some hosts drop a wake lock when the app is backgrounded; re-take it.
    if (state == AppLifecycleState.resumed) {
      widget.platform.setKeepAwake(true);
    }
  }

  /// Follows the window size: at (or within a hair of) the display size the
  /// window is maximized, so go fullscreen; anything smaller returns to a
  /// normal window. Web is excluded — a browser only grants fullscreen from a
  /// user gesture, so it gets an explicit button instead.
  Future<void> _syncFullscreen() async {
    final platform = widget.platform;
    if (!platform.canToggleFullscreen || platform.needsFullscreenGesture) {
      return;
    }
    final view = WidgetsBinding.instance.platformDispatcher.views.firstOrNull;
    if (view == null) return;
    final logical = view.physicalSize / view.devicePixelRatio;
    if (logical.isEmpty) return;
    if (_lastSize == logical) return;
    _lastSize = logical;

    final display = view.display.size / view.devicePixelRatio;
    // A maximized window is inset only by the taskbar/title bar; treat anything
    // covering nearly the whole display as "the operator wants the full panel".
    const slack = 96.0;
    final maximized = logical.width >= display.width - slack &&
        logical.height >= display.height - slack;
    if (maximized == _fullscreen) return;
    final reached = await platform.setFullscreen(maximized);
    if (mounted) _fullscreen = reached;
  }

  @override
  Widget build(BuildContext context) => widget.child;
}
