/// Shared visual materials. They decorate ordinary Material controls, so focus,
/// ink, hit targets and the PLC's semantic colours keep their existing owners.
library;

import 'dart:ui' as ui;

import 'package:flutter/material.dart';

enum SurfaceFinish { flat, neon, glass, blueprint, copper, paper, soft }

@immutable
class FraktalSurfaceTheme extends ThemeExtension<FraktalSurfaceTheme> {
  final SurfaceFinish finish;
  final Color canvas;
  final Color panel;
  final Color accent;
  final Color glint;
  final double radius;

  const FraktalSurfaceTheme({
    this.finish = SurfaceFinish.flat,
    required this.canvas,
    required this.panel,
    required this.accent,
    required this.glint,
    this.radius = 14,
  });

  bool get luminous =>
      finish == SurfaceFinish.neon || finish == SurfaceFinish.blueprint;
  bool get sculpted =>
      finish == SurfaceFinish.soft || finish == SurfaceFinish.paper;

  List<Color> get backdropColors => [
        Color.lerp(canvas, glint, 0.055)!,
        canvas,
        Color.lerp(canvas, accent, 0.04)!,
      ];

  static FraktalSurfaceTheme? of(BuildContext context) =>
      Theme.of(context).extension<FraktalSurfaceTheme>();

  @override
  FraktalSurfaceTheme copyWith({
    SurfaceFinish? finish,
    Color? canvas,
    Color? panel,
    Color? accent,
    Color? glint,
    double? radius,
  }) =>
      FraktalSurfaceTheme(
        finish: finish ?? this.finish,
        canvas: canvas ?? this.canvas,
        panel: panel ?? this.panel,
        accent: accent ?? this.accent,
        glint: glint ?? this.glint,
        radius: radius ?? this.radius,
      );

  @override
  FraktalSurfaceTheme lerp(FraktalSurfaceTheme? other, double t) {
    if (other == null) return this;
    return FraktalSurfaceTheme(
      finish: t < 0.5 ? finish : other.finish,
      canvas: Color.lerp(canvas, other.canvas, t)!,
      panel: Color.lerp(panel, other.panel, t)!,
      accent: Color.lerp(accent, other.accent, t)!,
      glint: Color.lerp(glint, other.glint, t)!,
      radius: ui.lerpDouble(radius, other.radius, t)!,
    );
  }
}

/// A static, repaint-isolated backdrop, shared by setup and the operator shell.
/// No continuously animated shaders or per-scan work on an industrial panel.
class FraktalBackdrop extends StatelessWidget {
  final Widget child;
  const FraktalBackdrop({super.key, required this.child});

  @override
  Widget build(BuildContext context) {
    final skin = FraktalSurfaceTheme.of(context);
    if (skin == null || skin.finish == SurfaceFinish.flat) return child;
    return Stack(fit: StackFit.expand, children: [
      Positioned.fill(
        child: IgnorePointer(
          child: RepaintBoundary(
            child: DecoratedBox(
              decoration: BoxDecoration(
                gradient: LinearGradient(
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                  colors: skin.backdropColors,
                ),
              ),
              child: CustomPaint(painter: _BackdropPainter(skin)),
            ),
          ),
        ),
      ),
      Theme(
        data: Theme.of(context)
            .copyWith(scaffoldBackgroundColor: Colors.transparent),
        child: child,
      ),
    ]);
  }
}

class _BackdropPainter extends CustomPainter {
  final FraktalSurfaceTheme skin;
  const _BackdropPainter(this.skin);

  @override
  void paint(Canvas canvas, Size size) {
    if (skin.finish == SurfaceFinish.blueprint ||
        skin.finish == SurfaceFinish.neon) {
      final paint = Paint()
        ..color = skin.accent.withValues(alpha: 0.045)
        ..strokeWidth = 0.7;
      const pitch = 32.0;
      for (var x = 0.0; x < size.width; x += pitch) {
        canvas.drawLine(Offset(x, 0), Offset(x, size.height), paint);
      }
      for (var y = 0.0; y < size.height; y += pitch) {
        canvas.drawLine(Offset(0, y), Offset(size.width, y), paint);
      }
    }
    if (skin.finish == SurfaceFinish.glass) {
      // Soft overlapping lenses give the local card blur something to refract.
      for (final (center, color) in [
        (Offset(size.width * 0.15, size.height * 0.2), skin.accent),
        (Offset(size.width * 0.85, size.height * 0.7), skin.glint),
      ]) {
        final radius = size.shortestSide * 0.65;
        canvas.drawCircle(
          center,
          radius,
          Paint()
            ..shader = RadialGradient(colors: [
              color.withValues(alpha: 0.07),
              color.withValues(alpha: 0),
            ]).createShader(Rect.fromCircle(center: center, radius: radius)),
        );
      }
    }
  }

  @override
  bool shouldRepaint(_BackdropPainter oldDelegate) => oldDelegate.skin != skin;
}

/// Drop-in Card with a single implementation of glow, glass and tactile depth.
/// Explicit fills (including severity tints) are preserved over the panel base.
/// Legacy themes still build Flutter's original Card unchanged.
class FraktalCard extends Card {
  const FraktalCard({
    super.key,
    super.color,
    super.shadowColor,
    super.surfaceTintColor,
    super.elevation,
    super.shape,
    super.borderOnForeground,
    super.margin,
    super.clipBehavior,
    super.semanticContainer,
    super.child,
  });

  @override
  Widget build(BuildContext context) {
    final skin = FraktalSurfaceTheme.of(context);
    if (skin == null || skin.finish == SurfaceFinish.flat) {
      return super.build(context);
    }
    final theme = Theme.of(context);
    final glass = skin.finish == SurfaceFinish.glass;
    final dark = theme.brightness == Brightness.dark;
    final reduceEffects = MediaQuery.disableAnimationsOf(context);
    final outline = shape ??
        theme.cardTheme.shape ??
        RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(skin.radius));
    final fill =
        color == null ? skin.panel : Color.alphaBlend(color!, skin.panel);
    final shadows = <BoxShadow>[
      if (skin.luminous)
        BoxShadow(
          color: skin.accent.withValues(alpha: 0.13),
          blurRadius: 14,
          spreadRadius: -3,
        )
      else ...[
        BoxShadow(
          color: (dark ? Colors.black : const Color(0xFF716653))
              .withValues(alpha: skin.sculpted ? 0.22 : 0.14),
          blurRadius: skin.finish == SurfaceFinish.paper ? 3 : 14,
          offset: const Offset(4, 6),
        ),
        if (skin.sculpted)
          const BoxShadow(
            color: Color(0xCFFFFFFF),
            blurRadius: 10,
            offset: Offset(-4, -4),
          ),
      ],
    ];
    Widget panel = DecoratedBox(
      decoration: ShapeDecoration(
        shape: outline,
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [
            Color.lerp(fill, Colors.white, glass ? 0.035 : 0.012)!
                .withValues(alpha: glass && !reduceEffects ? 0.78 : 1),
            fill.withValues(alpha: glass && !reduceEffects ? 0.90 : 1),
          ],
        ),
      ),
      child: Card(
        margin: EdgeInsets.zero,
        elevation: 0,
        color: Colors.transparent,
        shadowColor: Colors.transparent,
        surfaceTintColor: Colors.transparent,
        shape: outline,
        borderOnForeground: borderOnForeground,
        clipBehavior: clipBehavior ?? Clip.antiAlias,
        semanticContainer: semanticContainer,
        child: child,
      ),
    );
    if (glass && !reduceEffects) {
      // Clip each filter to its card. Nested cards intentionally do not share a
      // backdrop key: overlapping filters must sample their own backdrop.
      panel = BackdropFilter(
        filter: ui.ImageFilter.blur(sigmaX: 12, sigmaY: 12),
        child: panel,
      );
    }
    return Padding(
      padding: margin ?? theme.cardTheme.margin ?? const EdgeInsets.all(4),
      child: DecoratedBox(
        decoration: ShapeDecoration(shape: outline, shadows: shadows),
        child: ClipPath(
          clipper: ShapeBorderClipper(shape: outline),
          child: CustomPaint(
            foregroundPainter: _SurfaceEdgePainter(skin, outline),
            child: panel,
          ),
        ),
      ),
    );
  }
}

/// Directional edge light supplies the lens rim / folded edge without putting
/// a translucent overlay over text or changing the widget's hit-test shape.
class _SurfaceEdgePainter extends CustomPainter {
  final FraktalSurfaceTheme skin;
  final ShapeBorder shape;
  const _SurfaceEdgePainter(this.skin, this.shape);

  @override
  void paint(Canvas canvas, Size size) {
    final glass = skin.finish == SurfaceFinish.glass;
    final paper = skin.finish == SurfaceFinish.paper;
    final copper = skin.finish == SurfaceFinish.copper;
    if (!glass && !paper && !copper) return;
    final rect = (Offset.zero & size).deflate(paper ? 2 : 1);
    canvas.drawPath(
      shape.getOuterPath(rect),
      Paint()
        ..style = PaintingStyle.stroke
        ..strokeWidth = paper ? 3 : 1.5
        ..shader = LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [
            Colors.white.withValues(alpha: glass ? 0.75 : 0.9),
            skin.glint.withValues(alpha: glass ? 0.12 : 0.4),
            (paper ? const Color(0xFF79543C) : skin.glint)
                .withValues(alpha: paper ? 0.4 : 0.6),
          ],
          stops: const [0, 0.55, 1],
        ).createShader(rect),
    );
  }

  @override
  bool shouldRepaint(_SurfaceEdgePainter oldDelegate) =>
      skin != oldDelegate.skin || shape != oldDelegate.shape;
}

/// Added after control scaling, so it preserves the operator's target size.
ThemeData applySurfaceTheme(ThemeData theme, FraktalSurfaceTheme skin) {
  final cs = theme.colorScheme;
  final dark = theme.brightness == Brightness.dark;
  final bevel = skin.finish == SurfaceFinish.paper;
  final shape = RoundedRectangleBorder(
    borderRadius: BorderRadius.circular(skin.radius),
    side: BorderSide(
      color: skin.finish == SurfaceFinish.blueprint
          ? skin.glint.withValues(alpha: 0.7)
          : skin.luminous
              ? skin.accent.withValues(alpha: 0.65)
              : skin.finish == SurfaceFinish.copper
                  ? skin.glint.withValues(alpha: 0.6)
                  : dark
                      ? Colors.white24
                      : Colors.white70,
    ),
  );
  ButtonStyle decorate(ButtonStyle? base, {bool raised = false}) =>
      (base ?? const ButtonStyle()).copyWith(
        elevation: raised
            ? WidgetStateProperty.resolveWith((states) =>
                states.contains(WidgetState.disabled) ||
                        states.contains(WidgetState.pressed)
                    ? 0.0
                    : skin.sculpted
                        ? 4.0
                        : 2.0)
            : null,
        shadowColor: WidgetStatePropertyAll(skin.luminous
            ? skin.accent.withValues(alpha: 0.5)
            : Colors.black26),
        backgroundBuilder: (context, states, child) {
          if (states.contains(WidgetState.disabled))
            return child ?? const SizedBox.shrink();
          final pressed = states.contains(WidgetState.pressed);
          return DecoratedBox(
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(10),
              gradient: LinearGradient(
                begin: pressed ? Alignment.bottomRight : Alignment.topLeft,
                end: pressed ? Alignment.topLeft : Alignment.bottomRight,
                colors: [
                  Colors.white.withValues(alpha: pressed ? 0.02 : 0.08),
                  Colors.transparent,
                  Colors.black.withValues(alpha: pressed ? 0.09 : 0.02),
                ],
              ),
            ),
            child: child,
          );
        },
      );
  return theme.copyWith(
    extensions: [...theme.extensions.values, skin],
    // Remain usable in isolated hosts. Only FraktalBackdrop makes scaffolds
    // transparent, after supplying a real painted background behind them.
    scaffoldBackgroundColor: skin.canvas,
    cardTheme: theme.cardTheme.copyWith(
      color: skin.panel,
      elevation: 0,
      shape: bevel
          ? BeveledRectangleBorder(
              borderRadius: BorderRadius.circular(skin.radius),
              side: BorderSide(color: skin.glint.withValues(alpha: 0.35)))
          : shape,
      surfaceTintColor: Colors.transparent,
    ),
    appBarTheme: theme.appBarTheme.copyWith(
      backgroundColor: skin.panel,
      surfaceTintColor: Colors.transparent,
      elevation: skin.sculpted ? 3 : 0,
      shape: Border(bottom: BorderSide(color: cs.outlineVariant)),
    ),
    filledButtonTheme: FilledButtonThemeData(
        style: decorate(theme.filledButtonTheme.style, raised: true)),
    elevatedButtonTheme: ElevatedButtonThemeData(
        style: decorate(theme.elevatedButtonTheme.style, raised: true)),
    outlinedButtonTheme: OutlinedButtonThemeData(
        style: decorate(theme.outlinedButtonTheme.style)),
    inputDecorationTheme: theme.inputDecorationTheme.copyWith(
      filled: true,
      fillColor: Color.lerp(skin.panel, skin.canvas, 0.65),
      border: OutlineInputBorder(borderRadius: BorderRadius.circular(10)),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(10),
        borderSide: BorderSide(color: cs.outline),
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(10),
        borderSide: BorderSide(color: cs.primary, width: 2),
      ),
    ),
    chipTheme: theme.chipTheme.copyWith(
      backgroundColor: skin.panel,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
      side: BorderSide(color: cs.outlineVariant),
    ),
    dialogTheme: theme.dialogTheme.copyWith(
      backgroundColor: skin.panel,
      surfaceTintColor: Colors.transparent,
      shape: shape,
    ),
    dividerTheme: theme.dividerTheme.copyWith(color: cs.outlineVariant),
  );
}
