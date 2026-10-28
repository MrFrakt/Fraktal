/// §8.11.4 cycle-time profile — a GANTT of the last cycle: every step drawn on
/// one shared time axis at the offset it actually ran, coloured by time class,
/// with the Total vs Work (real cycle time) vs Wait split in the header. The
/// legend doubles as the filter: a class can be taken out of the chart to read
/// what the cycle looks like without it.
/// Pure CustomPaint; no charting package.
library;

import 'dart:math' as math;

import '../localization/localized_text.dart';
import 'package:flutter/material.dart';
import 'theme_surfaces.dart';
import '../domain/types.dart';
import 'app_theme.dart';
import 'timing_chart_filters.dart';

/// Each step's start offset from the cycle start, in ms.
///
/// FB_CycleProfiler closes the open step at the instant the next one opens
/// (`_M_CloseOpen`) and takes `_cycleStartMs` from the first step's open, so a
/// published profile's steps are contiguous by construction: a step starts where
/// its predecessor ended, and the last one ends at Total. Deriving the offsets
/// here keeps `Steps[].Started` out of the cyclic read (it would add 2 leaves x
/// MAX_PROFILE_STEPS per Unit) for a number the durations already carry exactly.
List<int> stepStartOffsetsMs(List<StepTiming> steps) {
  final offsets = <int>[];
  var acc = 0;
  for (final s in steps) {
    offsets.add(acc);
    acc += s.duration.inMilliseconds;
  }
  return offsets;
}

class CycleProfileView extends StatelessWidget {
  final CycleProfile profile;
  final Set<TimeClass>? hiddenTimeClasses;
  const CycleProfileView({super.key, required this.profile,
      this.hiddenTimeClasses});

  @override
  Widget build(BuildContext context) {
    if (profile.steps.isEmpty) return const SizedBox.shrink();
    return TimingChartFilters<TimeClass>(
      hiddenOptions: hiddenTimeClasses,
      options: [
        for (final c in TimeClass.values)
          if (profile.steps.any((s) => s.timeClass == c))
            TimingChartOption(c, timeClassLabel(c), timeClassColor(c),
                detail: _s(profile.steps
                    .where((s) => s.timeClass == c)
                    .fold(Duration.zero, (sum, s) => sum + s.duration))),
      ],
      builder: _chart,
    );
  }

  Widget _chart(BuildContext context, Set<TimeClass> hidden, Widget legend) {
    final p = profile;
    final theme = Theme.of(context);
    final scale = ControlScaleScope.of(context).textScale;

    final allStarts = stepStartOffsetsMs(p.steps);
    final steps = <StepTiming>[];
    final originalStarts = <int>[];
    for (var i = 0; i < p.steps.length; i++) {
      if (hidden.contains(p.steps[i].timeClass)) continue;
      steps.add(p.steps[i]);
      originalStarts.add(allStarts[i]);
    }
    // A filtered chart has its own LINEAR elapsed-time axis. Hidden durations
    // contribute neither an offset nor extent: each visible step follows the
    // previous visible step. PLC totals and original starts remain available.
    final starts = hidden.isEmpty ? allStarts : stepStartOffsetsMs(steps);
    final visibleMs =
        steps.fold<int>(0, (sum, s) => sum + s.duration.inMilliseconds);
    final spanMs = math.max(
        1,
        hidden.isEmpty
            ? math.max(p.total.inMilliseconds, visibleMs)
            : visibleMs);

    var hiddenMs = 0;
    var hiddenSteps = 0;
    for (final s in p.steps) {
      if (!hidden.contains(s.timeClass)) continue;
      hiddenMs += s.duration.inMilliseconds;
      hiddenSteps++;
    }

    final noW = 40 * scale;
    final nameW = 132 * scale;
    final startW = 52 * scale;
    final durW = 64 * scale; // includes the 8px gutter off the track
    final rowH = 26 * scale;
    final barH = 18 * scale;
    final axisH = 20 * scale;

    return FraktalCard(
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            const Icon(Icons.view_timeline_outlined),
            const SizedBox(width: 8),
            LText('Cycle #${p.cycleNo}', style: theme.textTheme.titleMedium),
            const Spacer(),
            // The header is the CYCLE, never the filtered slice: these numbers
            // reconcile with §8.11.1 and must not move because a class was
            // switched off. What the filter removed is stated below instead.
            _stat(context, 'Total', p.total),
            // These are numbers on a card, not chart fills: they take the
            // brightness-adapted foreground shades. timeClassColor stays fixed
            // for the BARS below, where the colour is a filled area and the
            // categorical assignment must never move.
            _stat(context, 'Work', p.workTime, color: okColor(context)),
            _stat(context, 'Wait', p.waitTime, color: infoColor(context)),
          ]),
          const SizedBox(height: 12),
          if (hidden.isNotEmpty)
            Padding(
              padding: const EdgeInsets.only(bottom: 6),
              child: LText('std.timing.filteredAxis',
                  style: theme.textTheme.labelMedium),
            ),
          // Start uses the same elapsed-time axis as the bars. When filtered,
          // the cell's tooltip retains its authoritative original cycle start.
          SizedBox(
            height: rowH,
            child: Row(children: [
              SizedBox(width: noW, child: _head(context, 'Step')),
              SizedBox(width: nameW, child: _head(context, 'Name')),
              SizedBox(
                  width: startW,
                  child: _head(context, 'Start', align: TextAlign.right)),
              const Expanded(child: SizedBox.shrink()),
              SizedBox(
                  width: durW,
                  child: _head(context, 'Duration', align: TextAlign.right)),
            ]),
          ),
          if (steps.isEmpty)
            Padding(
              padding: EdgeInsets.symmetric(vertical: rowH / 2),
              child: LText('Every time class is filtered out',
                  style: theme.textTheme.bodyMedium
                      ?.copyWith(color: theme.colorScheme.onSurfaceVariant)),
            )
          else
            Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
              SizedBox(
                width: noW + nameW + startW,
                child: Column(children: [
                  for (var i = 0; i < steps.length; i++)
                    _labels(context, steps[i], starts[i],
                        originalStartMs:
                            hidden.isEmpty ? null : originalStarts[i],
                        rowH: rowH,
                        noW: noW,
                        nameW: nameW,
                        startW: startW),
                ]),
              ),
              Expanded(
                child: SizedBox(
                  height: steps.length * rowH + axisH,
                  child: CustomPaint(
                    painter: _GanttPainter(
                      steps: steps,
                      startMs: starts,
                      spanMs: spanMs,
                      rowH: rowH,
                      barH: barH,
                      axisH: axisH,
                      textScale: scale,
                      gridInk: theme.colorScheme.outlineVariant,
                      guideInk: theme.colorScheme.onSurfaceVariant,
                      errorInk: theme.colorScheme.error,
                    ),
                  ),
                ),
              ),
              SizedBox(
                width: durW,
                child: Column(children: [
                  for (final s in steps) _duration(context, s, rowH: rowH),
                ]),
              ),
            ]),
          if (hidden.isNotEmpty)
            _filterSummary(context, hidden, hiddenMs, hiddenSteps, p.total),
          const SizedBox(height: 8),
          legend,
        ]),
      ),
    );
  }

  /// What the filter took out, as a number — and the §8.11.4(f) question it is
  /// really being asked: what would this cycle be without that class?
  Widget _filterSummary(BuildContext ctx, Set<TimeClass> hidden, int hiddenMs,
      int hiddenSteps, Duration total) {
    final theme = Theme.of(ctx);
    final names = [
      for (final c in TimeClass.values)
        if (hidden.contains(c)) ctx.tr(timeClassLabel(c))
    ].join(', ');
    final rest = Duration(milliseconds: total.inMilliseconds - hiddenMs);
    return Padding(
      padding: const EdgeInsets.only(top: 6),
      child: Row(children: [
        Icon(Icons.filter_alt_outlined,
            size: 16, color: theme.colorScheme.onSurfaceVariant),
        const SizedBox(width: 6),
        Flexible(
          child: LText(
            'Filtered out $names — ${_s(Duration(milliseconds: hiddenMs))} '
            'in $hiddenSteps ${hiddenSteps == 1 ? 'step' : 'steps'}; '
            'the cycle without ${hidden.length == 1 ? 'it' : 'them'} '
            'is ${_s(rest)}',
            style: theme.textTheme.labelMedium
                ?.copyWith(color: theme.colorScheme.onSurfaceVariant),
          ),
        ),
      ]),
    );
  }

  Widget _stat(BuildContext ctx, String label, Duration d, {Color? color}) {
    return Padding(
      padding: const EdgeInsets.only(left: 16),
      child: Column(children: [
        LText(label, style: Theme.of(ctx).textTheme.labelSmall),
        LText(_s(d),
            style: Theme.of(ctx).textTheme.titleMedium?.copyWith(color: color)),
      ]),
    );
  }

  Widget _head(BuildContext ctx, String text,
          {TextAlign align = TextAlign.left}) =>
      LText(text, style: Theme.of(ctx).textTheme.labelSmall, textAlign: align);

  /// Left gutter: the row identity and the start encoded by the chart axis.
  Widget _labels(BuildContext ctx, StepTiming s, int startMs,
      {int? originalStartMs,
      required double rowH,
      required double noW,
      required double nameW,
      required double startW}) {
    return SizedBox(
      height: rowH,
      child: Row(children: [
        SizedBox(
            width: noW,
            child: LText('${s.stepNo}',
                style: Theme.of(ctx).textTheme.labelMedium)),
        SizedBox(
            width: nameW,
            child: LText(s.stepName, overflow: TextOverflow.ellipsis)),
        SizedBox(
          width: startW,
          child: Tooltip(
            message: ctx.tr('std.timing.originalStart', {
              'seconds': _s(Duration(milliseconds: originalStartMs ?? startMs)),
            }),
            child: LText(_s(Duration(milliseconds: startMs)),
                textAlign: TextAlign.right,
                style: Theme.of(ctx).textTheme.bodySmall?.copyWith(
                    fontFeatures: const [FontFeature.tabularFigures()])),
          ),
        ),
      ]),
    );
  }

  /// Right gutter: the bar's length as a number. §8.11.4(c) — a step past its
  /// declared guard is called out in ink here as well as by the outline on the
  /// bar, so the overrun is never signalled by colour alone.
  Widget _duration(BuildContext ctx, StepTiming s, {required double rowH}) {
    final overrun = s.expected > Duration.zero && s.duration > s.expected;
    return SizedBox(
      height: rowH,
      child: Padding(
        padding: const EdgeInsets.only(left: 8),
        child: Align(
          alignment: Alignment.centerRight,
          child: LText(_s(s.duration),
              textAlign: TextAlign.right,
              style: Theme.of(ctx).textTheme.bodyMedium?.copyWith(
                fontFeatures: const [FontFeature.tabularFigures()],
                color: overrun ? Theme.of(ctx).colorScheme.error : null,
              )),
        ),
      ),
    );
  }

  static String _s(Duration d) =>
      '${(d.inMilliseconds / 1000).toStringAsFixed(1)}s';
}

/// One linear elapsed-time axis: complete cycle when unfiltered, concatenated
/// visible durations when filtered. No broken or nonlinear time mapping.
class _GanttPainter extends CustomPainter {
  final List<StepTiming> steps;
  final List<int> startMs;

  final int spanMs;
  final double rowH, barH, axisH, textScale;
  final Color gridInk, guideInk, errorInk;

  _GanttPainter({
    required this.steps,
    required this.startMs,
    required this.spanMs,
    required this.rowH,
    required this.barH,
    required this.axisH,
    required this.textScale,
    required this.gridInk,
    required this.guideInk,
    required this.errorInk,
  });

  @override
  void paint(Canvas canvas, Size size) {
    final plotH = size.height - axisH;
    final ticks = _ticks(spanMs);
    double x(int ms) => size.width * ms / spanMs;

    // Recessive solid hairline grid — one rule per axis tick, run through the
    // whole stack so every row is read against the same time marks.
    final grid = Paint()
      ..color = gridInk
      ..strokeWidth = 1;
    for (final t in ticks) {
      final gx = _fit(x(t), 0, size.width - 0.5);
      canvas.drawLine(Offset(gx, 0), Offset(gx, plotH), grid);
    }
    canvas.drawLine(Offset(0, plotH), Offset(size.width, plotH), grid);

    for (var i = 0; i < steps.length; i++) {
      final s = steps[i];
      final top = i * rowH + (rowH - barH) / 2;
      final left = _fit(x(startMs[i]), 0, size.width);
      // A sub-pixel step still has to be visible, and still has to start in the
      // right place: grow it rightward off its own start, never off the axis.
      final right = _fit(
          math.max(x(startMs[i] + s.duration.inMilliseconds), left + 2),
          0,
          size.width);
      final bar = RRect.fromRectAndRadius(
        Rect.fromLTRB(left, top, right, top + barH),
        const Radius.circular(4),
      );
      canvas.drawRRect(bar, Paint()..color = timeClassColor(s.timeClass));

      // §8.11.4(c): ExpectedTime drawn against the actual — a tick where the
      // declared guard would have ended this step. Guard and actual are
      // durations on the same linear scale, including on the filtered axis.
      final expectedMs = s.expected.inMilliseconds;
      if (expectedMs > 0) {
        final gx =
            _fit(x(startMs[i] + expectedMs), 0, math.max(0, size.width - 2));
        canvas.drawRect(
            Rect.fromLTWH(gx, top - 3, 2, barH + 6), Paint()..color = guideInk);
        if (s.duration > s.expected) {
          canvas.drawRRect(
            bar.deflate(1),
            Paint()
              ..color = errorInk
              ..style = PaintingStyle.stroke
              ..strokeWidth = 2,
          );
        }
      }
    }

    for (final t in ticks) {
      _tickLabel(
          canvas, _tickText(t, ticks), x(t), plotH + 4 * textScale, size.width);
    }
  }

  void _tickLabel(
      Canvas canvas, String text, double centerX, double top, double maxW) {
    final tp = TextPainter(
      text: TextSpan(
        text: text,
        style: TextStyle(
          color: guideInk,
          fontSize: 10 * textScale,
          fontFeatures: const [FontFeature.tabularFigures()],
        ),
      ),
      textDirection: TextDirection.ltr,
    )..layout();
    // Keep the first and last labels inside the track instead of clipping them.
    final dx = _fit(centerX - tp.width / 2, 0, math.max(0, maxW - tp.width));
    tp.paint(canvas, Offset(dx, top));
  }

  /// `num.clamp` widens to `num`; these are all canvas coordinates.
  static double _fit(double v, double lo, double hi) =>
      v < lo ? lo : (v > hi ? hi : v);

  /// Nice 1/2/5 tick steps, targeting at most six rules across the track.
  static List<int> _ticks(int spanMs) {
    const candidates = [
      50, 100, 200, 500, //
      1000, 2000, 5000, 10000, 15000, 30000, //
      60000, 120000, 300000, 600000, 1800000, 3600000,
    ];
    var step = candidates.last;
    for (final c in candidates) {
      if (spanMs / c <= 6) {
        step = c;
        break;
      }
    }
    final ticks = <int>[];
    for (var v = 0; v <= spanMs; v += step) {
      ticks.add(v);
    }
    return ticks;
  }

  static String _tickText(int ms, List<int> ticks) {
    final step = ticks.length > 1 ? ticks[1] : ms;
    return '${(ms / 1000).toStringAsFixed(step < 1000 ? 1 : 0)}s';
  }

  @override
  bool shouldRepaint(_GanttPainter old) =>
      old.steps != steps ||
      old.spanMs != spanMs ||
      old.rowH != rowH ||
      old.gridInk != gridInk ||
      old.errorInk != errorInk;
}
