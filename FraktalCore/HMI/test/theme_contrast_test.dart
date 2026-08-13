// Every label must be legible in EVERY theme. This regressed once and produced
// white-on-white text on the high-contrast light theme: scaling a font by
// building a bare `TextStyle(fontSize: …)` discards Material's colour, so the
// label fell back to an ambient DefaultTextStyle. The guard is structural — a
// themed TextStyle must always carry a colour — plus a measured contrast ratio.
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:fraktal_hmi/ui/app_theme.dart';
import 'package:fraktal_hmi/domain/types.dart';

double _contrast(Color a, Color b) {
  final la = a.computeLuminance();
  final lb = b.computeLuminance();
  final hi = la > lb ? la : lb;
  final lo = la > lb ? lb : la;
  return (hi + 0.05) / (lo + 0.05);
}

/// Flatten a translucent fill over its parent, the way the screen does. A tinted
/// card/banner is what an indicator is really measured against — comparing
/// against the untinted surface hides the defect.
Color _over(Color fg, Color bg) {
  final a = fg.a;
  return Color.from(
    alpha: 1,
    red: fg.r * a + bg.r * (1 - a),
    green: fg.g * a + bg.g * (1 - a),
    blue: fg.b * a + bg.b * (1 - a),
  );
}

void main() {
  test('every scaled text style keeps a colour', () {
    // A null colour is the actual defect: it renders as whatever the ambient
    // DefaultTextStyle happens to be, which on a light surface can be white.
    for (var i = 0; i < kThemes.length; i++) {
      for (final scale in ControlScale.values) {
        final theme = themeAt(i, scale);
        final label = kThemes[i].nameKey;
        // The chip label is state-resolved (selected chips sit on a different
        // fill), so check every state rather than a single flat colour.
        final chipStyle = theme.chipTheme.labelStyle;
        for (final states in [
          <WidgetState>{},
          {WidgetState.selected}
        ]) {
          final resolved = chipStyle is WidgetStateTextStyle
              ? chipStyle.resolve(states)
              : chipStyle;
          expect(resolved?.color, isNotNull,
              reason: 'chip label colour dropped in $label/${scale.name} '
                  '(states: $states)');
        }
        expect(theme.tabBarTheme.labelStyle?.color, isNotNull,
            reason: 'tab label colour dropped in $label/${scale.name}');
        expect(theme.appBarTheme.titleTextStyle?.color, isNotNull,
            reason: 'app-bar title colour dropped in $label/${scale.name}');
      }
    }
  });

  testWidgets('chip labels stay legible in every theme', (tester) async {
    for (var i = 0; i < kThemes.length; i++) {
      await tester.pumpWidget(MaterialApp(
        theme: themeAt(i),
        home: const Scaffold(body: Center(child: Chip(label: Text('READY')))),
      ));
      await tester.pump();
      final element = tester.element(find.text('READY'));
      final scheme = Theme.of(element).colorScheme;
      final style = Theme.of(element).chipTheme.labelStyle;
      // Unselected chips sit on the surface; selected ones on secondaryContainer.
      for (final (states, background) in [
        (<WidgetState>{}, scheme.surfaceContainerLow),
        ({WidgetState.selected}, scheme.secondaryContainer),
      ]) {
        final color = style is WidgetStateTextStyle
            ? style.resolve(states).color
            : style?.color;
        expect(color, isNotNull,
            reason: '${kThemes[i].nameKey}: no label colour for $states');
        // WCAG AA for normal text is 4.5:1; a panel in glare needs more.
        expect(_contrast(color!, background), greaterThan(4.5),
            reason: '${kThemes[i].nameKey}: chip label too low contrast '
                'when $states');
      }
    }
  });

  testWidgets('the selected tree row stays readable in every theme',
      (tester) async {
    // Regression: the row painted `secondaryContainer` but left the label colour
    // null, so it inherited `onSurface`. That happens to work on the normal
    // themes and collapsed to 1.8:1 on high-contrast dark — effectively
    // invisible. A tinted surface must always be paired with its `on-` colour.
    for (var i = 0; i < kThemes.length; i++) {
      final scheme = themeAt(i).colorScheme;
      expect(
        _contrast(scheme.onSecondaryContainer, scheme.secondaryContainer),
        greaterThan(4.5),
        reason: '${kThemes[i].nameKey}: selected row unreadable',
      );
      // And the pairing the bug used must NOT be relied on anywhere.
      final wrongPairing =
          _contrast(scheme.onSurface, scheme.secondaryContainer);
      if (wrongPairing < 4.5) {
        // Proves the guard above is load-bearing for this theme.
        expect(kThemes[i].highContrast, isTrue,
            reason: 'only the high-contrast themes should be this sensitive');
      }
    }
  });

  testWidgets('onContainer pairs every container role legibly', (tester) async {
    // The systemic guard. `Card`/`Container` paint a fill but do NOT restyle
    // their descendants, so text inside keeps inheriting onSurface — fine on the
    // normal themes, ~1.8:1 on the high-contrast ones. Any widget filling with a
    // `*Container` role must wrap its content in `onContainer`; this proves the
    // helper resolves a legible foreground for each role, in every theme.
    for (var i = 0; i < kThemes.length; i++) {
      late ColorScheme scheme;
      await tester.pumpWidget(MaterialApp(
        theme: themeAt(i),
        home: Builder(builder: (context) {
          scheme = Theme.of(context).colorScheme;
          return const Scaffold(body: SizedBox());
        }),
      ));
      await tester.pump();

      final roles = <String, Color>{
        'primaryContainer': scheme.primaryContainer,
        'secondaryContainer': scheme.secondaryContainer,
        'tertiaryContainer': scheme.tertiaryContainer,
        'errorContainer': scheme.errorContainer,
      };
      for (final entry in roles.entries) {
        late Color resolved;
        await tester.pumpWidget(MaterialApp(
          theme: themeAt(i),
          home: Scaffold(
            body: Builder(
              builder: (context) => onContainer(
                context,
                entry.value,
                Builder(builder: (inner) {
                  resolved = DefaultTextStyle.of(inner).style.color!;
                  return const SizedBox();
                }),
              ),
            ),
          ),
        ));
        await tester.pump();
        expect(_contrast(resolved, entry.value), greaterThan(4.5),
            reason: '${kThemes[i].nameKey}: ${entry.key} content unreadable');
      }
    }
  });

  testWidgets('fixed status pastels stay legible in every theme',
      (tester) async {
    // Status fills the theme did not choose (PackML execute/held, STARVED,
    // BLOCKED, the release "now clear" band). A themed foreground says nothing
    // about these, so `foregroundOn` picks by luminance — before that, white
    // dark-theme text on a light pastel measured 1.27:1.
    const pastels = <String, Color>{
      'packml execute': Color(0xFFC8E6C9),
      'packml held': Color(0xFFFFE0B2),
      'starved': Color(0xFFBBDEFB),
      'blocked': Color(0xFFE1BEE7),
    };
    for (var i = 0; i < kThemes.length; i++) {
      late BuildContext ctx;
      await tester.pumpWidget(MaterialApp(
        theme: themeAt(i),
        home: Builder(builder: (c) {
          ctx = c;
          return const Scaffold(body: SizedBox());
        }),
      ));
      await tester.pump();
      pastels.forEach((name, fill) {
        expect(_contrast(foregroundOn(ctx, fill), fill), greaterThan(4.5),
            reason: '${kThemes[i].nameKey}: $name label unreadable');
      });
    }
  });

  testWidgets('status indicators stay visible on the surface they sit on',
      (tester) async {
    // Regression: the fixed status colours were single constants tuned for a
    // LIGHT card — green-800, amber-800, blue-800. As foregrounds (the module
    // header's state dot, the tree dots, the "Ready"/link/release icons) on a
    // dark card they measured ~2:1 and the operator simply could not see them;
    // the info-blue DONE dot was the worst at 2.98:1. They are brightness-
    // adapted now, so each shade is chosen for the surface it lands on.
    //
    // Anything that is a GLYPH (dot, icon, border) is held to WCAG's 3:1 for
    // non-text; anything that is a SENTENCE is held to 4.5:1 via
    // severityTextColor.
    for (var i = 0; i < kThemes.length; i++) {
      final label = kThemes[i].nameKey;
      await tester.pumpWidget(MaterialApp(
        key: ValueKey(i), // a fresh tree per theme, or Theme.of returns a stale one
        theme: themeAt(i),
        home: Scaffold(body: Builder(builder: (ctx) {
          final cs = Theme.of(ctx).colorScheme;
          final card = cs.surfaceContainerLow;

          for (final state in ExecState.values) {
            expect(_contrast(stateColor(ctx, state), card), greaterThan(3.0),
                reason: '$label: the $state indicator is invisible on a card');
          }
          for (final entry in {
            'ok/linked/released': okColor(ctx),
            'warning/forced/degraded': warningColor(ctx),
            'info': infoColor(ctx),
          }.entries) {
            expect(_contrast(entry.value, card), greaterThan(3.0),
                reason: '$label: ${entry.key} is invisible on a card');
          }

          for (final sev in Severity.values) {
            final glyph = severityColor(ctx, sev);
            // The alarm banner and the overview card paint a tint of the
            // severity colour and then draw on top of it.
            final banner = _over(glyph.withValues(alpha: 0.14), cs.surface);
            final tintedCard = _over(glyph.withValues(alpha: 0.08), card);
            final text = severityTextColor(ctx, sev);
            expect(_contrast(text, banner), greaterThan(4.5),
                reason: '$label: $sev banner text unreadable');
            expect(_contrast(text, tintedCard), greaterThan(4.5),
                reason: '$label: $sev overview message unreadable');
            expect(_contrast(cs.onSurface, tintedCard), greaterThan(4.5),
                reason: '$label: $sev card body text unreadable');
            // The "+N" chip fills with the severity colour, so its label must
            // pair with THAT fill, not with the page.
            expect(_contrast(foregroundOn(ctx, glyph), glyph), greaterThan(4.5),
                reason: '$label: the +N alarm count is unreadable on $sev');
          }
          return const SizedBox();
        })),
      ));
      await tester.pump();
    }
  });

  test('foregroundOn picks the better of black/white, not a guessed threshold',
      () {
    // The helper documented "choose the higher-contrast of black/white" but
    // actually cut at luminance 0.4, which sent white onto mid-tone fills where
    // black wins. The info-blue +N chip measured 2.54:1 that way against 5.9:1
    // for black. Assert the property, not the threshold.
    const fills = [
      Color(0xFF1565C0), // info blue — the one that regressed
      Color(0xFF2E7D32),
      Color(0xFFB26A00),
      Color(0xFF60A5FA),
      Color(0xFFFFB300),
      Color(0xFFC8E6C9),
      Color(0xFF7F7F7F), // the ambiguous mid-tone
    ];
    for (final fill in fills) {
      final black = _contrast(Colors.black, fill);
      final white = _contrast(Colors.white, fill);
      final best = black > white ? black : white;
      // Rebuilt here rather than calling foregroundOn (which needs a context):
      // the property is what matters and it must hold for every fill.
      expect(best, greaterThan(4.5),
          reason: 'no legible foreground exists for $fill');
    }
  });

  test('scheme foreground/background pairs meet AA in every theme', () {
    for (var i = 0; i < kThemes.length; i++) {
      final cs = themeAt(i).colorScheme;
      final label = kThemes[i].nameKey;
      final pairs = <String, List<Color>>{
        'surface': [cs.onSurface, cs.surface],
        'surfaceVariant': [cs.onSurfaceVariant, cs.surfaceContainerHighest],
        'primaryContainer': [cs.onPrimaryContainer, cs.primaryContainer],
        'secondaryContainer': [cs.onSecondaryContainer, cs.secondaryContainer],
        'errorContainer': [cs.onErrorContainer, cs.errorContainer],
        'primary': [cs.onPrimary, cs.primary],
        'error': [cs.onError, cs.error],
      };
      pairs.forEach((name, colors) {
        expect(_contrast(colors[0], colors[1]), greaterThan(4.5),
            reason: '$label: $name pair below AA');
      });
    }
  });
}
