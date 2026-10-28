import 'dart:async';
import 'dart:ui' as ui;
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:fraktal_hmi/content/content_store.dart';
import 'package:fraktal_hmi/content/module_content_controller.dart';
import 'package:fraktal_hmi/data/sim_repository.dart';
import 'package:fraktal_hmi/data/scoped_plc_repository.dart';
import 'package:fraktal_hmi/domain/fieldbus.dart';
import 'package:fraktal_hmi/domain/module_node.dart';
import 'package:fraktal_hmi/domain/types.dart';
import 'package:fraktal_hmi/localization/localization_controller.dart';
import 'package:fraktal_hmi/localization/localized_text.dart';
import 'package:fraktal_hmi/main.dart';
import 'package:fraktal_hmi/state/app_state.dart';
import 'package:fraktal_hmi/ui/app_theme.dart';
import 'package:fraktal_hmi/ui/io_signal_led.dart';
import 'package:fraktal_hmi/ui/module_io_signals.dart';
import 'package:fraktal_hmi/ui/theme_chrome.dart';

IoChannel signal(String name, ChannelDir dir, bool value,
        {String owner = 'Press.Feeder',
        bool quality = true,
        bool forced = false,
        bool fault = false,
        ChannelKind kind = ChannelKind.digital,
        double analog = 0,
        String description = ''}) =>
    IoChannel(
        name: name,
        descriptionKey: description,
        address: 'EL1809 Ch1',
        path: 'Press.IO.$name',
        modulePath: owner,
        dir: dir,
        kind: kind,
        boolValue: value,
        analogValue: analog,
        unit: 'bar',
        quality: quality,
        forced: forced,
        faultActive: fault,
        diagnosticKey: fault ? 'Sensor fault' : '',
        forceable: true);

List<BusNode> bus(List<IoChannel> channels,
        {bool healthy = true, bool mapping = true}) =>
    [
      BusNode(
          name: 'EtherCAT',
          typeId: 'Master',
          address: '0',
          mappingValid: mapping,
          state: healthy ? NodeState.operational : NodeState.fault,
          linkOk: healthy,
          children: [
            BusNode(
                name: 'EL1809', typeId: 'DI', address: '1', channels: channels)
          ])
    ];

class ManualIoRepository extends SimRepository {
  final root = ModuleNode(
      name: 'Press',
      path: 'Press',
      type: ModuleType.unit,
      modeActive: UnitMode.manual,
      access: AccessSession(
          level: AccessLevel.operator,
          required: List.filled(GatedAction.values.length, AccessLevel.none)),
      children: [
        const ModuleNode(
            name: 'Feeder',
            path: 'Press.Feeder',
            type: ModuleType.controlModule,
            typeKey: 'std.moduleType.cylinder',
            commands: const [
              CommandInfo(1, 'Move to work position'),
              CommandInfo(2, 'Move to base position')
            ])
      ]);
  String? ioModule;
  int manualWrites = 0;
  @override
  Stream<List<ModuleNode>> forest() => Stream.value([root]);
  @override
  Stream<List<BusNode>> fieldbus() => Stream.value(bus([
        signal('_101B301B', ChannelDir.input, true,
            description: 'Feeder Extended'),
        signal('_101B301A', ChannelDir.input, false,
            description: 'Feeder Retracted'),
        signal('_101K301B', ChannelDir.output, true,
            description: 'Feeder Forward'),
        signal('_101K301A', ChannelDir.output, false,
            description: 'Feeder Backward'),
        signal('Other', ChannelDir.input, true, owner: 'Press.Feeder2'),
      ]));
  @override
  void setModuleIoViewActive(String? modulePath) {
    ioModule = modulePath;
  }

  @override
  Future<bool> manualCommand(
      String unitPath, String targetPath, int value) async {
    manualWrites++;
    return true;
  }
}

void main() {
  testWidgets(
      'manual card displays exact-owner Inputs/Outputs and withdraws hidden-tab demand',
      (tester) async {
    tester.view.physicalSize = const Size(1266, 900);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.reset);
    final repo = ManualIoRepository();
    final localization = LocalizationController();
    final content = ModuleContentController(
        store: MemoryContentStore(), localization: localization);
    await content.setTabs('Press.Feeder', const [
      ModuleTabDefinition(
            id: 'overview',
          title: 'Overview',
          kind: ModuleTabKind.overview,
          columns: 1,
          cards: [ModuleCardPlacement(ModuleCardKind.manualCommands)]),
      ModuleTabDefinition(
          id: 'notes',
          title: 'Notes',
          kind: ModuleTabKind.custom,
          controls: [
            ModuleControlDefinition(
                id: 'text', kind: ModuleControlKind.text, text: 'Notes')
          ]),
    ]);
    final app = AppState(repo,
        content: content, localization: localization, initialThemeIndex: 29);
    await tester.pumpWidget(FraktalHmiApp(app: app));
    await tester.pump(const Duration(seconds: 1));
    app.select('Press.Feeder');
    await tester.pump(const Duration(seconds: 1));
    await tester.pump();
    expect(find.text('Inputs'), findsOneWidget);
    expect(find.text('Outputs'), findsOneWidget);
    expect(find.text('_101B301B (Feeder Extended)', findRichText: true),
        findsOneWidget);
    expect(find.textContaining('Other', findRichText: true), findsNothing);
    expect(
        tester
            .widgetList<IoSignalLed>(find.byType(IoSignalLed))
            .map((led) => (led.direction, led.value)),
        [
          (ChannelDir.input, true),
          (ChannelDir.input, false),
          (ChannelDir.output, true),
          (ChannelDir.output, false)
        ]);
    expect(repo.ioModule, 'Press.Feeder');
    expect(repo.manualWrites, 0);
    await tester.tap(
        find.descendant(of: find.byType(TabBar), matching: find.text('Notes')));
    await tester.pumpAndSettle();
    expect(repo.ioModule, isNull);
    app.openOverview();
    await tester.pump();
    expect(repo.ioModule, isNull);
    await tester.pumpWidget(const SizedBox());
    app.dispose();
    expect(tester.takeException(), isNull);
  });

  testWidgets(
      'bad signal or bus quality stays unknown; analog, forced and fault information remain visible',
      (tester) async {
    final channels = [
      signal('bad', ChannelDir.input, true, quality: false),
      signal('forced', ChannelDir.output, true, forced: true, fault: true),
      signal('pressure', ChannelDir.input, false,
          kind: ChannelKind.analog, analog: 5.25),
      signal('invalid', ChannelDir.input, false,
          kind: ChannelKind.analog, analog: double.nan),
    ];
    Future<void> show({bool healthy = true}) => tester.pumpWidget(
        LocalizationScope(
            controller: LocalizationController(),
            child: MaterialApp(
                theme: themeAt(29),
                home: Scaffold(
                    body: ModuleIoSignals(
                        modulePath: 'Press.Feeder',
                        fieldbus: bus(channels, healthy: healthy))))));
    await show();
    expect(tester.widget<IoSignalLed>(find.byType(IoSignalLed).first).value,
        isNull);
    expect(find.text('I/O quality unavailable'), findsNWidgets(2));
    expect(find.text('5.25 bar'), findsOneWidget);
    expect(find.text('FORCED'), findsOneWidget);
    expect(find.text('Sensor fault'), findsOneWidget);
    expect(find.byType(Switch), findsNothing);
    expect(find.byType(IconButton), findsNothing);
    await show(healthy: false);
    expect(
        tester
            .widgetList<IoSignalLed>(find.byType(IoSignalLed))
            .every((led) => led.value == null),
        isTrue);
    expect(find.text('5.25 bar'), findsNothing);
    expect(tester.takeException(), isNull);
  });

  testWidgets(
      'long electrical tags wrap at narrow width and empty mapping is explicit',
      (tester) async {
    tester.view.physicalSize = const Size(320, 900);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.reset);
    await tester.pumpWidget(LocalizationScope(
        controller: LocalizationController(),
        child: MaterialApp(
            theme: themeAt(29),
            home: Scaffold(
                body: ModuleIoSignals(
                    modulePath: 'Press.Feeder',
                    fieldbus: bus([
                      signal('_VERY_LONG_ELECTRICAL_TAG_101B301B',
                          ChannelDir.input, true,
                          description:
                              'A long translated description that wraps')
                    ]))))));
    expect(tester.takeException(), isNull);
    await tester.pumpWidget(LocalizationScope(
        controller: LocalizationController(),
        child: MaterialApp(
            theme: themeAt(29),
            home: Scaffold(
                body: ModuleIoSignals(
                    modulePath: 'Press.Feeder',
                    fieldbus: bus([], mapping: false))))));
    expect(find.textContaining('mapping', findRichText: true), findsOneWidget);
  });

  test('Bosch circle glyphs point down/up and missing data has a distinct mark',
      () async {
    final buffers = <List<int>>[];
    for (final (dir, unavailable) in [
      (ChannelDir.input, false),
      (ChannelDir.output, false),
      (ChannelDir.input, true)
    ]) {
      final recorder = ui.PictureRecorder();
      IoSignalLedPainter(
              direction: dir,
              fill: kLikeABoschChrome.ioInputOn,
              glyph: Colors.white,
              unavailable: unavailable)
          .paint(Canvas(recorder), const Size(32, 32));
      final picture = recorder.endRecording();
      final image = await picture.toImage(32, 32);
      buffers.add((await image.toByteData())!.buffer.asUint8List());
      image.dispose();
      picture.dispose();
    }
    expect(buffers[0], isNot(buffers[1]));
    expect(buffers[0], isNot(buffers[2]));
    int whiteCount(List<int> pixels, int row) => [
          for (int x = 4; x < 28; x++)
            if (pixels[(row * 32 + x) * 4] > 240 &&
                pixels[(row * 32 + x) * 4 + 1] > 240)
              x
        ].length;
    expect(whiteCount(buffers[0], 21), greaterThan(whiteCount(buffers[0], 10)));
    expect(whiteCount(buffers[1], 10), greaterThan(whiteCount(buffers[1], 21)));
  });

  test('changing an HMI root assignment withdraws module I/O demand', () async {
    final source = ManualIoRepository();
    final scoped =
        ScopedPlcRepository(source, allowedRoots: ['Press'], configured: true);
    scoped.setModuleIoViewActive('Press.Feeder');
    expect(source.ioModule, 'Press.Feeder');
    scoped.setScope(['Other']);
    expect(source.ioModule, isNull);
    scoped.setModuleIoViewActive('Press.Feeder');
    expect(source.ioModule, isNull);
    scoped.dispose();
  });
}
