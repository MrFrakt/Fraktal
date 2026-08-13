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
        // A SELECTED segment is filled with secondaryContainer, an UNselected
        // one sits on the surface — exactly the split the chipTheme below
        // already resolves per state. A flat WidgetStatePropertyAll gave both
        // the SAME colour, which is invisible wherever the two fills differ in
        // lightness: on high-contrast LIGHT, Material widens the tonal spread
        // until secondaryContainer inverts to a DARK fill (44485c) while the
        // label stayed near-black — 1.05:1, the "Modules/Fieldbus" selector
        // simply disappeared. Resolve per state so each fill gets its `on-`.
        textStyle: WidgetStateTextStyle.resolveWith((states) {
          final base =
              scaled(theme.textTheme.labelLarge, 14) ?? const TextStyle();
          return base.copyWith(
            color: states.contains(WidgetState.selected)
                ? theme.colorScheme.onSecondaryContainer
                : theme.colorScheme.onSurface,
          );
        }),
        // The glyph beside that label needs the same pairing — iconColor is a
        // separate property and does not follow textStyle.
        iconColor: WidgetStateProperty.resolveWith((states) =>
            states.contains(WidgetState.selected)
                ? theme.colorScheme.onSecondaryContainer
                : theme.colorScheme.onSurface),
        foregroundColor: WidgetStateProperty.resolveWith((states) =>
            states.contains(WidgetState.selected)
                ? theme.colorScheme.onSecondaryContainer
                : theme.colorScheme.onSurface),
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
/// are the [warningColor]/[infoColor] semantics, brightness-adapted so an amber
/// or blue icon stays AA on a dark card (the single-shade constants measured
/// ~2-3:1 there).
Color severityColor(BuildContext ctx, Severity k) {
  switch (k) {
    case Severity.high:
      return Theme.of(ctx).colorScheme.error;
    case Severity.medium:
      return warningColor(ctx);
    case Severity.low:
      return infoColor(ctx);
  }
}

/// Fixed semantic GREEN: success / clear / linked / BUSY·DONE-ok. Same hue in
/// every theme; the SHADE adapts to brightness. The light shade (green-800) is
/// the only one that pairs AA with white text on a fill, so it is the fill
/// colour too — but as a FOREGROUND (icon, dot, border) on a dark card it
/// measured ~2:1 and the indicator vanished. Use this for foregrounds; use
/// [kOkFill] (or the constant) for a fill that carries white text.
Color okColor(BuildContext ctx) =>
    Theme.of(ctx).brightness == Brightness.dark
        ? const Color(0xFF66BB6A) // green-400: ~7:1 on a dark card
        : const Color(0xFF2E7D32); // green-800: AA on light + with white text

/// A fill in the success hue that keeps white text legible. Always the dark
/// shade: a light green fill under white text is ~1.7:1.
const Color kOkFill = Color(0xFF2E7D32);

/// Fixed semantic AMBER: warning / held / degraded / MEDIUM. Brightness-adapted
/// for foreground use; [kWarningFill] for white-on-fill.
Color warningColor(BuildContext ctx) =>
    Theme.of(ctx).brightness == Brightness.dark
        ? const Color(0xFFFFB300) // amber-600: ~10:1 on a dark card
        : const Color(0xFFB26A00); // amber-800
const Color kWarningFill = Color(0xFFB26A00);

/// Fixed semantic BLUE: info / LOW / DONE. Brightness-adapted for foreground.
Color infoColor(BuildContext ctx) =>
    Theme.of(ctx).brightness == Brightness.dark
        ? const Color(0xFF60A5FA) // blue-400: ~7:1 on a dark card
        : const Color(0xFF1565C0); // blue-800
const Color kInfoFill = Color(0xFF1565C0);

/// A severity colour safe for BODY TEXT, not just an icon or a dot.
///
/// [severityColor] is tuned for glyphs, which WCAG lets sit at 3:1. The same
/// amber used as a sentence on a tinted banner measured 3.4:1 — legible-ish in
/// an office, marginal on a glare-washed panel. Text callers use this instead:
/// it darkens/lightens only the shades that need it, so the hue stays the
/// fixed §8.1 semantic and nothing else about the palette changes.
Color severityTextColor(BuildContext ctx, Severity k) {
  final dark = Theme.of(ctx).brightness == Brightness.dark;
  switch (k) {
    case Severity.high:
      return Theme.of(ctx).colorScheme.error;
    case Severity.medium:
      // amber-900 on light (4.9:1 on the 8% tint); the light shade already
      // clears 4.5:1 on dark surfaces.
      return dark ? const Color(0xFFFFB300) : const Color(0xFF8A5200);
    case Severity.low:
      return dark ? const Color(0xFF60A5FA) : const Color(0xFF0D4C94);
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
    // Unknown fill: actually COMPUTE which of black/white wins, rather than
    // guessing from a luminance threshold. A fixed 0.4 cut sent white onto
    // mid-tone fills where black is the better pairing — the info-blue `+N`
    // alarm chip measured 2.54:1 that way, while black on the same fill is
    // 5.9:1. WCAG's own crossover is ~0.179, but deriving it is cheap and
    // cannot drift.
    _ => _betterOf(Colors.black, Colors.white, fill),
  };
}

/// Whichever of [a]/[b] contrasts more strongly with [on].
Color _betterOf(Color a, Color b, Color on) =>
    _contrastRatio(a, on) >= _contrastRatio(b, on) ? a : b;

double _contrastRatio(Color a, Color b) {
  final la = a.computeLuminance(), lb = b.computeLuminance();
  final hi = la > lb ? la : lb, lo = la > lb ? lb : la;
  return (hi + 0.05) / (lo + 0.05);
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
      return Theme.of(ctx).colorScheme.onSurfaceVariant;
    case ExecState.busy:
      return okColor(ctx);
    case ExecState.done:
      return infoColor(ctx);
    case ExecState.error:
      return Theme.of(ctx).colorScheme.error;
    case ExecState.aborted:
      return warningColor(ctx);
  }
}
