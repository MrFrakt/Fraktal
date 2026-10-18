/// Reference-inspired shell materials, independent of PLC/status semantics.
library;

import 'dart:ui' as ui;
import 'package:flutter/material.dart';
import '../domain/types.dart';

@immutable
class FraktalChromeTheme extends ThemeExtension<FraktalChromeTheme> {
  final Color navigation;
  final Color onNavigation;
  final Color selection;
  final Color onSelection;
  final double navigationWidth;
  final double rowHeight;
  final List<Color> bandColors;
  final Color errorBanner, warningBanner, infoBanner;
  final Color ioInputOn, ioOutputOn, ioOff;

  const FraktalChromeTheme({
    required this.navigation,
    required this.onNavigation,
    required this.selection,
    required this.onSelection,
    this.navigationWidth = 225,
    this.rowHeight = 56,
    required this.bandColors,
    this.errorBanner = const Color(0xFFE60012),
    this.warningBanner = const Color(0xFF9B6A00),
    this.infoBanner = const Color(0xFF005C8F),
    this.ioInputOn = const Color(0xFF91C64A),
    this.ioOutputOn = const Color(0xFFE89690),
    this.ioOff = const Color(0xFFD2D5D5),
  });

  static FraktalChromeTheme? of(BuildContext context) =>
      Theme.of(context).extension<FraktalChromeTheme>();

  /// Solid annunciation fills, each paired with white text at >= 4.5:1.
  Color eventFill(Severity severity) => switch (severity) {
    Severity.high => errorBanner,
    Severity.medium => warningBanner,
    Severity.low => infoBanner,
  };

  @override
  FraktalChromeTheme copyWith(
          {Color? navigation,
          Color? onNavigation,
          Color? selection,
          Color? onSelection,
          double? navigationWidth,
          double? rowHeight,
          List<Color>? bandColors, Color? errorBanner,
          Color? warningBanner, Color? infoBanner,
          Color? ioInputOn, Color? ioOutputOn, Color? ioOff}) =>
      FraktalChromeTheme(
        navigation: navigation ?? this.navigation,
        onNavigation: onNavigation ?? this.onNavigation,
        selection: selection ?? this.selection,
        onSelection: onSelection ?? this.onSelection,
        navigationWidth: navigationWidth ?? this.navigationWidth,
        rowHeight: rowHeight ?? this.rowHeight,
        bandColors: bandColors ?? this.bandColors,
        errorBanner: errorBanner ?? this.errorBanner,
        warningBanner: warningBanner ?? this.warningBanner,
        infoBanner: infoBanner ?? this.infoBanner,
        ioInputOn: ioInputOn ?? this.ioInputOn,
        ioOutputOn: ioOutputOn ?? this.ioOutputOn,
        ioOff: ioOff ?? this.ioOff,
      );

  @override
  FraktalChromeTheme lerp(FraktalChromeTheme? other, double t) {
    if (other == null) return this;
    return FraktalChromeTheme(
      navigation: Color.lerp(navigation, other.navigation, t)!,
      onNavigation: Color.lerp(onNavigation, other.onNavigation, t)!,
      selection: Color.lerp(selection, other.selection, t)!,
      onSelection: Color.lerp(onSelection, other.onSelection, t)!,
      navigationWidth:
          ui.lerpDouble(navigationWidth, other.navigationWidth, t)!,
      rowHeight: ui.lerpDouble(rowHeight, other.rowHeight, t)!,
      bandColors: t < 0.5 ? bandColors : other.bandColors,
      errorBanner: Color.lerp(errorBanner, other.errorBanner, t)!,
      warningBanner: Color.lerp(warningBanner, other.warningBanner, t)!,
      infoBanner: Color.lerp(infoBanner, other.infoBanner, t)!,
      ioInputOn: Color.lerp(ioInputOn, other.ioInputOn, t)!,
      ioOutputOn: Color.lerp(ioOutputOn, other.ioOutputOn, t)!,
      ioOff: Color.lerp(ioOff, other.ioOff, t)!,
    );
  }

  /// Scope the dark navigation separately from the light content. Semantic
  /// status helpers then choose their dark-surface shades automatically.
  ThemeData navigationTheme(ThemeData theme) => theme.copyWith(
        colorScheme: theme.colorScheme.copyWith(
          brightness: Brightness.dark,
          surface: navigation,
          surfaceContainerLow: navigation,
          onSurface: onNavigation,
          onSurfaceVariant: onNavigation,
          secondaryContainer: selection,
          onSecondaryContainer: onSelection,
          error: const Color(0xFFFFB4AB),
          onError: const Color(0xFF690005),
        ),
        textTheme: theme.textTheme
            .apply(bodyColor: onNavigation, displayColor: onNavigation),
        canvasColor: navigation,
        cardColor: navigation,
        iconTheme: theme.iconTheme.copyWith(color: onNavigation),
        dividerTheme:
            theme.dividerTheme.copyWith(color: const Color(0xFF444B50)),
      );
}

const kLikeABoschChrome = FraktalChromeTheme(
  navigation: Color(0xFF272F34),
  onNavigation: Color(0xFFFFFFFF),
  // Slightly deeper than the reference cyan to keep white labels at AA.
  selection: Color(0xFF007DA8),
  onSelection: Color(0xFFFFFFFF),
  bandColors: [
    Color(0xFF9D2335),
    Color(0xFFB7253A),
    Color(0xFFCF1830),
    Color(0xFFE21B27),
    Color(0xFF674394),
    Color(0xFF47499B),
    Color(0xFF244791),
    Color(0xFF16468B),
    Color(0xFF204B94),
    Color(0xFF2467A4),
    Color(0xFF2787B7),
    Color(0xFF26A5BE),
    Color(0xFF00A9C2),
    Color(0xFF00A978),
    Color(0xFF00A76A),
    Color(0xFF78BE72),
    Color(0xFF80C178),
    Color(0xFF299653),
  ],
);

/// Static full-width band; the diagonal joins follow the supplied screenshots.
class FraktalAccentBand extends StatelessWidget {
  final List<Color> colors;
  const FraktalAccentBand({super.key, required this.colors});
  @override
  Widget build(BuildContext context) => ExcludeSemantics(
        child: IgnorePointer(
            child: RepaintBoundary(
          child: SizedBox(
              height: 8,
              width: double.infinity,
              child: CustomPaint(painter: _AccentBandPainter(colors))),
        )),
      );
}

class _AccentBandPainter extends CustomPainter {
  final List<Color> colors;
  const _AccentBandPainter(this.colors);
  @override
  void paint(Canvas canvas, Size size) {
    if (colors.isEmpty) return;
    canvas.drawRect(Offset.zero & size, Paint()..color = colors.first);
    final width = size.width / colors.length;
    double join(int index) => index == 0 || index == colors.length
        ? 0
        : (index.isEven ? 1 : -1) * (width * 0.06).clamp(0.0, 4.0);
    for (var index = 0; index < colors.length; index++) {
      final left = index * width;
      final right = (index + 1) * width;
      canvas.drawPath(
          Path()
            ..moveTo(left, 0)
            ..lineTo(right, 0)
            ..lineTo(right + join(index + 1), size.height)
            ..lineTo(left + join(index), size.height)
            ..close(),
          Paint()..color = colors[index]);
    }
  }

  @override
  bool shouldRepaint(_AccentBandPainter old) => old.colors != colors;
}

ThemeData applyChromeTheme(ThemeData theme, FraktalChromeTheme chrome) {
  const square = RoundedRectangleBorder();
  const shape = WidgetStatePropertyAll<OutlinedBorder>(square);
  ButtonStyle squared(ButtonStyle? style) =>
      (style ?? const ButtonStyle()).copyWith(
        shape: shape,
        elevation: const WidgetStatePropertyAll(0),
      );
  final cs = theme.colorScheme;
  return theme.copyWith(
    extensions: [...theme.extensions.values, chrome],
    textTheme: theme.textTheme.apply(fontFamily: 'Segoe UI'),
    appBarTheme: theme.appBarTheme.copyWith(scrolledUnderElevation: 0),
    filledButtonTheme:
        FilledButtonThemeData(style: squared(theme.filledButtonTheme.style)),
    elevatedButtonTheme: ElevatedButtonThemeData(
        style: squared(theme.elevatedButtonTheme.style)),
    outlinedButtonTheme: OutlinedButtonThemeData(
        style: squared(theme.outlinedButtonTheme.style)),
    textButtonTheme:
        TextButtonThemeData(style: squared(theme.textButtonTheme.style)),
    iconButtonTheme:
        IconButtonThemeData(style: squared(theme.iconButtonTheme.style)),
    segmentedButtonTheme: SegmentedButtonThemeData(
        style: squared(theme.segmentedButtonTheme.style)),
    chipTheme: theme.chipTheme
        .copyWith(shape: square, side: BorderSide(color: cs.outlineVariant)),
    dialogTheme: theme.dialogTheme.copyWith(shape: square),
    drawerTheme: theme.drawerTheme.copyWith(shape: square),
    popupMenuTheme: theme.popupMenuTheme.copyWith(shape: square),
    inputDecorationTheme: theme.inputDecorationTheme.copyWith(
      filled: true,
      fillColor: const Color(0xFFEEEEEE),
      border: const UnderlineInputBorder(),
      enabledBorder:
          UnderlineInputBorder(borderSide: BorderSide(color: cs.outline)),
      focusedBorder: UnderlineInputBorder(
          borderSide: BorderSide(color: cs.primary, width: 2)),
    ),
    tabBarTheme: theme.tabBarTheme.copyWith(
      labelColor: cs.primary,
      unselectedLabelColor: cs.onSurface,
      indicatorColor: cs.primary,
      indicatorSize: TabBarIndicatorSize.label,
      indicator: UnderlineTabIndicator(
          borderSide: BorderSide(color: cs.primary, width: 2)),
      labelStyle:
          theme.tabBarTheme.labelStyle?.copyWith(fontWeight: FontWeight.w400),
    ),
    switchTheme: theme.switchTheme.copyWith(
      trackColor: WidgetStateProperty.resolveWith((states) =>
          states.contains(WidgetState.selected)
              ? cs.primary
              : const Color(0xFFA7AEB2)),
      thumbColor: const WidgetStatePropertyAll(Colors.white),
      trackOutlineColor: const WidgetStatePropertyAll(Colors.transparent),
    ),
  );
}
