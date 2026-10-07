/// Physical I/O indicators shared by the manual card and fieldbus view.
library;

import 'package:flutter/material.dart';
import '../domain/fieldbus.dart';
import '../localization/localized_text.dart';
import 'app_theme.dart';
import 'theme_chrome.dart';

class IoSignalLed extends StatelessWidget {
  final ChannelDir direction;
  final bool? value; // null is unavailable, never OFF
  final double size;
  const IoSignalLed(
      {super.key,
      required this.direction,
      required this.value,
      this.size = 16});
  @override
  Widget build(BuildContext context) {
    final chrome = FraktalChromeTheme.of(context);
    final cs = Theme.of(context).colorScheme;
    final fill = value == true
        ? (chrome == null
            ? (direction == ChannelDir.input ? okColor(context) : cs.primary)
            : (direction == ChannelDir.input
                ? chrome.ioInputOn
                : chrome.ioOutputOn))
        : (chrome?.ioOff ?? cs.surfaceContainerHighest);
    final state = context.tr(value == null
        ? 'std.io.unavailable'
        : value!
            ? 'std.io.on'
            : 'std.io.off');
    final label = context
        .tr(direction == ChannelDir.input ? 'std.io.input' : 'std.io.output');
    return Semantics(
      label: label,
      value: state,
      child: Tooltip(
          message: '$label: $state',
          child: ExcludeSemantics(
            child: SizedBox.square(
                dimension: size,
                child: CustomPaint(
                  painter: IoSignalLedPainter(
                      direction: direction,
                      fill: fill,
                      glyph: chrome == null ? cs.onSurface : Colors.white,
                      unavailable: value == null),
                )),
          )),
    );
  }
}

class IoSignalLedPainter extends CustomPainter {
  final ChannelDir direction;
  final Color fill, glyph;
  final bool unavailable;
  const IoSignalLedPainter(
      {required this.direction,
      required this.fill,
      required this.glyph,
      required this.unavailable});
  @override
  void paint(Canvas canvas, Size size) {
    final side = size.shortestSide;
    final center = Offset(size.width / 2, size.height / 2);
    canvas.drawCircle(center, side / 2, Paint()..color = fill);
    final ink = Paint()
      ..color = glyph
      ..style = PaintingStyle.stroke
      ..strokeWidth = side / 12
      ..strokeCap = StrokeCap.round
      ..strokeJoin = StrokeJoin.round;
    final start = center - Offset(side * .23, 0);
    final end = center + Offset(side * .23, 0);
    if (unavailable) {
      canvas.drawLine(start, end, ink);
      return;
    }
    final down = direction == ChannelDir.input ? 1.0 : -1.0;
    final tip = center + Offset(0, side * .26 * down);
    canvas.drawLine(center - Offset(0, side * .28 * down), tip, ink);
    canvas.drawPath(
        Path()
          ..moveTo(start.dx, center.dy)
          ..lineTo(tip.dx, tip.dy)
          ..lineTo(end.dx, center.dy),
        ink);
  }

  @override
  bool shouldRepaint(IoSignalLedPainter old) =>
      direction != old.direction ||
      fill != old.fill ||
      glyph != old.glyph ||
      unavailable != old.unavailable;
}
