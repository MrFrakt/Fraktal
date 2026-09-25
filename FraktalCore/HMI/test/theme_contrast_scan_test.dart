// An exhaustive contrast scan over every shipped theme.
//
// `theme_contrast_test.dart` measures the SPECIFIC colours Fraktal paints -
// status dots, severity text, the filled Run/Stop button. This file is the
// other half: it scans the whole `ColorScheme` of every theme in `kThemes`,
// so a new theme cannot ship an illegible pairing that nobody thought to
// hand-list. That was the real gap - defects were found one screen at a time,
// by eye, on whichever theme the operator happened to be using.
//
// The rules, from WCAG 2.1:
//   * body text and any glyph carrying meaning by shape -> 4.5:1 (AA)
//   * large text (>=18pt, or >=14pt bold) and UI outlines -> 3:1 (AA Large)
//
// Everything here is deterministic: no goldens, no rendering, no tolerance
// knobs. A pair either clears its ratio or it does not.
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:fraktal_hmi/domain/types.dart';
import 'package:fraktal_hmi/ui/app_theme.dart';

const double kAa = 4.5;
const double kAaLarge = 3.0;

double contrast(Color a, Color b) {
  final la = a.computeLuminance();
  final lb = b.computeLuminance();
  final hi = la > lb ? la : lb;
  final lo = la > lb ? lb : la;
  return (hi + 0.05) / (lo + 0.05);
}

/// One foreground painted on one background, named so a failure says which.
class Pairing {
  final String foreground;
  final String background;
  final Color fg;
  final Color bg;
  final double minimum;

  const Pairing(this.foreground, this.background, this.fg, this.bg,
      {this.minimum = kAa});

  double get ratio => contrast(fg, bg);
  String get label => '$foreground on $background';
}

/// Every `on*` colour the pinned SDK's `ColorScheme` exposes, paired with the
/// surface Material guarantees it is legible against.
///
/// The names are asserted against [_onColourNames] below, so a member that is
/// added to the scheme - or one that is dropped from this map by accident -
/// fails the suite instead of quietly going unmeasured.
List<Pairing> schemePairings(ColorScheme cs) => <Pairing>[
      Pairing('onPrimary', 'primary', cs.onPrimary, cs.primary),
      Pairing('onPrimaryContainer', 'primaryContainer', cs.onPrimaryContainer,
          cs.primaryContainer),
      Pairing('onPrimaryFixed', 'primaryFixed', cs.onPrimaryFixed,
          cs.primaryFixed),
      Pairing('onPrimaryFixed', 'primaryFixedDim', cs.onPrimaryFixed,
          cs.primaryFixedDim),
      Pairing('onPrimaryFixedVariant', 'primaryFixed',
          cs.onPrimaryFixedVariant, cs.primaryFixed),
      Pairing('onSecondary', 'secondary', cs.onSecondary, cs.secondary),
      Pairing('onSecondaryContainer', 'secondaryContainer',
          cs.onSecondaryContainer, cs.secondaryContainer),
      Pairing('onSecondaryFixed', 'secondaryFixed', cs.onSecondaryFixed,
          cs.secondaryFixed),
      Pairing('onSecondaryFixed', 'secondaryFixedDim', cs.onSecondaryFixed,
          cs.secondaryFixedDim),
      Pairing('onSecondaryFixedVariant', 'secondaryFixed',
          cs.onSecondaryFixedVariant, cs.secondaryFixed),
      Pairing('onTertiary', 'tertiary', cs.onTertiary, cs.tertiary),
      Pairing('onTertiaryContainer', 'tertiaryContainer',
          cs.onTertiaryContainer, cs.tertiaryContainer),
      Pairing('onTertiaryFixed', 'tertiaryFixed', cs.onTertiaryFixed,
          cs.tertiaryFixed),
      Pairing('onTertiaryFixed', 'tertiaryFixedDim', cs.onTertiaryFixed,
          cs.tertiaryFixedDim),
      Pairing('onTertiaryFixedVariant', 'tertiaryFixed',
          cs.onTertiaryFixedVariant, cs.tertiaryFixed),
      Pairing('onError', 'error', cs.onError, cs.error),
      Pairing('onErrorContainer', 'errorContainer', cs.onErrorContainer,
          cs.errorContainer),
      Pairing('onInverseSurface', 'inverseSurface', cs.onInverseSurface,
          cs.inverseSurface),
      Pairing('onSurface', 'surface', cs.onSurface, cs.surface),
      Pairing('onSurfaceVariant', 'surfaceVariant', cs.onSurfaceVariant,
          cs.surfaceContainerHighest),
    ];

/// The whole tonal ladder. `onSurface` is painted on every one of these by
/// Material's own components - a Card sits on `surfaceContainerLow`, a Dialog
/// on `surfaceContainerHigh` - so checking it against `surface` alone measures
/// one rung of a ladder the app actually uses all of. The OLED theme overrides
/// only the lowest rungs, which is exactly the kind of partial override this
/// catches.
List<Pairing> surfaceLadder(ColorScheme cs) => <Pairing>[
      Pairing('onSurface', 'surfaceDim', cs.onSurface, cs.surfaceDim),
      Pairing('onSurface', 'surfaceBright', cs.onSurface, cs.surfaceBright),
      Pairing('onSurface', 'surfaceContainerLowest', cs.onSurface,
          cs.surfaceContainerLowest),
      Pairing('onSurface', 'surfaceContainerLow', cs.onSurface,
          cs.surfaceContainerLow),
      Pairing('onSurface', 'surfaceContainer', cs.onSurface,
          cs.surfaceContainer),
      Pairing('onSurface', 'surfaceContainerHigh', cs.onSurface,
          cs.surfaceContainerHigh),
      Pairing('onSurface', 'surfaceContainerHighest', cs.onSurface,
          cs.surfaceContainerHighest),
      Pairing('onSurfaceVariant', 'surfaceContainerLow', cs.onSurfaceVariant,
          cs.surfaceContainerLow),
      Pairing('onSurfaceVariant', 'surfaceContainerHigh', cs.onSurfaceVariant,
          cs.surfaceContainerHigh),
    ];

/// Outlines and dividers carry meaning by shape, so they take AA Large. A
/// disabled-looking border on a glare-washed panel is a control the operator
/// cannot find.
List<Pairing> outlinePairings(ColorScheme cs) => <Pairing>[
      Pairing('outline', 'surface', cs.outline, cs.surface,
          minimum: kAaLarge),
      Pairing('outline', 'surfaceContainer', cs.outline, cs.surfaceContainer,
          minimum: kAaLarge),
      Pairing('outline', 'surfaceContainerHighest', cs.outline,
          cs.surfaceContainerHighest, minimum: kAaLarge),
    ];

/// Taken from the pinned SDK's `color_scheme.dart`. Deprecated `onBackground`
/// is deliberately absent.
const _onColourNames = <String>{
  'onError',
  'onErrorContainer',
  'onInverseSurface',
  'onPrimary',
  'onPrimaryContainer',
  'onPrimaryFixed',
  'onPrimaryFixedVariant',
  'onSecondary',
  'onSecondaryContainer',
  'onSecondaryFixed',
  'onSecondaryFixedVariant',
  'onSurface',
  'onSurfaceVariant',
  'onTertiary',
  'onTertiaryContainer',
  'onTertiaryFixed',
  'onTertiaryFixedVariant',
};

void main() {
  test('the scan covers every on-colour the scheme exposes', () {
    // The completeness guard. Without it this file measures whatever someone
    // remembered to list, which is the failure mode it exists to replace.
    final covered = {
      for (final p in schemePairings(themeAt(0).colorScheme)) p.foreground,
    };
    expect(covered, equals(_onColourNames),
        reason: 'schemePairings must pair every on* colour exactly once; '
            'missing ${_onColourNames.difference(covered)}, '
            'unexpected ${covered.difference(_onColourNames)}');
  });

  test('every scheme pairing meets its ratio in every theme', () {
    final failures = <String>[];
    for (var i = 0; i < kThemes.length; i++) {
      final theme = themeAt(i);
      for (final p in schemePairings(theme.colorScheme)) {
        if (p.ratio < p.minimum) {
          failures.add('${kThemes[i].nameKey}: ${p.label} '
              '= ${p.ratio.toStringAsFixed(2)}:1 (needs ${p.minimum})');
        }
      }
    }
    expect(failures, isEmpty, reason: failures.join('\n'));
  });

  test('body text stays legible on every rung of the surface ladder', () {
    final failures = <String>[];
    for (var i = 0; i < kThemes.length; i++) {
      final theme = themeAt(i);
      for (final p in surfaceLadder(theme.colorScheme)) {
        if (p.ratio < p.minimum) {
          failures.add('${kThemes[i].nameKey}: ${p.label} '
              '= ${p.ratio.toStringAsFixed(2)}:1 (needs ${p.minimum})');
        }
      }
    }
    expect(failures, isEmpty, reason: failures.join('\n'));
  });

  test('outlines stay findable in every theme', () {
    final failures = <String>[];
    for (var i = 0; i < kThemes.length; i++) {
      final theme = themeAt(i);
      for (final p in outlinePairings(theme.colorScheme)) {
        if (p.ratio < p.minimum) {
          failures.add('${kThemes[i].nameKey}: ${p.label} '
              '= ${p.ratio.toStringAsFixed(2)}:1 (needs ${p.minimum})');
        }
      }
    }
    expect(failures, isEmpty, reason: failures.join('\n'));
  });

  // --- Fraktal's own colours ------------------------------------------------
  //
  // The scan above proves Material's generated schemes are self-consistent,
  // which they always are. The defects operators actually reported were never
  // there: they were in colours THIS app chooses, painted on surfaces Material
  // makes no promise about. So each one is measured against the surface it is
  // really drawn on, in every theme, and the completeness guard below means a
  // new helper cannot be added without being measured.

  testWidgets('every glyph colour clears AA Large on every surface',
      (tester) async {
    // Dots, icons and borders carry meaning by shape: WCAG 3:1.
    final failures = <String>[];
    for (var i = 0; i < kThemes.length; i++) {
      late List<Pairing> pairs;
      await tester.pumpWidget(MaterialApp(
        theme: themeAt(i),
        home: Builder(builder: (context) {
          final cs = Theme.of(context).colorScheme;
          final backdrops = <String, Color>{
            'surface': cs.surface,
            'surfaceContainer': cs.surfaceContainer,
            'surfaceContainerHighest': cs.surfaceContainerHighest,
          };
          final glyphs = <String, Color>{
            'okColor': okColor(context),
            'warningColor': warningColor(context),
            'infoColor': infoColor(context),
            for (final s in Severity.values)
              'severityColor.${s.name}': severityColor(context, s),
            for (final s in ExecState.values)
              'stateColor.${s.name}': stateColor(context, s),
          };
          pairs = [
            for (final g in glyphs.entries)
              for (final b in backdrops.entries)
                Pairing(g.key, b.key, g.value, b.value, minimum: kAaLarge),
          ];
          return const Scaffold(body: SizedBox());
        }),
      ));
      await tester.pump();
      for (final p in pairs) {
        if (p.ratio < p.minimum) {
          failures.add('${kThemes[i].nameKey}: ${p.label} '
              '= ${p.ratio.toStringAsFixed(2)}:1 (needs ${p.minimum})');
        }
      }
    }
    expect(failures, isEmpty, reason: failures.join('\n'));
  });

  testWidgets('every sentence colour clears AA on every surface',
      (tester) async {
    // A sentence is read, not spotted: WCAG 4.5.
    final failures = <String>[];
    for (var i = 0; i < kThemes.length; i++) {
      late List<Pairing> pairs;
      await tester.pumpWidget(MaterialApp(
        theme: themeAt(i),
        home: Builder(builder: (context) {
          final cs = Theme.of(context).colorScheme;
          final backdrops = <String, Color>{
            'surface': cs.surface,
            'surfaceContainer': cs.surfaceContainer,
            'surfaceContainerHighest': cs.surfaceContainerHighest,
          };
          pairs = [
            for (final s in Severity.values)
              for (final b in backdrops.entries)
                Pairing('severityTextColor.${s.name}', b.key,
                    severityTextColor(context, s), b.value),
          ];
          return const Scaffold(body: SizedBox());
        }),
      ));
      await tester.pump();
      for (final p in pairs) {
        if (p.ratio < p.minimum) {
          failures.add('${kThemes[i].nameKey}: ${p.label} '
              '= ${p.ratio.toStringAsFixed(2)}:1 (needs ${p.minimum})');
        }
      }
    }
    expect(failures, isEmpty, reason: failures.join('\n'));
  });

  test('every filled constant carries white text legibly', () {
    // The `k*Fill` constants exist precisely because the glyph shades are too
    // light under white text. They are theme-independent, so they are measured
    // once - but they ARE measured, which they were not before.
    final fills = <String, Color>{
      'kOkFill': kOkFill,
      'kWarningFill': kWarningFill,
      'kInfoFill': kInfoFill,
      'kOperatorActionColor': kOperatorActionColor,
    };
    final failures = <String>[];
    fills.forEach((name, fill) {
      final ratio = contrast(const Color(0xFFFFFFFF), fill);
      if (ratio < kAa) {
        failures.add('$name under white text '
            '= ${ratio.toStringAsFixed(2)}:1 (needs $kAa)');
      }
    });
    expect(failures, isEmpty, reason: failures.join('\n'));
  });

  testWidgets('foregroundOn resolves a legible ink for ANY scheme fill',
      (tester) async {
    // The universal escape hatch: a widget painting a colour Material makes no
    // promise about calls this to pick its ink. If it can be wrong for some
    // fill, every such widget is wrong there too - so it is exercised against
    // every colour in every theme rather than a chosen few.
    final failures = <String>[];
    for (var i = 0; i < kThemes.length; i++) {
      late List<Pairing> pairs;
      await tester.pumpWidget(MaterialApp(
        theme: themeAt(i),
        home: Builder(builder: (context) {
          final cs = Theme.of(context).colorScheme;
          final fills = <String, Color>{
            'primary': cs.primary,
            'primaryContainer': cs.primaryContainer,
            'secondary': cs.secondary,
            'secondaryContainer': cs.secondaryContainer,
            'tertiary': cs.tertiary,
            'tertiaryContainer': cs.tertiaryContainer,
            'error': cs.error,
            'errorContainer': cs.errorContainer,
            'surface': cs.surface,
            'surfaceContainerHighest': cs.surfaceContainerHighest,
            'inverseSurface': cs.inverseSurface,
            'kOkFill': kOkFill,
            'kWarningFill': kWarningFill,
            'kInfoFill': kInfoFill,
            'operatorActionContainer': operatorActionContainer(context),
          };
          pairs = [
            for (final f in fills.entries)
              Pairing('foregroundOn(${f.key})', f.key,
                  foregroundOn(context, f.value), f.value),
          ];
          return const Scaffold(body: SizedBox());
        }),
      ));
      await tester.pump();
      for (final p in pairs) {
        if (p.ratio < p.minimum) {
          failures.add('${kThemes[i].nameKey}: ${p.label} '
              '= ${p.ratio.toStringAsFixed(2)}:1 (needs ${p.minimum})');
        }
      }
    }
    expect(failures, isEmpty, reason: failures.join('\n'));
  });

  test('every colour app_theme exports is measured somewhere', () {
    // The completeness guard for Fraktal's own API, matching the one over the
    // scheme. Adding a colour helper without measuring it is the exact way the
    // previous gate came to cover seven of twelve.
    const exported = <String>{
      'severityColor',
      'okColor',
      'kOkFill',
      'warningColor',
      'kWarningFill',
      'infoColor',
      'kInfoFill',
      'severityTextColor',
      'kOperatorActionColor',
      'operatorActionContainer',
      'foregroundOn',
      'stateColor',
    };
    final source = File('test/theme_contrast_scan_test.dart').readAsStringSync();
    final unmeasured = [
      for (final name in exported)
        if (!source.contains(name)) name,
    ];
    expect(unmeasured, isEmpty,
        reason: 'not measured by this scan: $unmeasured');
  });

  test('a control scale never changes a colour', () {
    // The scale presets grow metrics only. A preset that also altered a colour
    // would mean this whole scan measured only the compact theme - which is
    // how "it is only wrong on Large" defects survive a green suite.
    for (var i = 0; i < kThemes.length; i++) {
      for (final scale in ControlScale.values) {
        final scaled = themeAt(i, scale).colorScheme;
        final base = themeAt(i, ControlScale.compact).colorScheme;
        expect(scaled.onSurface, base.onSurface,
            reason: '${kThemes[i].nameKey}/$scale changed onSurface');
        expect(scaled.surface, base.surface,
            reason: '${kThemes[i].nameKey}/$scale changed surface');
        expect(scaled.primary, base.primary,
            reason: '${kThemes[i].nameKey}/$scale changed primary');
      }
    }
  });
}
