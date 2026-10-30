// Renders the screenshot catalog (shots.dart) to PNG, headless, with real
// fonts, against the integrated demo. Not part of the normal suite: run it
// on purpose.
//
//   flutter test tool/screenshots/capture_test.dart
//
// Environment (all optional):
//   FRAKTAL_SHOTS      comma list of shot ids; a trailing * matches a prefix
//                      (e.g. "overview,theme-*"). Default: every shot.
//   FRAKTAL_SHOT_DIR   output folder. Default: doc/screenshots.
//   FRAKTAL_SHOT_SCALE device pixel ratio of the PNGs (2 = retina). Default 1.
//
// Writes <id>.png, <id>.txt (what was on screen, as text), manifest.json and
// README.md (the catalog page) into the output folder. A partial run merges
// into the existing manifest instead of replacing it.
import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';

import 'hmi_driver.dart';
import 'shots.dart';

void main() {
  final env = Platform.environment;
  final outDir = Directory(env['FRAKTAL_SHOT_DIR'] ?? 'doc/screenshots');
  final scale = double.tryParse(env['FRAKTAL_SHOT_SCALE'] ?? '') ?? 1;
  final filters = (env['FRAKTAL_SHOTS'] ?? '')
      .split(',')
      .map((s) => s.trim())
      .where((s) => s.isNotEmpty)
      .toList();
  bool wanted(String id) =>
      filters.isEmpty ||
      filters.any((f) => f.endsWith('*')
          ? id.startsWith(f.substring(0, f.length - 1))
          : id == f);
  final captured = <String, Map<String, Object?>>{};

  setUpAll(loadHmiFonts);

  for (final shot in shots) {
    testWidgets(shot.id, (tester) async {
      final driver = HmiDriver(tester, outDir, pixelRatio: scale);
      try {
        await shot.stage(driver);
        final capture = await driver.capture(shot.id);
        captured[shot.id] = {
          'id': shot.id,
          'file': '${shot.id}.png',
          'text': '${shot.id}.txt',
          'group': shot.group,
          'title': shot.title,
          'caption': shot.caption,
          'spec': shot.spec,
          'width': (capture.size.width * capture.pixelRatio).round(),
          'height': (capture.size.height * capture.pixelRatio).round(),
        };
      } finally {
        await driver.dispose();
      }
    }, skip: !wanted(shot.id));
  }

  tearDownAll(() => writeCatalog(outDir, captured));
}

/// Merges [captured] into `manifest.json` and regenerates `README.md` from
/// every shot that has a picture on disk, in catalog order.
void writeCatalog(
    Directory outDir, Map<String, Map<String, Object?>> captured) {
  if (captured.isEmpty) return;
  outDir.createSync(recursive: true);
  final manifestFile = File('${outDir.path}/manifest.json');
  final entries = <String, Map<String, Object?>>{};
  if (manifestFile.existsSync()) {
    final prior = jsonDecode(manifestFile.readAsStringSync());
    for (final entry in (prior['shots'] as List? ?? const [])) {
      final map = Map<String, Object?>.from(entry as Map);
      entries[map['id'] as String] = map;
    }
  }
  entries.addAll(captured);
  final ordered = [
    for (final shot in shots)
      if (entries[shot.id] != null &&
          File('${outDir.path}/${shot.id}.png').existsSync())
        entries[shot.id]!,
  ];
  manifestFile.writeAsStringSync(const JsonEncoder.withIndent('  ').convert({
    'generator': 'FraktalCore/HMI/tool/screenshots/capture_test.dart',
    'source': 'SimRepository (integrated demo)',
    'shots': ordered,
  }));

  // Links back to the tool, from wherever under the package the page lands.
  final out = outDir.path.replaceAll('\\', '/');
  final depth = out.startsWith('/') || out.contains(':')
      ? null
      : out.split('/').where((s) => s.isNotEmpty && s != '.').length;
  final tool = depth == null
      ? 'FraktalCore/HMI/tool/screenshots'
      : '${'../' * depth}tool/screenshots';
  final readme = StringBuffer()
    ..writeln('# Fraktal HMI — screenshot catalog')
    ..writeln()
    ..writeln('Every picture is rendered headless from the generic HMI running '
        'against its integrated demo (`SimRepository`), by '
        '[`tool/screenshots/capture_test.dart`]($tool/capture_test.dart). '
        'Nothing is mocked up: each is the real widget tree at a moment the '
        'demo plant reaches by itself or an operator action causes. '
        '`manifest.json` lists the same shots for a site generator; each '
        '`<id>.txt` is the on-screen text of its picture.')
    ..writeln()
    ..writeln('Regenerate (from `FraktalCore/HMI`):')
    ..writeln()
    ..writeln('```')
    ..writeln('flutter test tool/screenshots/capture_test.dart')
    ..writeln('```')
    ..writeln()
    ..writeln('`FRAKTAL_SHOTS=overview,theme-*` renders a subset, '
        '`FRAKTAL_SHOT_SCALE=2` renders at twice the pixel density. See '
        '[`tool/screenshots/README.md`]($tool/README.md).')
    ..writeln();
  for (final group in groups.entries) {
    final inGroup = ordered.where((e) => e['group'] == group.key).toList();
    if (inGroup.isEmpty) continue;
    readme
      ..writeln('## ${group.value}')
      ..writeln();
    for (final e in inGroup) {
      readme
        ..writeln('### ${e['title']}')
        ..writeln()
        ..writeln('![${e['title']}](${e['file']})')
        ..writeln()
        ..writeln('${e['caption']}')
        ..writeln()
        ..writeln('`${e['id']}` · ${(e['spec'] as List).join(' · ')}')
        ..writeln();
    }
  }
  File('${outDir.path}/README.md').writeAsStringSync(readme.toString());
}
