// Every label must be legible in EVERY theme. This regressed once and produced
// white-on-white text on the high-contrast light theme: scaling a font by
// building a bare `TextStyle(fontSize: …)` discards Material's colour, so the
// label fell back to an ambient DefaultTextStyle. The guard is structural — a
// themed TextStyle must always carry a colour — plus a measured contrast ratio.
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:fraktal_hmi/ui/app_theme.dart';

double _contrast(Color a, Color b) {
  final la = a.computeLuminance();
  final lb = b.computeLuminance();
  final hi = la > lb ? la : lb;
  final lo = la > lb ? lb : la;
  return (hi + 0.05) / (lo + 0.05);
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
