// Whole-app contrast gate: boot the REAL shell in EVERY theme and check every
// glyph the app actually paints against the fill it actually lands on.
//
// This exists because the palette-level checks in theme_contrast_test.dart pass
// a colour that is still invisible on screen. They verify a pairing in the
// abstract; they cannot see a widget that paints one of those fills and then
// forgets to pair its foreground with it. Three real defects were invisible to
// them and obvious here:
//
//   * the Modules/Fieldbus selector — one flat label colour for both segment
//     states, while the SELECTED segment is filled with secondaryContainer,
//     which inverts to a DARK fill on the high-contrast themes (1.05:1);
//   * the tree's expand chevron on a selected row, inheriting onSurface while
//     the row is secondaryContainer (2.33:1 light, 1.77:1 HC dark);
//   * the machine's STOP button — a hardcoded white glyph on colorScheme.error,
//     which is a light salmon on every dark theme (1.70:1, 1.14:1 on HC dark).
//
// The measurement composites every ancestor fill down to the label, so a
// translucent severity tint over a card is evaluated as the operator sees it.
import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:fraktal_hmi/data/sim_repository.dart';
import 'package:fraktal_hmi/state/app_state.dart';
import 'package:fraktal_hmi/ui/app_theme.dart';
import 'package:fraktal_hmi/ui/fraktal_hmi_app.dart';

String _hex(Color? c) =>
    c == null ? 'NULL' : c.toARGB32().toRadixString(16).padLeft(8, '0');

double _contrast(Color a, Color b) {
  final la = a.computeLuminance(), lb = b.computeLuminance();
  final hi = la > lb ? la : lb, lo = la > lb ? lb : la;
  return (hi + 0.05) / (lo + 0.05);
}

Color _over(Color fg, Color bg) {
  final a = fg.a;
  if (a >= 1.0) return fg;
  return Color.from(
    alpha: 1,
    red: fg.r * a + bg.r * (1 - a),
    green: fg.g * a + bg.g * (1 - a),
    blue: fg.b * a + bg.b * (1 - a),
  );
}

/// The colour actually behind [leaf]: every ancestor fill composited over the
/// page surface, outermost first.
Color _backgroundOf(Element leaf, Color pageSurface) {
  final fills = <Color>[];
  leaf.visitAncestorElements((e) {
    final w = e.widget;
    Color? c;
    if (w is Material) {
      c = w.color;
    } else if (w is Container) {
      c = w.color;
    } else if (w is DecoratedBox) {
      final d = w.decoration;
      if (d is BoxDecoration) c = d.color;
    } else if (w is Card) {
      c = w.color;
    } else if (w is ColoredBox) {
      c = w.color;
    }
    if (c != null && c.a > 0) fills.add(c);
    return true;
  });
  var background = pageSurface;
  for (final fill in fills.reversed) {
    background = _over(fill, background);
  }
  return background;
}

void main() {
  for (var index = 0; index < kThemes.length; index++) {
    testWidgets('${kThemes[index].nameKey}: every painted glyph is legible',
        (tester) async {
      tester.view.physicalSize = const Size(1600, 1000);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.reset);

      final app = AppState(SimRepository(), initialThemeIndex: index);
      await tester.pumpWidget(FraktalHmiApp(app: app));
      await tester.pump(const Duration(seconds: 1));
      // Drill into a Unit as well as the overview: the module header's state
      // indicator, the mode bar and the Run/Stop button only exist there.
      final unit = find.text('Station A');
      if (unit.evaluate().isNotEmpty) {
        await tester.tap(unit.first, warnIfMissed: false);
        await tester.pump(const Duration(milliseconds: 600));
      }

      final scheme =
          Theme.of(tester.element(find.byType(Scaffold).first)).colorScheme;
      final failures = <String>[];
      final seen = <String>{};
      for (final element in find.byType(RichText, skipOffstage: true).evaluate()) {
        final render = element.renderObject;
        if (render is! RenderParagraph) continue;
        final ink = render.text.style?.color;
        final text = render.text.toPlainText().trim();
        if (ink == null || text.isEmpty) continue;
        final background = _backgroundOf(element, scheme.surface);
        final ratio = _contrast(ink, background);
        // 4.5:1 is WCAG AA for text. Icon glyphs come through the same path and
        // are held to it too — a machine panel in glare needs the headroom, and
        // every one of them cleared it once its pairing was fixed.
        if (ratio < 4.5 && seen.add('$text|${_hex(ink)}|${_hex(background)}')) {
          // Icons render as a private-use codepoint, so name them numerically.
          final label = text.runes.every((r) => r >= 0xE000 && r <= 0xF8FF)
              ? 'icon U+${text.runes.map((r) => r.toRadixString(16)).join(",")}'
              : '"$text"';
          failures.add('$label ${ratio.toStringAsFixed(2)}:1 '
              '(ink ${_hex(ink)} on ${_hex(background)})');
        }
      }
      // Dispose LAST and pump nothing after it — the shipped widget tests use
      // exactly this shape. SimRepository re-arms its 1 s tick on every listen,
      // so a trailing pump would leave a pending timer and the framework would
      // fail the test for that instead of reporting the contrast result.
      app.dispose();
      expect(failures, isEmpty,
          reason: '${kThemes[index].nameKey}: ${failures.length} illegible '
              'element(s):\n  ${failures.join("\n  ")}');
    });
  }
}
