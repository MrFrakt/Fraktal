import 'dart:ui' as ui;

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:fraktal_hmi/domain/types.dart';
import 'package:fraktal_hmi/localization/localization_controller.dart';
import 'package:fraktal_hmi/localization/localized_text.dart';
import 'package:fraktal_hmi/ui/cycle_trend_view.dart';
import 'package:fraktal_hmi/ui/theme_surfaces.dart';
import 'package:fraktal_hmi/ui/overview_and_indicators.dart';
import 'package:fraktal_hmi/ui/timing_chart_filters.dart';

const _second = Duration(seconds: 1);
const _history = [
  CycleSummary(
      cycleNo: 1,
      total: Duration(seconds: 20),
      workTime: _second,
      waitTime: Duration(seconds: 19),
      byClass: [
        _second,
        Duration(seconds: 10),
        Duration(seconds: 2),
        Duration(seconds: 3),
        Duration(seconds: 4),
      ]),
  CycleSummary(
      cycleNo: 2,
      total: Duration(seconds: 21),
      workTime: Duration(seconds: 2),
      waitTime: Duration(seconds: 19),
      byClass: [
        Duration(seconds: 2),
        Duration(seconds: 10),
        Duration(seconds: 2),
        Duration(seconds: 3),
        Duration(seconds: 4),
      ]),
];
const _stats = [
  StepStat(10, 'Process', TimeClass.work, _second, Duration(seconds: 2)),
  StepStat(20, 'Pallet', TimeClass.waitUpstream, Duration(seconds: 10),
      Duration(seconds: 12)),
  // Maximum is greater than the preceding row despite a smaller average.
  StepStat(30, 'Outfeed', TimeClass.waitDownstream, Duration(seconds: 3),
      Duration(seconds: 15)),
  StepStat(40, 'Operator', TimeClass.waitOperator, _second, _second),
  StepStat(50, 'Host', TimeClass.waitExternal, _second, _second),
];

Future<void> _pump(WidgetTester tester, Widget chart) async {
  await tester.pumpWidget(LocalizationScope(
    controller:
        LocalizationController(enabledLanguages: {'en'}, activeLanguage: 'en'),
    child: MaterialApp(home: Scaffold(body: chart)),
  ));
  await tester.pumpAndSettle();
}

Finder _chip(TimeClass c) => find.ancestor(
    of: find.text(timeClassLabel(c)), matching: find.byType(FilterChip));

CustomPainter _trendPainter(WidgetTester tester) => tester
    .widget<CustomPaint>(find.byWidgetPredicate((w) =>
        w is CustomPaint &&
        w.painter.runtimeType.toString() == '_TrendPainter'))
    .painter!;

// Render the actual painter: selection must change pixels and rescale surviving
// series, not just change the legend or a backing field.
Future<Map<TimeClass, int>> _coloredPixels(CustomPainter painter) async {
  final recorder = ui.PictureRecorder();
  painter.paint(Canvas(recorder), const Size(600, 140));
  final picture = recorder.endRecording();
  final image = await picture.toImage(600, 140);
  final bytes = (await image.toByteData(format: ui.ImageByteFormat.rawRgba))!;
  final result = {for (final c in TimeClass.values) c: 0};
  for (var offset = 0; offset < bytes.lengthInBytes; offset += 4) {
    for (final c in TimeClass.values) {
      final argb = timeClassColor(c).toARGB32();
      if (bytes.getUint8(offset) == (argb >> 16 & 255) &&
          bytes.getUint8(offset + 1) == (argb >> 8 & 255) &&
          bytes.getUint8(offset + 2) == (argb & 255) &&
          bytes.getUint8(offset + 3) == 255) result[c] = result[c]! + 1;
    }
  }
  image.dispose();
  picture.dispose();
  return result;
}

Finder _paretoFill(TimeClass c) => find.descendant(
    of: find.byType(StepParetoView),
    matching: find.byWidgetPredicate((w) =>
        w is Container &&
        w.decoration is BoxDecoration &&
        (w.decoration as BoxDecoration).color == timeClassColor(c) &&
        w.constraints?.maxWidth != 12));

void main() {
  testWidgets('filter animation does not repaint neighbouring chart content',
      (tester) async {
    final painter = _PaintCounter();
    await _pump(tester, TimingChartFilters<TimeClass>(
      options: [const TimingChartOption(TimeClass.work, 'Work', Colors.green)],
      builder: (context, hidden, legend) => FraktalCard(
        child: Column(children: [
          SizedBox(width: 200, height: 140,
              child: CustomPaint(painter: painter)),
          legend,
        ]),
      ),
    ));
    await tester.tap(find.text('Work'));
    await tester.pump();
    final afterChange = painter.count;
    for (var frame = 0; frame < 12; frame++) {
      await tester.pump(const Duration(milliseconds: 16));
    }
    expect(tester.widget<FilterChip>(find.byType(FilterChip)).selected, isFalse);
    expect(painter.count, afterChange,
        reason: 'chip animation must not redraw the chart every frame');
  });


  testWidgets('zero-time history does not claim an active filter',
      (tester) async {
    await _pump(
        tester,
        const CycleTrendView(history: [
          CycleSummary(cycleNo: 1),
          CycleSummary(cycleNo: 2),
        ]));
    expect(find.text('Every time class is filtered out'), findsNothing);
    expect(find.text('Show all'), findsNothing);
    expect(find.byType(FilterChip), findsNothing);
    expect(_trendPainter(tester), isNotNull);
  });

  testWidgets(
      'trend filters every time type, rescales work and preserves totals',
      (tester) async {
    await _pump(
        tester,
        const CycleTrendView(
            history: _history, minCycleTime: Duration(seconds: 20)));
    expect(find.byType(FilterChip), findsNWidgets(5));
    final before =
        await tester.runAsync(() => _coloredPixels(_trendPainter(tester)));
    for (final c in TimeClass.values.skip(1)) {
      await tester.tap(_chip(c));
      await tester.pumpAndSettle();
      final painted =
          await tester.runAsync(() => _coloredPixels(_trendPainter(tester)));
      expect(painted![c], 0, reason: '$c still drawn');
      expect(tester.widget<FilterChip>(_chip(c)).selected, isFalse);
    }
    final after =
        await tester.runAsync(() => _coloredPixels(_trendPainter(tester)));
    expect(after![TimeClass.work], greaterThan(before![TimeClass.work]! * 8));
    expect(find.text('best 20.0s'), findsNothing);
    final chart = find.byWidgetPredicate((w) =>
        w is CustomPaint &&
        w.painter.runtimeType.toString() == '_TrendPainter');
    await tester.tapAt(tester.getTopLeft(chart) + const Offset(10, 60));
    await tester.pumpAndSettle();
    expect(find.textContaining('Shown 1.0s · total 20.0s'), findsOneWidget);
    expect(_history.first.total, const Duration(seconds: 20));
    await tester.tap(find.text('Show all'));
    await tester.pumpAndSettle();
    expect(find.text('best 20.0s'), findsOneWidget);
    final restored =
        await tester.runAsync(() => _coloredPixels(_trendPainter(tester)));
    for (final c in TimeClass.values) expect(restored![c], greaterThan(0));
  });

  testWidgets('Pareto filters types and uses the greatest visible maximum',
      (tester) async {
    await _pump(tester, const StepParetoView(stats: _stats));
    final before = tester.getSize(_paretoFill(TimeClass.work)).width;
    for (final c in TimeClass.values.skip(1)) {
      await tester.tap(_chip(c));
      await tester.pumpAndSettle();
      expect(_paretoFill(c), findsNothing);
    }
    final after = tester.getSize(_paretoFill(TimeClass.work)).width;
    expect(after / before, closeTo(15 / 2, 0.01));
    expect(find.text('10 Process'), findsOneWidget);
    expect(find.text('1.0/2.0s'), findsOneWidget);
    await tester.tap(find.text('Show all'));
    await tester.pumpAndSettle();
    expect(find.text('20 Pallet'), findsOneWidget);
    expect(tester.getSize(_paretoFill(TimeClass.work)).width, before);
  });

  // A narrow flow column can leave a bar less than its own tick; it must lay
  // out inside whatever it gets instead of throwing from clamp().
  testWidgets('timing bar stays inside any granted width', (tester) async {
    for (final width in [0.0, 1.0, 1.5, 2.0, 3.0, 120.0]) {
      for (final frac in [0.0, 0.01, 0.5, 1.0]) {
        await _pump(
            tester,
            Align(
                alignment: Alignment.topLeft,
                child: SizedBox(
                    width: width,
                    child: TimingBar(
                        avgFraction: frac,
                        maxFraction: frac,
                        height: 14,
                        radius: 3,
                        color: timeClassColor(TimeClass.work),
                        tickColor: Colors.black))));
        expect(tester.takeException(), isNull, reason: 'width $width frac $frac');
        final bar = tester.getRect(find.byType(TimingBar));
        for (final box in tester.renderObjectList<RenderBox>(find.descendant(
            of: find.byType(TimingBar), matching: find.byType(Container)))) {
          final rect = box.localToGlobal(Offset.zero) & box.size;
          expect(rect.left, greaterThanOrEqualTo(bar.left - 1e-9));
          expect(rect.right, lessThanOrEqualTo(bar.right + 1e-9),
              reason: 'width $width frac $frac');
        }
      }
    }
  });

  // The flow layout gave this card 391 px; fixed 140+5x56 columns overflowed.
  testWidgets('command timing sizes its columns to the card it gets',
      (tester) async {
    const rows = [
      CommandTiming(1, 'RETRACT', 3, Duration(milliseconds: 420),
          Duration(milliseconds: 400), Duration(milliseconds: 1250),
          Duration(milliseconds: 610)),
      CommandTiming(2, 'EXTEND', 3, Duration(milliseconds: 380),
          Duration(milliseconds: 350), Duration(milliseconds: 900),
          Duration(milliseconds: 500)),
    ];
    for (final width in [120.0, 260.0, 300.0, 391.0, 700.0]) {
      await _pump(
          tester,
          Align(
              alignment: Alignment.topLeft,
              child: SizedBox(
                  width: width,
                  child: const CommandTimingView(
                      moduleName: 'PressRam', rows: rows))));
      expect(tester.takeException(), isNull, reason: 'width $width');
      expect(find.text('RETRACT'), findsOneWidget);
      expect(find.text('1.25s'), findsOneWidget);
      final scrolls = find.descendant(
          of: find.byType(CommandTimingView),
          matching: find.byType(SingleChildScrollView));
      // The test font draws every glyph as a full square, much wider than a
      // UI font, so only the widest card is guaranteed room for the bar.
      if (width >= 700) {
        expect(find.byType(TimingBar), findsNWidgets(2), reason: 'width $width');
        expect(scrolls, findsNothing);
        // The label keeps its full text when the numbers fit beside it.
        expect(tester.getSize(find.text('RETRACT')).width,
            greaterThanOrEqualTo(_naturalWidth(tester, 'RETRACT')));
      }
      if (width <= 120) expect(scrolls, findsOneWidget);
    }
  });

  for (final trend in [true, false]) {
    testWidgets(
        '${trend ? 'trend' : 'Pareto'} all-hidden selection is recoverable',
        (tester) async {
      await _pump(
          tester,
          trend
              ? const CycleTrendView(history: _history)
              : const StepParetoView(stats: _stats));
      for (final c in TimeClass.values) {
        await tester.tap(_chip(c));
        await tester.pumpAndSettle();
      }
      expect(find.text('Every time class is filtered out'), findsOneWidget);
      expect(find.byType(FilterChip), findsNWidgets(5));
      await tester.tap(find.text('Show all'));
      await tester.pumpAndSettle();
      expect(find.text('Every time class is filtered out'), findsNothing);
      for (final c in TimeClass.values) {
        expect(tester.widget<FilterChip>(_chip(c)).selected, isTrue);
      }
    });

    testWidgets(
        '${trend ? 'trend' : 'Pareto'} refresh retains present filters and releases absent ones',
        (tester) async {
      Widget chart(bool includeWaits) => trend
          ? CycleTrendView(
              history: includeWaits
                  ? _history
                  : const [
                      CycleSummary(
                          cycleNo: 3, total: _second, byClass: [_second]),
                      CycleSummary(
                          cycleNo: 4, total: _second, byClass: [_second]),
                    ])
          : StepParetoView(stats: includeWaits ? _stats : [_stats.first]);
      await _pump(tester, chart(true));
      await tester.tap(_chip(TimeClass.waitExternal));
      await tester.pumpAndSettle();
      await _pump(tester, chart(true));
      expect(tester.widget<FilterChip>(_chip(TimeClass.waitExternal)).selected,
          isFalse);
      await _pump(tester, chart(false));
      expect(_chip(TimeClass.waitExternal), findsNothing);
      expect(find.text('Show all'), findsNothing);
      await _pump(tester, chart(true));
      expect(tester.widget<FilterChip>(_chip(TimeClass.waitExternal)).selected,
          isTrue);
    });
  }
}

double _naturalWidth(WidgetTester tester, String text) {
  final context = tester.element(find.text(text));
  final painter = TextPainter(
      text: TextSpan(text: text, style: DefaultTextStyle.of(context).style),
      textDirection: TextDirection.ltr,
      textScaler: MediaQuery.textScalerOf(context))
    ..layout();
  final width = painter.width;
  painter.dispose();
  return width;
}

class _PaintCounter extends CustomPainter {
  int count = 0;
  @override
  void paint(Canvas canvas, Size size) {
    count++;
    canvas.drawRect(Offset.zero & size, Paint()..color = Colors.green);
  }
  @override
  bool shouldRepaint(_PaintCounter oldDelegate) => false;
}
