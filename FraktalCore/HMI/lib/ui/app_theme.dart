/// Material 3 theme palette for the HMI. Twelve operator-selectable themes
/// (HMI_CONTRACT 'Tree & theming'); selection is level-gated in AppState.setTheme.
///
/// **Event/state colours are fixed semantics across ALL themes and never change
/// with the selected theme** (HMI_CONTRACT, Core §8.1): HIGH=error, MEDIUM=amber,
/// LOW=info blue; READY=grey, BUSY=green, DONE=blue, ERROR=error, ABORTED=amber.
/// A theme only sets the chrome (Material seed + brightness). See severityColor /
/// stateColor below — they intentionally ignore the theme.
library;

import 'package:flutter/material.dart';
import 'package:flutter/gestures.dart';
import '../domain/types.dart';

/// Touch-first scrolling on EVERY platform and in EVERY app surface.
///
/// Flutter's desktop default only lets a *touch* device drag-scroll; on Windows
/// and Linux a list otherwise needs a mouse wheel or a scrollbar drag, which a
/// panel with no mouse or keyboard does not have. This enables drag-scroll from
/// every pointer kind, so lists behave the way they do on mobile.
///
/// **Every `MaterialApp` in this app must set `scrollBehavior: kTouchScroll`** —
/// the connection wizard runs in its own `MaterialApp`, separate from the
/// operator shell, and a list there is just as touch-only as one in the shell.
class TouchScrollBehavior extends MaterialScrollBehavior {
  const TouchScrollBehavior();

  @override
  Set<PointerDeviceKind> get dragDevices => const {
        PointerDeviceKind.touch,
        PointerDeviceKind.mouse,
        PointerDeviceKind.stylus,
        PointerDeviceKind.invertedStylus,
        PointerDeviceKind.trackpad,
        PointerDeviceKind.unknown,
      };
}

/// The single shared instance — use this rather than constructing your own.
const kTouchScroll = TouchScrollBehavior();

/// Operator-selectable control size. A panel's pixel density varies enormously
/// (a 1080p 10" desk monitor vs a 1080p 21" cabinet panel), so the same 48 px
/// target is comfortable on one and fiddly on the other — and gloves make it
/// worse. `compact` is the shipped Material baseline (48 px, unchanged); the
/// larger presets follow the common industrial guidance of roughly 15 mm and
/// 19 mm physical targets on a typical panel.
enum ControlScale { compact, medium, large }

/// Resolved dimensions for a [ControlScale]. Anything an operator or technician
/// must press is derived from these — never from a bare pixel literal.
class UiMetrics {
  /// Minimum square tap target (Material's floor is 48).
  final double touchTarget;

  /// Icon glyph size inside a tapped control.
  final double iconSize;

  /// Prominent run/stop glyph in the command rail.
  final double primaryIconSize;

  /// Width of the right-hand command rail.
  final double railWidth;

  /// Height of the top app bar. Must clear [touchTarget] plus breathing room,
  /// or the larger presets clip their own action buttons (Material's default
  /// toolbar is 56, which is already tight for a 48 px target).
  final double appBarHeight;

  /// Height of one navigation-tree row.
  final double treeRowHeight;

  /// Reserved height of the on-screen keyboard (numeric / alpha).
  final double keyboardNumericHeight;
  final double keyboardAlphaHeight;

  /// Multiplier applied to text so labels track the controls they sit in.
  final double textScale;

  const UiMetrics({
    required this.touchTarget,
    required this.iconSize,
    required this.primaryIconSize,
    required this.railWidth,
    required this.appBarHeight,
    required this.treeRowHeight,
    required this.keyboardNumericHeight,
    required this.keyboardAlphaHeight,
    required this.textScale,
  });

  static const _byScale = <ControlScale, UiMetrics>{
    // Baseline — identical to what the HMI shipped before presets existed.
    ControlScale.compact: UiMetrics(
      touchTarget: 48,
      iconSize: 20,
      primaryIconSize: 30,
      railWidth: 72,
      appBarHeight: 64,
      treeRowHeight: 40,
      keyboardNumericHeight: 250,
      keyboardAlphaHeight: 300,
      textScale: 1.0,
    ),
    ControlScale.medium: UiMetrics(
      touchTarget: 62,
      iconSize: 26,
      primaryIconSize: 38,
      railWidth: 92,
      appBarHeight: 84,
      treeRowHeight: 52,
      keyboardNumericHeight: 310,
      keyboardAlphaHeight: 360,
      textScale: 1.10,
    ),
    ControlScale.large: UiMetrics(
      touchTarget: 76,
      iconSize: 32,
      primaryIconSize: 46,
      railWidth: 112,
      appBarHeight: 104,
      treeRowHeight: 64,
      keyboardNumericHeight: 370,
      keyboardAlphaHeight: 430,
      textScale: 1.20,
    ),
  };

  static UiMetrics of(ControlScale scale) => _byScale[scale]!;
}

/// Exposes the active [UiMetrics] to the widget tree, so a control can size
/// itself without every widget having to be handed the AppState.
class ControlScaleScope extends InheritedWidget {
  final UiMetrics metrics;
  const ControlScaleScope({
    super.key,
    required this.metrics,
    required super.child,
  });

  /// Falls back to the compact baseline when no scope is mounted (tests and
  /// any embedded host that renders a widget in isolation).
  static UiMetrics of(BuildContext context) =>
      context
          .dependOnInheritedWidgetOfExactType<ControlScaleScope>()
          ?.metrics ??
      UiMetrics.of(ControlScale.compact);

  @override
  bool updateShouldNotify(ControlScaleScope oldWidget) =>
      metrics != oldWidget.metrics;
}

/// One selectable theme: a localised display-key, a Material seed, a brightness,
/// and (for OLED) a true-black surface override.
class FraktalThemeSpec {
  final String nameKey;
  final Color seed;
  final Brightness brightness;
  final bool trueBlack;

  /// Maximum-contrast variant (WCAG-oriented): Material widens the tonal spread
  /// and we add explicit outlines so controls stay separable on a washed-out
  /// panel or in direct sunlight.
  final bool highContrast;

  const FraktalThemeSpec(this.nameKey, this.seed, this.brightness,
      {this.trueBlack = false, this.highContrast = false});

  ThemeData toThemeData([ControlScale scale = ControlScale.compact]) {
    final scheme = ColorScheme.fromSeed(
      seedColor: seed,
      brightness: brightness,
      contrastLevel: highContrast ? 1.0 : 0.0,
    );
    var theme = ThemeData(useMaterial3: true, colorScheme: scheme);
    if (trueBlack) {
      theme = theme.copyWith(
        scaffoldBackgroundColor: Colors.black,
        canvasColor: Colors.black,
        colorScheme: scheme.copyWith(
          surface: Colors.black,
          surfaceContainerLowest: Colors.black,
          surfaceContainerLow: const Color(0xFF0A0A0A),
          surfaceContainer: const Color(0xFF121212),
        ),
      );
    }
    if (highContrast) {
      // A visible edge on every card/field matters more than the fill colour
      // when the panel is glare-washed.
      theme = theme.copyWith(
        cardTheme: CardThemeData(
          shape: RoundedRectangleBorder(
            side: BorderSide(color: theme.colorScheme.outline),
            borderRadius: BorderRadius.circular(12),
          ),
        ),
        inputDecorationTheme: InputDecorationTheme(
          border: const OutlineInputBorder(),
          enabledBorder: OutlineInputBorder(
            borderSide: BorderSide(color: theme.colorScheme.outline),
          ),
        ),
        dividerTheme: DividerThemeData(color: theme.colorScheme.outline),
      );
    }
    return _applyScale(theme, UiMetrics.of(scale));
  }
}

/// Grows every Material control an operator can press. Done once here rather
/// than at each call site, so a new screen inherits the preset for free.
ThemeData _applyScale(ThemeData theme, UiMetrics m) {
  final target = Size(m.touchTarget, m.touchTarget);
  final hPad = m.touchTarget * 0.34;
  // IMPORTANT: scale text by copying the theme's OWN TextStyle, never by building
  // a bare `TextStyle(fontSize: …)`. A bare style carries no colour, so the label
  // falls back to whatever ambient DefaultTextStyle applies — which on a light
  // surface can resolve to white-on-white. That is exactly how the high-contrast
  // themes lost their Chip and Tab labels.
  TextStyle? scaled(TextStyle? base, double size, {FontWeight? weight}) =>
      (base ?? const TextStyle())
          .copyWith(fontSize: size * m.textScale, fontWeight: weight);
  ButtonStyle buttonStyle() => ButtonStyle(
        minimumSize:
            WidgetStatePropertyAll(Size(m.touchTarget * 1.4, m.touchTarget)),
        padding: WidgetStatePropertyAll(
            EdgeInsets.symmetric(horizontal: hPad, vertical: 0)),
        iconSize: WidgetStatePropertyAll(m.iconSize),
        textStyle: WidgetStatePropertyAll(
            scaled(theme.textTheme.labelLarge, 14, weight: FontWeight.w500)),
      );
  return theme.copyWith(
    // The toolbar has to grow with its own actions, or the larger presets clip
    // the buttons they just enlarged. actionsIconTheme covers the bar's icons;
    // iconButtonTheme below gives them their tap target.
    appBarTheme: AppBarThemeData(
      toolbarHeight: m.appBarHeight,
      actionsIconTheme: IconThemeData(size: m.iconSize),
      iconTheme: IconThemeData(size: m.iconSize),
      titleTextStyle: theme.textTheme.titleLarge
          ?.copyWith(fontSize: 22 * m.textScale)
          .copyWith(color: theme.colorScheme.onSurface),
    ),
    filledButtonTheme: FilledButtonThemeData(style: buttonStyle()),
    elevatedButtonTheme: ElevatedButtonThemeData(style: buttonStyle()),
    outlinedButtonTheme: OutlinedButtonThemeData(style: buttonStyle()),
    textButtonTheme: TextButtonThemeData(style: buttonStyle()),
    iconButtonTheme: IconButtonThemeData(
      style: ButtonStyle(
        minimumSize: WidgetStatePropertyAll(target),
        iconSize: WidgetStatePropertyAll(m.iconSize),
      ),
    ),
    segmentedButtonTheme: SegmentedButtonThemeData(
      style: ButtonStyle(
        // Height alone does not make a segment easier to hit — the Modules /
        // Fieldbus selector is wide-and-short, so the horizontal padding has to
        // grow too, otherwise a larger preset only stretches it vertically.
        minimumSize:
            WidgetStatePropertyAll(Size(m.touchTarget * 1.6, m.touchTarget)),
        // Height comes from visualDensity. SegmentedButton rebuilds each segment
        // through `segmentStyleFor`, which copies a FIXED property list —
        // `minimumSize` is not in it, and the padding is recomputed for any
        // segment carrying an icon. visualDensity IS forwarded, and each unit
        // adds 4 dp, so this is the one lever that actually moves the height.
        visualDensity: VisualDensity(
          horizontal: 0,
          vertical: ((m.touchTarget - 48) / 4).clamp(0.0, 4.0),
        ),
        iconSize: WidgetStatePropertyAll(m.iconSize),
        textStyle:
            WidgetStatePropertyAll(scaled(theme.textTheme.labelLarge, 14)),
      ),
    ),
    chipTheme: ChipThemeData(
      padding: EdgeInsets.symmetric(
          horizontal: 8 * m.textScale, vertical: 6 * m.textScale),
      // A SELECTED chip (FilterChip/ChoiceChip) is filled with
      // secondaryContainer, an UNselected one sits on the surface. Forcing one
      // flat colour for both gave 1.8:1 on high-contrast dark — invisible. Resolve
      // per state so each fill gets its paired `on-` colour.
      labelStyle: WidgetStateTextStyle.resolveWith((states) {
        final base =
            scaled(theme.textTheme.labelLarge, 13) ?? const TextStyle();
        return base.copyWith(
          color: states.contains(WidgetState.selected)
              ? theme.colorScheme.onSecondaryContainer
              : theme.colorScheme.onSurfaceVariant,
        );
      }),
      secondaryLabelStyle: scaled(theme.textTheme.labelLarge, 13)
          ?.copyWith(color: theme.colorScheme.onSecondaryContainer),
    ),
    listTileTheme: ListTileThemeData(
      minVerticalPadding: 6 * m.textScale,
      minTileHeight: m.touchTarget,
    ),
    switchTheme: const SwitchThemeData(),
    tabBarTheme: TabBarThemeData(
      labelStyle:
          scaled(theme.textTheme.titleSmall, 14, weight: FontWeight.w600),
      unselectedLabelStyle: scaled(theme.textTheme.titleSmall, 14),
    ),
  );
}

/// The fourteen themes (indices are the persisted `themeIndex`). Light variants
/// first (0..5), then dark (6..11), then the two maximum-contrast variants
/// (12..13). Light Blue is the default and matches the seed the HMI has always
/// shipped. **Append only** — the index is persisted, so inserting would silently
/// change every stored selection.
const kThemes = <FraktalThemeSpec>[
  // — light —
  FraktalThemeSpec('std.theme.lightBlue', Color(0xFF3D6DEB), Brightness.light),
  FraktalThemeSpec('std.theme.cyan', Color(0xFF0093AB), Brightness.light),
  FraktalThemeSpec('std.theme.teal', Color(0xFF00796B), Brightness.light),
  FraktalThemeSpec('std.theme.indigo', Color(0xFF3F51B5), Brightness.light),
  FraktalThemeSpec('std.theme.slate', Color(0xFF546E7A), Brightness.light),
  FraktalThemeSpec('std.theme.amber', Color(0xFF8A6D00), Brightness.light),
  // — dark —
  FraktalThemeSpec('std.theme.darkBlue', Color(0xFF3D6DEB), Brightness.dark),
  FraktalThemeSpec('std.theme.darkCyan', Color(0xFF0093AB), Brightness.dark),
  FraktalThemeSpec('std.theme.darkTeal', Color(0xFF00796B), Brightness.dark),
  FraktalThemeSpec('std.theme.graphite', Color(0xFF455A64), Brightness.dark),
  FraktalThemeSpec('std.theme.darkSlate', Color(0xFF607D8B), Brightness.dark),
  FraktalThemeSpec('std.theme.oledBlack', Color(0xFF1565C0), Brightness.dark,
      trueBlack: true),
  // — maximum contrast (glare, sunlight, low-vision) —
  FraktalThemeSpec(
      'std.theme.highContrastLight', Color(0xFF00308F), Brightness.light,
      highContrast: true),
  FraktalThemeSpec(
      'std.theme.highContrastDark', Color(0xFF4FC3F7), Brightness.dark,
      trueBlack: true, highContrast: true),
];

/// Localised display keys for the picker (kept for any legacy consumer).
List<String> get kThemeNames => [for (final t in kThemes) t.nameKey];

ThemeData themeAt(int i, [ControlScale scale = ControlScale.compact]) =>
    kThemes[i.clamp(0, kThemes.length - 1)].toThemeData(scale);

/// Fixed severity colours — theme-aware only for HIGH (uses error). MEDIUM/LOW
/// are constants chosen for AA contrast on both light and dark surfaces.
Color severityColor(BuildContext ctx, Severity k) {
  switch (k) {
    case Severity.high:
      return Theme.of(ctx).colorScheme.error;
    case Severity.medium:
      return const Color(0xFFB26A00); // amber-800, AA on light+dark surfaces
    case Severity.low:
      return const Color(0xFF1565C0); // info blue
  }
}

/// Fixed accent for deliberate OPERATOR ACTION surfaces — manual commands,
/// operator decisions, hold-to-run. Blue, never red: red/pink reads as a fault
/// on a machine panel, and these are normal actions, not errors. Held here (not
/// taken from the theme's `tertiary` role) because Material derives tertiary
/// from the seed, which lands pink for several of the twelve themes.
const Color kOperatorActionColor = Color(0xFF1565C0);

/// Tinted container for the same surfaces; alpha keeps it legible on both
/// light and dark themes without a second constant per brightness.
Color operatorActionContainer(BuildContext ctx) =>
    kOperatorActionColor.withValues(
        alpha: Theme.of(ctx).brightness == Brightness.dark ? 0.22 : 0.10);

/// The foreground that belongs with a filled surface.
///
/// **Any widget that paints one of the `*Container` roles must wrap its content
/// in this** (or set the colour itself). `Card` and `Container` only paint a
/// fill — they do not restyle their descendants — so text inside keeps
/// inheriting `onSurface`. That is fine on the normal themes by luck and drops
/// to ~1.8:1 on the high-contrast ones, where the container roles are dark
/// fills. This regressed three separate times: the tree's selected row, the
/// severity filter chips, and the panels below.
/// The colour to draw ON [fill].
///
/// For the scheme's own container roles this returns Material's paired `on-`
/// colour. For any OTHER fill — a fixed status pastel, a tinted state colour —
/// it picks black or white by luminance, because a themed foreground says
/// nothing about a colour the theme did not choose. Without this, fixed pastels
/// under a dark theme's white text measured 1.3:1.
Color foregroundOn(BuildContext context, Color fill) {
  final scheme = Theme.of(context).colorScheme;
  return switch (fill) {
    _ when fill == scheme.primaryContainer => scheme.onPrimaryContainer,
    _ when fill == scheme.secondaryContainer => scheme.onSecondaryContainer,
    _ when fill == scheme.tertiaryContainer => scheme.onTertiaryContainer,
    _ when fill == scheme.errorContainer => scheme.onErrorContainer,
    _ when fill == scheme.surface => scheme.onSurface,
    // Unknown fill: choose the higher-contrast of black/white against it.
    _ => fill.computeLuminance() > 0.4 ? Colors.black : Colors.white,
  };
}

Widget onContainer(BuildContext context, Color container, Widget child) {
  final foreground = foregroundOn(context, container);
  return DefaultTextStyle.merge(
    style: TextStyle(color: foreground),
    child: IconTheme.merge(
      data: IconThemeData(color: foreground),
      child: child,
    ),
  );
}

Color stateColor(BuildContext ctx, ExecState s) {
  switch (s) {
    case ExecState.ready:
      return Colors.grey;
    case ExecState.busy:
      return const Color(0xFF2E7D32);
    case ExecState.done:
      return const Color(0xFF1565C0);
    case ExecState.error:
      return Theme.of(ctx).colorScheme.error;
    case ExecState.aborted:
      return const Color(0xFFB26A00);
  }
}
