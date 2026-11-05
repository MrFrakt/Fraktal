/// WP6.5: one root's host services, declaration-free.
///
/// The controller owns every key, ordinal and verdict. `RootService` only
/// answers the jobs the controller opens on its V6.11 ingress, and opens its
/// own live-document jobs. ConfigSets and ConfigProvider read and write the four
/// named documents in `FileStore`; LiveDocuments keep every document on
/// `FileMedium` when it changes, and restore them after a download while the
/// controller restores and its own set gate permits the session. Documents are
/// rendered from published facts alone. An unanswered request is never resent.
library;

import 'dart:io';

import 'package:fraktal_opcua_client/cip_host_service.dart';

import 'live_medium.dart';
import 'set_documents.dart';

// Core E_HmiRequestKind ordinals: binding-neutral, the same on every controller.
const save = 28,
    load = 29,
    list = 30,
    export = 32,
    import = 33,
    delete = 35,
    create = 37,
    exportCurrent = 38;
const deniedKey = 'std.error.accessDenied';
const importPlaceholder = '(import)'; // the broker's name before a header completes

/// A snapshot as a set document, from published facts alone.
Document render(CipHostFacts facts, String name, int kind, List values,
    String modelCode, int created, int clock, [int? revision]) {
  final rev = revision ?? facts.revision;
  final records = [
    for (final c in facts.capabilities)
      if (c.kind == kind)
        {
          'scope': facts.root,
          'key': c.key,
          'rev': rev,
          'kind': kind,
          'type': c.valueType,
          'value': c.valueType == 2
              ? ((values[c.ordinal - 1] as int) != 0 ? 'TRUE' : 'FALSE')
              : '${values[c.ordinal - 1]}'
        }
  ];
  return checkedDocument([
    {
      'set': name,
      'root': facts.root,
      'schema': 1,
      'configRev': rev,
      'kind': kind,
      'model': modelCode,
      'records': records.length,
      'created': created,
      'clock': clock
    },
    ...records
  ]);
}

int _signed(int value) => value > 0x7fffffff ? value - 0x100000000 : value;

/// A document as request bodies: its header, then up to eight records per scope.
List<Map<String, Object?>> documentChunks(Document document, {int? line}) {
  final header = document.first, records = document.skip(1).toList();
  final chunks = <Map<String, Object?>>[
    {
      'Kind': CipHost.header,
      'Count': 0,
      'Total': records.length,
      'Scope': header['root'],
      'Name': header['set'],
      'Model': header['model'],
      'SetSchema': header['schema'],
      'ConfigRev': header['configRev'],
      'RecordKind': header['kind'],
      'CreatedSeconds': _signed(header['created'] as int),
      'Synchronized': header['clock']
    }
  ];
  var index = 0;
  final integer = RegExp(r'^[+-]?[0-9]+$');
  while (index < records.length) {
    final part = [records[index]];
    while (part.length < 8 &&
        index + part.length < records.length &&
        records[index + part.length]['scope'] == part.first['scope']) {
      part.add(records[index + part.length]);
    }
    final types = <int>[], values = <int>[];
    for (final record in part) {
      // Syntax is translated, never authorized: anything else reaches the
      // controller as an invalid type, exactly as the broker sent it.
      final value = record['value'] as String, kind = record['type'] as int;
      final number = integer.hasMatch(value) ? BigInt.parse(value) : null;
      if (kind == 2 && {'true', 'false'}.contains(value.toLowerCase())) {
        types.add(kind);
        values.add(value.toLowerCase() == 'true' ? 1 : 0);
      } else if (number != null &&
          number >= BigInt.from(-0x80000000) &&
          number <= BigInt.from(0x7fffffff)) {
        types.add(kind);
        values.add(number.toInt());
      } else {
        types.add(-1);
        values.add(0);
      }
    }
    chunks.add({
      'Kind': CipHost.records,
      'Count': part.length,
      'Total': records.length,
      'Scope': part.first['scope'],
      'Keys': [for (final r in part) r['key']],
      'Revisions': [for (final r in part) r['rev']],
      'RecordKinds': [for (final r in part) r['kind']],
      'ValueTypes': types,
      'Values': values
    });
    index += part.length;
  }
  if (line != null) {
    chunks.add({
      'Kind': CipHost.text,
      'Count': line,
      'Total': records.length,
      'Line': renderLine(document[line])
    });
  }
  return chunks;
}

final class Health {
  String state = 'idle', error = '', restoredAt = '';
  bool failed = false;
  List<(String, String)> losses = [];

  Map<String, Object?> toJson() => {
        'state': state,
        'failed': failed,
        if (error.isNotEmpty) 'error': error,
        if (restoredAt.isNotEmpty) 'restoredAt': restoredAt,
        if (losses.isNotEmpty)
          'losses': [
            for (final (key, why) in losses) {'key': key, 'detail': why}
          ]
      };
}

/// One root's host services over one port; `step` answers at most one job.
final class RootService {
  final CipHostPort port;
  final FileStore store;
  final FileMedium? medium;
  final double Function() clock;
  final int Function() wall;
  final double keepInterval, retry;
  final session = Session();
  final health = Health();
  Document? committed; // an import's document, saved by its STORE job
  Document? exported; // a current export's rendering, served for its later lines
  (int, int, int, int)? answered;
  Map<String, String>? written; // live key -> content, loaded from the medium once
  int keepNext = 0;
  double keepAt = 0, retryAt = 0;
  // A denied restore is not retried under the permission it was denied
  // under: only once the session's permission has dropped and returned.
  bool deniedWhilePermitted = false;

  RootService(this.port, this.store, this.medium,
      {double Function()? clock,
      int Function()? wall,
      this.keepInterval = 2.0,
      this.retry = 10.0})
      : clock = clock ?? (() => DateTime.now().microsecondsSinceEpoch / 1e6),
        wall = wall ?? (() => DateTime.now().millisecondsSinceEpoch ~/ 1000);

  // -- transport --------------------------------------------------------------
  Future<Map<String, Object?>> _submit(Map<String, Object?> job,
      Map<String, Object?> body,
      {required bool last,
      int status = CipHost.ok,
      int? chunk,
      int argument = 0}) {
    return port.submit({
      'Service': job['JobService'],
      'JobSequence': job['JobSequence'],
      'Operation': job['JobOperation'],
      'Argument': argument,
      'Chunk': chunk ?? job['NextChunk'],
      'Final': last ? 1 : 0,
      'Status': status
    }, body);
  }

  /// Send a job's chunks in order; stop at the first one the controller refuses.
  Future<bool> _answer(Map<String, Object?> job, List<Map<String, Object?>> chunks,
      [int status = CipHost.ok]) async {
    final first = job['NextChunk'] as int;
    for (var i = 0; i < chunks.length; i++) {
      final reply = await _submit(job, chunks[i],
          last: i == chunks.length - 1, status: status, chunk: first + i);
      if (reply['Accepted'] != 1) return false;
    }
    return true;
  }

  Future<bool> _status(Map<String, Object?> job, int status) =>
      _answer(job, [
        {'Kind': CipHost.none}
      ], status);

  // -- the loop ---------------------------------------------------------------
  Future<void> step() async {
    final reply = await port.reply();
    if (reply['JobSequence'] == 0) {
      answered = null;
      if (medium != null) await _live(reply);
      return;
    }
    final mark = (
      reply['JobSequence'] as int,
      reply['JobService'] as int,
      reply['JobPhase'] as int,
      reply['NextChunk'] as int
    );
    if (mark == answered) return;
    answered = mark;
    final service = reply['JobService'], phase = reply['JobPhase'];
    final Future<bool> Function(Map<String, Object?>)? handler =
        service == CipHost.configSets && phase == CipHost.fetch
            ? _fetch
            : service == CipHost.configSets && phase == CipHost.store
                ? _store
                : service == CipHost.configProvider && phase == CipHost.present
                    ? _present
                    : null;
    if (handler == null) return; // a live-document job of ours
    if (reply['JobOperation'] != import) session.interrupt();
    if (reply['JobOperation'] != export && reply['JobOperation'] != exportCurrent) {
      exported = null;
    }
    try {
      await handler(reply);
    } on CipHostUnanswered catch (error) {
      health.error = error.message;
    }
  }

  // -- ConfigSets: before the transaction ----------------------------------------
  Future<bool> _fetch(Map<String, Object?> job) async {
    final operation = job['JobOperation'], name = job['JobName'] as String;
    if (operation == import) return _import(job);
    final Document document;
    int? line;
    try {
      if (operation == save) {
        final headers = store.list();
        final full = !headers.any((h) => h['set'] == name) && headers.length >= maxSets;
        return await _status(job, full ? CipHost.refused : CipHost.ok);
      }
      if (operation == delete) {
        store.read(name);
        return await _status(job, CipHost.ok);
      }
      final cached = exported;
      document = operation == export &&
              (job['JobInt'] as int) > 0 &&
              cached != null &&
              cached.first['set'] == name
          ? cached
          : store.read(name);
      if (operation == create && document.first['kind'] != 0)
        throw const SetRejected('creation source must be a model set');
      if (operation == export) {
        line = job['JobInt'] as int;
        if (line < 0 || line >= document.length)
          throw const SetRejected('export line is outside the document');
      }
    } on SetRejected {
      return _status(job, CipHost.refused);
    } on PathNotFoundException {
      return _status(job, CipHost.refused);
    } on FileSystemException {
      return _status(job, CipHost.unavailable);
    }
    return _answer(job, documentChunks(document, line: line));
  }

  Future<bool> _import(Map<String, Object?> job) async {
    var name = session.document?.first['set'] as String? ?? importPlaceholder;
    final Document? document;
    try {
      document = session.piece(
          job['JobText'] as String, job['JobInt'] == 1, job['JobBool'] != 0);
    } on SetRejected {
      return _answer(job, [
        {'Kind': CipHost.header, 'Name': name, 'Total': 0}
      ], CipHost.refused);
    }
    if (session.document != null) name = session.document!.first['set'] as String;
    if (document != null) {
      name = document.first['set'] as String;
      committed = document;
    }
    return _answer(job, [
      {
        'Kind': CipHost.header,
        'Name': name,
        'Total': document == null ? 0 : document.length - 1
      }
    ]);
  }

  // -- ConfigSets: after the acknowledgement ---------------------------------------
  Future<bool> _store(Map<String, Object?> job) async {
    final operation = job['JobOperation'];
    try {
      if (operation == save) {
        final snapshot = job['Snapshot'] as Map, facts = await port.facts();
        final kind = snapshot['Kind'] as int, model = snapshot['ModelOrdinal'] as int;
        final code = kind == 0 && model >= 1 && model <= facts.codes.length
            ? facts.codes[model - 1]
            : '';
        store.save(render(
            facts,
            job['JobName'] as String,
            kind,
            snapshot['Values'] as List,
            code,
            createdSeconds(snapshot['Date'] as int, snapshot['Clock'] as int),
            snapshot['Synchronized'] != 0 ? 1 : 0,
            snapshot['Revision'] as int));
      } else if (operation == delete) {
        store.delete(job['JobName'] as String);
      } else if (operation == import) {
        final document = committed;
        if (document == null || document.first['set'] != job['JobName'])
          throw const SetRejected('no committed import of that name');
        store.save(document);
        committed = null;
      } else {
        throw const SetRejected('no store for this operation');
      }
    } on SetRejected {
      return _status(job, CipHost.failed);
    } on FileSystemException {
      return _status(job, CipHost.failed);
    } on FormatException {
      return _status(job, CipHost.failed);
    }
    return _status(job, CipHost.ok);
  }

  // -- ConfigProvider: before the acknowledgement ------------------------------------
  Future<bool> _present(Map<String, Object?> job) async {
    if (job['JobOperation'] == list) {
      final List<Line> headers;
      try {
        headers = store.list();
      } on SetRejected {
        return _status(job, CipHost.unavailable);
      } on FileSystemException {
        return _status(job, CipHost.unavailable);
      }
      if (headers.isEmpty) return _status(job, CipHost.ok);
      return _answer(job, [
        for (final h in headers)
          {
            'Kind': CipHost.catalog,
            'Count': h['records'],
            'Total': headers.length,
            'Scope': h['root'],
            'Name': h['set'],
            'Model': h['model'],
            'SetSchema': h['schema'],
            'ConfigRev': h['configRev'],
            'RecordKind': h['kind'],
            'CreatedSeconds': _signed(h['created'] as int),
            'Synchronized': h['clock']
          }
      ]);
    }
    final snapshot = job['Snapshot'] as Map, facts = await port.facts();
    final Document document;
    try {
      final kind = snapshot['Kind'] as int, model = snapshot['ModelOrdinal'] as int;
      final code = kind == 0 && model >= 1 && model <= facts.codes.length
          ? facts.codes[model - 1]
          : '';
      document = render(
          facts,
          job['JobName'] as String,
          kind,
          snapshot['Values'] as List,
          code,
          createdSeconds(snapshot['Date'] as int, snapshot['Clock'] as int),
          snapshot['Synchronized'] != 0 ? 1 : 0,
          snapshot['Revision'] as int);
    } on SetRejected {
      return _status(job, CipHost.unavailable);
    } on FormatException {
      return _status(job, CipHost.unavailable);
    } on RangeError {
      return _status(job, CipHost.unavailable);
    }
    exported = document;
    return _answer(job, [
      {
        'Kind': CipHost.text,
        'Count': 0,
        'Total': document.length - 1,
        'Line': renderLine(document.first)
      }
    ]);
  }

  // -- LiveDocuments ---------------------------------------------------------------
  Future<void> _live(Map<String, Object?> reply) async {
    if (reply['Restoring'] != 0) {
      final permits = reply['SessionPermits'] != 0;
      if (!permits) deniedWhilePermitted = false;
      if (permits && !deniedWhilePermitted && clock() >= retryAt) await restore();
      return;
    }
    deniedWhilePermitted = false;
    if (clock() >= keepAt) {
      keepAt = clock() + keepInterval;
      await keepOne();
    }
  }

  Future<Map<String, Object?>> _open(int operation, Map<String, Object?> body,
      {int argument = 0, int status = CipHost.ok, bool last = false}) {
    return _submit({
      'JobService': CipHost.liveDocuments,
      'JobSequence': 0,
      'JobOperation': operation,
      'NextChunk': 0
    }, body, last: last, status: status, chunk: 0, argument: argument);
  }

  List<(String, int, int)> _documents(CipHostFacts facts) => [
        ('${facts.root}.station', 1, 0),
        if (facts.line) ('${facts.root}.line', 2, 0),
        if (facts.models)
          for (var i = 1; i <= facts.codes.length; i++) ('${facts.root}.model$i', 0, i)
      ];

  void _fail(String state, Object error) {
    health
      ..state = state
      ..failed = true
      ..error = '$error';
    retryAt = clock() + retry;
  }

  /// Keep the next document in turn; write it only when its content changed.
  Future<bool> keepOne() async {
    final facts = await port.facts(), wanted = _documents(facts);
    final (key, kind, index) = wanted[keepNext % wanted.length];
    keepNext++;
    try {
      if (written == null) {
        final known = <String, String>{};
        for (final (k, _, _) in wanted) {
          try {
            final document = medium!.read(k);
            if (document != null) known[k] = content(document);
          } on DocumentLost {
            // rewritten from the controller below
          }
        }
        written = known;
      }
    } on MediumUnreadable catch (error) {
      _fail('failed', error);
      return false;
    }
    final opened = await _open(exportCurrent,
        {'Kind': CipHost.none, 'RecordKind': kind, 'Count': index});
    if (opened['Accepted'] != 1) return false; // restoring, busy or preempted
    final snapshot = opened['Snapshot'] as Map;
    var status = CipHost.ok;
    try {
      final model = snapshot['ModelOrdinal'] as int;
      final code = (kind == 0 || kind == 1) && model >= 1 && model <= facts.codes.length
          ? facts.codes[model - 1]
          : '';
      final document = render(facts, liveName, kind, snapshot['Values'] as List, code,
          wall(), 0, snapshot['Revision'] as int);
      if (written![key] != content(document)) {
        medium!.write(key, document);
        written![key] = content(document);
      }
      health
        ..state = 'kept'
        ..failed = false
        ..error = '';
    } on Object catch (error) {
      if (error is! SetRejected && error is! FileSystemException && error is! MediumUnreadable)
        rethrow;
      _fail('failed', error);
      status = CipHost.failed;
    }
    await _submit(opened, {'Kind': CipHost.none}, last: true, status: status);
    return status == CipHost.ok;
  }

  /// One restore job; the verdict (accepted, key) or null when not delivered.
  Future<(bool, int)?> _restoreDocument(int operation, Document document,
      {int argument = 0, int status = CipHost.ok}) async {
    final chunks = documentChunks(document);
    final opened = await _open(operation, chunks.first,
        argument: argument, status: status, last: chunks.length == 1);
    if (opened['Accepted'] != 1) return null;
    var job = opened;
    for (var i = 1; i < chunks.length; i++) {
      job = await _submit(job, chunks[i], last: i == chunks.length - 1);
      if (job['Accepted'] != 1) return null;
    }
    for (var attempt = 0; attempt < 50; attempt++) {
      final reply = await port.reply();
      if (reply['JobSequence'] == opened['JobSequence'] && reply['JobPhase'] == CipHost.store) {
        final verdict = (reply['JobBool'] != 0, reply['JobInt'] as int);
        await _submit(reply, {'Kind': CipHost.none}, last: true);
        return verdict;
      }
      if (reply['JobSequence'] != opened['JobSequence']) return null;
      await port.wait();
    }
    return null;
  }

  /// One attempt in the medium's order; every outcome but completion retries later.
  Future<bool> restore() async {
    final facts = await port.facts();
    health.state = 'restoring';
    final losses = <(String, String)>[];
    final models = <(int, Document)>[];
    Document? line, station;
    Document? take(String key, int kind) {
      try {
        final document = medium!.read(key);
        if (document == null) return null;
        final h = document.first;
        if (h['set'] != liveName || h['root'] != facts.root || h['kind'] != kind) {
          losses.add((key, 'document identity differs'));
          return null;
        }
        return document;
      } on DocumentLost catch (error) {
        losses.add((key, error.message));
        return null;
      }
    }

    try {
      if (facts.models) {
        final capacity = facts.capacity != 0 ? facts.capacity : facts.codes.length;
        for (var index = 1; index <= capacity; index++) {
          final document = take('${facts.root}.model$index', 0);
          if (document != null) models.add((index, document));
        }
      }
      if (facts.line) line = take('${facts.root}.line', 2);
      station = take('${facts.root}.station', 1);
    } on MediumUnreadable catch (error) {
      _fail('unreadable', error);
      return false;
    }
    final codes = [...facts.codes];
    Future<bool> send(String key, int operation, Document document,
        {int argument = 0, int status = CipHost.ok}) async {
      final verdict = await _restoreDocument(operation, document,
          argument: argument, status: status);
      if (verdict == null) throw CipHostUnanswered('$key: restore job was not answered');
      final (accepted, diagnostic) = verdict;
      if (accepted) return true;
      if (await port.keyText(diagnostic) == deniedKey)
        throw StateError('$key: the controller session may not load sets');
      losses.add((key, 'controller refused ($diagnostic)'));
      return false;
    }

    try {
      for (final (index, document) in models) {
        final key = '${facts.root}.model$index', code = document.first['model'] as String;
        if (index <= codes.length && codes[index - 1] == code) {
          await send(key, load, document, argument: index);
        } else if (index == codes.length + 1 && index <= facts.capacity) {
          if (await send(key, create, document)) codes.add(code);
        } else {
          losses.add((key, 'the catalog no longer offers this model at its position'));
        }
      }
      if (line != null) await send('${facts.root}.line', load, line);
      station ??= checkedDocument([
        {
          'set': liveName,
          'root': facts.root,
          'schema': 1,
          'configRev': facts.revision,
          'kind': 1,
          'model': '',
          'records': 0,
          'created': 0,
          'clock': 0
        }
      ]);
      final active = station.first['model'] as String;
      final model = codes.indexOf(active) + 1;
      if (!await send('${facts.root}.station', load, station,
          argument: model, status: losses.isEmpty ? CipHost.ok : CipHost.lost)) {
        _fail('restoring', 'station load refused');
        return false;
      }
    } on CipHostUnanswered catch (error) {
      _fail('restoring', error.message);
      return false;
    } on StateError catch (error) {
      _fail('restoring', error.message);
      deniedWhilePermitted = true;
      return false;
    }
    health
      ..state = 'restored'
      ..failed = false
      ..error = ''
      ..losses = losses
      ..restoredAt = DateTime.now().toUtc().toIso8601String();
    written = null; // the restored image becomes the next keep baseline
    return true;
  }
}
