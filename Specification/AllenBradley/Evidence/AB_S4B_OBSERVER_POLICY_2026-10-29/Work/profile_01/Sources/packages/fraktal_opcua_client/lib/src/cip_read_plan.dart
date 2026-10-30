library;

import 'dart:async';
import 'dart:convert';
import 'dart:typed_data';

import 'cip_namespace.dart';
import 'cip_publication.dart';
import 'cip_read_coherence.dart';
import 'cip_read_pool.dart';
import 'cip_template.dart';
import 'cip_transport.dart';

final class _CountDependency {
  final String path;
  final int extent;
  final int? index;
  const _CountDependency(this.path, this.extent, this.index);
}

final class _NativeReadLayout {
  final String path;
  final int bytes, count;
  final int? structureHandle, atomic;
  const _NativeReadLayout(
      this.path, this.bytes, this.count, this.structureHandle, this.atomic);
  CipBatchRead get batch => CipBatchRead(
      cipSymbolPath(path),
      (ByteData(6)
            ..setUint16(0, count, Endian.little)
            ..setUint32(2, 0, Endian.little))
          .buffer
          .asUint8List(),
      bytes + (structureHandle == null ? 2 : 4),
      atomic: atomic,
      structureHandle: structureHandle);
}

final class _PlannedRow {
  final CipPublishedField field;
  final String path;
  final bool element;
  final Set<String>? selection;
  final CipReadCoherenceBinding binding;
  final List<CipBatchRead> requests;
  _PlannedRow(this.field, this.path, this.element, this.selection, this.binding,
      this.requests);
}

final class _SharedRowProof {
  final CipCoherentSample sample;
  final int startedAtUs, finishedAtUs, rows;
  final CipReadTransport replies;
  _SharedRowProof(this.sample, this.startedAtUs, this.finishedAtUs, this.rows,
      this.replies);
}

final class _PackedRequests {
  final requests = <CipBatchRead>[];
  final aliases = <int>[];
  _PackedRequests(Iterable<CipBatchRead> original) {
    final indices = <(int?, int?, int, String, String), int>{};
    for (final r in original) {
      final key = (
        r.atomic,
        r.structureHandle,
        r.replyDataBytes,
        base64Encode(r.path),
        base64Encode(r.data)
      );
      final index = indices.putIfAbsent(key, () {
        requests.add(r);
        return requests.length - 1;
      });
      aliases.add(index);
    }
  }
}

// Only accepted packet replies are replayed, against their exact requests.
// This adapter has no socket and never performs a fallback or a write.
final class _BatchReplies implements CipReadTransport {
  final List<CipBatchRead> requests;
  final List<CipReply> replies;
  var _next = 0;
  _BatchReplies(this.requests, this.replies);
  @override
  Future<CipReply> request(int service, Uint8List path,
      [Uint8List? data]) async {
    if (_next >= requests.length)
      throw const FormatException('Unplanned batched tag read.');
    final expected = requests[_next];
    bool equal(Uint8List a, Uint8List? b) =>
        b != null &&
        a.length == b.length &&
        List.generate(a.length, (i) => a[i] == b[i]).every((v) => v);
    if (service != 0x52 ||
        !equal(expected.path, path) ||
        !equal(expected.data, data))
      throw const FormatException('Batched tag read differs from its plan.');
    return replies[_next++];
  }

  @override
  void abort() {}
  @override
  Future<void> close() async {}
}

/// Bounded row acquisition over the canonical schema. Fragment members of one
/// row share a guard. Nested collections get their own rows; a document is not
/// represented as one atomic sample. No observation frame is consulted.
final class CipReadPlan {
  final CipPublication publication;
  final CipReadTransport wire;
  final int Function() _clockUs;
  final CipReadCoherenceGuard guard;
  bool _coalescingUnavailable = false;
  // A packet may fit the connection while its service cost exceeds the
  // publication window. Learn a smaller packing bound after an exhausted
  // proof; never spend another attempt on the same rows in that acquisition.
  final Map<(String, String, int), int> _coalescedRowLimits = {};
  (String, String, int) _coalescingKey(CipReadCoherenceBinding binding) => (
        binding.canonicalPrefix,
        binding.revisionSymbol,
        binding.mutationPeriodUs
      );
  final Map<String, Object?> _values = {};
  final Map<String, String> _types = {};
  final Map<String, Map<String, Object?>> _samples = {};
  final Map<String, int> _counts = {};
  final Map<String, int> _tokens = {}, _progress = {};
  final Map<String, int> _revisionFinishedAt = {};
  final Map<String, int> _countTokens = {};
  final Map<String, List<CipPublishedField>> _childCache = {};
  final Map<String, bool> _arrayCache = {};
  late final Set<String> _countSchemas = {
    for (final field in publication.fields.values)
      if (field.annotation['countPath'] is String)
        field.annotation['countPath'] as String
  };
  final List<Map<String, Object?>> acquisitions = [];
  Set<String> slowPaths = {}, excludedPaths = {};
  int _lastSlow = -1000000000;
  bool _refreshSlow = true;
  List<List<_PlannedRow>> _slowGroups = [];
  int _slowCursor = 0;
  int? _slowStartedAtUs;
  Set<String>? _slowProfile, _excludedProfile;
  // Trace-only walk summary (WP4b.3): per-phase group counts and durations of
  // the last full acquire, consumed by the engine's snapshot trace.
  String? _phaseLabel;
  Map<String, Object?>? lastWalkTrace;
  static const _pollPeriodMs = 250;
  static const _fastGoodMs = 1000, _fastExpiryMs = 3000;
  static const _slowPeriodMs = 5000, _slowGoodMs = 7500, _slowExpiryMs = 15000;
  static const slowIntervalUs = _slowPeriodMs * 1000;
  static const freshnessBudget = <String, int>{
    'schemaVersion': 1,
    'pollPeriodMs': _pollPeriodMs,
    'fastGoodMs': _fastGoodMs,
    'fastExpiryMs': _fastExpiryMs,
    'slowPeriodMs': _slowPeriodMs,
    'slowGoodMs': _slowGoodMs,
    'slowExpiryMs': _slowExpiryMs
  };

  CipReadPlan(this.publication, this.wire,
      {int Function()? clockUs, CipReadCoherenceGuard? guard})
      : _clockUs = clockUs ?? _clock(),
        // Several paced attempts can fall within one active publication
        // phase. Keep the total deadline and each row's proof window bounded.
        guard = guard ?? CipReadCoherenceGuard(maxAttempts: 20) {
    if (publication.manifest.minor < 7)
      throw const FormatException(
          'Live CIP requires explicit coherence bindings.');
  }
  static int Function() _clock() {
    final clock = Stopwatch()..start();
    return () => clock.elapsedMicroseconds;
  }

  void refreshSlow() => _refreshSlow = true;

  Future<bool> proveProgress() async {
    final bindings = {
      for (final b in publication.manifest.coherence) b.revisionSymbol: b
    };
    for (final b in bindings.values) {
      int? before;
      var proved = false;
      for (var attempt = 0; attempt < 100; attempt++) {
        final started = _clockUs();
        final token = await CipNamespace.readDint(wire, b.revisionSymbol);
        if (token < 0 || token > 2147483646)
          throw const FormatException('Invalid publisher counter.');
        if (token.isEven) {
          if (before != null && before != token) {
            _tokens[b.revisionSymbol] = token;
            _progress[b.revisionSymbol] = started;
            _revisionFinishedAt[b.revisionSymbol] = _clockUs();
            proved = true;
            break;
          }
          before = token;
        }
        await Future<void>.delayed(const Duration(milliseconds: 1));
      }
      if (!proved) return false;
    }
    return true;
  }

  List<CipPublishedField> _children(String prefix) => _childCache.putIfAbsent(
      prefix,
      () => publication.fields.values
          .where((f) =>
              !f.commandOnly &&
              f.path.startsWith('$prefix/') &&
              !f.path.substring(prefix.length + 1).contains('/'))
          .toList());

  List<_CountDependency> _dependencies(
      CipPublishedField field, String concrete) {
    final actual = concrete.split('/'), schema = field.path.split('/');
    final result = <_CountDependency>[];
    for (var i = 0; i < schema.length; i++) {
      final key =
          schema.take(i + 1).join('/').replaceFirst(RegExp(r'\[\*\]$'), '');
      final array = publication.fields[key];
      if (array == null ||
          !array.member.isArray ||
          array.annotation['countPath'] == null) continue;
      final match = RegExp(r'\[(-?\d+)\]$').firstMatch(actual[i]);
      result.add(_CountDependency(
          '${actual.take(i).join('/')}/${(array.annotation['countPath'] as String).split('/').last}',
          array.annotation['elementCount'] as int,
          match == null
              ? null
              : int.parse(match[1]!) -
                  (array.annotation['lowerBound'] as int)));
    }
    return result;
  }

  String _physicalPath(CipFieldSource source, String concrete) {
    final actual =
        concrete.substring(source.record.target.length + 1).split('/');
    final parts = <String>[source.record.source];
    var schema = source.record.target;
    if (actual.length != source.chain.length)
      throw const FormatException('Physical/logical chain depth differs.');
    for (var i = 0; i < source.chain.length; i++) {
      final m = source.chain[i];
      schema += '/${m.name}';
      var component = m.name;
      final index = RegExp(r'\[(-?\d+)\]$').firstMatch(actual[i]);
      if (index != null) {
        final a = publication.fields[schema]!.annotation;
        final physical = int.parse(index[1]!) - (a['lowerBound'] as int);
        if (physical < 0 || physical >= (a['elementCount'] as int))
          throw const FormatException(
              'Logical index exceeds published extent.');
        component += '[$physical]';
      }
      parts.add(component);
      if (m.isArray) schema += '[*]';
    }
    return parts.join('.');
  }

  _NativeReadLayout _layout(CipFieldSource source, String concrete,
      {bool element = false, int? countOverride}) {
    final m = source.member,
        count = countOverride ?? (m.isArray && !element ? m.info : 1);
    final size = m.isStructure
        ? publication.decoder.templates[m.handle]!.byteSize * count
        : m.atomic == 0xc1
            ? (m.isArray && !element ? ((count + 31) ~/ 32) * 4 : 1)
            : CipTemplateDecoder.atomicByteSize(m.atomic) * count;
    return _NativeReadLayout(
        _physicalPath(source, concrete),
        size,
        count,
        m.isStructure
            ? publication.namespace.templates[m.handle]!.structureHandle
            : null,
        m.isStructure ? null : m.atomic);
  }

  Future<Object> _read(CipFieldSource source, String concrete,
      {bool element = false,
      int? countOverride,
      CipReadTransport? transport}) async {
    final native = _layout(source, concrete,
        element: element, countOverride: countOverride);
    final bytes = await CipNamespace.readExact(
        transport ?? wire, native.path, native.bytes,
        structureHandle: native.structureHandle,
        atomic: native.atomic,
        elementCount: native.count);
    final m = source.member;
    final layout = countOverride == null
        ? m
        : CipTemplateMember(m.name, countOverride, m.code, m.offset);
    return publication.decoder.decodeMember(layout, bytes, element: element);
  }

  Future<int> _count(String path, {CipReadTransport? transport}) async {
    final field = _countField(path);
    final raw = await _read(field.sources.single, path, transport: transport);
    if (raw is BigInt && raw >= BigInt.zero && raw <= BigInt.from(100000))
      return raw.toInt();
    if (raw is! int)
      throw const FormatException('Count source is not integral.');
    return raw;
  }

  CipPublishedField _countField(String path) {
    final field = publication.fields[cipSchemaKey(path)];
    if (field == null ||
        field.commandOnly ||
        field.member.isStructure ||
        field.member.isArray ||
        field.sources.length != 1)
      throw const FormatException('Invalid count source.');
    return field;
  }

  int? _nativeCount(CipPublishedField field, String concrete, bool element,
      Map<String, int> counts) {
    final m = field.member;
    if (!m.isArray || element || m.isStructure) return null;
    final a = field.annotation;
    var logical = a['elementCount'] as int;
    if (a['countPath'] != null)
      logical = counts[
          '${concrete.substring(0, concrete.lastIndexOf('/'))}/${(a['countPath'] as String).split('/').last}']!;
    if (a['indices'] != null)
      logical = (a['indices'] as List).isEmpty
          ? 0
          : ((a['indices'] as List).last as int) + 1;
    return a['logicalType'] == 'BOOL' && m.atomic == 0xd3
        ? (logical + 31) ~/ 32
        : logical;
  }

  List<CipBatchRead>? _batchPlan(
      int? capacity,
      List<_CountDependency> dependencies,
      List<(CipPublishedField, String, bool)> parts,
      {int minimumReads = 2}) {
    if (capacity == null) return null;
    final result = <CipBatchRead>[];
    for (final dependency in dependencies) {
      final field = _countField(dependency.path);
      result.add(_layout(field.sources.single, dependency.path).batch);
    }
    for (final part in parts) {
      final m = part.$1.member;
      // A variable-length primitive read needs the count returned inside this
      // very proof. Keep its original reader rather than planning from cache.
      if (m.isArray &&
          !m.isStructure &&
          !part.$3 &&
          part.$1.annotation['countPath'] != null) return null;
      final count = _nativeCount(part.$1, part.$2, part.$3, {});
      if (count == 0) continue;
      for (final source in part.$1.sources) {
        final native =
            _layout(source, part.$2, element: part.$3, countOverride: count);
        if (native.bytes + (native.structureHandle == null ? 2 : 4) > 4000)
          return null;
        result.add(native.batch);
      }
    }
    if (result.length < minimumReads) return null;
    return cipEncodeReadBatch(result, capacity) == null ? null : result;
  }

  bool _wanted(String path, Set<String>? requested) =>
      requested == null ||
      requested.any((p) =>
          p == path ||
          p.startsWith('$path/') ||
          p.startsWith('$path[') ||
          path.startsWith('$p/'));
  // Tier sets contain thousands of concrete leaves. Check the bounded path's
  // ancestors rather than scanning that entire set for every row and value.
  bool _within(String path, Set<String> scopes) {
    if (scopes.contains(path)) return true;
    for (var i = path.length - 1; i > 0; i--) {
      final code = path.codeUnitAt(i);
      if ((code == 47 || code == 91) && scopes.contains(path.substring(0, i))) {
        return true;
      }
    }
    return false;
  }

  bool _excluded(String path) => _within(path, excludedPaths);
  bool _slow(String path) => _within(path, slowPaths);

  void _recordCount(String path, int count, int revision) {
    final previous = _countTokens[path];
    if (previous != null && previous == revision && _counts[path] != count) {
      wire.abort();
      throw const FormatException(
          'Count changed within one publication revision.');
    }
    if (previous == null ||
        previous == revision ||
        cipRevisionIsLater(revision, previous)) {
      _countTokens[path] = revision;
      _counts[path] = count;
    }
  }

  Future<void> _group(CipPublishedField field, String path,
      {bool element = false, Set<String>? selection}) async {
    final grouped = wire;
    if (grouped is CipGroupedReadTransport) {
      return grouped.withGroup((transport) => _groupOn(transport, field, path,
          element: element, selection: selection));
    }
    return _groupOn(wire, field, path, element: element, selection: selection);
  }

  Future<void> _groupMany(List<_PlannedRow> rows,
      {void Function(Future<void> Function())? deferDecode}) async {
    final limit = _coalescedRowLimits[_coalescingKey(rows.first.binding)];
    if (limit != null && rows.length > limit) {
      // Queued work and cached slow chunks can predate the learned bound.
      // These disjoint rows have not used an attempt in this acquisition.
      for (var start = 0; start < rows.length; start += limit) {
        final end = start + limit < rows.length ? start + limit : rows.length;
        await _groupMany(rows.sublist(start, end), deferDecode: deferDecode);
      }
      return;
    }
    if (_coalescingUnavailable || rows.length == 1) {
      for (final row in rows) {
        await _group(row.field, row.path,
            element: row.element, selection: row.selection);
      }
      return;
    }
    final grouped = wire as CipGroupedReadTransport;
    await grouped.withGroup((transport) async {
      if (transport is! CipBatchReadTransport) {
        throw const FormatException(
            'Row-batch capacity lacks a batch transport.');
      }
      // Identical typed dependencies need one native read within this proven
      // window. Every logical row retains its exact request/reply cursor.
      final packet = _PackedRequests([for (final row in rows) ...row.requests]);
      final requests = packet.requests;
      final started = _clockUs();
      var candidateStarted = started, revisionStarted = started;
      List<CipReply> replies = [];
      var fallback = false;
      final sample = await guard.read(
          binding: rows.first.binding,
          readRevision: (symbol) {
            revisionStarted = _clockUs();
            return CipNamespace.readDint(transport, symbol);
          },
          readGroup: () async {
            candidateStarted = revisionStarted;
            try {
              replies = await transport.readBatch(requests);
            } on CipBatchUnavailable {
              fallback = true;
              rethrow;
            }
            if (replies.length != requests.length) {
              throw const FormatException('Coalesced row reply count differs.');
            }
            if (replies.any((r) => r.status == 6)) {
              fallback = true;
              throw const CipBatchUnavailable();
            }
            for (final reply in replies) {
              reply.requireSuccess();
            }
            return Uint8List(0);
          });
      final finished = _clockUs();
      if (!fallback && sample.quality == CipSampleQuality.uncertain) {
        final smaller = (rows.length + 1) ~/ 2;
        final key = _coalescingKey(rows.first.binding);
        final prior = _coalescedRowLimits[key];
        if (prior == null || smaller < prior) {
          _coalescedRowLimits[key] = smaller;
        }
      }
      try {
        if (fallback) {
          // A refused/partial packet consumed an attempt for every row.
          // Individual fallback gets only the remaining original attempts
          // and deadline, including time spent on preceding fallback rows.
          _coalescingUnavailable = true;
          final attempts = guard.maxAttempts - sample.attempts;
          for (final row in rows) {
            final remaining =
                guard.timeout.inMicroseconds - (_clockUs() - started);
            if (attempts <= 0 || remaining <= 0) {
              wire.abort();
              throw const FormatException(
                  'Coalesced fallback budget exhausted.');
            }
            await _groupOn(transport, row.field, row.path,
                element: row.element,
                selection: row.selection,
                boundedGuard: CipReadCoherenceGuard(
                    maxAttempts: attempts,
                    timeout: Duration(microseconds: remaining),
                    clockUs: _clockUs),
                priorAttempts: sample.attempts,
                overallStartedAtUs: started);
          }
          return;
        }
        if (sample.quality == CipSampleQuality.bad) {
          throw const FormatException(
              'CIP row acquisition failed; rediscovery required.');
        }
        Future<void> decode() async {
          try {
            var offset = 0;
            for (final row in rows) {
              final end = offset + row.requests.length;
              // Each row gets its own exact-reply cursor: a count shrink may
              // withdraw that row without consuming its now-ineligible body.
              final cached = _BatchReplies(
                  row.requests,
                  sample.quality == CipSampleQuality.good
                      ? [
                          for (var i = offset; i < end; i++)
                            replies[packet.aliases[i]]
                        ]
                      : []);
              // The decoder has only captured replies, never a live socket.
              await _groupOn(cached, row.field, row.path,
                  element: row.element,
                  selection: row.selection,
                  shared: _SharedRowProof(
                      sample, candidateStarted, finished, rows.length, cached));
              offset = end;
            }
          } on Object {
            wire.abort();
            rethrow;
          }
        }

        if (deferDecode == null) {
          await decode();
        } else {
          deferDecode(decode);
        }
      } on Object {
        wire.abort();
        rethrow;
      }
    });
  }

  List<(CipPublishedField, String, bool)> _parts(CipPublishedField field,
      String path, bool element, Set<String>? selection) {
    final parts = <(CipPublishedField, String, bool)>[];
    void select(CipPublishedField f, String p, bool one) {
      final children = f.member.isStructure &&
              publication
                      .decoder.templates[f.member.handle]!.stringByteCapacity ==
                  null
          ? _children(f.path + (f.member.isArray ? '[*]' : ''))
          : <CipPublishedField>[];
      if (selection != null &&
          !selection.any((s) => s == p || p.startsWith('$s/')) &&
          children.isNotEmpty) {
        for (final child in children)
          if (_wanted('$p/${child.member.name}', selection))
            select(child, '$p/${child.member.name}', false);
      } else {
        parts.add((f, p, one));
      }
    }

    select(field, path, element);
    return parts;
  }

  Future<void> _groupOn(
      CipReadTransport transport, CipPublishedField field, String path,
      {bool element = false,
      Set<String>? selection,
      _SharedRowProof? shared,
      CipReadCoherenceGuard? boundedGuard,
      int priorAttempts = 0,
      int? overallStartedAtUs}) async {
    final parts = _parts(field, path, element, selection);
    if (parts.isEmpty) return;
    final dependencies = _dependencies(field, path),
        binding =
            publication.manifest.coherence.singleWhere((b) => b.covers(path));
    var batch = _batchPlan(
        transport is CipBatchReadTransport ? transport.readBatchBytes : null,
        dependencies,
        parts);
    var groupTransport = shared?.replies ?? transport;
    Map<String, Object?> candidate = {};
    Map<String, String> types = {};
    Map<String, int> counts = {};
    var candidateStartedAtUs = shared?.startedAtUs ?? _clockUs(),
        revisionStartedAtUs = _clockUs();
    Future<Uint8List> readBody() async {
      candidateStartedAtUs = shared?.startedAtUs ?? revisionStartedAtUs;
      // Counter requests complete outside this body packet. No MSP
      // execution-order or whole-packet atomicity assumption is needed.
      groupTransport = shared?.replies ?? transport;
      final requests = batch;
      if (shared == null && requests != null) {
        List<CipReply>? replies;
        try {
          replies =
              await (transport as CipBatchReadTransport).readBatch(requests);
        } on CipBatchUnavailable {
          batch = null;
        }
        if (replies != null) {
          if (replies.length != requests.length)
            throw const FormatException('Batched row reply count differs.');
          if (replies.any((reply) => reply.status == 6)) {
            // Fallback remains in this original attempt/window/deadline,
            // including the discarded packet.
            batch = null;
          } else {
            groupTransport = _BatchReplies(requests, replies);
          }
        }
      }
      candidate = {};
      types = {};
      counts = {};
      for (final d in dependencies) {
        final n = await _count(d.path, transport: groupTransport);
        if (n < 0 || n > d.extent)
          throw const FormatException('Live count exceeds declared extent.');
        counts[d.path] = n;
      }
      if (dependencies
          .any((d) => d.index != null && d.index! >= counts[d.path]!))
        return Uint8List(0);
      for (final requested in parts)
        for (final source in requested.$1.sources) {
          final nativeCount =
              _nativeCount(requested.$1, requested.$2, requested.$3, counts);
          if (nativeCount == 0) continue;
          final value = await _read(source, requested.$2,
              element: requested.$3,
              countOverride: nativeCount,
              transport: groupTransport);
          final part = publication.projectSubtree(
              requested.$2, source.member, value, counts,
              element: requested.$3);
          final next = Map<String, Object?>.from(part['values'] as Map);
          if (next.keys.any(candidate.containsKey))
            throw const FormatException('Colliding row leaves.');
          candidate.addAll(next);
          types.addAll(Map<String, String>.from(part['types'] as Map));
        }
      return Uint8List(0);
    }

    final CipCoherentSample sample;
    if (shared != null) {
      sample = shared.sample;
      if (sample.quality == CipSampleQuality.good) await readBody();
    } else {
      sample = await (boundedGuard ?? guard).read(
          binding: binding,
          readRevision: (symbol) async {
            revisionStartedAtUs = _clockUs();
            return CipNamespace.readDint(transport, symbol);
          },
          readGroup: readBody);
    }
    final now = _clockUs();
    acquisitions.add({
      'path': path,
      'quality': sample.quality.name,
      'reason': sample.reason,
      'attempts': sample.attempts + priorAttempts,
      'acquisitionUs': overallStartedAtUs == null
          ? sample.acquisitionUs
          : now - overallStartedAtUs,
      if (shared != null) 'sharedRows': shared.rows,
      if (priorAttempts != 0) 'fallbackAttempts': priorAttempts,
      if (_phaseLabel != null) 'phase': _phaseLabel
    });
    if (acquisitions.length > 10000) acquisitions.removeAt(0);
    if (sample.quality == CipSampleQuality.bad) {
      // A timed-out read may still be in flight. It cannot share a socket with
      // the next row or consume a reply after this proof has ended.
      wire.abort();
      throw const FormatException(
          'CIP row acquisition failed; rediscovery required.');
    }
    final previous = _samples.keys
        .where((p) => parts.any((part) =>
            p == part.$2 ||
            p.startsWith('${part.$2}/') ||
            p.startsWith('${part.$2}[')))
        .toSet();
    if (sample.quality != CipSampleQuality.good) {
      for (final p in previous) {
        _values.remove(p);
        _samples[p] = {
          ...?_samples[p],
          'type': _types[p],
          'status': 0x40000000,
          'reason': sample.reason,
          'coherenceAttempts': sample.attempts + priorAttempts,
          'coherenceAcquisitionUs': overallStartedAtUs == null
              ? sample.acquisitionUs
              : now - overallStartedAtUs,
          'coherenceFailures': sample.failures
        }..remove('value');
      }
      return;
    }
    final symbol = binding.revisionSymbol, token = sample.revision!;
    // An older parallel row must not renew progress after a newer observation.
    final previousToken = _tokens[symbol];
    if (previousToken != null &&
        token != previousToken &&
        !cipRevisionIsLater(token, previousToken) &&
        candidateStartedAtUs > (_revisionFinishedAt[symbol] ?? now)) {
      wire.abort();
      throw const FormatException(
          'Publication counter restarted; rediscovery required.');
    }
    if (previousToken == null || cipRevisionIsLater(token, previousToken)) {
      if (previousToken != null &&
          candidateStartedAtUs > (_progress[symbol] ?? -1))
        _progress[symbol] = candidateStartedAtUs;
      _tokens[symbol] = token;
    }
    if (_tokens[symbol] == token)
      _revisionFinishedAt[symbol] = shared?.finishedAtUs ?? now;
    final progressing = _progress.containsKey(symbol) &&
        now - _progress[symbol]! < _fastGoodMs * 1000;
    counts.forEach((p, n) => _recordCount(p, n, token));
    for (final e
        in candidate.entries.where((e) => e.key.endsWith('/Status/Name'))) {
      final module = e.key.substring(0, e.key.length - '/Status/Name'.length);
      if (e.value != module.replaceAll('/', '.'))
        throw const FormatException(
            'Module identity differs from browse path.');
      final kind = candidate['$module/Status/ModuleType'];
      if (kind != null &&
          !(publication.roots.contains(module) ? const {1} : const {2, 3})
              .contains(kind))
        throw const FormatException('Invalid module tier.');
    }
    for (final p in previous.difference(candidate.keys.toSet())) {
      _values.remove(p);
      _types.remove(p);
      _samples.remove(p);
    }
    for (final e in candidate.entries) {
      _types[e.key] = types[e.key]!;
      _samples[e.key] = {
        'type': types[e.key],
        'status': progressing ? 0 : 0x40000000,
        'sampledAtUs': candidateStartedAtUs,
        'revision': token,
        'acquisitionUs': sample.acquisitionUs,
        'acceptedWindowUs': sample.acceptedWindowUs,
        if (!progressing) 'reason': 'publisher-progress-unproved',
        if (progressing) 'value': e.value
      };
      if (progressing)
        _values[e.key] = e.value;
      else
        _values.remove(e.key);
      if (e.value is int && _countSchemas.contains(cipSchemaKey(e.key)))
        _recordCount(e.key, e.value as int, token);
    }
  }

  bool _fitsBatch(List<_PlannedRow> rows, _PlannedRow row, int? capacity) =>
      capacity != null &&
      rows.length < cipMaximumBatchReads &&
      rows.length <
          (_coalescedRowLimits[_coalescingKey(row.binding)] ??
              cipMaximumBatchReads) &&
      row.requests.isNotEmpty &&
      rows.first.requests.isNotEmpty &&
      rows.first.binding.revisionSymbol == row.binding.revisionSymbol &&
      rows.first.binding.canonicalPrefix == row.binding.canonicalPrefix &&
      rows.first.binding.mutationPeriodUs == row.binding.mutationPeriodUs &&
      cipEncodeReadBatch(
              _PackedRequests(
                      [for (final r in rows) ...r.requests, ...row.requests])
                  .requests,
              capacity) !=
          null;

  /// Whether a slow sweep has remaining rows or its heartbeat is due.
  bool get slowAcquisitionDue =>
      _slowGroups.isNotEmpty &&
      (_refreshSlow ||
          _slowCursor != 0 ||
          _clockUs() - _lastSlow >= slowIntervalUs);

  /// One bounded native group between fast snapshots, on the same serialized
  /// worker and the same row owner. A new sweep is due from its start time;
  /// finishing a long sweep cannot add another full slow-period gap.
  Future<void> acquireSlowChunk() async {
    if (!slowAcquisitionDue) return;
    if (_refreshSlow) {
      _slowCursor = 0;
      _slowStartedAtUs = null;
    }
    if (_slowCursor == 0 &&
        !_refreshSlow &&
        _clockUs() - _lastSlow < slowIntervalUs) return;
    _refreshSlow = false;
    _slowStartedAtUs ??= _clockUs();
    if (_slowGroups.isNotEmpty) {
      await _groupMany(_slowGroups[_slowCursor]);
      _slowCursor++;
    }
    if (_slowCursor >= _slowGroups.length) {
      _lastSlow = _slowStartedAtUs!;
      _slowStartedAtUs = null;
      _slowCursor = 0;
    }
  }

  Future<void> acquire({Set<String>? paths, bool fastOnly = false}) async {
    final due =
        !fastOnly && (_refreshSlow || _clockUs() - _lastSlow >= slowIntervalUs);
    final slowGroups = <List<_PlannedRow>>[];
    final slowPending = <_PlannedRow>[];
    final walkStart = acquisitions.length;
    final seenCounts = <String>{};
    final statuses = <(CipPublishedField, String, Set<String>)>[];
    final identityPaths = <String>{};
    var statusPhase = false;
    var discoveringCounts = false, queuedCount = false;
    // On a slow-due walk the phases split the leaf groups: all-slow groups
    // first, then every group with a fast leaf, so fast rows do not age
    // behind slow I/O. Null outside those phases; see acquire() below.
    bool? slowOnlyPhase;
    final grouped = wire;
    final concurrency =
        grouped is CipGroupedReadTransport ? grouped.groupConcurrency : 1;
    if (concurrency < 1 || concurrency > 4)
      throw const FormatException('Invalid CIP group concurrency.');
    final workQueue = <Future<void> Function()>[];
    final decodeQueue = <Future<void> Function()>[];
    final pending = <_PlannedRow>[];
    final capacity = grouped is CipBatchedGroupReadTransport
        ? grouped.groupBatchBytes
        : null;
    Future<void> drainActive() async {
      // Compile this phase before opening any guard. Path/layout validation
      // and packet construction must not steal another row's I/O window.
      final work = List<Future<void> Function()>.of(workQueue);
      workQueue.clear();
      var next = 0;
      Object? failure;
      StackTrace? failureStack;
      Future<void> worker() async {
        while (failure == null && next < work.length) {
          final task = work[next++];
          try {
            await task();
          } on Object catch (error, stack) {
            failure ??= error;
            failureStack ??= stack;
          }
        }
      }

      await Future.wait(
          [for (var i = 0; i < concurrency && i < work.length; i++) worker()]);
      if (failure != null) Error.throwWithStackTrace(failure!, failureStack!);
      // Flatten captured bytes only after the phase's wire proofs finish.
      // Decoder CPU must not consume another connection's proof window.
      for (final decode in decodeQueue) {
        await decode();
      }
      decodeQueue.clear();
    }

    Future<void> dispatch(Future<void> Function() work) async {
      workQueue.add(work);
    }

    Future<void> flushPending() async {
      if (pending.isEmpty) return;
      final rows = List<_PlannedRow>.of(pending);
      pending.clear();
      await dispatch(() => _groupMany(rows, deferDecode: decodeQueue.add));
    }

    Future<void> flush() async {
      await flushPending();
      await drainActive();
    }

    Future<void> acquireGroup(CipPublishedField field, String concrete,
        {bool element = false, Set<String>? selection}) async {
      // A targeted read uses the same bounded leases and external proof as a
      // cyclic read; selection still limits its body to the requested leaves.
      final requests = !_coalescingUnavailable
          ? _batchPlan(capacity, _dependencies(field, concrete),
              _parts(field, concrete, element, selection),
              minimumReads: 1)
          : null;
      if (requests == null) {
        await flushPending();
        await dispatch(() =>
            _group(field, concrete, element: element, selection: selection));
        return;
      }
      final binding =
          publication.manifest.coherence.singleWhere((b) => b.covers(concrete));
      final row =
          _PlannedRow(field, concrete, element, selection, binding, requests);
      if (pending.isNotEmpty && !_fitsBatch(pending, row, capacity)) {
        await flushPending();
      }
      pending.add(row);
      // Packet bounds cover both directions/read count; a previously exhausted
      // binding can additionally require smaller groups for its proof window.
    }

    Future<void> visit(CipPublishedField field, String concrete,
        {bool element = false}) async {
      if (!_wanted(concrete, paths) || paths == null && _excluded(concrete))
        return;
      final m = field.member;
      if (m.isArray && m.isStructure && !element) {
        final a = field.annotation,
            extent = a['elementCount'] as int,
            lower = a['lowerBound'] as int;
        var count = extent;
        if (a['countPath'] != null) {
          final cp =
              '${concrete.substring(0, concrete.lastIndexOf('/'))}/${(a['countPath'] as String).split('/').last}';
          if (seenCounts.add(cp)) {
            if (discoveringCounts) {
              // Collect independent routing counts before expanding their
              // arrays. Descendant counts wait for the next drained level.
              await acquireGroup(publication.fields[cipSchemaKey(cp)]!, cp);
              queuedCount = true;
              return;
            } else {
              await flush();
              await _group(publication.fields[cipSchemaKey(cp)]!, cp);
            }
          }
          final n = _counts[cp];
          if (n == null) return;
          if (n < 0 || n > extent)
            throw const FormatException('Live logical count exceeds extent.');
          count = n;
        }
        final indices = a['indices'] == null
            ? List.generate(count, (i) => i)
            : List<int>.from(a['indices'] as List);
        for (final index in indices)
          await visit(field, '$concrete[${lower + index}]', element: true);
        return;
      }
      final prefix = field.path + (m.isArray ? '[*]' : '');
      final children = m.isStructure &&
              publication.decoder.templates[m.handle]!.stringByteCapacity ==
                  null
          ? _children(prefix)
          : <CipPublishedField>[];
      final hasArrays = _arrayCache.putIfAbsent(
          field.path,
          () => children.any((f) =>
              f.member.isArray ||
              publication.fields.values.any(
                  (d) => d.path.startsWith('${f.path}/') && d.member.isArray)));
      if (discoveringCounts && !hasArrays) return;
      // Keep the Core discovery header small. Large diagnostics and device
      // data must not turn an unavailable body row into a missing module.
      // These exact fields are read once, together, at the end of the walk.
      final statusPrefix =
          field.path.endsWith('/Status') ? field.path : '${field.path}/Status';
      if (paths == null &&
          !statusPhase &&
          m.isStructure &&
          publication.fields.containsKey('$statusPrefix/Name') &&
          publication.fields.containsKey('$statusPrefix/ModuleType')) {
        final status = publication.fields[statusPrefix]!;
        final actual =
            field.path.endsWith('/Status') ? concrete : '$concrete/Status';
        if (!statuses.any((s) => s.$2 == actual)) {
          final selected = <String>{
            for (final name in [
              'Name',
              'ModuleType',
              'State',
              'ConfigRev',
              'TypeKey'
            ])
              if (publication.fields.containsKey('$statusPrefix/$name') &&
                  !_excluded('$actual/$name'))
                '$actual/$name'
          };
          identityPaths.addAll(selected);
          if (selected.isNotEmpty) statuses.add((status, actual, selected));
        }
      }
      if (hasArrays) {
        for (final child in children)
          await visit(child, '$concrete/${child.member.name}');
      } else {
        final leaves = m.isArray && !m.isStructure && !element
            ? <String>{
                for (final index in field.annotation['indices'] as List? ??
                    List.generate(
                        field.annotation['elementCount'] as int, (i) => i))
                  '$concrete[${(field.annotation['lowerBound'] as int) + (index as int)}]'
              }
            : children.isEmpty
                ? <String>{concrete}
                : {
                    for (final f in publication.fields.values)
                      if (!f.commandOnly &&
                          f.path.startsWith('$prefix/') &&
                          (!f.member.isStructure ||
                              publication.decoder.templates[f.member.handle]!
                                      .stringByteCapacity !=
                                  null))
                        concrete + f.path.substring(prefix.length)
                  };
        // Tiers name logical leaves, including primitive-array elements. An
        // excluded sibling is not a fast consumer of the native read group.
        final consumed = paths == null
            ? leaves
                .where((p) => !_excluded(p) && !identityPaths.contains(p))
                .toSet()
            : leaves;
        if (paths == null && consumed.isEmpty) return;
        final allSlow = consumed.every(_slow);
        final selection =
            paths ?? (consumed.length != leaves.length ? consumed : null);
        if (selection?.isEmpty == true) return;
        if (fastOnly && allSlow) {
          final binding = publication.manifest.coherence
              .singleWhere((b) => b.covers(concrete));
          final row = _PlannedRow(
              field,
              concrete,
              element,
              selection,
              binding,
              _batchPlan(capacity, _dependencies(field, concrete),
                      _parts(field, concrete, element, selection),
                      minimumReads: 1) ??
                  []);
          if (slowPending.isNotEmpty &&
              !_fitsBatch(slowPending, row, capacity)) {
            slowGroups.add(List.of(slowPending));
            slowPending.clear();
          }
          if (row.requests.isEmpty) {
            slowGroups.add([row]);
          } else {
            slowPending.add(row);
          }
          return;
        }
        if (paths == null && !due && allSlow) return;
        // A slow-due walk reads all-slow groups in the slow phase and every
        // other group in the fast phase; the request multiset is unchanged.
        if (paths == null &&
            due &&
            slowOnlyPhase != null &&
            slowOnlyPhase != allSlow) {
          return;
        }
        await acquireGroup(field, concrete,
            element: element, selection: selection);
      }
    }

    Future<void> walkRecords() async {
      for (final target in publication.records
          .where((r) => !r.fragment)
          .map((r) => r.target)) {
        for (final child in _children(target))
          await visit(child, '$target/${child.member.name}');
      }
    }

    try {
      if (capacity != null) {
        discoveringCounts = true;
        do {
          queuedCount = false;
          await walkRecords();
          await flush();
        } while (queuedCount);
        discoveringCounts = false;
      }
      if (paths == null && due && slowPaths.isNotEmpty && _tokens.isNotEmpty) {
        // The slow phase completes (and its requests drain) before any fast
        // group starts, so the oldest fast row ages only behind fast and
        // Status work. Count reads stay once per walk through seenCounts.
        // A plan with no observed revision yet walks unphased: the first
        // acquisition of a walk proves progress, and a slow group would
        // otherwise carry that Uncertainty for a whole slow interval.
        slowOnlyPhase = true;
        _phaseLabel = 'slow';
        await walkRecords();
        await flush();
        slowOnlyPhase = false;
        _phaseLabel = 'fast';
        await walkRecords();
        await flush();
        slowOnlyPhase = null;
        _phaseLabel = null;
      } else {
        await walkRecords();
        await flush();
      }
      statusPhase = true;
      _phaseLabel = 'status';
      for (final status in statuses)
        await acquireGroup(status.$1, status.$2, selection: status.$3);
      await flush();
    } on Object {
      // Execution drains its started rows before throwing. A planning refusal
      // discards work that has not opened a guard or borrowed a connection.
      _phaseLabel = null;
      workQueue.clear();
      decodeQueue.clear();
      rethrow;
    }
    _phaseLabel = null;
    // A parent count can shrink between independently coherent rows. Remove
    // departed rows, rather than retaining stale data at now-ineligible paths.
    for (final entry in _counts.entries) {
      final schema = cipSchemaKey(entry.key);
      for (final array in publication.fields.values
          .where((f) => f.annotation['countPath'] == schema)) {
        final prefix =
            '${entry.key.substring(0, entry.key.lastIndexOf('/'))}/${array.member.name}[';
        final lower = array.annotation['lowerBound'] as int;
        final gone = _samples.keys
            .where((p) =>
                p.startsWith(prefix) &&
                int.parse(p.substring(
                            prefix.length, p.indexOf(']', prefix.length))) -
                        lower >=
                    entry.value)
            .toList();
        for (final p in gone) {
          _values.remove(p);
          _types.remove(p);
          _samples.remove(p);
        }
      }
    }
    if (fastOnly) {
      if (slowPending.isNotEmpty) slowGroups.add(List.of(slowPending));
      if (!identical(_slowProfile, slowPaths) ||
          !identical(_excludedProfile, excludedPaths) ||
          _slowGroups.length != slowGroups.length) {
        refreshSlow();
        _slowProfile = slowPaths;
        _excludedProfile = excludedPaths;
      }
      _slowGroups = slowGroups;
    }
    if (paths == null && due) {
      _lastSlow = _clockUs();
      _refreshSlow = false;
    }
    if (paths == null) {
      final walk = acquisitions.skip(walkStart).toList();
      Map<String, Object?> phase(String? label) {
        final rows = walk.where((g) =>
            g['phase'] == label || (label == null && !g.containsKey('phase')));
        return {
          'groups': rows.length,
          'us': rows.fold<int>(0, (a, g) => a + (g['acquisitionUs'] as int))
        };
      }

      final phased = walk.any((g) => g['phase'] == 'slow');
      lastWalkTrace = {
        'due': due,
        'phases': {
          if (phased) 'slow': phase('slow'),
          if (phased) 'fast': phase('fast'),
          if (!phased) 'main': phase(null),
          'status': phase('status'),
        },
        'multiAttemptGroups':
            walk.where((g) => (g['attempts'] as int) > 2).length
      };
    }
  }

  Map<String, Object?> snapshot({bool includeExcluded = false}) {
    final now = _clockUs(),
        values = <String, Object?>{},
        samples = <String, Object?>{};
    for (final e in _samples.entries) {
      if (!includeExcluded && _excluded(e.key)) continue;
      final sample = Map<String, Object?>.from(e.value);
      final age = now - (sample['sampledAtUs'] as int? ?? -1000000000);
      final slow = _slow(e.key) || _excluded(e.key);
      final goodUs = (slow ? _slowGoodMs : _fastGoodMs) * 1000;
      final expiryUs = (slow ? _slowExpiryMs : _fastExpiryMs) * 1000;
      if (age >= expiryUs) {
        sample.remove('value');
        sample['status'] = 0x80000000;
        sample['reason'] = 'read-expired';
      } else if (age >= goodUs &&
          ((sample['status'] as int) & 0xc0000000) == 0) {
        sample.remove('value');
        sample['status'] = 0x40000000;
        sample['reason'] = 'read-late';
      }
      if (sample['status'] == 0) values[e.key] = _values[e.key];
      sample.remove('sampledAtUs');
      sample['ageMs'] = age / 1000;
      sample['tier'] = slow ? 'slow' : 'fast';
      samples[e.key] = sample;
    }
    return {
      ...publication.snapshotDocument(
          values, {for (final p in samples.keys) p: _types[p]!}),
      'dataValues': samples,
      'nodeCount': samples.length
    };
  }
}
