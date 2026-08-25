// §8.11.4 — the cycle profile is a Gantt: every step sits on one shared time
// axis at the offset it actually ran, and the legend filters classes out of it.
// These lock the three things that have to stay true — the derived offsets, the
// fact that they are also readable as text, and that filtering hides rows
// without ever moving the ones that remain.

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:fraktal_hmi/domain/types.dart';
import 'package:fraktal_hmi/localization/localization_controller.dart';
import 'package:fraktal_hmi/localization/localized_text.dart';
import 'package:fraktal_hmi/ui/cycle_profile_view.dart';

const _steps = [
  StepTiming(90, 'Await pallet', TimeClass.waitUpstream,
      Duration(milliseconds: 2100)),
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
    expect(tester.widget<Text>(find.text('2.3s')).style?.color, isNotNull);
    expect(tester.widget<Text>(find.text('1.6s')).style?.color, isNull);
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

  testWidgets('filtering a class out drops its rows and keeps the rest put',
      (tester) async {
    await _pump(tester, _profile);
    await tester.tap(_chip(_starved));
    await tester.pumpAndSettle();

    // The starved step is gone...
    expect(find.text('Await pallet'), findsNothing);
    expect(find.text('0.0s'), findsNothing);
    // ...and every survivor still reports the start it really had. A re-flow of
    // the visible steps would have pulled Separate back to 0.0s.
    expect(find.text('Separate'), findsOneWidget);
    for (final start in ['2.1s', '3.7s', '6.0s', '7.5s']) {
      expect(find.text(start), findsWidgets, reason: 'moved start $start');
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
      controller:
          LocalizationController(enabledLanguages: {'en'}, activeLanguage: 'en'),
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
                StepTiming(200, 'Clamp', TimeClass.work,
                    Duration(milliseconds: 2300)),
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
}
