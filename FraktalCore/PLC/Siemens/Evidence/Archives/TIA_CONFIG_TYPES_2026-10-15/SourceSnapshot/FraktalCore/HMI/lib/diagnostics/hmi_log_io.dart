library;

import 'dart:io';

/// Rotated past this so a panel that runs for months keeps a bounded file.
const int _maxBytes = 1024 * 1024;

final String logPath = () {
  final env = Platform.environment;
  // `flutter test` must not write into the operator's real log.
  if (env.containsKey('FLUTTER_TEST')) return '';
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
  final sep = Platform.pathSeparator;
  return '$base${sep}Fraktal${sep}HMI${sep}hmi.log';
}();

bool _ready = false;

void append(String line) {
  if (logPath.isEmpty) return;
  final file = File(logPath);
  if (!_ready) {
    file.parent.createSync(recursive: true);
    _ready = true;
  }
  if (file.existsSync() && file.lengthSync() > _maxBytes) {
    final previous = File('$logPath.1');
    if (previous.existsSync()) previous.deleteSync();
    file.renameSync(previous.path);
  }
  // Synchronous and flushed: the point is that the line is on disk before the
  // next statement runs, so a hang after it cannot lose it.
  file.writeAsStringSync('$line\n', mode: FileMode.append, flush: true);
}
