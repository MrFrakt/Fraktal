/// §3.13 — the sequence flow chart.
///
/// Draws every step the chain has published, highlights the active one with the
/// time it has been running, and blinks it red once it outruns its declared
/// guard. A step that names the module it commands is click-through into that
/// module's own chart; a step that raised an error links to the module that
/// actually failed, whatever it was commanding; any other step opens its detail.
///
/// §6.12 — a parallel step makes several rows live at once, so liveness is read
/// per row rather than derived from the Unit's single current step. Rows on a
/// concurrent leg are indented under the fork and carry their leg number.
library;

import 'package:flutter/material.dart';

import '../domain/module_node.dart';
import '../domain/types.dart';
import '../localization/localized_text.dart';
import '../state/app_state.dart';
import 'app_theme.dart';

/// §6.12 — how one row's liveness is resolved, in one place because a parallel
/// step breaks the old assumption that the Unit's single current step names the
/// only live row.
///
/// [rowsAreLive] is TRUE when the PLC publishes per-row liveness at all. An older
/// runtime publishes none, and the chart still has to draw: it then falls back to
/// matching the Unit's current step, which is exactly the pre-§6.12 behaviour.
class SequenceRowState {
  final bool active;
  final bool timedOut;
  final Duration elapsed;
  const SequenceRowState({
    required this.active,
    required this.timedOut,
    required this.elapsed,
  });

  factory SequenceRowState.of(ModuleNode node, SequenceStep step,
      {required bool rowsAreLive}) {
    final active = rowsAreLive
        ? step.active
        : ((node.step?.active ?? false) && step.stepNo == node.step?.stepNo);
    // A leg times itself, because the §6.9 stall watchdog is singular and follows
    // the main line. The main line keeps using that watchdog.
    final timedOut = rowsAreLive
        ? (step.timedOut ||
            (step.branch == 0 && active && node.currentStepTimedOut))
        : (active && node.currentStepTimedOut);
    final Duration elapsed;
    if (!active) {
      elapsed = step.lastDuration;
    } else if (rowsAreLive && step.branch > 0) {
      elapsed = step.elapsed;
    } else {
      elapsed = node.currentStepElapsed;
    }
    return SequenceRowState(
        active: active, timedOut: timedOut, elapsed: elapsed);
  }
}

class SequenceModuleTab extends StatefulWidget {
  final AppState app;
  final ModuleNode node;
  const SequenceModuleTab({super.key, required this.app, required this.node});

  @override
  State<SequenceModuleTab> createState() => _SequenceModuleTabState();
}

class _SequenceModuleTabState extends State<SequenceModuleTab>
    with SingleTickerProviderStateMixin {
  late final AnimationController _blink;

  @override
  void initState() {
    super.initState();
    // One controller drives every timed-out row, so the blink stays in phase
    // and costs one animation regardless of chain length.
    _blink = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 700),
    )..repeat(reverse: true);
  }

  @override
  void dispose() {
    _blink.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final node = widget.node;
    final steps = node.sequenceSteps;
    if (steps.isEmpty) {
      return const Center(child: LText('std.module.sequence.empty'));
    }
    final metrics = ControlScaleScope.of(context);
    final gap = 8.0 * metrics.textScale;
    // A chain that publishes per-row liveness owns the answer; one that does not
    // (an older PLC, or a Unit whose rows were never marked) still renders from
    // the single current step, so the tab never goes blank on an old runtime.
    final rowsAreLive = steps.any((s) => s.active);

    return ListView.builder(
      padding: EdgeInsets.all(gap),
      itemCount: steps.length,
      itemBuilder: (context, index) {
        final step = steps[index];
        final row = SequenceRowState.of(node, step, rowsAreLive: rowsAreLive);
        return _StepRow(
          step: step,
          isActive: row.active,
          isLast: index == steps.length - 1,
          elapsed: row.elapsed,
          // A raised error marks its own row, whether or not it is still the
          // active one; a timeout only ever marks a running step.
          errored: step.errorActive,
          // A warning did not stop anything, so it never blinks: it is a
          // steady mark saying this step had something to report.
          warned: step.warningActive,
          timedOut: row.timedOut,
          blink: _blink,
          metrics: metrics,
          onTap: () => _onTap(step),
        );
      },
    );
  }

  void _onTap(SequenceStep step) {
    // The PLC decided this: a step is click-through only when it declared a
    // target — through Awaits, or through the link a raised error carried. An
    // error with no link (the Unit itself failed) falls through to the detail.
    if (step.drillsDown) {
      for (final root in widget.app.forest) {
        if (root.find(step.linkPath) != null) {
          widget.app.select(step.linkPath);
          return;
        }
      }
    }
    showDialog<void>(
      context: context,
      builder: (context) => _StepDetailDialog(step: step),
    );
  }
}

class _StepRow extends StatelessWidget {
  final SequenceStep step;
  final bool isActive;
  final bool isLast;
  final Duration elapsed;
  final bool errored;
  final bool warned;
  final bool timedOut;
  final Animation<double> blink;
  final UiMetrics metrics;
  final VoidCallback onTap;

  const _StepRow({
    required this.step,
    required this.isActive,
    required this.isLast,
    required this.elapsed,
    required this.errored,
    required this.warned,
    required this.timedOut,
    required this.blink,
    required this.metrics,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final gap = 8.0 * metrics.textScale;

    return AnimatedBuilder(
      animation: blink,
      builder: (context, _) {
        Color fill;
        if (timedOut || errored) {
          // Blink between the surface and the error container so the row stays
          // legible at both ends of the cycle, on every theme.
          fill = Color.lerp(
              scheme.surfaceContainer, scheme.errorContainer, blink.value)!;
        } else if (isActive) {
          fill = scheme.primaryContainer;
        } else if (warned) {
          fill = scheme.tertiaryContainer;
        } else if (step.visited) {
          fill = scheme.surfaceContainerHigh;
        } else {
          fill = scheme.surfaceContainer;
        }
        final fg = foregroundOn(context, fill);

        return Semantics(
          button: true,
          selected: isActive,
          child: InkWell(
            onTap: onTap,
            child: Container(
              constraints: BoxConstraints(minHeight: metrics.touchTarget),
              margin: EdgeInsets.only(bottom: isLast ? 0 : gap / 2),
              padding:
                  EdgeInsets.symmetric(horizontal: gap, vertical: gap / 2),
              decoration: BoxDecoration(
                color: fill,
                borderRadius: BorderRadius.circular(8),
                border:
                    isActive ? Border.all(color: scheme.primary, width: 2) : null,
              ),
              child: Row(children: [
                if (step.branch > 0) ...[
                  SizedBox(width: gap * 1.5),
                  Container(
                    padding: EdgeInsets.symmetric(
                        horizontal: 5 * metrics.textScale, vertical: 1),
                    margin: EdgeInsets.only(right: gap / 2),
                    decoration: BoxDecoration(
                      border: Border.all(color: fg.withValues(alpha: 0.5)),
                      borderRadius: BorderRadius.circular(4),
                    ),
                    child: Text(
                      // U+2225 — the IEC symbol for a simultaneous divergence.
                      '∥${step.branch}',
                      style: TextStyle(
                          color: fg, fontSize: 11 * metrics.textScale),
                    ),
                  ),
                ],
                SizedBox(
                  width: 58 * metrics.textScale,
                  child: Text(
                    'N${step.stepNo}',
                    style: TextStyle(
                      color: fg,
                      fontWeight: FontWeight.w700,
                      fontFeatures: const [FontFeature.tabularFigures()],
                      fontSize: 13 * metrics.textScale,
                    ),
                  ),
                ),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      LText(
                        step.stepName,
                        style: TextStyle(
                            color: fg, fontSize: 14 * metrics.textScale),
                      ),
                      if (step.awaitingLabel.isNotEmpty)
                        Text(
                          step.awaitingLabel,
                          style: TextStyle(
                            color: fg.withValues(alpha: 0.75),
                            fontSize: 12 * metrics.textScale,
                          ),
                        ),
                    ],
                  ),
                ),
                if (warned)
                  Padding(
                    padding: EdgeInsets.only(left: gap / 2, right: gap / 2),
                    child: Icon(Icons.info_outline,
                        color: fg, size: 18 * metrics.textScale),
                  ),
                _elapsed(fg),
                if (step.drillsDown)
                  Padding(
                    padding: EdgeInsets.only(left: gap / 2),
                    child: Icon(Icons.chevron_right,
                        color: fg, size: 20 * metrics.textScale),
                  ),
              ]),
            ),
          ),
        );
      },
    );
  }

  Widget _elapsed(Color fg) {
    if (elapsed == Duration.zero && !isActive) return const SizedBox.shrink();
    return Column(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.end,
      children: [
        Text(
          _seconds(elapsed),
          style: TextStyle(
            color: fg,
            fontFeatures: const [FontFeature.tabularFigures()],
            fontWeight: isActive ? FontWeight.w700 : FontWeight.w400,
            fontSize: 13 * metrics.textScale,
          ),
        ),
        if (step.expected > Duration.zero)
          Text(
            '/ ${_seconds(step.expected)}',
            style: TextStyle(
              color: fg.withValues(alpha: 0.7),
              fontSize: 11 * metrics.textScale,
            ),
          ),
      ],
    );
  }
}

String _seconds(Duration d) =>
    '${(d.inMilliseconds / 1000.0).toStringAsFixed(1)} s';

class _StepDetailDialog extends StatelessWidget {
  final SequenceStep step;
  const _StepDetailDialog({required this.step});

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: Text('N${step.stepNo}'),
      content: SingleChildScrollView(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _row(context, 'std.module.sequence.name', locKey: step.stepName),
            if (step.awaitingLabel.isNotEmpty)
              _row(context, 'std.module.sequence.awaiting',
                  plain: step.awaitingLabel),
            if (step.branch > 0)
              _row(context, 'std.module.sequence.branch',
                  plain: step.branch.toString()),
            _row(context, 'std.module.sequence.timeClass',
                plain: step.timeClass.name),
            _row(context, 'std.module.sequence.expected',
                plain: _seconds(step.expected)),
            _row(context, 'std.module.sequence.lastDuration',
                plain: _seconds(step.lastDuration)),
            if (step.awaitsPath.isNotEmpty)
              _row(context, 'std.module.sequence.commands',
                  plain: step.awaitsPath),
            if (step.warningActive)
              _row(context, 'std.module.sequence.warning',
                  locKey: step.warningKey),
            if (step.warningActive && step.warningSourcePath.isNotEmpty)
              _row(context, 'std.module.sequence.reportedBy',
                  plain: step.warningSourcePath),
            if (step.errorActive)
              _row(context, 'std.module.sequence.error',
                  plain: step.errorSourcePath.isEmpty
                      ? '-'
                      : step.errorSourcePath),
          ],
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(context).pop(),
          child: const LText('std.action.close'),
        ),
      ],
    );
  }

  Widget _row(BuildContext context, String label,
      {String? plain, String? locKey}) {
    final scheme = Theme.of(context).colorScheme;
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 3),
      child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
        SizedBox(
          width: 150,
          child: LText(label,
              style: TextStyle(color: scheme.onSurfaceVariant, fontSize: 13)),
        ),
        Expanded(
          child: locKey != null
              ? LText(locKey, style: TextStyle(color: scheme.onSurface))
              : Text(plain ?? '', style: TextStyle(color: scheme.onSurface)),
        ),
      ]),
    );
  }
}
