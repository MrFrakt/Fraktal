/// Widgets closing the audit gaps: current-step card (§6.5/§6.9), step Pareto
/// (§8.11.4), plant overview dashboard, global alarm banner, connection chip.
library;

import '../localization/localized_text.dart';
import 'package:flutter/material.dart';
import '../domain/module_node.dart';
import '../domain/types.dart';
import '../state/app_state.dart';
import 'app_theme.dart';
import 'cycle_profile_view.dart';

/// §6.5/§6.9 — what the Unit is doing right now, and what it waits for.
class CurrentStepCard extends StatelessWidget {
  final StepInfo step;
  const CurrentStepCard({super.key, required this.step});
  @override
  Widget build(BuildContext context) {
    if (!step.active) return const SizedBox.shrink();
    final waiting = step.awaitingLabel.isNotEmpty;
    final failing = step.conds.where((c) => !c.ok).toList();
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            const Icon(Icons.directions_run),
            const SizedBox(width: 8),
            LText('std.step.current',
                args: {
                  'number': step.stepNo,
                  'name': context.tr(step.stepName),
                },
                style: Theme.of(context).textTheme.titleMedium),
            const Spacer(),
            // Fixed pastels need an explicit paired label: the themed one is
            // resolved for the default surfaces and goes white on a dark theme.
            if (step.starved)
              Chip(
                  label: const LText('STARVED'),
                  backgroundColor: const Color(0xFFBBDEFB),
                  labelStyle: TextStyle(
                      color: foregroundOn(context, const Color(0xFFBBDEFB)))),
            if (step.blocked)
              Chip(
                  label: const LText('BLOCKED'),
                  backgroundColor: const Color(0xFFE1BEE7),
                  labelStyle: TextStyle(
                      color: foregroundOn(context, const Color(0xFFE1BEE7)))),
          ]),
          if (waiting)
            Padding(
              padding: const EdgeInsets.only(top: 6),
              child: LText('std.step.awaitingModule',
                  args: {'module': step.awaitingLabel}),
            ),
          for (final c in failing)
            Padding(
              padding: const EdgeInsets.only(top: 4),
              child: Row(children: [
                Icon(Icons.pending_outlined,
                    size: 16, color: Theme.of(context).colorScheme.tertiary),
                const SizedBox(width: 6),
                LText('std.step.awaitingCondition',
                    args: {'condition': context.tr(c.label)}),
              ]),
            ),
          if (step.expected > Duration.zero)
            Padding(
              padding: const EdgeInsets.only(top: 6),
              child: LText('std.step.expectedMaximum',
                  args: {
                    'seconds':
                        (step.expected.inMilliseconds / 1000).toStringAsFixed(1)
                  },
                  style: Theme.of(context).textTheme.labelMedium),
            ),
        ]),
      ),
    );
  }
}

/// §8.11.4 — step Pareto: per-step Avg (bar) with Max marker, worst-first, so the
/// dominant cycle-time contributor is obvious. Complements the cycle Gantt.
class StepParetoView extends StatelessWidget {
  final List<StepStat> stats;
  const StepParetoView({super.key, required this.stats});
  @override
  Widget build(BuildContext context) {
    if (stats.isEmpty) return const SizedBox.shrink();
    final sorted = [...stats]
      ..sort((a, b) => b.avg.inMilliseconds - a.avg.inMilliseconds);
    final maxMs = sorted.first.max.inMilliseconds.clamp(1, 1 << 30);
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            const Icon(Icons.bar_chart),
            const SizedBox(width: 8),
            LText('Step Pareto (Avg, Max marker)',
                style: Theme.of(context).textTheme.titleMedium),
          ]),
          const SizedBox(height: 8),
          for (final s in sorted) _bar(context, s, maxMs),
        ]),
      ),
    );
  }

  Widget _bar(BuildContext ctx, StepStat s, int maxMs) {
    final avgFrac = s.avg.inMilliseconds / maxMs;
    final maxFrac = s.max.inMilliseconds / maxMs;
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 3),
      child: Row(children: [
        SizedBox(
            width: 130,
            child: LText('${s.stepNo} ${s.label}',
                overflow: TextOverflow.ellipsis)),
        Expanded(
          child: LayoutBuilder(builder: (_, box) {
            return SizedBox(
              height: 20,
              child: Stack(children: [
                Container(
                    decoration: BoxDecoration(
                        color:
                            Theme.of(ctx).colorScheme.surfaceContainerHighest,
                        borderRadius: BorderRadius.circular(4))),
                Container(
                  width: (box.maxWidth * avgFrac).clamp(2.0, box.maxWidth),
                  decoration: BoxDecoration(
                      color: timeClassColor(s.timeClass),
                      borderRadius: BorderRadius.circular(4)),
                ),
                Positioned(
                  left: (box.maxWidth * maxFrac).clamp(0.0, box.maxWidth - 2),
                  child: Container(
                      width: 2,
                      height: 20,
                      color: Theme.of(ctx).colorScheme.onSurface),
                ),
              ]),
            );
          }),
        ),
        const SizedBox(width: 8),
        SizedBox(
            width: 88,
            child: LText(
                '${(s.avg.inMilliseconds / 1000).toStringAsFixed(1)}/${(s.max.inMilliseconds / 1000).toStringAsFixed(1)}s',
                textAlign: TextAlign.right,
                style: Theme.of(ctx).textTheme.labelMedium)),
      ]),
    );
  }
}

/// Core §7.5.2 — the standing commissioning/engineering-gate annunciation.
///
/// This is the lowest-priority alarm the framework raises (LOW/SYSTEM), and that
/// is exactly why it needs its own strip: [GlobalAlarmBanner] shows the single
/// WORST active event, so during commissioning — the phase that generates the
/// most process alarms — a severity-ordered banner would bury the one message
/// that says the machine is not running its production software.
///
/// Three properties are deliberate and must not be "improved" away:
///   * no dismiss control — no operator action closes the underlying event, and
///     a banner the operator could tap away would give back exactly the
///     capability §7.5.2 removes;
///   * shown regardless of shelving — the reason is rationalized as not
///     suppressible (§8.9), so shelving cannot reach it either;
///   * a low-risk visual register — warning-tinted, not error-tinted. The
///     station is not faulted: this reports how the software was BUILT, and
///     dressing it as a fault would train operators to ignore real ones.
///
/// It disappears only when the PLC stops reporting a gate, which — gates being
/// build constants (§7.5.1) — means a new download.
class EngineeringModeBanner extends StatelessWidget {
  final AppState app;
  const EngineeringModeBanner({super.key, required this.app});
  @override
  Widget build(BuildContext context) {
    final gates = app.activeEngineeringGates;
    if (gates.isEmpty) return const SizedBox.shrink();
    final c = warningColor(context);
    return Material(
      color: c.withValues(alpha: 0.14),
      child: Container(
        width: double.infinity,
        decoration: BoxDecoration(
            border: Border(left: BorderSide(width: 4, color: c))),
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
        child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Icon(Icons.construction, color: c),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  LText('std.engineering.banner',
                      // A sentence, not a glyph: the 4.5:1 shade (app_theme).
                      style: TextStyle(
                          color: severityTextColor(context, Severity.medium),
                          fontWeight: FontWeight.w700)),
                  for (final gate in gates)
                    LText('• ${context.tr(gate.description)}',
                        style: TextStyle(
                            color: severityTextColor(context, Severity.medium))),
                ]),
          ),
        ]),
      ),
    );
  }
}

/// Global alarm banner: the single worst active event across the whole forest,
/// visible from any screen (standard HMI safety pattern). Tapping selects it.
class GlobalAlarmBanner extends StatelessWidget {
  final AppState app;
  const GlobalAlarmBanner({super.key, required this.app});
  @override
  Widget build(BuildContext context) {
    final events = app.allActiveEvents
        .where((e) => !e.shelved)
        .toList(); // §8.10: shelved = no annunciation
    if (events.isEmpty) return const SizedBox.shrink();
    final worst = events.first;
    final c = severityColor(context, worst.severity);
    final more = events.length - 1;
    return Material(
      color: c.withValues(alpha: 0.14),
      child: InkWell(
        onTap: () => app.select(worst.sourcePath),
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
          child: Row(children: [
            Icon(
              switch (worst.severity) {
                Severity.high => Icons.error,
                Severity.medium => Icons.warning_amber,
                Severity.low => Icons.info_outline
              },
              color: c,
            ),
            const SizedBox(width: 10),
            Expanded(
                child: LText(
                    '${context.tr(worst.description)}  ·  ${worst.sourcePath}',
                    overflow: TextOverflow.ellipsis,
                    // Body text, so the text-weight shade — the icon-weight one
                    // is only held to 3:1 and read 3.4:1 here.
                    style: TextStyle(
                        color: severityTextColor(context, worst.severity),
                        fontWeight: FontWeight.w600))),
            if (more > 0)
              // The banner paints a severity tint over the surface, so a default
              // Chip lands fill-on-fill: its own surfaceContainerLow sits on an
              // already-tinted background and the label keeps the ambient
              // onSurface. On high-contrast dark that measured ~1.9:1 and the
              // count vanished. Fill it with the severity colour and pair the
              // label with foregroundOn, like every other fixed-colour fill.
              Chip(
                  label: LText('+$more',
                      style: TextStyle(
                          color: foregroundOn(context, c),
                          fontWeight: FontWeight.w600)),
                  backgroundColor: c,
                  side: BorderSide.none,
                  visualDensity: VisualDensity.compact),
          ]),
        ),
      ),
    );
  }
}

/// Connection liveness chip for the app bar — shown **only when something is
/// wrong**. `ConnectionBootstrap` removes the whole operator shell on STALE/DOWN
/// and blocks it until LIVE, so a working panel would permanently display a
/// "Live" badge that can never say anything else: chrome with no information.
/// The degraded states stay, because those the operator does need to see (and
/// they can appear briefly before the shell is torn down).
class ConnectionChip extends StatelessWidget {
  final LinkState state;
  const ConnectionChip({super.key, required this.state});
  @override
  Widget build(BuildContext context) {
    if (state == LinkState.live) return const SizedBox.shrink();
    final (label, color, icon) = switch (state) {
      LinkState.live => (
          'Live',
          okColor(context),
          Icons.cloud_done_outlined
        ),
      LinkState.connecting => (
          'Connecting',
          warningColor(context),
          Icons.cloud_sync_outlined
        ),
      LinkState.stale => (
          'Stale',
          warningColor(context),
          Icons.cloud_off_outlined
        ),
      LinkState.down => (
          'Offline',
          Theme.of(context).colorScheme.error,
          Icons.cloud_off
        ),
    };
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 8),
      child: Chip(
          // Follows the size preset like the rest of the bar (app_theme).
          avatar: Icon(icon,
              size: ControlScaleScope.of(context).iconSize * 0.9, color: color),
          label: LText(label),
          visualDensity: VisualDensity.compact),
    );
  }
}

/// Plant overview dashboard — the at-a-glance landing screen: one card per root
/// with state, model, mode, counters, and worst active severity. Tap to drill in.
class PlantOverview extends StatelessWidget {
  final AppState app;
  const PlantOverview({super.key, required this.app});
  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(builder: (context, box) {
      final cols = box.maxWidth ~/ 340;
      return GridView.count(
        padding: const EdgeInsets.all(16),
        crossAxisCount: cols.clamp(1, 4),
        childAspectRatio: 1.7,
        mainAxisSpacing: 12,
        crossAxisSpacing: 12,
        children: [for (final r in app.forest) _rootCard(context, r)],
      );
    });
  }

  Widget _rootCard(BuildContext context, ModuleNode r) {
    final sev = r.effectiveSeverity;
    final tint = sev == null ? null : severityColor(context, sev);
    return Card(
      color: tint?.withValues(alpha: 0.08),
      child: InkWell(
        onTap: () => app.select(r.path),
        child: Padding(
          padding: const EdgeInsets.all(14),
          child:
              Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Row(children: [
              Icon(Icons.factory_outlined, color: tint),
              const SizedBox(width: 8),
              Expanded(
                  child: LText(
                      r.displayNameKey.isEmpty ? r.name : r.displayNameKey,
                      style: Theme.of(context).textTheme.titleLarge,
                      overflow: TextOverflow.ellipsis)),
              Container(
                  width: 12,
                  height: 12,
                  decoration: BoxDecoration(
                      color: stateColor(context, r.state),
                      shape: BoxShape.circle)),
            ]),
            const Spacer(),
            Wrap(spacing: 6, runSpacing: 6, children: [
              Chip(
                  visualDensity: VisualDensity.compact,
                  avatar: const Icon(Icons.qr_code_2, size: 16),
                  label: LText(r.modelCode)),
              Chip(
                  visualDensity: VisualDensity.compact,
                  label: LText(r.modeActive?.name.toUpperCase() ?? '-')),
              Chip(
                  visualDensity: VisualDensity.compact,
                  label: LText('Good ${r.goodCount}')),
              if (r.nokCount > 0)
                Chip(
                    visualDensity: VisualDensity.compact,
                    label: LText('NOK ${r.nokCount}')),
            ]),
            const SizedBox(height: 6),
            if (sev != null)
              LText(r.message,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: TextStyle(
                      color: severityTextColor(context, sev),
                      fontWeight: FontWeight.w600))
            else
              LText(r.message,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: Theme.of(context).textTheme.bodySmall),
          ]),
        ),
      ),
    );
  }
}
