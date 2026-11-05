/// Core 3.8b live documents on the host medium, as `fraktal_ab_live_medium.py`
/// keeps them: keyed JSON-lines documents and the index of confirmed keys.
library;

import 'dart:convert';
import 'dart:io';

import 'package:fraktal_opcua_client/cip_host_service.dart' show cipSha256;

import 'set_documents.dart';

const liveName = '_live'; // TC3's SetName for live documents
const indexName = 'index.json',
    indexSchema = 'fraktal.ab.live-documents',
    indexVersion = 1;

/// The medium did not answer. Retry; never treat it as "nothing there".
final class MediumUnreadable implements Exception {
  final String message;
  const MediumUnreadable(this.message);
  @override
  String toString() => 'MediumUnreadable: $message';
}

/// A confirmed document is missing, or a document does not parse.
final class DocumentLost implements Exception {
  final String message;
  const DocumentLost(this.message);
  @override
  String toString() => 'DocumentLost: $message';
}

/// What a document says, without when it was written.
String content(Document document) => jsonEncode([
      {
        for (final e in document.first.entries)
          if (e.key != 'created' && e.key != 'clock') e.key: e.value
      },
      ...document.skip(1)
    ]);

Object? _sorted(Object? value) => value is Map
    ? {
        for (final key in (value.keys.cast<String>().toList()..sort()))
          key: _sorted(value[key])
      }
    : value;

final class FileMedium {
  final Directory directory;
  FileMedium(this.directory);

  File _path(String key) {
    checkedName(key);
    return File('${directory.path}${Platform.pathSeparator}'
        '${cipSha256(ascii.encode(key))}.jsonl');
  }

  /// The path a key is kept at (tests remove one to simulate a loss).
  File pathOf(String key) => _path(key);

  static void checkedName(String key) {
    if (key.isEmpty || key.length > nameMax || key.codeUnits.any((c) => c > 127 || c == 0))
      throw const SetRejected('text width or type');
  }

  Map<String, Object?> index() {
    final file = File('${directory.path}${Platform.pathSeparator}$indexName');
    final String text;
    try {
      text = ascii.decode(file.readAsBytesSync());
    } on PathNotFoundException {
      return {};
    } on FileSystemException catch (error) {
      throw MediumUnreadable('live document index unreadable: ${error.message}');
    } on FormatException {
      throw const MediumUnreadable('live document index is damaged');
    }
    try {
      final held = jsonDecode(text);
      if (held is! Map ||
          held['schema'] != indexSchema ||
          held['schemaVersion'] != indexVersion) throw const FormatException('schema');
      final confirmed = held['documents'];
      if (confirmed is! Map ||
          confirmed.values.any((v) => v is! Map || v['generation'] is! int))
        throw const FormatException('documents');
      return Map<String, Object?>.from(confirmed);
    } on FormatException {
      // Which keys were confirmed is unknown: a loss could not be told from a
      // first start, so the medium has not answered.
      throw const MediumUnreadable('live document index is damaged');
    }
  }

  /// The document, null if never confirmed, or DocumentLost.
  Document? read(String key) {
    final confirmed = index();
    final path = _path(key);
    final String text;
    try {
      if (FileSystemEntity.isLinkSync(path.path)) throw DocumentLost('$key: store symlink');
      if (path.lengthSync() > (maxRecords + 1) * (lineMax + 1))
        throw DocumentLost('$key: document exceeds capacity');
      text = ascii.decode(path.readAsBytesSync());
    } on PathNotFoundException {
      if (confirmed.containsKey(key)) throw DocumentLost('$key: confirmed document is missing');
      return null;
    } on FormatException catch (error) {
      throw DocumentLost('$key: ${error.message}');
    } on FileSystemException catch (error) {
      throw MediumUnreadable('$key: ${error.message}');
    }
    try {
      return checkedDocument([for (final line in splitLines(text)) parseLine(line)]);
    } on SetRejected catch (error) {
      throw DocumentLost('$key: ${error.message}');
    }
  }

  void write(String key, Document document) {
    document = checkedDocument(document);
    final text = '${document.map(renderLine).join('\n')}\n';
    final confirmed = index();
    replaceText(directory, _path(key), text);
    final entry = confirmed[key] as Map? ?? const {'generation': 0};
    confirmed[key] = {
      'generation': (entry['generation'] as int) + 1,
      'sha256': cipSha256(ascii.encode(text))
    };
    final held = {
      'schema': indexSchema,
      'schemaVersion': indexVersion,
      'documents': confirmed
    };
    // Python's json.dumps(sort_keys=True, indent=1), then a newline.
    replaceText(directory, File('${directory.path}${Platform.pathSeparator}$indexName'),
        '${const JsonEncoder.withIndent(' ').convert(_sorted(held))}\n');
  }
}
