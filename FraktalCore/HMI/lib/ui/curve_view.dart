/// The Curve tab: the last curve a module judged (Modules `ST_CurveRecord`,
/// `FB_CurveMonitor`) - the measured samples, the windows and envelopes they
/// were judged against, and the verdict. Read-only: nothing here writes to the
/// PLC, and the PLC's verdict is shown, never recomputed.
library;

import 'package:flutter/material.dart';

import '../domain/module_node.dart';
import '../domain/types.dart';
import '../localization/localized_text.dart';
import 'app_theme.dart';
import 'theme_surfaces.dart';

/// The colours the chart draws with. Each is a semantic role, measured against
/// the card it sits on in every theme (theme_contrast_test): a window takes its
/// pass/fail colour, the measured curve and the envelopes the theme's own inks.
class CurvePalette {
  final Color curve, envelope, windowPassed, windowFailed, frame;
  const CurvePalette({
    required this.curve,
    required this.envelope,
    required this.windowPassed,
    required this.windowFailed,
    required this.frame,
  });

  factory CurvePalette.of(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return CurvePalette(
      curve: scheme.primary,
      envelope: scheme.onSurfaceVariant,
      windowPassed: okColor(context),
      windowFailed: severityColor(context, Severity.high),
      frame: scheme.outline,
    );
  }

  @override
  bool operator ==(Object other) =>
      other is CurvePalette &&
      other.curve == curve &&
      other.envelope == envelope &&
      other.windowPassed == windowPassed &&
      other.windowFailed == windowFailed &&
      other.frame == frame;

  @override
  int get hashCode =>
      Object.hash(curve, envelope, windowPassed, windowFailed, frame);
}

class CurveModuleTab extends StatelessWidget {
  final ModuleNode node;
  const CurveModuleTab({super.key, required this.node});

  @override
  Widget build(BuildContext context) {
    final curve = node.curve;
    if (curve == null) {
      return const Center(child: LText('std.module.curve.notPublished'));
    }
    if (!curve.loaded) {
      return const Center(child: LText('std.module.curve.loading'));
    }
    final theme = Theme.of(context);
    final palette = CurvePalette.of(context);
    return ListView(padding: const EdgeInsets.all(16), children: [
      FraktalCard(
        child: Padding(
          padding: const EdgeInsets.all(12),
          child:
              Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Row(children: [
              const Icon(Icons.show_chart),
              const SizedBox(width: kInlineItemGap),
              Flexible(
                child: LText('std.module.curve.title',
                    style: theme.textTheme.titleMedium,
                    overflow: TextOverflow.ellipsis),
              ),
              const Spacer(),
              _VerdictChip(verdict: curve.verdict),
            ]),
            if (curve.verdict == Verdict.nok && curve.reason.isNotEmpty)
              Padding(
                padding: const EdgeInsets.only(top: 4),
                child: LText(curve.reason,
                    style: TextStyle(
                        color: severityTextColor(context, Severity.high))),
              ),
            const SizedBox(height: 12),
            // Geometry is fractions of this box, so one record draws the
            // same on a 10" panel and a 21" monitor.
            AspectRatio(
              aspectRatio: 16 / 9,
              child: CustomPaint(
                painter: CurvePainter(curve: curve, palette: palette),
                child: const SizedBox.expand(),
              ),
            ),
            const SizedBox(height: 12),
            Wrap(spacing: 16, runSpacing: 8, children: [
              _LegendEntry(
                  color: palette.curve, label: 'std.module.curve.legendCurve'),
              if (curve.envelopes.isNotEmpty)
                _LegendEntry(
                    color: palette.envelope,
                    label: 'std.module.curve.legendEnvelope'),
              if (curve.windows.any((window) => window.passed))
                _LegendEntry(
                    color: palette.windowPassed,
                    label: 'std.module.curve.legendWindowPassed'),
              if (curve.windows.any((window) => !window.passed))
                _LegendEntry(
                    color: palette.windowFailed,
                    label: 'std.module.curve.legendWindowFailed'),
            ]),
            const SizedBox(height: 8),
            LText('std.module.curve.samples', args: {
              'count': curve.samples.length,
              'judged': curve.judgedSamples,
            }),
            if (curve.truncated)
              LText('std.module.curve.truncated',
                  args: {'count': curve.samples.length}),
          ]),
        ),
      ),
    ]);
  }
}

class _VerdictChip extends StatelessWidget {
  final Verdict verdict;
  const _VerdictChip({required this.verdict});

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final (label, color) = switch (verdict) {
      Verdict.ok => ('OK', okColor(context)),
      Verdict.nok => ('NOK', severityColor(context, Severity.high)),
      Verdict.rework => ('REWORK', warningColor(context)),
      Verdict.none => ('—', scheme.onSurfaceVariant),
    };
    // A 15% tint reads as the page surface: the themed label pairs with it and
    // the border carries the status hue (as the part card's verdict chip).
    return Chip(
        label: LText(label),
        backgroundColor: color.withValues(alpha: 0.15),
        labelStyle: TextStyle(color: scheme.onSurface),
        side: BorderSide(color: color));
  }
}

class _LegendEntry extends StatelessWidget {
  final Color color;
  final String label;
  const _LegendEntry({required this.color, required this.label});

  @override
  Widget build(BuildContext context) =>
      Row(mainAxisSize: MainAxisSize.min, children: [
        Container(width: 18, height: 4, color: color),
        const SizedBox(width: 6),
        LText(label),
      ]);
}

/// Draws one curve record scaled to fit its box: windows as rectangles in their
/// pass/fail colour, envelopes as polylines, the measured samples as the curve,
/// and a marker on the first sample past each envelope.
class CurvePainter extends CustomPainter {
  final CurveFacet curve;
  final CurvePalette palette;
  const CurvePainter({required this.curve, required this.palette});

  @override
  void paint(Canvas canvas, Size size) {
    double? x0, x1, y0, y1;
    void take(double x, double y) {
      x0 = x0 == null || x < x0! ? x : x0;
      x1 = x1 == null || x > x1! ? x : x1;
      y0 = y0 == null || y < y0! ? y : y0;
      y1 = y1 == null || y > y1! ? y : y1;
    }

    for (final sample in curve.samples) {
      take(sample.x, sample.y);
    }
    for (final window in curve.windows) {
      take(window.xMin, window.yMin);
      take(window.xMax, window.yMax);
    }
    for (final envelope in curve.envelopes) {
      for (final point in envelope.points) {
        take(point.x, point.y);
      }
    }
    final frame = Paint()
      ..color = palette.frame
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1;
    canvas.drawRect(Offset.zero & size, frame);
    if (x0 == null || !x0!.isFinite || !x1!.isFinite || !y0!.isFinite ||
        !y1!.isFinite) {
      return;
    }
    // A margin keeps a window drawn on the data's edge inside the frame.
    var spanX = x1! - x0!;
    var spanY = y1! - y0!;
    if (spanX <= 0) spanX = 1;
    if (spanY <= 0) spanY = 1;
    final left = x0! - spanX * 0.05, width = spanX * 1.1;
    final bottom = y0! - spanY * 0.05, height = spanY * 1.1;
    Offset at(double x, double y) => Offset(
        (x - left) / width * size.width,
        size.height - (y - bottom) / height * size.height);

    for (final window in curve.windows) {
      final color = window.passed ? palette.windowPassed : palette.windowFailed;
      final rect = Rect.fromPoints(
          at(window.xMin, window.yMax), at(window.xMax, window.yMin));
      canvas.drawRect(rect, Paint()..color = color.withValues(alpha: 0.10));
      canvas.drawRect(
          rect,
          Paint()
            ..color = color
            ..style = PaintingStyle.stroke
            ..strokeWidth = 2);
    }
    for (final envelope in curve.envelopes) {
      _polyline(canvas, [for (final p in envelope.points) at(p.x, p.y)],
          palette.envelope, 2);
    }
    _polyline(canvas, [for (final s in curve.samples) at(s.x, s.y)],
        palette.curve, 2.5);
    for (final envelope in curve.envelopes) {
      final index = envelope.cutIndex;
      if (index < 1 || index > curve.samples.length) continue;
      final cut = curve.samples[index - 1];
      canvas.drawCircle(
          at(cut.x, cut.y),
          5,
          Paint()
            ..color = palette.windowFailed
            ..style = PaintingStyle.stroke
            ..strokeWidth = 2);
    }
  }

  static void _polyline(
      Canvas canvas, List<Offset> points, Color color, double width) {
    if (points.length < 2) return;
    final path = Path()..moveTo(points.first.dx, points.first.dy);
    for (final point in points.skip(1)) {
      path.lineTo(point.dx, point.dy);
    }
    canvas.drawPath(
        path,
        Paint()
          ..color = color
          ..style = PaintingStyle.stroke
          ..strokeWidth = width
          ..strokeJoin = StrokeJoin.round);
  }

  @override
  bool shouldRepaint(CurvePainter oldDelegate) =>
      !identical(oldDelegate.curve, curve) || oldDelegate.palette != palette;
}
