/// §7.8 release panel — a persistent bottom strip that shows WHY the current
/// action is blocked: the full rollup (mode, access, alarm, interlock reasons),
/// each with its description. Stays visible while blocked; a Dismiss clears it.
library;

import '../localization/localized_text.dart';
import 'package:flutter/material.dart';
import '../domain/types.dart';
import '../state/app_state.dart';
import 'app_theme.dart';

class ReleasePanel extends StatelessWidget {
  final AppState app;
  const ReleasePanel({super.key, required this.app});

  @override
  Widget build(BuildContext context) {
    if (!app.releasePanelVisible) return const SizedBox.shrink();
    final r = app.releaseReport;
    final cs = Theme.of(context).colorScheme;
    if (app.releaseLoading || r == null) {
      return Material(
        color: cs.secondaryContainer,
        child: onContainer(
          context,
          cs.secondaryContainer,
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 10, 8, 10),
            child: Row(children: [
              const SizedBox(
                width: 20,
                height: 20,
                child: CircularProgressIndicator(strokeWidth: 2.5),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: LText(
                  'std.release.checking',
                  style: Theme.of(context)
                      .textTheme
                      .titleMedium
                      ?.copyWith(fontWeight: FontWeight.w600),
                ),
              ),
              IconButton(
                icon: const Icon(Icons.close),
                onPressed: app.clearRelease,
                tooltip: context.tr('Dismiss'),
              ),
            ]),
          ),
        ),
      );
    }
    // released -> a themed 'now clear' confirmation; blocked -> error-tinted
    // list. Both fills are paired with their `on-` colour (app_theme.onContainer)
    // — a hardcoded light green left dark-theme text at 1.34:1, unreadable.
    final clear = r.released;
    final fill = clear ? cs.primaryContainer : cs.errorContainer;
    return Material(
      color: fill,
      child: onContainer(
        context,
        fill,
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 8, 8, 8),
          child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(children: [
                  Icon(clear ? Icons.check_circle : Icons.block,
                      color: clear ? okColor(context) : cs.error),
                  const SizedBox(width: 8),
                  LText(
                      clear
                          ? 'Now released — you can proceed'
                          : app.releaseTitle,
                      style: Theme.of(context)
                          .textTheme
                          .titleMedium
                          ?.copyWith(fontWeight: FontWeight.w600)),
                  const Spacer(),
                  IconButton(
                      icon: const Icon(Icons.close),
                      onPressed: app.clearRelease,
                      tooltip: context.tr('Dismiss')),
                ]),
                if (!clear)
                  Wrap(spacing: 8, runSpacing: 8, children: [
                    if (r.reasons.isEmpty)
                      _reasonChip(
                        context,
                        const ReleaseReason(
                          'std.release.noDetails',
                          ReleaseKind.other,
                        ),
                      )
                    else
                      for (final reason in r.reasons)
                        _reasonChip(context, reason),
                  ]),
              ]),
        ),
      ),
    );
  }

  Widget _reasonChip(BuildContext context, ReleaseReason reason) {
    final icon = switch (reason.kind) {
      ReleaseKind.mode => Icons.tune,
      ReleaseKind.access => Icons.lock_outline,
      ReleaseKind.alarm => Icons.notification_important_outlined,
      ReleaseKind.interlock => Icons.link_off,
      ReleaseKind.other => Icons.info_outline,
    };
    final owner = reason.sourcePath.isEmpty ? '' : '${reason.sourcePath}: ';
    final code = reason.reasonCode == 0 ? '' : ' (#${reason.reasonCode})';
    // The chip paints its OWN fill inside a panel filled with errorContainer,
    // so it must pair its own foreground: the label inherited the panel's
    // on-colour and rendered white on the chip's white surface. A bare label
    // with no colour is worse than a wrong one - it cannot even be measured
    // (app_theme.foregroundOn).
    final chipFill = Theme.of(context).colorScheme.surface;
    final ink = foregroundOn(context, chipFill);
    return Chip(
      avatar: Icon(icon, size: 18, color: ink),
      label: Text(
        owner +
            context.tr(reason.description) +
            code +
            (reason.bypassable ? context.tr(' (bypassable)') : ''),
        style: TextStyle(color: ink),
      ),
      backgroundColor: chipFill,
    );
  }
}
