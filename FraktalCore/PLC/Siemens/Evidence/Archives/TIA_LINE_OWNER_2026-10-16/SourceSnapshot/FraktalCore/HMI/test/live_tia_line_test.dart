@Tags(['live'])
library;

// Partial Line profile: isolated .53 engineering bench only (Core 1.5).
import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'dart:ui' as ui;

import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:fraktal_hmi/content/content_store.dart';
import 'package:fraktal_hmi/content/module_content_controller.dart';
import 'package:fraktal_hmi/data/opcua_repository.dart';
import 'package:fraktal_hmi/data/plc_repository.dart';
import 'package:fraktal_hmi/domain/module_node.dart';
import 'package:fraktal_hmi/domain/types.dart';
import 'package:fraktal_hmi/localization/localization_controller.dart';
import 'package:fraktal_hmi/localization/localized_text.dart';
import 'package:fraktal_hmi/state/app_state.dart';
import 'package:fraktal_hmi/ui/config_and_history.dart';
import 'package:fraktal_opcua_client/webapi_session_client.dart';

import 'support/tia_line_transport.dart';

void main() {
  final live = Platform.environment['FRAKTAL_TIA_LINE_LIVE'] == '1';
  if (live) {
    final binding = LiveTestWidgetsFlutterBinding.ensureInitialized();
    binding.framePolicy = LiveTestWidgetsFlutterBindingFramePolicy.fullyLive;
  }
  testWidgets('TIA line: generic editor publishes a shared owner edit',
      (tester) async {
    HttpOverrides.global = null;
    tester.view.physicalSize = const Size(1600, 1100);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    final output = Directory(Platform.environment['FRAKTAL_TIA_LINE_OUTPUT']!);
    final plc = Directory('../PLC/Siemens').absolute.path;
    final boundary = GlobalKey();
    PlcRepository? repository;
    StreamSubscription<List<ModuleNode>>? subscription;
    AppState? app;
    var editValue = 2600;
    var forest = const <ModuleNode>[];
    ModuleNode node(String root) => forest.singleWhere((n) => n.path == root);
    Future<void> until(bool Function() predicate, String label) async {
      final timer = Stopwatch()..start();
      while (!predicate() && timer.elapsed < const Duration(minutes: 4)) {
        await Future<void>.delayed(const Duration(milliseconds: 100));
      }
      expect(predicate(), isTrue, reason: label);
    }

    try {
      await tester.runAsync(() async {
        final client = await WebApiSessionClient.connect(
            transport: GuardedLineTransport(
                HttpsWebApiTransport(
                    host: '169.254.212.53',
                    pinnedCertificate: File('${output.path}/certificate.der')
                        .readAsBytesSync()),
                '$plc/tools/Invoke-TiaIsolatedBench.ps1',
                '$plc/Tests/Line/bench_owner.json'),
            user: 'fraktal',
            password: Platform.environment['FRAKTAL_TIA_WEB_PASSWORD']!,
            roots: const ['StationA', 'StationB'],
            batchSize: 64);
        repository = await OpcUaRepository.connectWithClient(client);
        subscription = repository!.forest().listen((value) => forest = value);
        await until(
            () =>
                forest.length == 2 &&
                node('StationA')
                        .config
                        .where((f) => f.kind == CfgKind.lineCfg)
                        .length ==
                    8,
            'eight line fields');
        for (final root in ['StationA', 'StationB']) {
          expect(
              await repository!.login(root, 'admin',
                  Platform.environment['FRAKTAL_TIA_ADMIN_PIN']!),
              isTrue);
          await until(
              () =>
                  node(root).access?.level == AccessLevel.admin &&
                  node(root).config.any((f) =>
                      f.writeKey == 'line.taktMs' &&
                      int.tryParse(f.value) != null),
              'authenticated line values $root');
        }
        final beforeValue = int.parse(node('StationA')
            .config
            .singleWhere((f) => f.writeKey == 'line.taktMs')
            .value);
        editValue = beforeValue == 2600 ? 2700 : 2600;
        final localization = LocalizationController(
            enabledLanguages: {'en'}, activeLanguage: 'en');
        app = AppState(repository!,
            localization: localization,
            content: ModuleContentController(
                store: MemoryContentStore(), localization: localization));
        app!.select('StationA');
        await until(() => app!.forest.length == 2, 'app forest');
      });
      final editor = AnimatedBuilder(
          animation: app!,
          builder: (context, _) => ConfigEditor(
              app: app!,
              node: app!.forest.singleWhere((n) => n.path == 'StationA'),
              kind: CfgKind.lineCfg));
      final window = MaterialApp(
          home: Scaffold(body: SingleChildScrollView(child: editor)));
      final localized =
          LocalizationScope(controller: app!.localization, child: window);
      await tester.pumpWidget(RepaintBoundary(key: boundary, child: localized));
      await tester.pump(const Duration(milliseconds: 500));
      expect(find.text('Line config'), findsWidgets);
      final row = find.byKey(const ValueKey('cfg-0-line.taktMs'));
      expect(row, findsOneWidget);
      await tester.ensureVisible(row);
      await tester.enterText(
          find.descendant(of: row, matching: find.byType(EditableText)),
          editValue.toString());
      await tester.runAsync(() async {
        await tester.tap(
            find.descendant(of: row, matching: find.byType(IconButton)).first);
        for (final root in ['StationA', 'StationB']) {
          await until(
              () => node(root).config.any((f) =>
                  f.writeKey == 'line.taktMs' &&
                  int.tryParse(f.value) == editValue),
              'shared editor value $root');
        }
      });
      await tester.pump(const Duration(milliseconds: 500));
      expect(tester.takeException(), isNull);
      await tester.runAsync(() async {
        final image = await (boundary.currentContext!.findRenderObject()
                as RenderRepaintBoundary)
            .toImage();
        final png = await image.toByteData(format: ui.ImageByteFormat.png);
        await File('${output.path}/line-editor.png')
            .writeAsBytes(png!.buffer.asUint8List());
        image.dispose();
        final field = node('StationA')
            .config
            .singleWhere((f) => f.writeKey == 'line.taktMs');
        expect(
            await repository!.writeConfig('StationA', field, '2500'), isTrue);
        await until(
            () => ['StationA', 'StationB'].every((root) => node(root)
                .config
                .any((f) =>
                    f.writeKey == 'line.taktMs' &&
                    int.tryParse(f.value) == 2500)),
            'normalized shared value');
        for (final root in ['StationA', 'StationB']) {
          await repository!.logout(root);
          await until(() => node(root).access?.level == AccessLevel.none,
              'logged out $root');
        }
        File('${output.path}/result.json').writeAsStringSync(jsonEncode({
          'roots': forest.map((n) => n.path).toList(),
          'lineFields': 8,
          'renderedEditorWrite': editValue,
          'peerValue': editValue,
          'normalizedValue': 2500,
          'productionHmiChanged': false,
        }));
      });
    } finally {
      await tester.pumpWidget(const SizedBox());
      await subscription?.cancel();
      app?.dispose();
      repository?.dispose();
    }
  }, skip: !live, timeout: const Timeout(Duration(minutes: 10)));
}
