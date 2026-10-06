// §8.11.4 — the cycle profile is a Gantt: every step sits on one shared time
// axis at the offset it actually ran, and the legend filters classes out of it.
// Original offsets remain authoritative. A filtered chart uses a separate,
// linear elapsed-time axis that excludes hidden durations completely.

import 'dart:ui' as ui;

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:fraktal_hmi/domain/types.dart';
import 'package:fraktal_hmi/localization/localization_controller.dart';
import 'package:fraktal_hmi/localization/localized_text.dart';
import 'package:fraktal_hmi/ui/cycle_profile_view.dart';

const _steps = [
  StepTiming(
      90, 'Await pallet', TimeClass.waitUpstream, Duration(milliseconds: 2100)),
  StepTiming(100, 'Separate', TimeClass.work, Duration(milliseconds: 1600),
      Duration(milliseconds: 2000)),
  StepTiming(200, 'Clamp', TimeClass.work, Duration(milliseconds: 2300),
      Duration(milliseconds: 2000)),
  StepTiming(300, 'Robot pick', TimeClass.work, Duration(milliseconds: 1500),
      Duration(milliseconds: 2000)),
  StepTiming(400, 'Await outfeed', TimeClass.waitDownstream,
      Duration(milliseconds: 700)),
];

const _profile = CycleProfile(
  cycleNo: 12,
  total: Duration(milliseconds: 8200),
  workTime: Duration(milliseconds: 5400),
  waitTime: Duration(milliseconds: 2800),
  steps: _steps,
);

const _starved = 'Wait ↑ (starved)';

Future<void> _pump(WidgetTester tester, CycleProfile profile) async {
  // A panel-sized surface: the card lays out fixed gutters plus a track, and an
  // 800px default would overflow before anything under test could be read.
  tester.view.physicalSize = const Size(1280, 900);
  tester.view.devicePixelRatio = 1.0;
  addTearDown(tester.view.reset);

  await tester.pumpWidget(LocalizationScope(
    controller:
        LocalizationController(enabledLanguages: {'en'}, activeLanguage: 'en'),
    child: MaterialApp(
      home: Scaffold(body: CycleProfileView(profile: profile)),
    ),
  ));
}

Finder _chip(String label) =>
    find.ancestor(of: find.text(label), matching: find.byType(FilterChip));

void main() {
  test('a step starts where its predecessor ended, and the last ends at Total',
      () {
    final offsets = stepStartOffsetsMs(_steps);
    expect(offsets, [0, 2100, 3700, 6000, 7500]);
    // FB_CycleProfiler publishes contiguous steps, so the Gantt's axis and the
    // §8.11.1 cycle time are the same span — the last bar lands on the end.
    expect(offsets.last + _steps.last.duration.inMilliseconds,
        _profile.total.inMilliseconds);
  });

  test('offsets of an empty profile are empty, not a crash', () {
    expect(stepStartOffsetsMs(const []), isEmpty);
  });

  testWidgets('every bar position is also readable as a Start value',
      (tester) async {
    await _pump(tester, _profile);

    // The Start column is the Gantt's table-view twin: position is never the
    // only encoding of when a step ran.
    for (final start in ['0.0s', '2.1s', '3.7s', '6.0s', '7.5s']) {
      expect(find.text(start), findsWidgets, reason: 'missing start $start');
    }
    expect(find.text('Start'), findsOneWidget);
    expect(find.text('Duration'), findsOneWidget);
    // header split, unchanged by the new form
    expect(find.text('8.2s'), findsOneWidget);
    expect(find.text('5.4s'), findsWidgets);
    expect(find.text('2.8s'), findsOneWidget);
  });

  testWidgets('§8.11.4(c) a step past its guard is called out in ink too',
      (tester) async {
    await _pump(tester, _profile);

    // Clamp ran 2.3s against a declared 2.0s: the bar gets the overrun outline,
    // and the number gets the error colour so it is not signalled by the chart
    // alone. Separate ran 1.6s inside its guard and stays default ink.
    //
    // Assert the two inks against the theme, not against null. The widget sets
    // `copyWith(color: overrun ? error : null)`, and copyWith IGNORES a null
    // argument - so the in-guard label keeps bodyMedium's own onSurface and can
    // never come back null under Material 3. Testing for null asserted a proxy
    // that stopped being true when the base style gained a colour, and the
    // failure was filed against a Flutter version delta rather than read.
    final ctx = tester.element(find.text('1.6s'));
    final errorInk = Theme.of(ctx).colorScheme.error;
    final defaultInk = Theme.of(ctx).textTheme.bodyMedium?.color;

    expect(tester.widget<Text>(find.text('2.3s')).style?.color, errorInk);
    expect(tester.widget<Text>(find.text('1.6s')).style?.color, defaultInk);
    expect(
        tester.widget<Text>(find.text('1.6s')).style?.color, isNot(errorInk));
  });

  testWidgets('a profile with no steps renders nothing', (tester) async {
    await _pump(tester, const CycleProfile());
    expect(find.byType(Card), findsNothing);
  });

  testWidgets('the legend offers one filter per class actually in the cycle',
      (tester) async {
    await _pump(tester, _profile);
    // Work, starved and blocked are in this cycle; operator and external are
    // not, so they get no chip to switch.
    expect(find.byType(FilterChip), findsNWidgets(3));
    expect(_chip('Wait operator'), findsNothing);
    for (final chip in tester.widgetList<FilterChip>(find.byType(FilterChip))) {
      expect(chip.selected, isTrue, reason: 'nothing is filtered at first');
    }
  });

  testWidgets(
      'filtering drops rows and excludes their time from visible starts',
      (tester) async {
    await _pump(tester, _profile);
    await tester.tap(_chip(_starved));
    await tester.pumpAndSettle();

    // The starved step is gone...
    expect(find.text('Await pallet'), findsNothing);
    // Visible starts use the filtered axis; original starts remain in tooltips.
    expect(find.text('Separate'), findsOneWidget);
    for (final start in ['0.0s', '1.6s', '3.9s', '5.4s']) {
      expect(find.text(start), findsWidgets,
          reason: 'missing filtered start $start');
    }
    for (final start in ['2.1s', '3.7s', '6.0s', '7.5s']) {
      expect(find.byTooltip('Original cycle start: $start'), findsOneWidget);
    }
    // The header stays the cycle's truth — §8.11.1 does not move on a filter.
    expect(find.text('8.2s'), findsOneWidget);
  });

  testWidgets('the filter states what it removed and what is left',
      (tester) async {
    await _pump(tester, _profile);
    await tester.tap(_chip(_starved));
    await tester.pumpAndSettle();

    // 8.2s total less the 2.1s starved step = the §8.11.4(f) what-if.
    expect(find.textContaining('2.1s in 1 step'), findsOneWidget);
    expect(find.textContaining('the cycle without it is 6.1s'), findsOneWidget);
    expect(tester.widget<FilterChip>(_chip(_starved)).selected, isFalse);
  });

  testWidgets('Show all restores every class', (tester) async {
    await _pump(tester, _profile);
    await tester.tap(_chip(_starved));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Show all'));
    await tester.pumpAndSettle();

    expect(find.text('Await pallet'), findsOneWidget);
    expect(find.text('Show all'), findsNothing);
    expect(find.textContaining('the cycle without it is'), findsNothing);
  });

  testWidgets('filtering everything out says so instead of drawing nothing',
      (tester) async {
    await _pump(tester, _profile);
    for (final label in ['Work', _starved, 'Wait ↓ (blocked)']) {
      await tester.tap(_chip(label));
      await tester.pumpAndSettle();
    }

    expect(find.text('Every time class is filtered out'), findsOneWidget);
    // The chips survive, or there would be no way back.
    expect(find.byType(FilterChip), findsNWidgets(3));
    await tester.tap(find.text('Show all'));
    await tester.pumpAndSettle();
    expect(find.text('Await pallet'), findsOneWidget);
  });

  testWidgets('a class that leaves the cycle does not stay latched out',
      (tester) async {
    await _pump(tester, _profile);
    await tester.tap(_chip(_starved));
    await tester.pumpAndSettle();
    expect(find.textContaining('Filtered out'), findsOneWidget);

    // Next cycle ran without a starved step at all: its chip is gone, so the
    // filter has to release or nothing could switch it back on.
    await tester.pumpWidget(LocalizationScope(
      controller: LocalizationController(
          enabledLanguages: {'en'}, activeLanguage: 'en'),
      child: const MaterialApp(
        home: Scaffold(
          body: CycleProfileView(
            profile: CycleProfile(
              cycleNo: 13,
              total: Duration(milliseconds: 6100),
              workTime: Duration(milliseconds: 5400),
              waitTime: Duration(milliseconds: 700),
              steps: [
                StepTiming(100, 'Separate', TimeClass.work,
                    Duration(milliseconds: 1600)),
                StepTiming(
                    200, 'Clamp', TimeClass.work, Duration(milliseconds: 2300)),
                StepTiming(300, 'Robot pick', TimeClass.work,
                    Duration(milliseconds: 1500)),
                StepTiming(400, 'Await outfeed', TimeClass.waitDownstream,
                    Duration(milliseconds: 700)),
              ],
            ),
          ),
        ),
      ),
    ));
    await tester.pumpAndSettle();

    expect(find.textContaining('Filtered out'), findsNothing);
    expect(find.byType(FilterChip), findsNWidgets(2));
  });

  testWidgets('interior and edge waits contribute no filtered axis time',
      (tester) async {
    const profile = CycleProfile(
      total: Duration(seconds: 77),
      workTime: Duration(seconds: 2),
      waitTime: Duration(seconds: 75),
      steps: [
        StepTiming(10, 'Pallet', TimeClass.waitUpstream, Duration(seconds: 10)),
        StepTiming(20, 'First work', TimeClass.work, Duration(seconds: 1)),
        StepTiming(
            30, 'Decision', TimeClass.waitOperator, Duration(seconds: 60)),
        StepTiming(40, 'Second work', TimeClass.work, Duration(seconds: 1)),
        StepTiming(
            50, 'Outfeed', TimeClass.waitDownstream, Duration(seconds: 5)),
      ],
    );
    await _pump(tester, profile);
    for (final label in [_starved, 'Wait operator', 'Wait ↓ (blocked)']) {
      await tester.tap(_chip(label));
      await tester.pumpAndSettle();
    }
    final paintFinder = find.byWidgetPredicate((w) =>
        w is CustomPaint &&
        w.painter.runtimeType.toString() == '_GanttPainter');
    final painter = tester.widget<CustomPaint>(paintFinder).painter!;
    final dynamic geometry = painter;
    expect(geometry.spanMs, 2000);
    expect(geometry.startMs, [0, 1000]);
    expect(
        find.text('Filtered time axis — hidden time excluded'), findsOneWidget);
    expect(find.text('77.0s'), findsOneWidget);
    expect(find.byTooltip('Original cycle start: 10.0s'), findsOneWidget);
    expect(find.byTooltip('Original cycle start: 71.0s'), findsOneWidget);

    // Render the production painter: both one-second bars occupy half the
    // retained axis. A 60-second blank interval would leave these pixels empty.
    final pixels = await tester.runAsync(() async {
      final recorder = ui.PictureRecorder();
      painter.paint(Canvas(recorder), const Size(600, 72));
      final picture = recorder.endRecording();
      final image = await picture.toImage(600, 72);
      final bytes =
          (await image.toByteData(format: ui.ImageByteFormat.rawRgba))!;
      final colors = [
        for (final (x, y) in [(150, 13), (450, 39)])
          [
            for (var channel = 0; channel < 4; channel++)
              bytes.getUint8((y * 600 + x) * 4 + channel)
          ]
      ];
      image.dispose();
      picture.dispose();
      return colors;
    });
    expect(pixels, [
      [46, 125, 50, 255],
      [46, 125, 50, 255]
    ]);

    await tester.tap(find.text('Show all'));
    await tester.pumpAndSettle();
    final dynamic restored = tester.widget<CustomPaint>(paintFinder).painter!;
    expect(restored.spanMs, 77000);
    expect(restored.startMs, [0, 10000, 11000, 71000, 72000]);
    expect(
        find.text('Filtered time axis — hidden time excluded'), findsNothing);
  });

  testWidgets('zero-duration survivors still render on a bounded filtered axis',
      (tester) async {
    await _pump(
        tester,
        const CycleProfile(total: Duration(seconds: 10), steps: [
          StepTiming(10, 'Wait', TimeClass.waitOperator, Duration(seconds: 10)),
          StepTiming(20, 'Instant work', TimeClass.work, Duration.zero),
        ]));
    await tester.tap(_chip('Wait operator'));
    await tester.pumpAndSettle();
    expect(find.text('Instant work'), findsOneWidget);
    expect(find.text('0.0s'), findsWidgets);
    expect(tester.takeException(), isNull);
  });
}
