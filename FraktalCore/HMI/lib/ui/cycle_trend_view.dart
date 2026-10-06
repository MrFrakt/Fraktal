/// §8.11.4 cycle-time ANALYSIS — answers "why did cycle time go up?".
/// Stacked per-cycle columns split by time class (work vs each wait cause) with
/// the rolling-best (MinCycleTime) reference line, plus a command-timing
/// drill-through table (§8.11.4(a)/(c)). Pure CustomPaint; no packages.
library;

import 'package:flutter/material.dart';
import 'package:flutter/foundation.dart' show setEquals;
import 'theme_surfaces.dart';
import '../domain/types.dart';
import '../localization/localized_text.dart';
import 'timing_chart_filters.dart';

/// Stacked column trend of the last completed cycles. Each column is one cycle
/// split by time class; the dashed line is the rolling best (demonstrated
/// capability). A grown green share = the process slowed (wear, air, settle);
/// a grown colored share names the external cause (starved/blocked/operator/
/// external) — that is the §8.11.4(f) attribution, charted.
class CycleTrendView extends StatefulWidget {
  final List<CycleSummary> history;
  final Duration minCycleTime;
  final Set<TimeClass>? hiddenTimeClasses;
  const CycleTrendView(
      {super.key, required this.history, this.minCycleTime = Duration.zero,
      this.hiddenTimeClasses});

  @override
  State<CycleTrendView> createState() => _CycleTrendViewState();
}

class _CycleTrendViewState extends State<CycleTrendView> {
  int? _hover; // hovered/tapped cycle index (tooltip + table row highlight)

  @override
  Widget build(BuildContext context) {
    final h = widget.history;
    if (h.length < 2) return const SizedBox.shrink();
    return TimingChartFilters<TimeClass>(
      hiddenOptions: widget.hiddenTimeClasses,
      options: [
        for (final c in TimeClass.values)
          if (h.any((s) =>
              c.index < s.byClass.length && s.byClass[c.index] > Duration.zero))
            TimingChartOption(c, timeClassLabel(c), timeClassColor(c)),
      ],
      builder: _chart,
    );
  }

  Widget _chart(BuildContext context, Set<TimeClass> hidden, Widget legend) {
    final h = widget.history;
    final theme = Theme.of(context);
    final selected = _hover != null && _hover! < h.length ? h[_hover!] : null;
    return FraktalCard(
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            const Icon(Icons.stacked_bar_chart),
            const SizedBox(width: 8),
            Expanded(
              child: LText('Cycle-time trend (${h.length} cycles)',
                  style: theme.textTheme.titleMedium,
                  overflow: TextOverflow.ellipsis),
            ),
            if (hidden.isEmpty && widget.minCycleTime > Duration.zero)
              LText('best ${_s(widget.minCycleTime)}',
                  style: theme.textTheme.labelMedium),
          ]),
          const SizedBox(height: 8),
          if (hidden.isNotEmpty &&
              hidden.length ==
                  TimeClass.values
                      .where((c) => h.any((s) =>
                          c.index < s.byClass.length &&
                          s.byClass[c.index] > Duration.zero))
                      .length)
            const LText('Every time class is filtered out')
          else
            SizedBox(
              height: 140,
              width: double.infinity,
              child: LayoutBuilder(builder: (context, box) {
                return MouseRegion(
                  onHover: (e) => _pick(e.localPosition.dx, box.maxWidth),
                  onExit: (_) => setState(() => _hover = null),
                  child: GestureDetector(
                    onTapDown: (e) => _pick(e.localPosition.dx, box.maxWidth),
                    child: CustomPaint(
                      size: Size(box.maxWidth, 140),
                      painter: _TrendPainter(
                        history: h,
                        // The PLC best is the full-cycle reference; there is no
                        // authoritative filtered best to compare a slice against.
                        minCycle: hidden.isEmpty
                            ? widget.minCycleTime
                            : Duration.zero,
                        hidden: hidden,
                        hover: _hover,
                        surface: theme.colorScheme.surface,
                        gridInk: theme.colorScheme.outlineVariant,
                        refInk: theme.colorScheme.onSurfaceVariant,
                      ),
                    ),
                  ),
                );
              }),
            ),
          const SizedBox(height: 6),
          // tooltip row: the picked cycle's class split, in ink (never series color)
          if (selected != null)
            LText(
              'Cycle #${selected.cycleNo}: '
              '${hidden.isEmpty ? '' : '${context.tr('std.timing.shown')} ${_s(_shownTime(selected, hidden))} · '}'
              'total ${_s(selected.total)} · '
              'work ${_s(selected.workTime)}'
              '${_waits(selected)}',
              style: theme.textTheme.labelMedium,
            )
          else
            LText('Hover or tap a cycle for its split',
                style: theme.textTheme.labelSmall),
          const SizedBox(height: 6),
          legend,
        ]),
      ),
    );
  }

  void _pick(double dx, double width) {
    final n = widget.history.length;
    final index = (dx / (width / n)).floor().clamp(0, n - 1);
    if (index != _hover) setState(() => _hover = index);
  }

  String _waits(CycleSummary s) {
    final parts = <String>[];
    for (final c in TimeClass.values) {
      if (c == TimeClass.work) continue;
      if (c.index >= s.byClass.length) continue;
      final d = s.byClass[c.index];
      if (d > Duration.zero) parts.add('${timeClassLabel(c)} ${_s(d)}');
    }
    return parts.isEmpty ? '' : ' · ${parts.join(' · ')}';
  }

  static String _s(Duration d) =>
      '${(d.inMilliseconds / 1000).toStringAsFixed(1)}s';
}

// Keep the original samples intact for full-cycle readout. The chart axis
// and columns describe the sum of the selected classes only.
Duration _shownTime(CycleSummary cycle, Set<TimeClass> hidden) =>
    TimeClass.values
        .where((c) => !hidden.contains(c) && c.index < cycle.byClass.length)
        .fold(Duration.zero, (sum, c) => sum + cycle.byClass[c.index]);

class _TrendPainter extends CustomPainter {
  final List<CycleSummary> history;
  final Duration minCycle;
  final Set<TimeClass> hidden;
  final int? hover;
  final Color surface, gridInk, refInk;
  _TrendPainter({
    required this.history,
    required this.minCycle,
    required this.hidden,
    required this.hover,
    required this.surface,
    required this.gridInk,
    required this.refInk,
  });

  @override
  void paint(Canvas canvas, Size size) {
    final maxMs = history.map((s) {
      final shown = _shownTime(s, hidden).inMilliseconds;
      return hidden.isEmpty && s.total.inMilliseconds > shown
          ? s.total.inMilliseconds
          : shown;
    }).fold<int>(1, (a, b) => a > b ? a : b);
    final n = history.length;
    final slot = size.width / n;
    final barW = (slot - 2).clamp(1.0, 24.0); // 2px surface gap between columns

    // recessive horizontal grid: quarter lines only
    final grid = Paint()
      ..color = gridInk.withValues(alpha: 0.4)
      ..strokeWidth = 1;
    for (var g = 1; g <= 3; g++) {
      final y = size.height * (1 - g / 4);
      canvas.drawLine(Offset(0, y), Offset(size.width, y), grid);
    }

    final gapPaint = Paint()..color = surface;
    for (var i = 0; i < n; i++) {
      final s = history[i];
      final x = i * slot + (slot - barW) / 2;
      var yBottom = size.height;
      final dim = hover != null && hover != i;
      // stack in fixed class order: work first (baseline), then waits
      for (final c in TimeClass.values) {
        if (hidden.contains(c)) continue;
        final ms =
            c.index < s.byClass.length ? s.byClass[c.index].inMilliseconds : 0;
        if (ms <= 0) continue;
        final hPx = size.height * ms / maxMs;
        final top = yBottom - hPx;
        final paint = Paint()
          ..color = timeClassColor(c).withValues(alpha: dim ? 0.35 : 1.0);
        final isBase = yBottom >= size.height;
        canvas.drawRRect(
          RRect.fromRectAndCorners(
            Rect.fromLTRB(x, top, x + barW, yBottom),
            topLeft: const Radius.circular(3),
            topRight: const Radius.circular(3),
            bottomLeft: isBase ? Radius.zero : Radius.zero,
          ),
          paint,
        );
        // 2px surface gap between stacked segments
        canvas.drawRect(Rect.fromLTWH(x, top - 1, barW, 1), gapPaint);
        yBottom = top - 1;
      }
    }

    // rolling-best reference: dashed line at MinCycleTime
    if (minCycle > Duration.zero) {
      final y = size.height * (1 - minCycle.inMilliseconds / maxMs);
      final dash = Paint()
        ..color = refInk
        ..strokeWidth = 1.5;
      const dashW = 6.0, dashGap = 4.0;
      var x = 0.0;
      while (x < size.width) {
        canvas.drawLine(Offset(x, y), Offset(x + dashW, y), dash);
        x += dashW + dashGap;
      }
    }
  }

  @override
  bool shouldRepaint(_TrendPainter old) =>
      old.history != history ||
      old.hover != hover ||
      old.minCycle != minCycle ||
      !setEquals(old.hidden, hidden);
}

/// §8.11.4(a)/(c) — drill-through: the module command timing table. When a step
/// in the cycle Gantt is slow, this names the command (and its Min/Avg/Max drift)
/// that consumed the time. Plain table = the accessibility fallback by design.
class CommandTimingView extends StatelessWidget {
  final String moduleName;
  final List<CommandTiming> rows;
  const CommandTimingView(
      {super.key, required this.moduleName, required this.rows});

  @override
  Widget build(BuildContext context) {
    if (rows.isEmpty) return const SizedBox.shrink();
    final theme = Theme.of(context);
    final maxMs = rows
        .map((r) => r.maximum.inMilliseconds)
        .fold<int>(1, (a, b) => a > b ? a : b);
    return FraktalCard(
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            const Icon(Icons.av_timer),
            const SizedBox(width: 8),
            LText('Command timing — $moduleName',
                style: theme.textTheme.titleMedium),
          ]),
          const SizedBox(height: 8),
          Row(children: [
            const SizedBox(width: 140),
            _h(context, 'Count'),
            _h(context, 'Last'),
            _h(context, 'Min'),
            _h(context, 'Avg'),
            _h(context, 'Max'),
            const Expanded(child: SizedBox.shrink()),
          ]),
          for (final r in rows) _row(context, r, maxMs),
        ]),
      ),
    );
  }

  Widget _h(BuildContext context, String text) => SizedBox(
      width: 56,
      child: LText(text,
          style: Theme.of(context).textTheme.labelSmall,
          textAlign: TextAlign.right));

  Widget _row(BuildContext context, CommandTiming r, int maxMs) {
    final avgFrac = r.avg.inMilliseconds / maxMs;
    final maxFrac = r.maximum.inMilliseconds / maxMs;
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 3),
      child: Row(children: [
        SizedBox(
            width: 140, child: LText(r.label, overflow: TextOverflow.ellipsis)),
        _cell(context, '${r.count}'),
        _cell(context, _s(r.last)),
        _cell(context, _s(r.minimum)),
        _cell(context, _s(r.avg)),
        _cell(context, _s(r.maximum)),
        const SizedBox(width: 8),
        Expanded(
          child: LayoutBuilder(builder: (context, box) {
            return Stack(children: [
              Container(
                  height: 14,
                  decoration: BoxDecoration(
                      color:
                          Theme.of(context).colorScheme.surfaceContainerHighest,
                      borderRadius: BorderRadius.circular(3))),
              Container(
                height: 14,
                width: (box.maxWidth * avgFrac).clamp(2.0, box.maxWidth),
                decoration: BoxDecoration(
                    color: timeClassColor(TimeClass.work),
                    borderRadius: BorderRadius.circular(3)),
              ),
              Positioned(
                left: (box.maxWidth * maxFrac - 2).clamp(0.0, box.maxWidth - 2),
                child: Container(
                    width: 2,
                    height: 14,
                    color: Theme.of(context).colorScheme.onSurfaceVariant),
              ),
            ]);
          }),
        ),
      ]),
    );
  }

  Widget _cell(BuildContext context, String text) => SizedBox(
      width: 56,
      child: LText(text,
          style: Theme.of(context).textTheme.bodySmall,
          textAlign: TextAlign.right));

  static String _s(Duration d) =>
      '${(d.inMilliseconds / 1000).toStringAsFixed(2)}s';
}
