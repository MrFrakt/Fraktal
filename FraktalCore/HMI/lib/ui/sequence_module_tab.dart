/// §3.13 — the sequence flow chart.
///
/// Draws every step the chain has published, highlights the active one with the
/// time it has been running, and blinks it red once it outruns its declared
/// guard. A step that names the module it commands is click-through into that
/// module's own chart; any other step opens its detail instead.
library;

import 'package:flutter/material.dart';

import '../domain/module_node.dart';
import '../domain/types.dart';
import '../localization/localized_text.dart';
import '../state/app_state.dart';
import 'app_theme.dart';

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
    final activeNo = node.step?.stepNo ?? 0;
    final activeNow = node.step?.active ?? false;

    return ListView.builder(
      padding: EdgeInsets.all(gap),
      itemCount: steps.length,
      itemBuilder: (context, index) {
        final step = steps[index];
        final isActive = activeNow && step.stepNo == activeNo;
        return _StepRow(
          step: step,
          isActive: isActive,
          isLast: index == steps.length - 1,
          elapsed: isActive ? node.currentStepElapsed : step.lastDuration,
          timedOut: isActive && node.currentStepTimedOut,
          blink: _blink,
          metrics: metrics,
          onTap: () => _onTap(step),
        );
      },
    );
  }

  void _onTap(SequenceStep step) {
    // The PLC decided this: a step is click-through only when it declared the
    // module it commands, so there is nothing to infer here.
    if (step.drillsDown) {
      for (final root in widget.app.forest) {
        if (root.find(step.awaitsPath) != null) {
          widget.app.select(step.awaitsPath);
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
  final bool timedOut;
  final Animation<double> blink;
  final UiMetrics metrics;
  final VoidCallback onTap;

  const _StepRow({
    required this.step,
    required this.isActive,
    required this.isLast,
    required this.elapsed,
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
        if (timedOut) {
          // Blink between the surface and the error container so the row stays
          // legible at both ends of the cycle, on every theme.
          fill = Color.lerp(
              scheme.surfaceContainer, scheme.errorContainer, blink.value)!;
        } else if (isActive) {
          fill = scheme.primaryContainer;
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
            _row(context, 'std.module.sequence.timeClass',
                plain: step.timeClass.name),
            _row(context, 'std.module.sequence.expected',
                plain: _seconds(step.expected)),
            _row(context, 'std.module.sequence.lastDuration',
                plain: _seconds(step.lastDuration)),
            if (step.drillsDown)
              _row(context, 'std.module.sequence.commands',
                  plain: step.awaitsPath),
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
