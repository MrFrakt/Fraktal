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
              ),
              onPlaceControl: onPlace,
              onAddControlAt: onAddAt,
              onReorderControl: onReorder,
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
}
