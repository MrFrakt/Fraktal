import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:fraktal_hmi/localization/default_catalogs.dart';
import 'package:fraktal_hmi/localization/localization_controller.dart';
import 'package:fraktal_hmi/localization/localized_text.dart';
import 'package:fraktal_hmi/ui/app_theme.dart';
import 'package:fraktal_hmi/ui/theme_picker.dart';
import 'package:fraktal_hmi/ui/theme_surfaces.dart';

double contrast(Color a, Color b) {
  final x = a.computeLuminance(), y = b.computeLuminance();
  return ((x > y ? x : y) + 0.05) / ((x < y ? x : y) + 0.05);
}

void main() {
  test('saved theme indices still name the original themes', () {
    expect(kThemes.take(14).map((theme) => theme.nameKey), [
      'std.theme.lightBlue',
      'std.theme.cyan',
      'std.theme.teal',
      'std.theme.indigo',
      'std.theme.slate',
      'std.theme.amber',
      'std.theme.darkBlue',
      'std.theme.darkCyan',
      'std.theme.darkTeal',
      'std.theme.graphite',
      'std.theme.darkSlate',
      'std.theme.oledBlack',
      'std.theme.highContrastLight',
      'std.theme.highContrastDark',
    ]);
    expect(kThemes.skip(14), hasLength(15));
    expect(kThemes.map((theme) => theme.nameKey).toSet(),
        hasLength(kThemes.length));
    for (final spec in kThemes) {
      expect(standardEnglish[spec.nameKey], isNotEmpty);
    }
  });

  test('the picker shows the standard themes first, ISA-101 leading', () {
    final order = kThemeDisplayOrder;
    expect(order.toSet(), hasLength(kThemes.length),
        reason: 'every theme exactly once');
    final firstModern = order.indexWhere((i) => !kThemes[i].standard);
    expect(order.skip(firstModern).every((i) => !kThemes[i].standard), isTrue,
        reason: 'no standard theme after a modern one');
    expect(order.take(2).map((i) => kThemes[i].nameKey),
        ['std.theme.processGrey', 'std.theme.processGreyDark']);
    expect(kThemes.where((t) => t.isa101).every((t) => t.standard), isTrue);
    // Grouping is by finish, so a decorated theme can never land in Standard.
    expect(
        kThemes
            .where((t) => t.nameKey == 'std.theme.aetherBlueprint')
            .single
            .standard,
        isFalse);
  });

  test('new surfaces preserve contrast and scaled operator targets', () {
    for (final spec in kThemes.where((spec) => spec.surfaces != null)) {
      final skin = spec.surfaces!;
      for (final scale in ControlScale.values) {
        final theme = spec.toThemeData(scale);
        final cs = theme.colorScheme;
        final target = theme.filledButtonTheme.style!.minimumSize!.resolve({})!;
        expect(target.height,
            greaterThanOrEqualTo(UiMetrics.of(scale).touchTarget));
        // Both the brightest end of the panel and the actual page gradient
        // (including a sunset wash) must carry text. As painted: the glass
        // fill composited over each end, then the reflection over the fill.
        for (final background in skin.backdropColors) {
          final top = Color.lerp(skin.panel, Colors.white,
              skin.finish == SurfaceFinish.glass ? 0.035 : 0.012)!;
          final glazed = skin.finish == SurfaceFinish.glass
              ? Color.alphaBlend(top.withValues(alpha: 0.72), background)
              : top;
          final fill = Color.alphaBlend(
              Colors.white.withValues(alpha: skin.sheen), glazed);
          for (final ink in [cs.onSurface, cs.onSurfaceVariant]) {
            expect(contrast(ink, background), greaterThan(4.5),
                reason: '${spec.nameKey}: page text');
            expect(contrast(ink, fill), greaterThan(4.5),
                reason: '${spec.nameKey}: panel text');
          }
        }
      }
    }
  });

  testWidgets('glass is clipped and reduced effects remove its blur',
      (tester) async {
    final spec = kThemes.firstWhere((s) => s.nameKey == 'std.theme.glassPearl');
    for (final reduced in [false, true]) {
      await tester.pumpWidget(MaterialApp(
        theme: spec.toThemeData(),
        home: MediaQuery(
          data: MediaQueryData(disableAnimations: reduced),
          child: const FraktalBackdrop(
            child: Scaffold(
                body: Center(child: FraktalCard(child: Text('Panel')))),
          ),
        ),
      ));
      await tester.pumpAndSettle();
      expect(
          find.byType(BackdropFilter), reduced ? findsNothing : findsOneWidget);
      if (!reduced) {
        expect(
            find.ancestor(
                of: find.byType(BackdropFilter),
                matching: find.byType(ClipPath)),
            findsWidgets);
      }
      expect(tester.takeException(), isNull);
    }
  });

  testWidgets('the shared picker selects themes and respects the access gate',
      (tester) async {
    tester.view.physicalSize = const Size(390, 844);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.reset);
    int? chosen;
    final localization =
        LocalizationController(enabledLanguages: {'en'}, activeLanguage: 'en');
    addTearDown(localization.dispose);
    Widget host({required bool enabled}) => LocalizationScope(
          controller: localization,
          child: MaterialApp(
            theme: themeAt(12), // the selected label must also work on HC light
            home: Scaffold(
                body: SingleChildScrollView(
                    child: ThemePicker(
              selectedIndex: 14,
              onChanged: enabled ? (index) => chosen = index : null,
            ))),
          ),
        );
    await tester.pumpWidget(host(enabled: true));
    final last = find.byKey(ValueKey('theme-${kThemes.last.nameKey}'));
    await tester.ensureVisible(last);
    await tester.tap(last);
    expect(chosen, kThemes.length - 1);
    expect(tester.takeException(), isNull);
    chosen = null;
    await tester.pumpWidget(host(enabled: false));
    await tester.ensureVisible(last);
    await tester.tap(last);
    expect(chosen, isNull);
    expect(tester.takeException(), isNull);
  });

  testWidgets('a severity fill survives the material treatment',
      (tester) async {
    const tint = Color(0x22880000);
    final spec =
        kThemes.firstWhere((s) => s.nameKey == 'std.theme.cloudLavender');
    await tester.pumpWidget(MaterialApp(
      theme: spec.toThemeData(),
      home:
          const Scaffold(body: FraktalCard(color: tint, child: Text('Alarm'))),
    ));
    final decorations =
        tester.widgetList<DecoratedBox>(find.byType(DecoratedBox));
    final fills = decorations
        .map((box) => box.decoration)
        .whereType<ShapeDecoration>()
        .where((shape) => shape.gradient != null);
    expect(
        fills.any((fill) =>
            fill.gradient!.colors.last ==
            Color.alphaBlend(tint, spec.surfaces!.panel)),
        isTrue);
  });
}
