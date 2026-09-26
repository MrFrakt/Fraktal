// Contrast measured on what is PAINTED, not on what the theme declares.
//
// The other two contrast suites read colours out of `ColorScheme` and out of
// `app_theme`'s own API. Both passed while the app rendered invisible chip
// labels in all fourteen themes, because `ChipThemeData.labelStyle` is a plain
// `TextStyle?` and had been handed a `WidgetStateTextStyle`. Consumed
// unresolved, that reports `color == null`; the chip then inherited the
// ambient DefaultTextStyle, which on a black card is black on black. A test
// that resolved the style by hand saw the colour the widget never got.
//
// So this suite pumps real widgets and asks the element tree what ink the text
// actually has. A null ink is a failure on its own - text with no colour is
// one theme change away from being invisible, and it is invisible NOW on
// whichever surface happens to match the fallback.
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:fraktal_hmi/ui/app_theme.dart';

const double kAa = 4.5;

double contrast(Color a, Color b) {
  final la = a.computeLuminance();
  final lb = b.computeLuminance();
  final hi = la > lb ? la : lb;
  final lo = la > lb ? lb : la;
  return (hi + 0.05) / (lo + 0.05);
}

Color flatten(Color fg, Color bg) => Color.from(
      alpha: 1,
      red: fg.r * fg.a + bg.r * (1 - fg.a),
      green: fg.g * fg.a + bg.g * (1 - fg.a),
      blue: fg.b * fg.a + bg.b * (1 - fg.a),
    );

/// The ink this Text will really be drawn with: its own style if it sets a
/// colour, otherwise whatever it inherits at its own position in the tree.
Color? paintedInk(WidgetTester tester, Finder text) {
  final widget = tester.widget<Text>(text);
  final explicit = widget.style?.color;
  if (explicit != null) return explicit;
  return DefaultTextStyle.of(tester.element(text)).style.color;
}

/// The nearest painted fill behind this Text, flattened onto the scaffold.
Color paintedFill(WidgetTester tester, Finder text, Color scaffold) {
  Color? found;
  tester.element(text).visitAncestorElements((element) {
    final widget = element.widget;
    if (widget is Material && widget.color != null) {
      found = widget.color;
      return false;
    }
    if (widget is ColoredBox) {
      found = widget.color;
      return false;
    }
    if (widget is DecoratedBox) {
      final decoration = widget.decoration;
      if (decoration is BoxDecoration && decoration.color != null) {
        found = decoration.color;
        return false;
      }
    }
    return true;
  });
  return found == null ? scaffold : flatten(found!, scaffold);
}

/// One widget worth measuring, with the label it renders.
class Specimen {
  final String name;
  final String label;
  final Widget Function() build;
  const Specimen(this.name, this.label, this.build);
}

final specimens = <Specimen>[
  Specimen('Chip', 'CHIP', () => const Chip(label: Text('CHIP'))),
  Specimen('Chip with avatar', 'MODEL',
      () => const Chip(avatar: Icon(Icons.qr_code_2), label: Text('MODEL'))),
  Specimen('FilledButton', 'FILLED',
      () => FilledButton(onPressed: () {}, child: const Text('FILLED'))),
  Specimen('ElevatedButton', 'ELEVATED',
      () => ElevatedButton(onPressed: () {}, child: const Text('ELEVATED'))),
  Specimen('OutlinedButton', 'OUTLINED',
      () => OutlinedButton(onPressed: () {}, child: const Text('OUTLINED'))),
  Specimen('TextButton', 'TEXTBTN',
      () => TextButton(onPressed: () {}, child: const Text('TEXTBTN'))),
  Specimen('ListTile', 'TILE', () => const ListTile(title: Text('TILE'))),
  Specimen('Card body', 'CARDTEXT',
      () => const Card(child: Padding(
            padding: EdgeInsets.all(12), child: Text('CARDTEXT')))),
  Specimen('Tooltip child', 'TIPCHILD',
      () => const Tooltip(message: 'm', child: Text('TIPCHILD'))),
];

void main() {
  testWidgets('no painted label is left without a colour', (tester) async {
    // The defect this suite exists for. Checked separately from the ratio so
    // the failure says "no ink" rather than an arithmetic result on a
    // fallback that happened to be legible in the test harness.
    final colourless = <String>[];
    for (var i = 0; i < kThemes.length; i++) {
      for (final specimen in specimens) {
        await tester.pumpWidget(MaterialApp(
          theme: themeAt(i),
          home: Scaffold(body: Center(child: specimen.build())),
        ));
        await tester.pumpAndSettle();
        final finder = find.text(specimen.label);
        if (paintedInk(tester, finder) == null) {
          colourless.add('${kThemes[i].nameKey}: ${specimen.name}');
        }
      }
    }
    expect(colourless, isEmpty,
        reason: 'these inherit whatever ambient style they land in:\n'
            '${colourless.join('\n')}');
  });

  testWidgets('every painted label clears AA against its own fill',
      (tester) async {
    final failures = <String>[];
    for (var i = 0; i < kThemes.length; i++) {
      final theme = themeAt(i);
      for (final specimen in specimens) {
        await tester.pumpWidget(MaterialApp(
          theme: theme,
          home: Scaffold(body: Center(child: specimen.build())),
        ));
        await tester.pumpAndSettle();
        final finder = find.text(specimen.label);
        final scaffold = theme.scaffoldBackgroundColor;
        final ink = paintedInk(tester, finder);
        if (ink == null) continue; // reported by the test above
        final fill = paintedFill(tester, finder, scaffold);
        final ratio = contrast(flatten(ink, fill), fill);
        if (ratio < kAa) {
          failures.add('${kThemes[i].nameKey}: ${specimen.name} '
              '= ${ratio.toStringAsFixed(2)}:1 (needs $kAa)');
        }
      }
    }
    expect(failures, isEmpty, reason: failures.join('\n'));
  });

  testWidgets('the specimens really are painted on different fills',
      (tester) async {
    // Guard against the measurement quietly degrading into "everything on the
    // scaffold": if every specimen resolved the same fill, this suite would
    // be measuring one pairing fourteen times and would not have caught the
    // chip.
    final fills = <Color>{};
    final theme = themeAt(0);
    for (final specimen in specimens) {
      await tester.pumpWidget(MaterialApp(
        theme: theme,
        home: Scaffold(body: Center(child: specimen.build())),
      ));
      await tester.pumpAndSettle();
      fills.add(paintedFill(
          tester, find.text(specimen.label), theme.scaffoldBackgroundColor));
    }
    expect(fills.length, greaterThan(1),
        reason: 'every specimen resolved the same fill; the walk is broken');
  });
}
