// Controls placed on a tab's machine picture: the geometry that keeps them on
// the sensor they annotate, the bounded state rules that colour them, and the
// ADMIN drag-and-drop that places them.
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:fraktal_hmi/content/module_layout.dart';
import 'package:fraktal_hmi/data/sim_repository.dart';
import 'package:fraktal_hmi/domain/module_node.dart';
import 'package:fraktal_hmi/domain/types.dart';
import 'package:fraktal_hmi/localization/localization_controller.dart';
import 'package:fraktal_hmi/localization/localized_text.dart';
import 'package:fraktal_hmi/state/app_state.dart';
import 'package:fraktal_hmi/ui/app_theme.dart';
import 'package:fraktal_hmi/ui/background_canvas.dart';
import 'package:fraktal_hmi/ui/custom_module_tabs.dart';

// A 2x1 PNG (opaque), so the painted rect has a known aspect ratio.
const _png2x1 =
    'iVBORw0KGgoAAAANSUhEUgAAAAIAAAABCAYAAAD0In+KAAAADklEQVR4nGMQUDD4D8IACYMCv8+jTkgAAAAASUVORK5CYII=';

const _door = ModuleControlDefinition(
  id: 'door1',
  kind: ModuleControlKind.shape,
  label: 'Door 1',
  bindings: ['OutImm/DoorClosed', 'OutImm/DoorFaulted'],
  rules: [
    ModuleStateRule(
        bindingIndex: 1,
        compare: ModuleCompare.isTrue,
        token: ModuleStateToken.error),
    ModuleStateRule(
        bindingIndex: 0,
        compare: ModuleCompare.isTrue,
        token: ModuleStateToken.ok),
  ],
  defaultToken: ModuleStateToken.warning,
  placement: ModulePlacement(x: 0.1, y: 0.2, width: 0.2, height: 0.4),
);

void main() {
  group('painted image geometry', () {
    test(
        'contain letterboxes: positions are relative to the image, not the box',
        () {
      final rect = paintedImageRect(
        imageSize: const Size(200, 100),
        box: const Rect.fromLTWH(0, 0, 400, 400),
        fit: BoxFit.contain,
        alignment: Alignment.center,
      );
      expect(rect, const Rect.fromLTWH(0, 100, 400, 200));
      // The image's centre is the box's centre, not (200, 200) of a grid cell
      // that drifts with the letterbox.
      expect(
        placementRect(
          const ModulePlacement(x: 0.5, y: 0.5, width: 0.1, height: 0.1),
          rect,
        ).topLeft,
        const Offset(200, 200),
      );
    });

    test('cover crops: the whole image rect extends past the box', () {
      final rect = paintedImageRect(
        imageSize: const Size(200, 100),
        box: const Rect.fromLTWH(0, 0, 400, 400),
        fit: BoxFit.cover,
        alignment: Alignment.center,
      );
      expect(rect, const Rect.fromLTWH(-200, 0, 800, 400));
    });

    test('a drop centres the control on the pointer, kept inside the image',
        () {
      const image = Rect.fromLTWH(0, 100, 400, 200);
      final placed = placementCenteredAt(const Offset(200, 200), image,
          width: 0.1, height: 0.2);
      expect(placed.x, closeTo(0.45, 1e-9));
      expect(placed.y, closeTo(0.4, 1e-9));
      final corner = placementCenteredAt(const Offset(0, 100), image,
          width: 0.1, height: 0.2);
      expect(corner.x, 0);
      expect(corner.y, 0);
    });
  });

  group('state rules', () {
    test('first matching rule wins, else the default', () {
      expect(_door.resolveState([true, false]), ModuleStateToken.ok);
      expect(_door.resolveState([false, false]), ModuleStateToken.warning);
      expect(_door.resolveState([true, true]), ModuleStateToken.error,
          reason: 'a faulted door is red even while it reads closed');
    });

    test('comparisons are numeric; text never claims a state', () {
      const high = ModuleStateRule(compare: ModuleCompare.above, constant: 80);
      expect(high.matches(81), isTrue);
      expect(high.matches('90.5'), isTrue);
      expect(high.matches(80), isFalse);
      expect(high.matches('OK'), isFalse);
      expect(
          const ModuleStateRule(compare: ModuleCompare.isFalse).matches(false),
          isTrue);
    });

    test('a layout survives export, and a rule past its bindings is refused',
        () {
      final restored = ModuleControlDefinition.fromJson(_door.toJson())!;
      expect(restored.rules, hasLength(2));
      expect(restored.rules.first.token, ModuleStateToken.error);
      expect(restored.placement, _door.placement);
      expect(restored.resolveState([false, false]), ModuleStateToken.warning);

      final json = _door.toJson()
        ..['bindings'] = ['OutImm/DoorClosed']
        ..['binding'] = 'OutImm/DoorClosed';
      expect(ModuleControlDefinition.fromJson(json), isNull,
          reason: 'half-applying the rules would drop the fault rule');
    });

    test('a placement is kept inside the image', () {
      final placement = ModulePlacement.fromJson(
          {'x': 0.95, 'y': -1, 'width': 0.2, 'height': 0.0})!;
      expect(placement.x + placement.width, lessThanOrEqualTo(1));
      expect(placement.y, 0);
      expect(placement.height, ModulePlacement.minSize);
      expect(ModulePlacement.fromJson({'x': 'a'}), isNull);
    });
  });

  group('on the picture', () {
    late AppState app;
    late LocalizationController localization;

    setUp(() {
      app = AppState(SimRepository());
      localization = LocalizationController(
          enabledLanguages: {'en'}, activeLanguage: 'en');
    });
    tearDown(() => app.dispose());

    Future<void> mount(
      WidgetTester tester, {
      required Map<String, Object?> values,
      required List<ModuleControlDefinition> controls,
      bool editing = false,
      void Function(String, ModulePlacement?)? onPlace,
      void Function(ModuleControlKind, ModulePlacement)? onAddAt,
      void Function(int, int)? onReorder,
      bool picture = true,
      bool reduceMotion = false,
      Map<String, ModuleCondition> layerConditions = const {},
      ModuleGrid? grid,
      void Function(ModuleGrid)? onGrid,
    }) async {
      await tester.binding.setSurfaceSize(const Size(1000, 600));
      addTearDown(() => tester.binding.setSurfaceSize(null));
      final node = ModuleNode(
        path: 'Press.Guard',
        name: 'Guard',
        type: ModuleType.equipmentModule,
        publishedValues: values,
      );
      await tester.pumpWidget(LocalizationScope(
        controller: localization,
        child: MaterialApp(
          builder: (context, child) => MediaQuery(
            data: MediaQuery.of(context)
                .copyWith(disableAnimations: reduceMotion),
            child: child!,
          ),
          home: Scaffold(
            body: CustomModuleTabView(
              app: app,
              node: node,
              editing: editing,
              tab: ModuleTabDefinition(
                id: 'guards',
                title: 'Guards',
                kind: ModuleTabKind.custom,
                controls: controls,
                background: picture
                    ? const ModuleTabBackground(imageBase64: _png2x1)
                    : null,
                layerConditions: layerConditions,
                grid: grid,
              ),
              onPlaceControl: onPlace,
              onAddControlAt: onAddAt,
              onReorderControl: onReorder,
              onGridChanged: onGrid,
            ),
          ),
        ),
      ));
      // The image decodes outside the fake clock; the overlay waits for its size.
      await tester.runAsync(
          () => Future<void>.delayed(const Duration(milliseconds: 200)));
      await tester.pump();
      await tester.pump();
    }

    testWidgets('a door takes the colour of its first matching rule',
        (tester) async {
      await mount(tester,
          values: {'OutImm/DoorClosed': true, 'OutImm/DoorFaulted': false},
          controls: [_door]);
      expect(find.byTooltip('Door 1: OK'), findsOneWidget);

      await mount(tester,
          values: {'OutImm/DoorClosed': true, 'OutImm/DoorFaulted': true},
          controls: [_door]);
      expect(find.byTooltip('Door 1: Fault'), findsOneWidget);
    });

    testWidgets('missing data renders unavailable, never a state',
        (tester) async {
      await mount(tester,
          values: {'OutImm/DoorClosed': true}, controls: [_door]);
      expect(find.byTooltip('Door 1: UNAVAILABLE'), findsOneWidget);
      expect(find.byTooltip('Door 1: OK'), findsNothing);
    });

    testWidgets('the control sits on the painted image, not on the tab',
        (tester) async {
      await mount(tester,
          values: {'OutImm/DoorClosed': true, 'OutImm/DoorFaulted': false},
          controls: [_door]);
      // 1000x600 tab, 2:1 image, contain: painted 1000x500 at y=50.
      final rect = tester.getRect(find.byTooltip('Door 1: OK'));
      expect(rect.left, closeTo(100, 0.5));
      expect(rect.top, closeTo(50 + 0.2 * 500, 0.5));
      expect(rect.width, closeTo(200, 0.5));
      expect(rect.height, closeTo(200, 0.5));
    });

    testWidgets('dragging a placed control moves it by the image fraction',
        (tester) async {
      String? movedId;
      ModulePlacement? moved;
      await mount(
        tester,
        values: {'OutImm/DoorClosed': true, 'OutImm/DoorFaulted': false},
        controls: [_door],
        editing: true,
        onPlace: (id, placement) {
          movedId = id;
          moved = placement;
        },
      );
      await tester.drag(
          find.byKey(const ValueKey('placed-door1')), const Offset(68, 0));
      await tester.pump();
      expect(movedId, 'door1');
      // Editing leaves 680 px beside the 320 px panel: painted 680 wide.
      expect(moved!.x, closeTo(0.1 + 68 / 680, 0.02));
      expect(moved!.y, closeTo(0.2, 1e-9));
    });

    testWidgets('a control dragged from the palette lands where it is dropped',
        (tester) async {
      ModuleControlKind? kind;
      ModulePlacement? at;
      await mount(
        tester,
        values: const {},
        controls: const [],
        editing: true,
        onAddAt: (k, placement) {
          kind = k;
          at = placement;
        },
      );
      final source =
          tester.getCenter(find.byKey(const ValueKey('palette-level')));
      // Canvas: 680 x 600, painted 680 x 340 at y = 130. Drop at its centre.
      final gesture = await tester.startGesture(source);
      await gesture.moveBy(const Offset(-20, 0));
      await tester.pump();
      await gesture.moveTo(const Offset(340, 300));
      await tester.pump();
      await gesture.up();
      await tester.pump();
      expect(kind, ModuleControlKind.level);
      expect(at!.x + at!.width / 2, closeTo(0.5, 0.01));
      expect(at!.y + at!.height / 2, closeTo(0.5, 0.01));
    });
    testWidgets('a bound enabled disables - and missing data disables too',
        (tester) async {
      const stop = ModuleControlDefinition(
        id: 'stop',
        kind: ModuleControlKind.button,
        label: 'Stop',
        action: ModuleActionKind.unitStop,
        confirmation: ModuleActionConfirmation.none,
        enabledWhen: ModuleCondition(binding: 'OutImm/Safe'),
      );
      bool enabled() => tester
              .widget<FilledButton>(find.ancestor(
                  of: find.text('Stop'), matching: find.byType(FilledButton)))
              .onPressed !=
          null;
      await mount(tester,
          values: {'OutImm/Safe': true}, controls: [stop], picture: false);
      expect(enabled(), isTrue);
      await mount(tester,
          values: {'OutImm/Safe': false}, controls: [stop], picture: false);
      expect(enabled(), isFalse);
      await mount(tester, values: const {}, controls: [stop], picture: false);
      expect(enabled(), isFalse,
          reason: 'Bad/Uncertain or missing data never enables an input');
    });

    testWidgets('a layer chip hides and shows its whole set', (tester) async {
      const lamp = ModuleControlDefinition(
        id: 'lamp',
        kind: ModuleControlKind.indicator,
        label: 'Part',
        bindings: ['OutImm/Part'],
        layer: 'Sensors',
        placement: ModulePlacement(x: 0.5, y: 0.5, width: 0.05, height: 0.1),
      );
      await mount(tester,
          values: {'OutImm/Part': true},
          controls: [_door.withPlacement(_door.placement), lamp]);
      expect(find.byTooltip('Part: ON'), findsOneWidget);
      await tester.tap(find.byKey(const ValueKey('layer-Sensors')));
      await tester.pump();
      expect(find.byTooltip('Part: ON'), findsNothing);
      await tester.tap(find.byKey(const ValueKey('layer-Sensors')));
      await tester.pump();
      expect(find.byTooltip('Part: ON'), findsOneWidget);
    });

    testWidgets('a bound layer follows its tag - never hidden on missing data',
        (tester) async {
      const lamp = ModuleControlDefinition(
        id: 'lamp',
        kind: ModuleControlKind.indicator,
        label: 'Part',
        bindings: ['OutImm/Part'],
        layer: 'Sensors',
        placement: ModulePlacement(x: 0.5, y: 0.5, width: 0.05, height: 0.1),
      );
      const shown = {'Sensors': ModuleCondition(binding: 'OutImm/Service')};
      await mount(tester,
          values: {'OutImm/Part': true, 'OutImm/Service': false},
          controls: [lamp],
          layerConditions: shown);
      expect(find.byTooltip('Part: ON'), findsNothing);
      await mount(tester,
          values: {'OutImm/Part': true, 'OutImm/Service': true},
          controls: [lamp],
          layerConditions: shown);
      expect(find.byTooltip('Part: ON'), findsOneWidget);
      await mount(tester,
          values: {'OutImm/Part': true},
          controls: [lamp],
          layerConditions: shown);
      expect(find.byTooltip('Part: ON'), findsOneWidget,
          reason: 'unavailable data never hides a layer');
    });

    testWidgets('a state shows its icon, turns with its value, and dims',
        (tester) async {
      const valve = ModuleControlDefinition(
        id: 'valve',
        kind: ModuleControlKind.shape,
        label: 'Valve',
        bindings: ['OutImm/Locked'],
        rules: [
          ModuleStateRule(token: ModuleStateToken.warning, glyph: ModuleGlyph.lock),
        ],
        defaultToken: ModuleStateToken.ok,
        defaultGlyph: ModuleGlyph.check,
        rotation: ModuleRotation(binding: 'OutImm/Opening', maxDegrees: 90),
        dimmedWhen: ModuleCondition(binding: 'OutImm/OutOfService'),
        placement: ModulePlacement(x: 0.4, y: 0.4, width: 0.1, height: 0.2),
      );
      await mount(tester, values: {
        'OutImm/Locked': true,
        'OutImm/Opening': 50,
        'OutImm/OutOfService': false,
      }, controls: [
        valve
      ]);
      expect(find.byKey(const ValueKey('glyph-lock')), findsOneWidget);
      final turned = tester.widget<Transform>(find
          .ancestor(
              of: find.byKey(const ValueKey('glyph-lock')),
              matching: find.byType(Transform))
          .first);
      // 50 of 0..100 -> 45 degrees: the rotation matrix's cos term.
      expect(turned.transform.entry(0, 0), closeTo(0.7071, 1e-3));
      expect(
          find.ancestor(
              of: find.byKey(const ValueKey('glyph-lock')),
              matching: find.byType(Opacity)),
          findsNothing);
      await mount(tester, values: {
        'OutImm/Locked': false,
        'OutImm/Opening': 50,
        'OutImm/OutOfService': true,
      }, controls: [
        valve
      ]);
      expect(find.byKey(const ValueKey('glyph-check')), findsOneWidget,
          reason: 'the default state has its own icon');
      expect(
          tester
              .widget<Opacity>(find.ancestor(
                  of: find.byKey(const ValueKey('glyph-check')),
                  matching: find.byType(Opacity)))
              .opacity,
          ModuleControlDefinition.dimmedOpacity);
    });

    testWidgets('a grid places controls by fraction; a scale variant reflows',
        (tester) async {
      const a = ModuleControlDefinition(
          id: 'a', kind: ModuleControlKind.text, label: 'Alpha');
      const b = ModuleControlDefinition(
          id: 'b', kind: ModuleControlKind.text, label: 'Beta');
      const c = ModuleControlDefinition(
          id: 'c', kind: ModuleControlKind.text, label: 'Gamma');
      const grid = ModuleGrid(
        base: ModuleGridLayout(columns: 4, rows: 2, cells: {
          'a': ModuleGridCell(column: 0, row: 0),
          'b': ModuleGridCell(column: 2, row: 1, columnSpan: 2),
        }),
        variants: {
          'large': ModuleGridLayout(columns: 1, rows: 2, cells: {
            'a': ModuleGridCell(column: 0, row: 0),
            'b': ModuleGridCell(column: 0, row: 1),
          }),
        },
      );
      app.controlScale = ControlScale.medium;
      await mount(tester,
          values: const {}, controls: [a, b, c], picture: false, grid: grid);
      final ra = tester.getRect(find.byKey(const ValueKey('grid-cell-a')));
      final rb = tester.getRect(find.byKey(const ValueKey('grid-cell-b')));
      expect(rb.width, closeTo(ra.width * 2, 0.5), reason: 'spans two columns');
      expect(rb.left - ra.left, closeTo(ra.width * 2, 0.5),
          reason: 'column 2 of 4 starts half way across');
      expect(rb.top, greaterThan(ra.top), reason: 'row 1 is below row 0');
      expect(find.byKey(const ValueKey('grid-cell-c')), findsNothing);
      expect(find.text('Gamma'), findsOneWidget,
          reason: 'a control without a cell is listed beneath the grid');

      app.controlScale = ControlScale.large;
      await mount(tester,
          values: const {}, controls: [a, b, c], picture: false, grid: grid);
      final la = tester.getRect(find.byKey(const ValueKey('grid-cell-a')));
      final lb = tester.getRect(find.byKey(const ValueKey('grid-cell-b')));
      expect(lb.left, closeTo(la.left, 0.5),
          reason: 'the large-scale variant stacks them in one column');
      app.controlScale = ControlScale.medium;
    });

    testWidgets('editing a grid cell reports the new grid', (tester) async {
      const a = ModuleControlDefinition(
          id: 'a', kind: ModuleControlKind.text, label: 'Alpha');
      ModuleGrid? changed;
      await mount(tester,
          values: const {},
          controls: [a],
          picture: false,
          editing: true,
          grid: const ModuleGrid(
              base: ModuleGridLayout(columns: 4, rows: 2)),
          onGrid: (grid) => changed = grid);
      await tester.tap(find.byKey(const ValueKey('grid-unplaced-a')));
      await tester.tap(find.text('Place'));
      await tester.pumpAndSettle();
      await tester.enterText(
          find.byKey(const ValueKey('grid-cell-std.module.grid.column')), '3');
      await tester.enterText(
          find.byKey(const ValueKey('grid-cell-std.module.grid.columnSpan')),
          '2');
      await tester.tap(find.byKey(const ValueKey('grid-cell-save')));
      await tester.pumpAndSettle();
      expect(changed!.base.cells['a'],
          const ModuleGridCell(column: 2, row: 0, columnSpan: 2));
    });

    testWidgets('a bound visible hides - but never on missing data',
        (tester) async {
      const guarded = ModuleControlDefinition(
        id: 'hint',
        kind: ModuleControlKind.text,
        label: 'Door open',
        visibleWhen: ModuleCondition(
            binding: 'OutImm/DoorClosed', compare: ModuleCompare.isFalse),
        placement: ModulePlacement(x: 0.1, y: 0.1, width: 0.2, height: 0.1),
      );
      await mount(tester,
          values: {'OutImm/DoorClosed': true}, controls: [guarded]);
      expect(find.byTooltip('Door open'), findsNothing);
      await mount(tester,
          values: {'OutImm/DoorClosed': false}, controls: [guarded]);
      expect(find.byTooltip('Door open'), findsOneWidget);
      await mount(tester, values: const {}, controls: [guarded]);
      expect(find.byTooltip('Door open'), findsOneWidget,
          reason: 'unavailable data never hides an indicator');
    });

    testWidgets('a blinking rule flashes, and holds steady on reduced motion',
        (tester) async {
      const estop = ModuleControlDefinition(
        id: 'estop',
        kind: ModuleControlKind.shape,
        label: 'E-stop',
        shape: ModuleShape.circle,
        bindings: ['OutImm/EStop'],
        rules: [ModuleStateRule(token: ModuleStateToken.error, blink: true)],
        defaultToken: ModuleStateToken.ok,
        placement: ModulePlacement(x: 0.4, y: 0.4, width: 0.1, height: 0.2),
      );
      Finder flashing() => find.descendant(
          of: find.byTooltip('E-stop: Fault'),
          matching: find.byType(FadeTransition));
      await mount(tester, values: {'OutImm/EStop': true}, controls: [estop]);
      expect(flashing(), findsOneWidget);
      await mount(tester,
          values: {'OutImm/EStop': true},
          controls: [estop],
          reduceMotion: true);
      expect(flashing(), findsNothing);
      await mount(tester, values: {'OutImm/EStop': false}, controls: [estop]);
      expect(
          find.descendant(
              of: find.byTooltip('E-stop: OK'),
              matching: find.byType(FadeTransition)),
          findsNothing);
    });

    testWidgets('an operating view draws OK neutral, not green (7.4)',
        (tester) async {
      await mount(tester,
          values: {'OutImm/DoorClosed': true, 'OutImm/DoorFaulted': false},
          controls: [_door.withPlacement(null)],
          picture: false);
      final context = tester.element(find.byType(CustomModuleTabView));
      final borders = tester
          .widgetList<DecoratedBox>(find.byType(DecoratedBox))
          .map((box) => box.decoration)
          .whereType<BoxDecoration>()
          .map((decoration) => decoration.border?.top.color)
          .toList();
      expect(borders,
          contains(stateTokenColor(context, ModuleStateToken.neutral)));
      expect(borders,
          isNot(contains(stateTokenColor(context, ModuleStateToken.ok))));
    });

    testWidgets('front and back restack by control order (7.2 z-order)',
        (tester) async {
      (int, int)? moved;
      const other = ModuleControlDefinition(
        id: 'other',
        kind: ModuleControlKind.text,
        label: 'Other',
        placement: ModulePlacement(x: 0.6, y: 0.6, width: 0.2, height: 0.1),
      );
      await mount(tester,
          values: {'OutImm/DoorClosed': true, 'OutImm/DoorFaulted': false},
          controls: [_door, other],
          editing: true,
          onReorder: (from, to) => moved = (from, to));
      await tester.tap(find.byKey(const ValueKey('placed-door1')));
      await tester.pump();
      await tester.tap(find.byTooltip('Bring to front'));
      expect(moved, (0, 1));
    });
  });

  test('a bound enabled travels in the layout and counts as a read', () {
    const control = ModuleControlDefinition(
      id: 'b',
      kind: ModuleControlKind.button,
      action: ModuleActionKind.unitStop,
      enabledWhen: ModuleCondition(
          binding: 'OutImm/Safe', compare: ModuleCompare.equals, constant: 1),
    );
    final restored = ModuleControlDefinition.fromJson(control.toJson())!;
    expect(restored.enabledWhen!.binding, 'OutImm/Safe');
    expect(restored.enabledWhen!.matches(1), isTrue);
    expect(restored.boundReads, 1);
  });

  test('layer, visible and blink travel in the layout and count as reads', () {
    const control = ModuleControlDefinition(
      id: 'c',
      kind: ModuleControlKind.shape,
      bindings: ['OutImm/A'],
      rules: [ModuleStateRule(token: ModuleStateToken.error, blink: true)],
      layer: 'Sensors',
      visibleWhen: ModuleCondition(
          binding: 'OutImm/B', compare: ModuleCompare.above, constant: 3),
    );
    final restored = ModuleControlDefinition.fromJson(control.toJson())!;
    expect(restored.layer, 'Sensors');
    expect(restored.visibleWhen!.binding, 'OutImm/B');
    expect(restored.visibleWhen!.matches(4), isTrue);
    expect(restored.rules.single.blink, isTrue);
    expect(restored.boundReads, 2, reason: 'the visible binding is a read too');
  });

  test('a rotation maps its range onto the angles, clamped at both ends', () {
    const rotation = ModuleRotation(
        binding: 'OutImm/A', minimum: 0, maximum: 100, minDegrees: 0, maxDegrees: 90);
    expect(rotation.degreesFor(50), 45);
    expect(rotation.degreesFor(-10), 0);
    expect(rotation.degreesFor(250), 90);
    expect(rotation.degreesFor('text'), 0, reason: 'text never turns a shape');
    expect(
        ModuleRotation.fromJson(
            {...rotation.toJson(), 'minimum': 100, 'maximum': 0}),
        isNull,
        reason: 'an empty range is refused, not divided by');
  });

  test('icon, rotation and dimming travel in the layout and count as reads', () {
    const control = ModuleControlDefinition(
      id: 'c',
      kind: ModuleControlKind.shape,
      bindings: ['OutImm/A'],
      rules: [ModuleStateRule(token: ModuleStateToken.error, glyph: ModuleGlyph.stop)],
      defaultGlyph: ModuleGlyph.play,
      rotation: ModuleRotation(binding: 'OutImm/B', maxDegrees: 180),
      dimmedWhen: ModuleCondition(binding: 'OutImm/C'),
    );
    final restored = ModuleControlDefinition.fromJson(control.toJson())!;
    expect(restored.rules.single.glyph, ModuleGlyph.stop);
    expect(restored.defaultGlyph, ModuleGlyph.play);
    expect(restored.rotation!.maxDegrees, 180);
    expect(restored.dimmedWhen!.binding, 'OutImm/C');
    expect(restored.glyphFor([true]), ModuleGlyph.stop);
    expect(restored.glyphFor([false]), ModuleGlyph.play);
    expect(restored.boundReads, 3);
  });

  test('a view declares its layers and budget; a budget only lowers', () {
    const tab = ModuleTabDefinition(
      id: 't',
      title: 'T',
      kind: ModuleTabKind.custom,
      controls: [
        ModuleControlDefinition(
            id: 'c', kind: ModuleControlKind.value, bindings: ['OutImm/A'], layer: 'L'),
      ],
      layerConditions: {'L': ModuleCondition(binding: 'OutImm/Show')},
      readBudget: 40,
    );
    final restored = ModuleTabDefinition.fromJson(tab.toJson())!;
    expect(restored.layerConditions['L']!.binding, 'OutImm/Show');
    expect(restored.effectiveReadBudget, 40);
    expect(restored.boundReads, 2, reason: 'a layer condition is a read');
    final raised = ModuleTabDefinition.fromJson({...tab.toJson(), 'readBudget': 500})!;
    expect(raised.effectiveReadBudget, ModuleTabDefinition.maxBoundReads,
        reason: 'a declaration never raises the standard');
  });

  group('grid container', () {
    test('cells are fractions of the grid, and must lie inside it', () {
      const cell = ModuleGridCell(column: 1, row: 2, columnSpan: 2, rowSpan: 1);
      final f = cell.fractionIn(4, 4);
      expect((f.x, f.y, f.width, f.height), (0.25, 0.5, 0.5, 0.25));
      expect(cell.fits(4, 4), isTrue);
      expect(cell.fits(2, 4), isFalse);
    });

    test('shrinking a grid takes off the cells that no longer fit', () {
      const layout = ModuleGridLayout(columns: 4, rows: 4, cells: {
        'in': ModuleGridCell(column: 0, row: 0),
        'out': ModuleGridCell(column: 3, row: 0),
      });
      final smaller = layout.copyWith(columns: 2);
      expect(smaller.cells.keys, ['in']);
    });

    test('a grid travels in the layout; bad cells and scales are dropped', () {
      const tab = ModuleTabDefinition(
        id: 't',
        title: 'T',
        kind: ModuleTabKind.custom,
        controls: [
          ModuleControlDefinition(id: 'a', kind: ModuleControlKind.text),
        ],
        grid: ModuleGrid(
          base: ModuleGridLayout(columns: 3, rows: 2, cells: {
            'a': ModuleGridCell(column: 1, row: 1),
          }),
          variants: {'compact': ModuleGridLayout(columns: 1, rows: 3)},
        ),
      );
      final json = tab.toJson();
      final restored = ModuleTabDefinition.fromJson(json)!;
      expect(restored.grid!.base.cells['a'], const ModuleGridCell(column: 1, row: 1));
      expect(restored.grid!.layoutFor('compact').columns, 1);
      expect(restored.grid!.layoutFor('large').columns, 3,
          reason: 'a scale without a variant uses the base');

      final grid = (json['grid'] as Map).cast<String, Object?>();
      final base = (grid['base'] as Map).cast<String, Object?>();
      final tampered = ModuleTabDefinition.fromJson({
        ...json,
        'grid': {
          'base': {
            ...base,
            'cells': {
              'a': {'column': 5, 'row': 0},
              'ghost': {'column': 0, 'row': 0},
            },
          },
          'variants': {'huge': base},
        },
      })!;
      expect(tampered.grid!.base.cells, isEmpty,
          reason: 'a cell outside the grid, or for no control, is dropped');
      expect(tampered.grid!.variants, isEmpty,
          reason: 'variants key only to the control-scale presets');

      final pictured = ModuleTabDefinition.fromJson({
        ...json,
        'background': const ModuleTabBackground(imageBase64: _png2x1).toJson(),
        'viewClass': 'maintenance',
      })!;
      expect(pictured.grid, isNull, reason: 'a picture view places on its picture');
    });
  });
}
