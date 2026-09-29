// Card tabs: every built-in data view is a flow of cards an administrator
// arranges - which cards, in what order, hidden or not, behind which level, in
// how many columns - and any tab can be the default one, which leads the row.
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:fraktal_hmi/content/content_store.dart';
import 'package:fraktal_hmi/content/module_content_controller.dart';
import 'package:fraktal_hmi/data/sim_repository.dart';
import 'package:fraktal_hmi/domain/types.dart';
import 'package:fraktal_hmi/localization/localization_controller.dart';
import 'package:fraktal_hmi/main.dart';
import 'package:fraktal_hmi/state/app_state.dart';
import 'package:fraktal_hmi/ui/flow_columns.dart';

void main() {
  group('card tab model', () {
    test('the Overview carries every card, with its own-tab ones hidden', () {
      const overview = ModuleTabDefinition(
          id: 'overview', title: 'o', kind: ModuleTabKind.overview);
      final cards = overview.effectiveCards;
      expect(cards.map((card) => card.kind), ModuleCardKind.values);
      for (final card in cards) {
        expect(card.hidden, ModuleCardKind.ownTab.contains(card.kind),
            reason: '${card.kind} on the Overview');
      }
      expect(overview.effectiveColumns, 2);
    });

    test('Hardware, Statistics and Events hold their own cards in one column',
        () {
      const hardware = ModuleTabDefinition(
          id: 'hardware', title: 'h', kind: ModuleTabKind.hardware);
      expect(hardware.effectiveCards.map((card) => card.kind), [
        ModuleCardKind.link,
        ModuleCardKind.safety,
        ModuleCardKind.systemHealth,
        ModuleCardKind.controlPower,
        ModuleCardKind.motion,
        ModuleCardKind.nameplate,
      ]);
      expect(hardware.effectiveColumns, 1);
      expect(
          const ModuleTabDefinition(
                  id: 'events', title: 'e', kind: ModuleTabKind.events)
              .effectiveCards
              .map((card) => card.kind),
          [ModuleCardKind.activeEvents, ModuleCardKind.history]);
    });

    test('cards, columns and the default flag survive the round trip', () {
      const tab = ModuleTabDefinition(
        id: 'statistics',
        title: 's',
        kind: ModuleTabKind.statistics,
        columns: 3,
        isDefault: true,
        cards: [
          ModuleCardPlacement(ModuleCardKind.oee),
          ModuleCardPlacement(ModuleCardKind.counters,
              hidden: true, requiredLevel: AccessLevel.technician),
        ],
      );
      final restored = ModuleTabDefinition.fromJson(tab.toJson())!;
      expect(restored.columns, 3);
      expect(restored.isDefault, isTrue);
      expect(restored.cards.map((card) => card.kind),
          [ModuleCardKind.oee, ModuleCardKind.counters]);
      expect(restored.cards.last.hidden, isTrue);
      expect(restored.cards.last.requiredLevel, AccessLevel.technician);
    });

    test('a picture stored on the Overview is dropped, not failed on', () {
      final restored = ModuleTabDefinition.fromJson({
        'id': 'overview',
        'title': 'o',
        'kind': 'overview',
        'requiredLevel': 'none',
        'background': {'imageBase64': 'AAAA', 'imageName': 'old.png'},
        'viewClass': 'maintenance',
      })!;
      expect(restored.background, isNull);
      expect(restored.viewClass, ModuleViewClass.operating);
    });

    test('a stored configuration card becomes the three data cards in place',
        () {
      final restored = ModuleTabDefinition.fromJson({
        'id': 'overview',
        'title': 'o',
        'kind': 'overview',
        'requiredLevel': 'none',
        'cards': [
          {'kind': 'oee'},
          {'kind': 'configuration', 'hidden': true, 'requiredLevel': 'engineer'},
          {'kind': 'counters'},
        ],
      })!;
      expect(restored.cards.map((card) => card.kind), [
        ModuleCardKind.oee,
        ModuleCardKind.modelData,
        ModuleCardKind.stationData,
        ModuleCardKind.lineData,
        ModuleCardKind.counters,
      ]);
      final data = restored.cards.where((card) => card.kind.configKind != null);
      expect(data.every((card) => card.hidden), isTrue);
      expect(data.every((card) => card.requiredLevel == AccessLevel.engineer),
          isTrue);
    });
  });

  group('tab order', () {
    ModuleContentController controller() => ModuleContentController(
          store: MemoryContentStore(),
          localization: LocalizationController(
              enabledLanguages: {'en'}, activeLanguage: 'en'),
        );
    const capabilities = ModuleTabCapabilities(unit: true);

    test('the stored order wins, and the default tab leads', () async {
      final content = controller();
      final tabs = content.tabsFor('StationA', capabilities).toList();
      final events = tabs.firstWhere((tab) => tab.id == 'events');
      final reordered = [
        for (final tab in tabs.reversed)
          tab.id == 'events' ? events.copyWith(isDefault: true) : tab,
      ];
      await content.setTabs('StationA', reordered);
      final ids = content.tabsFor('StationA', capabilities).map((t) => t.id);
      expect(ids.first, 'events', reason: 'the default tab leads');
      expect(ids.skip(1), [
        for (final tab in tabs.reversed)
          if (tab.id != 'events') tab.id,
      ], reason: 'the rest keep the order they were dragged into');
    });

    test('a built-in tab a stored layout predates is appended', () async {
      final content = controller();
      await content.setTabs('StationA', const [
        ModuleTabDefinition(
            id: 'overview', title: 'o', kind: ModuleTabKind.overview),
      ]);
      final ids = content.tabsFor('StationA', capabilities).map((t) => t.id);
      expect(ids.first, 'overview');
      expect(ids, containsAll(['hardware', 'statistics', 'events']));
    });

    test('two default tabs are refused', () async {
      final content = controller();
      expect(
        () => content.setTabs('StationA', const [
          ModuleTabDefinition(
              id: 'a', title: 'a', kind: ModuleTabKind.custom, isDefault: true),
          ModuleTabDefinition(
              id: 'b', title: 'b', kind: ModuleTabKind.custom, isDefault: true),
        ]),
        throwsFormatException,
      );
    });
  });

  testWidgets('a flow, not a grid: each card goes to the shortest column',
      (tester) async {
    Widget box(String key, double height) =>
        SizedBox(key: Key(key), height: height);
    await tester.pumpWidget(Directionality(
      textDirection: TextDirection.ltr,
      child: Align(
        alignment: Alignment.topLeft,
        child: SizedBox(
          width: 412,
          child: FlowColumns(columns: 2, gap: 12, children: [
            box('a', 100),
            box('b', 300),
            box('c', 50),
            box('empty', 0),
            box('d', 50),
          ]),
        ),
      ),
    ));
    Offset at(String key) => tester.getTopLeft(find.byKey(Key(key)));
    expect(at('a'), Offset.zero);
    expect(at('b'), const Offset(212, 0));
    expect(at('c'), const Offset(0, 112),
        reason: 'under the short card, not below the tall one');
    expect(at('d'), const Offset(0, 174),
        reason: 'an empty card takes no place and no gap');
    expect(tester.getSize(find.byType(FlowColumns)).height, 300);
  });

  testWidgets('the Overview flows its cards across two columns',
      (tester) async {
    tester.view.physicalSize = const Size(1800, 1200);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    final repo = SimRepository();
    final app = AppState(repo);
    await tester.pumpWidget(FraktalHmiApp(app: app));
    await tester.pump(const Duration(seconds: 2));
    expect(await repo.login('StationA', 'admin1', '2468'), isTrue);
    app.select('StationA');
    await tester.pump(const Duration(seconds: 1));

    final cards = find.byWidgetPredicate((widget) =>
        widget is KeyedSubtree &&
        widget.key is ValueKey<String> &&
        (widget.key! as ValueKey<String>).value.startsWith('module-card-'));
    expect(cards, findsWidgets);
    final lefts = {
      for (final element in cards.evaluate())
        tester.getTopLeft(find.byWidget(element.widget)).dx.round(),
    };
    expect(lefts, hasLength(2), reason: 'two columns on the Overview');
    expect(find.byKey(const ValueKey('module-card-modelData')), findsNothing,
        reason: 'configuration has its own tab and starts hidden here');
    app.dispose();
  });

  testWidgets('a tab with nothing to show is hidden, and back in edit mode',
      (tester) async {
    tester.view.physicalSize = const Size(1800, 1200);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    final repo = SimRepository();
    final app = AppState(repo);
    await tester.pumpWidget(FraktalHmiApp(app: app));
    await tester.pump(const Duration(seconds: 2));
    expect(await repo.login('StationA', 'admin1', '2468'), isTrue);
    app.select('StationA.Separator1');
    await tester.pump(const Duration(seconds: 1));

    List<String> tabs() => [
          for (final text in tester.widgetList<Text>(find.descendant(
              of: find.byType(TabBar), matching: find.byType(Text))))
            text.data ?? '',
        ];
    final shown = tabs();
    expect(shown, isNot(contains('Hardware')),
        reason: 'a separator publishes no hardware facet: nothing to show');
    await tester.tap(find.byKey(const Key('module-layout-edit-toggle')));
    await tester.pump(const Duration(milliseconds: 500));
    final editing = tabs();
    expect(editing, contains('Hardware'),
        reason: 'an ADMIN arranging tabs sees the empty ones too');
    expect(shown.every(editing.contains), isTrue);
    app.dispose();
  });
}
