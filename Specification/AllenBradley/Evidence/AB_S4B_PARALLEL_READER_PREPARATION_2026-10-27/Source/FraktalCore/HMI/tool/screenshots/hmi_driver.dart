/// A programmatic driver for the generic HMI, for people and agents who need
/// to SEE it without a display, a browser or an MCP server.
///
/// It boots the real application against the integrated demo
/// ([SimRepository]) inside `flutter test`, steers it through the same
/// [AppState] and repository surface the widgets use, advances plant time
/// deterministically, and renders the frame to PNG with real fonts. Beside
/// every picture it writes what was on screen as text, so a caller that cannot
/// read images can still check a shot.
///
/// Nothing here reaches into the application's private state: navigation goes
/// through [AppState], machine actions through the repository's gated write
/// surface (the PLC path), and anything an operator would click is clicked.
library;

import 'dart:io';
import 'dart:ui' as ui;

import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:fraktal_hmi/content/content_store_base.dart';
import 'package:fraktal_hmi/content/module_content_controller.dart';
import 'package:fraktal_hmi/data/connection_settings_store_base.dart';
import 'package:fraktal_hmi/data/plc_repository.dart';
import 'package:fraktal_hmi/data/sim_repository.dart';
import 'package:fraktal_hmi/domain/connection_settings.dart';
import 'package:fraktal_hmi/domain/module_node.dart';
import 'package:fraktal_hmi/localization/catalog_store_base.dart';
import 'package:fraktal_hmi/localization/localization_controller.dart';
import 'package:fraktal_hmi/main.dart';
import 'package:fraktal_hmi/state/app_state.dart';
import 'package:fraktal_hmi/state/hmi_clock.dart';
import 'package:fraktal_hmi/ui/app_theme.dart';
import 'package:fraktal_hmi/ui/connection_bootstrap.dart';

/// When every capture happens: a Tuesday morning in the early shift, so the
/// pictures do not depend on the day and hour they were rendered.
final demoEpoch = DateTime(2026, 10, 13, 10, 24, 30);

/// The demo's users (the simulated `FB_LocalAccessProvider`).
const demoPins = {
  'op1': '1111',
  'tech1': '4711',
  'eng1': '9999',
  'admin1': '2468',
};

/// The [kThemes] index of a theme by the last segment of its name key
/// (`processGrey`, `likeABosch`, ...).
int themeIndexOf(String name) {
  final index =
      kThemes.indexWhere((theme) => theme.nameKey == 'std.theme.$name');
  if (index < 0) {
    throw ArgumentError.value(name, 'theme',
        'known: ${kThemes.map((t) => t.nameKey.substring(10)).join(', ')}');
  }
  return index;
}

bool _fontsLoaded = false;

/// Real glyphs instead of the test font's boxes: Roboto and the Material icon
/// font from the Flutter SDK running the test, and - when the host has them -
/// the Windows UI and monospace faces the desktop HMI really renders with.
Future<void> loadHmiFonts() async {
  if (_fontsLoaded) return;
  final material = _materialFontsDir();
  if (material == null) {
    throw StateError('Flutter material fonts not found next to '
        '${Platform.resolvedExecutable}; set FLUTTER_ROOT.');
  }
  final windows = Platform.environment['WINDIR'] ?? r'C:\Windows';
  bool exists(String path) => File(path).existsSync();
  Future<void> family(String name, List<String> files) async {
    final present = files.where(exists).toList();
    if (present.isEmpty) return;
    final loader = FontLoader(name);
    for (final path in present) {
      loader.addFont(
          Future.value(ByteData.sublistView(File(path).readAsBytesSync())));
    }
    await loader.load();
  }

  final roboto = [
    for (final weight in ['regular', 'medium', 'bold', 'light', 'italic'])
      '$material/roboto-$weight.ttf',
  ];
  await family('Roboto', roboto);
  await family('MaterialIcons', ['$material/materialicons-regular.otf']);
  final segoe = [
    for (final file in ['segoeui', 'seguisb', 'segoeuib', 'segoeuil'])
      '$windows/Fonts/$file.ttf',
  ];
  await family('Segoe UI', segoe.any(exists) ? segoe : roboto);
  // The symbol faces the UI names as fallbacks (the IEC ∥ of a parallel leg).
  await family('Segoe UI Symbol', ['$windows/Fonts/seguisym.ttf']);
  await family(
      'DejaVu Sans', ['/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf']);
  await family(
      'monospace',
      [
        '$windows/Fonts/CascadiaMono.ttf',
        '$windows/Fonts/consola.ttf',
        '/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf',
        ...roboto,
      ].where(exists).take(1).toList());
  _fontsLoaded = true;
}

String? _materialFontsDir() {
  final candidates = <String>[
    if (Platform.environment['FLUTTER_ROOT'] case final root?)
      '$root/bin/cache/artifacts/material_fonts',
  ];
  var dir = File(Platform.resolvedExecutable).parent;
  for (var depth = 0; depth < 8; depth++) {
    candidates
      ..add('${dir.path}/material_fonts')
      ..add('${dir.path}/artifacts/material_fonts')
      ..add('${dir.path}/bin/cache/artifacts/material_fonts');
    dir = dir.parent;
  }
  for (final path in candidates) {
    if (File('$path/materialicons-regular.otf').existsSync()) return path;
  }
  return null;
}

/// What one capture produced.
class Capture {
  final String id;
  final File png;
  final File text;
  final Size size;
  final double pixelRatio;
  const Capture(this.id, this.png, this.text, this.size, this.pixelRatio);
}

class HmiDriver {
  final WidgetTester tester;
  final Directory outDir;

  /// Device pixel ratio of every capture unless a boot names its own.
  final double pixelRatio;
  HmiDriver(this.tester, this.outDir, {this.pixelRatio = 1});

  final _frame = GlobalKey();
  late SimRepository sim;
  late LocalizationController localization;
  late ModuleContentController content;
  AppState? _app;
  Size _size = const Size(1440, 900);
  double _pixelRatio = 1;

  AppState get app {
    final app = _app;
    if (app == null) throw StateError('boot() first');
    return app;
  }

  void _configureView(Size size, double pixelRatio) {
    _size = size;
    _pixelRatio = pixelRatio;
    tester.view.physicalSize = size * pixelRatio;
    tester.view.devicePixelRatio = pixelRatio;
  }

  LocalizationController _localization(String language) =>
      LocalizationController(
          store: MemoryCatalogStore(),
          enabledLanguages: {'en', 'es', 'de', language},
          activeLanguage: language);

  /// Boots the operator shell, already connected, on the demo.
  Future<void> boot({
    SimRepository? repository,
    String theme = 'processGrey',
    ControlScale scale = ControlScale.compact,
    Size size = const Size(1440, 900),
    double? pixelRatio,
    String language = 'en',
    bool floatingKeyboard = false,
  }) async {
    debugDefaultTargetPlatformOverride = TargetPlatform.windows;
    _configureView(size, pixelRatio ?? this.pixelRatio);
    sim = repository ?? SimRepository(epoch: demoEpoch);
    hmiNow = () => sim.plantTime; // the panel and the plant agree on "now"
    localization = _localization(language);
    content = ModuleContentController(
        store: MemoryContentStore(), localization: localization);
    await localization.load();
    await content.load();
    _app = AppState(sim,
        localization: localization,
        content: content,
        initialThemeIndex: themeIndexOf(theme),
        initialFloatingKeyboard: floatingKeyboard,
        initialControlScale: scale);
    await tester.pumpWidget(
        RepaintBoundary(key: _frame, child: FraktalHmiApp(app: app)));
    await advance(const Duration(seconds: 2));
  }

  /// Boots the first-run flow (language, connection, Unit assignment,
  /// appearance) with [settings] as what this panel remembers.
  Future<void> bootSetup({
    ConnectionSettings? settings,
    PlcRepository Function()? repository,
    String theme = 'processGrey',
    Size size = const Size(1440, 900),
    double? pixelRatio,
    String language = 'en',
  }) async {
    debugDefaultTargetPlatformOverride = TargetPlatform.windows;
    _configureView(size, pixelRatio ?? this.pixelRatio);
    sim = SimRepository(epoch: demoEpoch);
    hmiNow = () => sim.plantTime;
    localization = _localization(language);
    content = ModuleContentController(
        store: MemoryContentStore(), localization: localization);
    await tester.pumpWidget(RepaintBoundary(
      key: _frame,
      child: ConnectionBootstrap(
        store: MemoryConnectionSettingsStore(settings),
        repositoryFactory: (_) => repository?.call() ?? sim,
        localization: localization,
        content: content,
      ),
    ));
    await advance(const Duration(seconds: 1));
  }

  /// Releases everything the boot created; call once per test.
  Future<void> dispose() async {
    await tester.pumpWidget(const SizedBox.shrink());
    await tester.pump(const Duration(seconds: 1));
    _app?.dispose();
    _app = null;
    hmiNow = DateTime.now;
    debugDefaultTargetPlatformOverride = null;
    tester.view.resetPhysicalSize();
    tester.view.resetDevicePixelRatio();
  }

  // ---- time ----

  /// Runs the plant (and the UI) for [plantTime].
  Future<void> advance(Duration plantTime) async {
    var left = plantTime;
    const chunk = Duration(seconds: 5);
    while (left > chunk) {
      await tester.pump(chunk);
      left -= chunk;
    }
    await tester.pump(left);
    await settle();
  }

  /// Lets transitions and dialogs finish. Deliberately not `pumpAndSettle`:
  /// a live plant and a blinking step never settle.
  Future<void> settle() async {
    for (var i = 0; i < 8; i++) {
      await tester.pump(const Duration(milliseconds: 50));
    }
  }

  /// Runs the plant until [condition] holds; throws when it never does, so a
  /// shot cannot silently show the wrong moment.
  Future<void> until(String what, bool Function() condition,
      {Duration within = const Duration(seconds: 200)}) async {
    var waited = Duration.zero;
    while (!condition()) {
      if (waited >= within) {
        throw StateError('HMI driver: "$what" not reached within $within');
      }
      await tester.pump(SimTour.tick);
      waited += SimTour.tick;
    }
    await settle();
  }

  // ---- reading ----

  ModuleNode node(String path) {
    for (final root in app.forest) {
      final hit = root.find(path);
      if (hit != null) return hit;
    }
    throw StateError('no module $path');
  }

  // ---- the operator's actions ----

  /// Logs [user] in on [roots] (default: every root) through the PLC's own
  /// login path, the way the login dialog does.
  Future<void> login(String user, {List<String>? roots}) async {
    final pin = demoPins[user] ?? (throw ArgumentError.value(user, 'user'));
    for (final root in roots ?? [for (final r in app.forest) r.path]) {
      if (!await sim.login(root, user, pin)) {
        throw StateError('login $user on $root refused');
      }
    }
    await settle();
  }

  Future<void> overview() async {
    app.openOverview();
    await settle();
  }

  Future<void> fieldbus() async {
    app.setFieldbusView(true);
    await settle();
  }

  /// Opens [path] on [tab] (a tab id: overview, hardware, statistics, events,
  /// description, configuration, sequence, motion, vision, code-reader, rfid,
  /// or a custom tab's id).
  Future<void> open(String path, {String? tab}) async {
    // Re-entering builds the detail afresh, so the tab is honoured even when
    // the module is already open on another one.
    app.openOverview();
    await tester.pump();
    if (tab != null) app.moduleView(path).selectedTabId = tab;
    app.select(path);
    await settle();
  }

  Future<void> setTheme(String name) async {
    app.setTheme(themeIndexOf(name));
    await settle();
  }

  Future<void> setLanguage(String code) async {
    localization.setActiveLanguage(code);
    await settle();
  }

  Finder _one(Finder finder, String what) {
    final count = finder.evaluate().length;
    if (count == 0) throw StateError('nothing to tap: $what');
    return finder.first;
  }

  /// Taps like a finger: the target is scrolled into view first, because a
  /// tap on something below the fold lands on whatever covers that point.
  Future<void> _tap(Finder finder, String what) async {
    final target = _one(finder, what);
    await tester.ensureVisible(target);
    await tester.pump();
    await tester.tap(target);
    await settle();
  }

  Future<void> tapKey(String key) => _tap(find.byKey(Key(key)), 'key $key');

  Future<void> tapText(String text) => _tap(find.text(text), 'text "$text"');

  Future<void> tapTooltip(String tooltip) =>
      _tap(find.byTooltip(tooltip), 'tooltip "$tooltip"');

  Future<void> tapIcon(IconData icon) => _tap(find.byIcon(icon), 'icon $icon');

  /// Taps [icon] in the row that shows [text] (a tree row's chevron, say).
  Future<void> tapIconBeside(String text, IconData icon) {
    final row = find.ancestor(of: find.text(text), matching: find.byType(Row));
    return _tap(find.descendant(of: row.first, matching: find.byIcon(icon)),
        'icon $icon beside "$text"');
  }

  Future<void> enterText(String text, {int index = 0}) async {
    final fields = find.byType(EditableText);
    if (fields.evaluate().length <= index) {
      throw StateError('no text field #$index');
    }
    await tester.enterText(fields.at(index), text);
    await settle();
  }

  /// Scrolls the enclosing view until [target] sits at its top edge.
  Future<void> scrollTo(Finder target) async {
    await tester.ensureVisible(_one(target, 'scroll target $target'));
    await settle();
  }

  /// Closes the topmost dialog or sheet.
  Future<void> dismiss() async {
    final navigator = tester.state<NavigatorState>(find.byType(Navigator).last);
    navigator.pop();
    await settle();
  }

  // ---- output ----

  /// Renders the current frame to `<outDir>/<id>.png` and writes what is on
  /// screen to `<id>.txt`.
  Future<Capture> capture(String id) async {
    await settle();
    // Image decoding finishes on the real event loop, which fake time never
    // reaches: yield to it, then let a frame pick the pictures up (a picture
    // view lays its overlay out against the decoded image's own size).
    for (var round = 0; round < 3; round++) {
      await tester.runAsync(
          () => Future<void>.delayed(const Duration(milliseconds: 80)));
      await tester.pump();
    }
    final png = File('${outDir.path}/$id.png');
    final text = File('${outDir.path}/$id.txt');
    final description = describe();
    final boundary =
        _frame.currentContext!.findRenderObject()! as RenderRepaintBoundary;
    await tester.runAsync(() async {
      final image = await boundary.toImage(pixelRatio: _pixelRatio);
      final data = await image.toByteData(format: ui.ImageByteFormat.png);
      image.dispose();
      png.parent.createSync(recursive: true);
      png.writeAsBytesSync(data!.buffer.asUint8List());
      text.writeAsStringSync(description);
    });
    return Capture(id, png, text, _size, _pixelRatio);
  }

  /// What an operator would read on the screen right now: the view, the
  /// session, each root's state, then every visible line of text in reading
  /// order. The plain-text twin of a screenshot.
  String describe() {
    final out = StringBuffer();
    final app = _app;
    if (app != null) {
      out.writeln(
          'view: ${app.showFieldbus ? 'fieldbus' : app.showOverview ? 'overview' : 'module ${app.selectedPath}'}');
      final s = app.session;
      out.writeln('session: ${s.user.isEmpty ? '(none)' : s.user} '
          '(${s.level.name})');
      for (final root in app.forest) {
        out.writeln('root ${root.path}: ${root.state.name}, '
            'mode ${root.modeActive?.name ?? '-'}, '
            'step ${root.step?.stepNo ?? 0}, '
            '"${localization.resolve(root.message)}"');
      }
    }
    // Render-tree order, not geometry: it groups the screen the way it is
    // built - banners, tree, content, mode bar - and keeps a card's lines
    // together. The one exception is the top bar, which a Scaffold lays out
    // after its body but a reader reads first.
    out.writeln('--- visible text ---');
    final screen = Offset.zero & _size;
    final bar = <String>[], rest = <String>[];
    for (final object in tester.allRenderObjects) {
      if (object is! RenderParagraph || !object.attached || !object.hasSize) {
        continue;
      }
      final rect = object.localToGlobal(Offset.zero) & object.size;
      if (rect.isEmpty || !rect.overlaps(screen) || _hidden(object)) continue;
      final value = object.text.toPlainText().trim().replaceAll('\n', ' ');
      if (value.isEmpty || _isIconGlyph(value)) continue;
      (rect.bottom <= 64 ? bar : rest).add(value);
    }
    String? previous;
    for (final value in [...bar, ...rest]) {
      if (value != previous) out.writeln(value);
      previous = value;
    }
    return out.toString();
  }

  /// An icon font renders its glyph as a paragraph of private-use codepoints.
  static bool _isIconGlyph(String text) => text.runes.every(
      (r) => (r >= 0xE000 && r <= 0xF8FF) || (r >= 0xF0000 && r <= 0xFFFFD));

  /// Laid out but not painted: offstage, fully transparent, or a child an
  /// IndexedStack is not showing (a dropdown keeps every item laid out).
  static bool _hidden(RenderObject object) {
    RenderObject child = object;
    for (var parent = object.parent; parent != null; parent = parent.parent) {
      if (parent is RenderOffstage && parent.offstage) return true;
      if (parent is RenderOpacity && parent.opacity == 0) return true;
      if (parent is RenderAnimatedOpacity && parent.opacity.value == 0) {
        return true;
      }
      if (parent is RenderIndexedStack) {
        var index = 0;
        for (var c = parent.firstChild;
            c != null && c != child;
            c = parent.childAfter(c)) {
          index++;
        }
        if (parent.index != index) return true;
      }
      child = parent;
    }
    return false;
  }
}
