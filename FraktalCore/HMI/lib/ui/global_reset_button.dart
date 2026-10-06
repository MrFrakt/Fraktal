/// Always-visible fault-clear control (§8.3(b)), as an app-bar action.
///
/// One press sends `OPERATOR_RESET` to EVERY root Unit this HMI shows — the same
/// gated request the per-module reset uses, once per root, never anything wider.
/// Scope is the HMI's assigned root set (§3.1a is a forest of peers with no shared
/// super-root, so there is nothing to "reset globally" in the PLC): the fan-out is
/// deliberately a client concern, `ScopedPlcRepository` re-clamps every call to the
/// assigned scope, and the PLC re-checks §7.7 authority per root regardless.
///
/// The equivalent hardwired button is NOT this widget: a cabinet pushbutton calls
/// `FB_UnitBase.RequestLocalReset()` from the project's hardware driver, once per
/// root Unit it should clear, so one physical input can serve one Unit or several.
library;

import 'package:flutter/material.dart';
import '../domain/module_node.dart';
import '../domain/types.dart';
import '../state/app_state.dart';
import '../localization/localized_text.dart';
import 'app_theme.dart';

/// TRUE when this root has something a reset could actually clear: a blocking
/// manual-reset event on its log, or a latched fault anywhere in its subtree.
bool rootNeedsReset(ModuleNode root) {
  if (root.blocking) return true;
  bool faulted(ModuleNode n) => n.faultActive || n.children.any(faulted);
  return faulted(root);
}

/// A circled-checkmark app-bar action. Armed (error-tinted, with a count badge)
/// when any visible root is latched; quiet but always present otherwise, so its
/// position never moves and muscle memory holds (Core O3: recoverability visible).
class GlobalResetButton extends StatefulWidget {
  final AppState app;
  const GlobalResetButton({super.key, required this.app});

  @override
  State<GlobalResetButton> createState() => _GlobalResetButtonState();
}

class _GlobalResetButtonState extends State<GlobalResetButton> {
  bool _busy = false;

  Future<void> _resetAll() async {
    final app = widget.app;
    final roots = app.visibleRoots;
    if (roots.isEmpty || _busy) return;
    setState(() => _busy = true);
    var accepted = 0;
    final refused = <String>[];
    try {
      for (final root in roots) {
        // Per-root authority: the session is published per root (§7.7), so a
        // fan-out must ask each one rather than the selected module's session.
        final session = root.access ?? const AccessSession();
        if (!app.permitsLocal(GatedAction.alarmReset, forSession: session)) {
          refused.add(root.path);
          continue;
        }
        if (await app.repo.operatorReset(root.path)) {
          accepted++;
        } else {
          refused.add(root.path);
        }
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
    if (!mounted) return;
    final messenger = ScaffoldMessenger.of(context);
    // Replace any previous result instead of queueing behind it: repeated presses
    // would otherwise play the banners back to back and look like one that never
    // clears. The outcome is a transient confirmation — the authoritative state is
    // the reset button's own armed/idle rendering, which is always on screen.
    messenger.hideCurrentSnackBar();
    final blocked = refused.isEmpty ? null : refused.first;
    final message = blocked == null
        ? context.tr('std.alarm.resetAllAccepted', {'count': '$accepted'})
        : context.tr('std.alarm.resetAllPartial', {
            'count': '$accepted',
            'refused': '${refused.length}',
          });
    messenger.showSnackBar(SnackBar(
      duration: const Duration(seconds: 10),
      // Deliberately NO SnackBarAction: Flutter never auto-dismisses a SnackBar
      // that has one — it waits for the user — so attaching "Why?" silently
      // defeated `duration` and left the banner covering the machine view.
      // Tapping the banner itself opens the report, which keeps the §7.8
      // "a refusal is never a dead end" affordance AND lets it time out.
      content: blocked == null
          ? LText(message)
          : InkWell(
              onTap: () => app.showReleaseReportAction(
                blocked,
                GatedAction.alarmReset,
                context.tr('std.alarm.resetAll'),
              ),
              child: Row(children: [
                Expanded(child: LText(message)),
                const SizedBox(width: 12),
                LText(context.tr('std.release.why'),
                    style: const TextStyle(fontWeight: FontWeight.w700)),
              ]),
            ),
    ));
  }

  @override
  Widget build(BuildContext context) {
    final app = widget.app;
    final roots = app.visibleRoots;
    final pending = roots.where(rootNeedsReset).length;
    final armed = pending > 0;
    final scheme = Theme.of(context).colorScheme;
    final icon = _busy
        ? const SizedBox(
            width: 20,
            height: 20,
            child: CircularProgressIndicator(strokeWidth: 2))
        : Icon(armed ? Icons.check_circle : Icons.check_circle_outline);
    // Filled + error-tinted when a fault is latched so it reads from across the
    // machine; a quiet outline icon when healthy.
    return IconButton(
      key: const Key('global-reset'),
      tooltip: context.tr('std.alarm.resetAllTooltip'),
      icon: Badge(
        isLabelVisible: armed && roots.length > 1,
        label: Text('$pending'),
        backgroundColor: scheme.error,
        textColor: scheme.onError,
        child: icon,
      ),
      color: armed ? scheme.error : scheme.onSurfaceVariant,
      // Slightly larger than a plain bar icon — this is the recovery control.
      iconSize: ControlScaleScope.of(context).iconSize * 1.4,
      onPressed: _busy ? null : _resetAll,
    );
  }
}
