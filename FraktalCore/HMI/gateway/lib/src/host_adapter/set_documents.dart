/// Core 3.8b parameter-set documents and their host store.
///
/// The same portable JSON-lines format, bounds and file layout as
/// `fraktal_ab_set_documents.py`, byte for byte: a set the Python broker saved
/// is a set this store reads, and the reverse.
library;

import 'dart:convert';
import 'dart:io';

import 'package:fraktal_opcua_client/cip_host_service.dart' show cipSha256;

import 'python_json.dart';

const maxSets = 4, maxRecords = 64, lineMax = 480, nameMax = 80;
const setDirEnv = 'FRAKTAL_AB_CONFIG_SET_DIR';
const headerFields = [
  'set',
  'root',
  'schema',
  'configRev',
  'kind',
  'model',
  'records',
  'created',
  'clock'
];
const recordFields = ['scope', 'key', 'rev', 'kind', 'type', 'value'];

/// A document, line or name the format refuses.
final class SetRejected implements Exception {
  final String message;
  const SetRejected(this.message);
  @override
  String toString() => 'SetRejected: $message';
}

typedef Line = Map<String, Object?>;
typedef Document = List<Line>;

/// The set store's folder: one per commissioned root and controller serial.
Directory directoryFor(String root, String serial,
    [Map<String, String>? environment]) {
  final environ = environment ?? Platform.environment;
  final chosen = environ[setDirEnv];
  if (chosen != null && chosen.isNotEmpty) return Directory(chosen);
  final base = environ['LOCALAPPDATA'] ??
      environ['HOME'] ??
      Directory.current.path;
  return Directory('$base${Platform.pathSeparator}Fraktal'
      '${Platform.pathSeparator}ConfigSets${Platform.pathSeparator}$serial-$root');
}

/// A controller date (YYYYMMDD) and clock (HHMMSS and microseconds) as UTC epoch seconds.
int createdSeconds(int date, int clock) {
  final year = date ~/ 10000, month = (date ~/ 100) % 100, day = date % 100;
  final hour = clock ~/ 10000000,
      minute = (clock ~/ 100000) % 100,
      second = (clock ~/ 1000) % 100;
  final stamp = DateTime.utc(year, month, day, hour, minute, second);
  // DateTime normalizes out-of-range parts; Python's datetime refuses them.
  if (year < 1 ||
      stamp.year != year ||
      stamp.month != month ||
      stamp.day != day ||
      stamp.hour != hour ||
      stamp.minute != minute ||
      stamp.second != second) throw const FormatException('Invalid controller time.');
  return stamp.millisecondsSinceEpoch ~/ 1000;
}

String _text(Object? value, int maximum, {bool nonempty = false}) {
  // The frozen AB StringFamily transport is ASCII: refuse, never shorten.
  if (value is! String || value.length > maximum || (nonempty && value.isEmpty))
    throw const SetRejected('text width or type');
  if (value.codeUnits.any((c) => c > 127 || c == 0))
    throw const SetRejected('text is outside the frozen ASCII transport');
  return value;
}

int _int(Object? value, [int low = 0, int high = 2147483647]) {
  if (value is! int || value < low || value > high)
    throw const SetRejected('integer width or type');
  return value;
}

Line checkedHeader(Object? header) {
  if (header is! Map ||
      header.length != headerFields.length ||
      !headerFields.every(header.containsKey))
    throw const SetRejected('header shape');
  final h = Map<String, Object?>.from(header);
  for (final n in ['set', 'root', 'model']) {
    _text(h[n], nameMax, nonempty: n != 'model');
  }
  _int(h['schema'], 1, 65535);
  _int(h['configRev']);
  _int(h['kind'], 0, 2);
  _int(h['records'], 0, maxRecords);
  _int(h['created'], 0, 4294967295);
  _int(h['clock'], 0, 1);
  return h;
}

Line checkedRecord(Object? record) {
  if (record is! Map ||
      record.length != recordFields.length ||
      !recordFields.every(record.containsKey))
    throw const SetRejected('record shape');
  final r = Map<String, Object?>.from(record);
  _text(r['scope'], nameMax);
  _text(r['key'], 160, nonempty: true);
  _text(r['value'], nameMax);
  _int(r['rev']);
  _int(r['kind'], 0, 2);
  _int(r['type'], 0, 3);
  return r;
}

Line parseLine(String line) {
  _text(line, lineMax, nonempty: true);
  final Object? value;
  try {
    value = strictJsonDecode(line);
  } on FormatException {
    throw const SetRejected('invalid JSON line');
  }
  return value is Map && value.containsKey('set')
      ? checkedHeader(value)
      : checkedRecord(value);
}

String renderLine(Line value) {
  final header = value.containsKey('set');
  final checked = header ? checkedHeader(value) : checkedRecord(value);
  final order = header ? headerFields : recordFields;
  final line = '{${order.map((k) => '${pythonJsonString(k)}:${_jsonValue(checked[k])}').join(',')}}';
  return _text(line, lineMax, nonempty: true);
}

Document checkedDocument(Object? document) {
  if (document is! List || document.isEmpty)
    throw const SetRejected('empty document');
  final h = checkedHeader(document.first);
  final records = [for (final r in document.skip(1)) checkedRecord(r)];
  if (records.length != h['records'])
    throw const SetRejected('header record count differs');
  final result = <Line>[h, ...records];
  for (final value in result) {
    renderLine(value); // complete bounded export, or no import
  }
  return result;
}

String _jsonValue(Object? value) =>
    value is String ? pythonJsonString(value) : '$value';

/// Python's `str.splitlines()` over ASCII text.
List<String> splitLines(String text) {
  final out = <String>[];
  var start = 0;
  for (var i = 0; i < text.length; i++) {
    final c = text.codeUnitAt(i);
    if (c == 0x0d && i + 1 < text.length && text.codeUnitAt(i + 1) == 0x0a) {
      out.add(text.substring(start, i));
      i++;
      start = i + 1;
    } else if ({0x0a, 0x0b, 0x0c, 0x0d, 0x1c, 0x1d, 0x1e}.contains(c)) {
      out.add(text.substring(start, i));
      start = i + 1;
    }
  }
  if (start < text.length) out.add(text.substring(start));
  return out;
}


/// Atomic ASCII replacement: write a sibling temporary, flush it, rename.
void replaceText(Directory directory, File path, String text) {
  directory.createSync(recursive: true);
  if (FileSystemEntity.isLinkSync(path.path)) throw const SetRejected('store symlink');
  final temporary = File('${directory.path}${Platform.pathSeparator}.pending-'
      '${DateTime.now().microsecondsSinceEpoch}-$pid');
  try {
    final handle = temporary.openSync(mode: FileMode.writeOnly);
    try {
      handle.writeFromSync(ascii.encode(text));
      handle.flushSync();
    } finally {
      handle.closeSync();
    }
    temporary.renameSync(path.path);
  } finally {
    if (temporary.existsSync()) temporary.deleteSync();
  }
}

String _readAscii(File file) => ascii.decode(file.readAsBytesSync());

/// Four named documents, atomic replacement and explicit I/O failures.
final class FileStore {
  final Directory directory;
  FileStore(this.directory);

  File path(String name) {
    _text(name, nameMax, nonempty: true);
    return File('${directory.path}${Platform.pathSeparator}'
        '${cipSha256(ascii.encode(name))}.jsonl');
  }

  static const _bound = (maxRecords + 1) * (lineMax + 1);

  Document _load(File file) {
    if (FileSystemEntity.isLinkSync(file.path)) throw const SetRejected('store symlink');
    if (file.lengthSync() > _bound) throw const SetRejected('document exceeds capacity');
    final String text;
    try {
      text = _readAscii(file);
    } on FormatException {
      throw const SetRejected('document is not ASCII');
    }
    return checkedDocument([for (final line in splitLines(text)) parseLine(line)]);
  }

  /// The named document; a missing one throws PathNotFoundException.
  Document read(String name) {
    final result = _load(path(name));
    if (result.first['set'] != name) throw const SetRejected('stored name differs');
    return result;
  }

  List<Line> list() {
    if (!directory.existsSync()) return [];
    final files = directory
        .listSync()
        .whereType<File>()
        .where((f) => f.path.endsWith('.jsonl'))
        .toList()
      ..sort((a, b) => a.path.compareTo(b.path));
    final rows = <Line>[];
    for (final file in files) {
      final document = _load(file);
      if (file.path != path(document.first['set'] as String).path)
        throw const SetRejected('stored identity differs');
      rows.add(document.first);
      if (rows.length > maxSets) throw const SetRejected('store exceeds capacity');
    }
    return rows..sort((a, b) => (a['set'] as String).compareTo(b['set'] as String));
  }

  void save(Document document) {
    document = checkedDocument(document);
    final target = path(document.first['set'] as String);
    final rows = list();
    if (!rows.any((h) => h['set'] == document.first['set']) && rows.length >= maxSets)
      throw const SetRejected('store is full; delete a set first');
    replaceText(directory, target, '${document.map(renderLine).join('\n')}\n');
  }

  void delete(String name) {
    read(name); // refuse absent/corrupt entries; never guess a path
    path(name).deleteSync();
  }
}

/// An import's framing: pieces of lines, then the document on commit.
final class Session {
  String partial = '';
  Document? document;

  void interrupt() {
    partial = '';
    document = null;
  }

  Document? piece(String text, bool more, bool commit) {
    try {
      _text(text, 255);
      _text(partial + text, lineMax);
      if (more) {
        if (commit) throw const SetRejected('commit before the final piece');
        partial += text;
        return null;
      }
      final line = partial + text;
      partial = '';
      final parsed = parseLine(line);
      if (parsed.containsKey('set')) {
        document = [parsed];
      } else if (document == null) {
        throw const SetRejected('record before header');
      } else {
        document!.add(parsed);
        if (document!.length - 1 > maxRecords)
          throw const SetRejected('import exceeds record capacity');
      }
      if (commit) {
        final result = checkedDocument(document);
        document = null;
        return result;
      }
      return null;
    } on Object {
      interrupt();
      rethrow;
    }
  }
}
