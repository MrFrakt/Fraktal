/// Shared visual materials. They decorate ordinary Material controls, so focus,
/// ink, hit targets and the PLC's semantic colours keep their existing owners.
library;

import 'dart:ui' as ui;

import 'package:flutter/material.dart';
import 'theme_chrome.dart';

/// Unit-card spacing for inline chips, badges and actions, including wrap runs.
const kInlineItemGap = 8.0;

/// `console`: the dark operations dashboard - borderless slate panels on a deep
/// canvas, depth from shadow and a top-edge reflection rather than outlines.
enum SurfaceFinish {
  flat,
  neon,
  glass,
  blueprint,
  copper,
  paper,
  soft,
  console
}

@immutable
class FraktalSurfaceTheme extends ThemeExtension<FraktalSurfaceTheme> {
  final SurfaceFinish finish;
  final Color canvas;
  final Color panel;
  final Color accent;
  final Color glint;
  final double radius;

  /// A strong colour the backdrop sweeps in from the top-left (a sunset wash
  /// behind glass panels). Null keeps the quiet tinted canvas.
  final Color? wash;

  const FraktalSurfaceTheme({
    this.finish = SurfaceFinish.flat,
    required this.canvas,
    required this.panel,
    required this.accent,
    required this.glint,
    this.radius = 14,
    this.wash,
  });

  /// How strong the card's reflection sheen is. Painted UNDER the content, so
  /// it never lowers the contrast of the text it sits behind.
  double get sheen => switch (finish) {
        SurfaceFinish.glass => 0.10,
        SurfaceFinish.console => 0.045,
        SurfaceFinish.neon || SurfaceFinish.blueprint => 0.05,
        SurfaceFinish.copper => 0.06,
        SurfaceFinish.soft => 0.55,
        SurfaceFinish.paper || SurfaceFinish.flat => 0,
      };

  bool get luminous =>
      finish == SurfaceFinish.neon || finish == SurfaceFinish.blueprint;
  bool get sculpted =>
      finish == SurfaceFinish.soft || finish == SurfaceFinish.paper;

  List<Color> get backdropColors => wash == null
      ? [
          Color.lerp(canvas, glint, 0.055)!,
          canvas,
          Color.lerp(canvas, accent, 0.04)!,
        ]
      : [wash!, Color.lerp(wash, canvas, 0.55)!, canvas];

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
    Color? wash,
  }) =>
      FraktalSurfaceTheme(
        finish: finish ?? this.finish,
        canvas: canvas ?? this.canvas,
        panel: panel ?? this.panel,
        accent: accent ?? this.accent,
        glint: glint ?? this.glint,
        radius: radius ?? this.radius,
        wash: wash ?? this.wash,
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
      wash: Color.lerp(wash, other.wash, t),
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
    if (skin == null || skin.finish == SurfaceFinish.flat) {
      final chrome = FraktalChromeTheme.of(context);
      return chrome == null ? child : Column(children: [
        FraktalAccentBand(colors: chrome.bandColors),
        Expanded(child: child),
      ]);
    }
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
    final bounds = Offset.zero & size;
    if (skin.finish == SurfaceFinish.blueprint ||
        skin.finish == SurfaceFinish.neon) {
      // Drafting paper: a faint minor grid under a major one (blueprint only).
      if (skin.finish == SurfaceFinish.blueprint) {
        _grid(canvas, size, 8, skin.accent.withValues(alpha: 0.022), 0.5);
      }
      _grid(canvas, size, 32, skin.accent.withValues(alpha: 0.05), 0.7);
    }
    switch (skin.finish) {
      case SurfaceFinish.glass:
        // Soft overlapping lenses give the local card blur something to
        // refract - the translucency only reads when something is behind it.
        _lens(canvas, size, const Offset(0.15, 0.2), skin.accent, 0.12, 0.65);
        _lens(canvas, size, const Offset(0.85, 0.7), skin.glint, 0.12, 0.65);
        _lens(canvas, size, const Offset(0.55, 0.05), skin.glint, 0.07, 0.4);
      case SurfaceFinish.soft:
        _lens(canvas, size, const Offset(0.1, 0.1), skin.accent, 0.05, 0.55);
        _lens(canvas, size, const Offset(0.9, 0.85), skin.glint, 0.07, 0.55);
      case SurfaceFinish.console:
        _lens(canvas, size, const Offset(0.5, -0.1), skin.accent, 0.06, 0.8);
      default:
        break;
    }
    if (skin.luminous || skin.finish == SurfaceFinish.console) {
      // Vignette: the eye settles on the middle of the panel, not its corners.
      canvas.drawRect(
        bounds,
        Paint()
          ..shader = RadialGradient(
            radius: 0.95,
            colors: [
              skin.canvas.withValues(alpha: 0),
              Color.lerp(skin.canvas, const Color(0xFF000000), 0.45)!
                  .withValues(alpha: 0.55),
            ],
            stops: const [0.55, 1],
          ).createShader(bounds),
      );
    }
  }

  static void _grid(
      Canvas canvas, Size size, double pitch, Color color, double width) {
    final paint = Paint()
      ..color = color
      ..strokeWidth = width;
    for (var x = 0.0; x < size.width; x += pitch) {
      canvas.drawLine(Offset(x, 0), Offset(x, size.height), paint);
    }
    for (var y = 0.0; y < size.height; y += pitch) {
      canvas.drawLine(Offset(0, y), Offset(size.width, y), paint);
    }
  }

  /// A soft coloured light at [at] (fractions of the backdrop).
  static void _lens(Canvas canvas, Size size, Offset at, Color color,
      double alpha, double reach) {
    final center = Offset(size.width * at.dx, size.height * at.dy);
    final radius = size.shortestSide * reach;
    canvas.drawCircle(
      center,
      radius,
      Paint()
        ..shader = RadialGradient(colors: [
          color.withValues(alpha: alpha),
          color.withValues(alpha: 0),
        ]).createShader(Rect.fromCircle(center: center, radius: radius)),
    );
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
      return RepaintBoundary(child: super.build(context));
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
      if (skin.luminous) ...[
        // A tight halo and a wide bloom: the edge reads as lit, not outlined.
        BoxShadow(
          color: skin.accent.withValues(alpha: 0.26),
          blurRadius: 12,
          spreadRadius: -2,
        ),
        BoxShadow(
          color: skin.accent.withValues(alpha: 0.10),
          blurRadius: 36,
          spreadRadius: 2,
        ),
      ] else ...[
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
                .withValues(alpha: glass && !reduceEffects ? 0.72 : 1),
            fill.withValues(alpha: glass && !reduceEffects ? 0.86 : 1),
          ],
        ),
      ),
      // The reflection is painted between the fill and the content, never
      // over the text.
      child: CustomPaint(
        painter: skin.sheen > 0 ? _SheenPainter(skin, outline) : null,
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
    final decorated = Padding(
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
    return RepaintBoundary(child: decorated);
  }
}

/// A panel's reflection: light falling on its upper part, fading out before the
/// middle, like a lacquered or glass surface under ceiling light.
class _SheenPainter extends CustomPainter {
  final FraktalSurfaceTheme skin;
  final ShapeBorder shape;
  const _SheenPainter(this.skin, this.shape);

  @override
  void paint(Canvas canvas, Size size) {
    final rect = Offset.zero & size;
    canvas.drawPath(
      shape.getOuterPath(rect),
      Paint()
        ..shader = LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: [
            Colors.white.withValues(alpha: skin.sheen),
            Colors.white.withValues(alpha: skin.sheen * 0.25),
            Colors.white.withValues(alpha: 0),
          ],
          stops: const [0, 0.22, 0.5],
        ).createShader(rect),
    );
  }

  @override
  bool shouldRepaint(_SheenPainter oldDelegate) =>
      skin != oldDelegate.skin || shape != oldDelegate.shape;
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
    if (skin.luminous) {
      // The lit tube: a crisp accent line just inside the border.
      canvas.drawPath(
        shape.getOuterPath((Offset.zero & size).deflate(2.5)),
        Paint()
          ..style = PaintingStyle.stroke
          ..strokeWidth = 1
          ..color = skin.accent.withValues(alpha: 0.28),
      );
      return;
    }
    if (skin.finish == SurfaceFinish.console) {
      // Top-edge catch light: the only edge a console panel shows.
      final rect = Offset.zero & size;
      canvas.drawLine(
        Offset(skin.radius, 0.75),
        Offset(size.width - skin.radius, 0.75),
        Paint()
          ..strokeWidth = 1.5
          ..shader = LinearGradient(colors: [
            Colors.white.withValues(alpha: 0),
            Colors.white.withValues(alpha: 0.16),
            Colors.white.withValues(alpha: 0),
          ]).createShader(rect),
      );
      return;
    }
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
  if (skin.finish == SurfaceFinish.flat) {
    // A flat palette (the ISA-101 greys): its own canvas and panel colours and
    // a quiet edge, and none of the glow, sheen or bevel treatment below.
    return theme.copyWith(
      extensions: [...theme.extensions.values, skin],
      scaffoldBackgroundColor: skin.canvas,
      cardTheme: theme.cardTheme.copyWith(
        color: skin.panel,
        elevation: 0,
        surfaceTintColor: Colors.transparent,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(skin.radius),
          side: BorderSide(color: cs.outlineVariant),
        ),
      ),
      appBarTheme: theme.appBarTheme.copyWith(
        backgroundColor: skin.panel,
        surfaceTintColor: Colors.transparent,
        elevation: 0,
        shape: Border(bottom: BorderSide(color: cs.outlineVariant)),
      ),
      dialogTheme: theme.dialogTheme.copyWith(
        backgroundColor: skin.panel,
        surfaceTintColor: Colors.transparent,
      ),
    );
  }
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
                  : skin.finish == SurfaceFinish.console
                      ? Colors.transparent
                      : dark
                          ? Colors.white24
                          : Colors.white70,
    ),
  );
  // The selected tab is a lit pill on the luminous, glass and console
  // finishes; the others keep Material's underline.
  final pillTabs = skin.luminous ||
      skin.finish == SurfaceFinish.glass ||
      skin.finish == SurfaceFinish.console;
  final tabPill = ShapeDecoration(
    color: cs.primary.withValues(alpha: 0.14),
    shape: RoundedRectangleBorder(
      borderRadius: BorderRadius.circular(8),
      side: BorderSide(color: cs.primary.withValues(alpha: 0.75)),
    ),
    shadows: skin.luminous
        ? [
            BoxShadow(
              color: skin.accent.withValues(alpha: 0.35),
              blurRadius: 10,
              spreadRadius: -1,
            ),
          ]
        : null,
  );
  ButtonStyle decorate(ButtonStyle? base, {bool raised = false}) =>
      (base ?? const ButtonStyle()).copyWith(
        elevation: raised
            ? WidgetStateProperty.resolveWith((states) =>
                states.contains(WidgetState.disabled) ||
                        states.contains(WidgetState.pressed)
                    ? 0.0
                    : skin.sculpted || skin.luminous
                        ? 4.0
                        : 2.0)
            : null,
        shadowColor: WidgetStatePropertyAll(skin.luminous
            ? skin.accent.withValues(alpha: 0.7)
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
    tabBarTheme: pillTabs
        ? theme.tabBarTheme.copyWith(
            indicator: tabPill,
            indicatorSize: TabBarIndicatorSize.tab,
            dividerColor: Colors.transparent,
          )
        : theme.tabBarTheme,
  );
}
