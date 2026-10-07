import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:fraktal_hmi/data/sim_repository.dart';
import 'package:fraktal_hmi/state/app_state.dart';
import 'package:fraktal_hmi/domain/types.dart';
import 'package:fraktal_hmi/ui/app_theme.dart';
import 'package:fraktal_hmi/ui/fraktal_hmi_app.dart';
import 'package:fraktal_hmi/ui/theme_chrome.dart';
import 'package:fraktal_hmi/ui/theme_surfaces.dart';
import 'package:fraktal_hmi/ui/tree_menu.dart';
import 'package:fraktal_hmi/ui/theme_picker.dart';

final boschIndex =
    kThemes.indexWhere((theme) => theme.nameKey == 'std.theme.likeABosch');

double contrast(Color a, Color b) {
  final x = a.computeLuminance(), y = b.computeLuminance();
  return ((x > y ? x : y) + 0.05) / ((x < y ? x : y) + 0.05);
}

void main() {
  test('light content and dark navigation keep readable colour pairs', () {
    final theme = themeAt(boschIndex);
    final chrome = theme.extension<FraktalChromeTheme>()!;
    final navigation = chrome.navigationTheme(theme);
    expect(theme.brightness, Brightness.light);
    expect(navigation.brightness, Brightness.dark);
    expect(contrast(chrome.onNavigation, chrome.navigation), greaterThan(4.5));
    expect(contrast(chrome.onSelection, chrome.selection), greaterThan(4.5));
    expect(contrast(theme.colorScheme.onPrimary, theme.colorScheme.primary),
        greaterThan(4.5));
    for (final scale in ControlScale.values) {
      final scaled = themeAt(boschIndex, scale);
      expect(scaled.filledButtonTheme.style!.minimumSize!.resolve({})!.height,
          greaterThanOrEqualTo(UiMetrics.of(scale).touchTarget));
    }
  });

  testWidgets('the multicolor band stays full width in setup-sized surfaces',
      (tester) async {
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.reset);
    for (final width in [390.0, 1266.0]) {
      tester.view.physicalSize = Size(width, 792);
      await tester.pumpWidget(MaterialApp(
          theme: themeAt(boschIndex),
          home: const FraktalBackdrop(child: Scaffold(body: SizedBox()))));
      await tester.pumpAndSettle();
      expect(find.byType(FraktalAccentBand), findsOneWidget);
      expect(tester.getSize(find.byType(FraktalAccentBand)), Size(width, 8));
      expect(tester.getTopLeft(find.byType(Scaffold)), const Offset(0, 8));
      expect(tester.takeException(), isNull);
    }
    await tester.pumpWidget(MaterialApp(
        theme: themeAt(0),
        home: const FraktalBackdrop(child: Scaffold(body: SizedBox()))));
    await tester.pumpAndSettle();
    expect(find.byType(FraktalAccentBand), findsNothing);
  });

  testWidgets('status and alarm foregrounds stay visible on the dark tree',
      (tester) async {
    final theme = themeAt(boschIndex);
    final chrome = theme.extension<FraktalChromeTheme>()!;
    await tester.pumpWidget(MaterialApp(
        theme: chrome.navigationTheme(theme),
        home: Builder(builder: (context) {
          for (final state in ExecState.values) {
            expect(contrast(stateColor(context, state), chrome.navigation),
                greaterThan(3));
          }
          for (final severity in Severity.values) {
            final color = severityColor(context, severity);
            final background = Color.alphaBlend(
                color.withValues(alpha: 0.28), chrome.navigation);
            expect(contrast(color, background), greaterThan(3),
                reason: '$severity glyph');
            expect(
                contrast(Theme.of(context).colorScheme.onSurface, background),
                greaterThan(4.5),
                reason: '$severity tree label');
          }
          return const Scaffold();
        })));
    expect(tester.takeException(), isNull);
  });

  testWidgets(
      'real operator shell preserves the band and responsive navigation',
      (tester) async {
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.reset);
    for (final scale in ControlScale.values) {
      for (final size in [const Size(1266, 792), const Size(390, 844)]) {
        tester.view.physicalSize = size;
        final app = AppState(SimRepository(),
            initialThemeIndex: boschIndex, initialControlScale: scale);
        await tester.pumpWidget(FraktalHmiApp(app: app));
        await tester.pump(const Duration(seconds: 1));
        app.select(app.forest.first.path);
        await tester.pump(const Duration(milliseconds: 600));
        expect(find.byType(FraktalAccentBand), findsOneWidget);
        expect(
            tester.getSize(find.byType(FraktalAccentBand)).width, size.width);
        if (size.width >= 900) {
          final tree = find.byType(TreeMenu).last;
          expect(tester.getSize(tree).width, 225);
          final surface =
              find.descendant(of: tree, matching: find.byType(Material)).first;
          expect(
              tester.widget<Material>(surface).color, const Color(0xFF272F34));
          app.toggleRail();
          await tester.pump(const Duration(milliseconds: 200));
        } else if (scale != ControlScale.compact) {
          await tester.tap(find.byKey(const Key('shell-more-actions')));
          await tester.pumpAndSettle();
          await tester.tap(find.text('Settings'));
          await tester.pumpAndSettle();
          expect(find.byType(ThemePicker), findsOneWidget,
              reason: 'settings remain reachable with large phone controls');
        }
        expect(tester.takeException(), isNull,
            reason: '$scale/$size must not overflow');
        app.dispose();
        await tester.pumpWidget(const SizedBox());
      }
    }
  });
}
