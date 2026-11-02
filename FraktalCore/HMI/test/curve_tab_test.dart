// Modules ST_CurveRecord - the Curve tab draws the last judged curve read-only,
// in every theme, and asks for the record only while it is the open tab.
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:fraktal_hmi/data/sim_repository.dart';
import 'package:fraktal_hmi/domain/module_node.dart';
import 'package:fraktal_hmi/domain/types.dart';
import 'package:fraktal_hmi/localization/localization_controller.dart';
import 'package:fraktal_hmi/localization/localized_text.dart';
import 'package:fraktal_hmi/main.dart';
import 'package:fraktal_hmi/state/app_state.dart';
import 'package:fraktal_hmi/ui/app_theme.dart';
import 'package:fraktal_hmi/ui/curve_view.dart';

const _nok = CurveFacet(
  loaded: true,
  sampleCount: 3,
  truncated: true,
  samples: [CurvePoint(0, 0), CurvePoint(1, 12), CurvePoint(2, 30)],
  windows: [
    CurveWindow(0.5, 1.5, 5, 15, passed: true),
    CurveWindow(1.5, 2.5, 5, 15),
  ],
  envelopes: [
    CurveEnvelope(
        upper: true,
        points: [CurvePoint(0, 20), CurvePoint(2, 20)],
        cutIndex: 3),
  ],
  complete: true,
  verdict: Verdict.nok,
  reason: 'std.error.curveWindowViolated',
  judgedSamples: 300,
);

Widget _host(int theme, ModuleNode node) {
  final localization =
      LocalizationController(enabledLanguages: {'en'}, activeLanguage: 'en');
  return MaterialApp(
    key: ValueKey(theme),
    theme: themeAt(theme),
    home: LocalizationScope(
      controller: localization,
      child: Scaffold(body: CurveModuleTab(node: node)),
    ),
  );
}

ModuleNode _sealer(CurveFacet? curve) => ModuleNode(
    path: 'Packer.Sealer',
    name: 'Sealer',
    type: ModuleType.controlModule,
    curve: curve);

void main() {
  testWidgets('a judged curve draws with its verdict and legend in every theme',
      (tester) async {
    for (var i = 0; i < kThemes.length; i++) {
      await tester.pumpWidget(_host(i, _sealer(_nok)));
      await tester.pump();
      expect(tester.takeException(), isNull, reason: kThemes[i].nameKey);
      expect(
          find.descendant(
              of: find.byType(CurveModuleTab),
              matching: find.byWidgetPredicate((widget) =>
                  widget is CustomPaint && widget.painter is CurvePainter)),
          findsOneWidget);
      expect(find.text('NOK'), findsOneWidget);
      expect(find.text('Window passed'), findsOneWidget);
      expect(find.text('Window failed'), findsOneWidget);
      expect(find.text('3 samples shown, 300 judged'), findsOneWidget);
      expect(find.textContaining('Only the first 3 samples'), findsOneWidget);
    }
  });

  testWidgets('a record not yet read says so, and none at all says that',
      (tester) async {
    await tester.pumpWidget(_host(0, _sealer(const CurveFacet(sampleCount: 3))));
    expect(find.text('Reading the last curve…'), findsOneWidget);
    await tester.pumpWidget(_host(0, _sealer(null)));
    expect(find.text('No curve record is published.'), findsOneWidget);
  });

  testWidgets('the Curve tab demands the record only while it is open',
      (tester) async {
    tester.view.physicalSize = const Size(1800, 1200);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    final repo = _DemandRepository();
    final app = AppState(repo);
    await tester.pumpWidget(FraktalHmiApp(app: app));
    await tester.pump(const Duration(seconds: 2));
    expect(await repo.login('PackerC', 'admin1', '2468'), isTrue);
    app.select('PackerC.Sealer');
    await tester.pump(const Duration(seconds: 1));
    expect(repo.containers, isNot(contains('Curve')));
    await tester.tap(find.descendant(
        of: find.byType(TabBar), matching: find.text('Curve')));
    await tester.pump();
    expect(repo.containers, {'Curve'});
    expect(find.byType(CurveModuleTab), findsOneWidget);
    app.dispose();
  });
}

class _DemandRepository extends SimRepository {
  Set<String>? containers;
  @override
  void setModuleDetailActive(String rootPath, bool active,
      {Set<String>? containers}) {
    this.containers = containers == null ? null : Set.of(containers);
  }
}
