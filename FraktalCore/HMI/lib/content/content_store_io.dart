library;

import 'dart:convert';
import 'dart:io';
import 'content_store_base.dart';

ContentStore createContentStore() => _FileContentStore();

class _FileContentStore implements ContentStore {
  File get _file {
    final env = Platform.environment;
    final String base;
    if (Platform.isWindows) {
      base = env['APPDATA'] ?? env['LOCALAPPDATA'] ?? Directory.current.path;
    } else if (Platform.isMacOS) {
      base =
          '${env['HOME'] ?? Directory.current.path}/Library/Application Support';
    } else {
      base = env['XDG_CONFIG_HOME'] ??
          '${env['HOME'] ?? Directory.current.path}/.config';
    }
    return File('$base${Platform.pathSeparator}Fraktal${Platform.pathSeparator}'
        'HMI${Platform.pathSeparator}module_content.json');
  }

  File get _backup => File('${_file.path}.bak');

  Future<Map<String, Object?>> _read(File file) async {
    if (!await file.exists()) return {};
    final value = jsonDecode(await file.readAsString());
    return value is Map ? Map<String, Object?>.from(value) : {};
  }

  @override
  Future<Map<String, Object?>> load() async {
    try {
      final primary = await _read(_file);
      if (primary.isNotEmpty || await _file.exists()) return primary;
    } on Object {
      // Fall through to the last known-good generation.
    }
    try {
      return await _read(_backup);
    } on Object {
      return {};
    }
  }

  @override
  Future<void> save(Map<String, Object?> value) async {
    await _file.parent.create(recursive: true);
    final temp = File(
        '${_file.path}.${pid}.${DateTime.now().microsecondsSinceEpoch}.tmp');
    await temp.writeAsString(jsonEncode(value), flush: true);
    var movedPrimary = false;
    try {
      if (await _file.exists()) {
        if (await _backup.exists()) await _backup.delete();
        await _file.rename(_backup.path);
        movedPrimary = true;
      }
      await temp.rename(_file.path);
    } on Object {
      if (movedPrimary && !await _file.exists() && await _backup.exists()) {
        await _backup.rename(_file.path);
      }
      rethrow;
    } finally {
      if (await temp.exists()) await temp.delete();
    }
  }
}
