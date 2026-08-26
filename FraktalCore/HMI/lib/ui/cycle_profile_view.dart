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
import '../domain/types.dart';
import 'app_theme.dart';

// Categorical palette validated with the dataviz six-checks (light PASS; dark
// passes with a contrast WARN on blocked, relieved by direct labels + the table
// views these charts always carry). Fixed assignment — never re-ordered.
Color timeClassColor(TimeClass c) {
  switch (c) {
    case TimeClass.work:
      return const Color(0xFF2E7D32); // green: value-adding
    case TimeClass.waitUpstream:
      return const Color(0xFF1565C0); // blue: starved
    case TimeClass.waitDownstream:
      return const Color(0xFFAD1457); // magenta: blocked
    case TimeClass.waitOperator:
      return const Color(0xFFB26A00); // amber: operator
    case TimeClass.waitExternal:
      return const Color(0xFF0097A7); // teal: host/tool
  }
}

String timeClassLabel(TimeClass c) => switch (c) {
      TimeClass.work => 'Work',
      TimeClass.waitUpstream => 'Wait ↑ (starved)',
      TimeClass.waitDownstream => 'Wait ↓ (blocked)',
      TimeClass.waitOperator => 'Wait operator',
      TimeClass.waitExternal => 'Wait external',
    };

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

class CycleProfileView extends StatefulWidget {
  final CycleProfile profile;
  const CycleProfileView({super.key, required this.profile});

  @override
  State<CycleProfileView> createState() => _CycleProfileViewState();
}

class _CycleProfileViewState extends State<CycleProfileView> {
  /// Time classes taken out of the chart. Filtering HIDES rows; it never moves
  /// the ones that remain — the axis stays the real cycle, so a step keeps the
  /// position (and the colour) it had before the filter, and the gap a hidden
  /// class leaves behind is where that time actually went.
  final Set<TimeClass> _hidden = {};

  @override
  void didUpdateWidget(CycleProfileView old) {
    super.didUpdateWidget(old);
    // A class that is no longer anywhere in the cycle must not stay latched
    // out: its chip is gone, so nothing would be left to switch it back on.
    _hidden.removeWhere(
        (c) => !widget.profile.steps.any((s) => s.timeClass == c));
  }

  @override
  Widget build(BuildContext context) {
    final p = widget.profile;
    if (p.steps.isEmpty) return const SizedBox.shrink();
    final theme = Theme.of(context);
    final scale = ControlScaleScope.of(context).textScale;

    // Offsets come from the WHOLE cycle, then the hidden rows are dropped — the
    // survivors keep their true start, which a re-flow of the visible steps
    // would silently falsify.
    final allStarts = stepStartOffsetsMs(p.steps);
    final steps = <StepTiming>[];
    final starts = <int>[];
    for (var i = 0; i < p.steps.length; i++) {
      if (_hidden.contains(p.steps[i].timeClass)) continue;
      steps.add(p.steps[i]);
      starts.add(allStarts[i]);
    }

    // The FULL cycle extent. Total is the authority (§8.11.1 reconciles with
    // it); the step sum only wins if a profile arrives inconsistent, so the last
    // bar can never run off the end.
    final cycleMs = math.max(
      1,
      math.max(p.total.inMilliseconds,
          allStarts.last + p.steps.last.duration.inMilliseconds),
    );

    // §8.11.4(c) - the axis ZOOMS to the time still charted, so filtering out a
    // class that dominates the cycle does not leave the survivors as slivers
    // against an axis mostly describing bars that are no longer drawn.
    //
    // Zooming is not RE-FLOWING, and the difference is the whole point. Every
    // surviving bar keeps its TRUE start offset: only the window the axis
    // describes changes, so a step that really began at 4.2 s is still drawn at
    // 4.2 s and still labelled from the same clock. Re-flowing the survivors to
    // close the gaps would silently falsify when each step ran, which is the one
    // thing this chart exists to show.
    var originMs = 0;
    var endMs = cycleMs;
    if (_hidden.isNotEmpty && steps.isNotEmpty) {
      var lo = starts.first;
      var hi = starts.first + steps.first.duration.inMilliseconds;
      for (var i = 1; i < steps.length; i++) {
        final s = starts[i];
        final e = s + steps[i].duration.inMilliseconds;
        if (s < lo) lo = s;
        if (e > hi) hi = e;
      }
      // Never zoom past the cycle, and never invert: a profile that arrives
      // inconsistent degrades to the full axis rather than to a broken one.
      originMs = lo.clamp(0, cycleMs);
      endMs = hi.clamp(originMs + 1, cycleMs);
    }
    final spanMs = math.max(1, endMs - originMs);

    final present = [
      for (final c in TimeClass.values)
        if (p.steps.any((s) => s.timeClass == c)) c
    ];
    var hiddenMs = 0;
    var hiddenSteps = 0;
    for (final s in p.steps) {
      if (!_hidden.contains(s.timeClass)) continue;
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

    return Card(
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
          // Column headings. Start is the value the Gantt adds, and it is text
          // here so position is never the only way to read it — the row set is
          // this chart's table-view twin.
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
                        rowH: rowH, noW: noW, nameW: nameW, startW: startW),
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
                      originMs: originMs,
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
          if (_hidden.isNotEmpty)
            _filterSummary(context, hiddenMs, hiddenSteps, p.total),
          const SizedBox(height: 8),
          // Legend AND filter: the swatch carries identity, the chip's checkmark
          // and the struck-through label carry the on/off state, so what is in
          // the chart is never signalled by colour alone.
          Wrap(spacing: 8, runSpacing: 4, children: [
            for (final c in present) _classChip(context, c, p.steps),
          ]),
        ]),
      ),
    );
  }

  Widget _classChip(BuildContext ctx, TimeClass c, List<StepTiming> all) {
    final theme = Theme.of(ctx);
    final shown = !_hidden.contains(c);
    var ms = 0;
    for (final s in all) {
      if (s.timeClass == c) ms += s.duration.inMilliseconds;
    }
    final ink = timeClassColor(c);
    return FilterChip(
      selected: shown,
      onSelected: (_) => setState(() {
        if (shown) {
          _hidden.add(c);
        } else {
          _hidden.remove(c);
        }
      }),
      tooltip: ctx.tr(shown ? 'Filter out of the chart' : 'Add to the chart'),
      label: Row(mainAxisSize: MainAxisSize.min, children: [
        Container(
          width: 12,
          height: 12,
          decoration: BoxDecoration(
            // Hollow when filtered out — the second, non-colour encoding.
            color: shown ? ink : Colors.transparent,
            border: Border.all(color: ink, width: 2),
            borderRadius: BorderRadius.circular(3),
          ),
        ),
        const SizedBox(width: 6),
        LText(timeClassLabel(c),
            style: TextStyle(
                fontSize: 12,
                decoration: shown ? null : TextDecoration.lineThrough)),
        const SizedBox(width: 6),
        LText(_s(Duration(milliseconds: ms)),
            style: theme.textTheme.labelSmall?.copyWith(
                fontFeatures: const [FontFeature.tabularFigures()])),
      ]),
    );
  }

  /// What the filter took out, as a number — and the §8.11.4(f) question it is
  /// really being asked: what would this cycle be without that class?
  Widget _filterSummary(
      BuildContext ctx, int hiddenMs, int hiddenSteps, Duration total) {
    final theme = Theme.of(ctx);
    final names = [
      for (final c in TimeClass.values)
        if (_hidden.contains(c)) ctx.tr(timeClassLabel(c))
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
            'the cycle without ${_hidden.length == 1 ? 'it' : 'them'} '
            'is ${_s(rest)}',
            style: theme.textTheme.labelMedium
                ?.copyWith(color: theme.colorScheme.onSurfaceVariant),
          ),
        ),
        const SizedBox(width: 8),
        TextButton(
          onPressed: () => setState(_hidden.clear),
          child: const LText('Show all'),
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

  /// Left gutter: the row's identity, plus the start offset the bar encodes.
  Widget _labels(BuildContext ctx, StepTiming s, int startMs,
      {required double rowH,
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
          child: LText(_s(Duration(milliseconds: startMs)),
              textAlign: TextAlign.right,
              style: Theme.of(ctx).textTheme.bodySmall?.copyWith(
                  fontFeatures: const [FontFeature.tabularFigures()])),
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

/// The Gantt track: one shared time axis, one floating bar per step placed at
/// the offset it ran. Steps are contiguous, so the bars read as the staircase
/// the cycle actually walked — and a wait class now shows WHERE in the cycle it
/// fell, not only how much of the cycle it took.
class _GanttPainter extends CustomPainter {
  final List<StepTiming> steps;
  final List<int> startMs;

  /// Width of the drawn window, and the offset it begins at. [originMs] is
  /// non-zero only when a filter has zoomed the axis in; bars keep their true
  /// start and the window moves under them.
  final int spanMs;
  final int originMs;
  final double rowH, barH, axisH, textScale;
  final Color gridInk, guideInk, errorInk;

  _GanttPainter({
    required this.steps,
    required this.startMs,
    required this.spanMs,
    this.originMs = 0,
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
    final ticks = _ticks(originMs, spanMs);
    // The window, not the cycle: a bar's true offset is mapped through the
    // origin so filtering changes the SCALE and never the story.
    double x(int ms) => size.width * (ms - originMs) / spanMs;

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
      // declared guard would have ended this step, so a bar reaching past it is
      // the overrun, measured on the cycle's own axis.
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

  /// Nice 1/2/5 tick steps, targeting at most six rules across the track, laid
  /// out over the drawn window [originMs, originMs + spanMs].
  static List<int> _ticks(int originMs, int spanMs) {
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
    // Start at the first round multiple inside the window so the labels stay
    // readable clock offsets (2.0s, 2.5s ...) rather than an arbitrary origin
    // plus a step. The window edge itself is always marked.
    final end = originMs + spanMs;
    final first = (originMs / step).ceil() * step;
    final ticks = <int>[if (first > originMs) originMs];
    for (var v = first; v <= end; v += step) {
      ticks.add(v);
    }
    return ticks;
  }

  static String _tickText(int ms, List<int> ticks) {
    // The step is the GAP between ticks, which is not ticks[1] once the window
    // opens with a partial first interval.
    final step = ticks.length > 2
        ? ticks[2] - ticks[1]
        : (ticks.length > 1 ? ticks[1] - ticks[0] : ms);
    return '${(ms / 1000).toStringAsFixed(step < 1000 ? 1 : 0)}s';
  }

  @override
  bool shouldRepaint(_GanttPainter old) =>
      old.steps != steps ||
      old.spanMs != spanMs ||
      old.originMs != originMs ||
      old.rowH != rowH ||
      old.gridInk != gridInk ||
      old.errorInk != errorInk;
}
