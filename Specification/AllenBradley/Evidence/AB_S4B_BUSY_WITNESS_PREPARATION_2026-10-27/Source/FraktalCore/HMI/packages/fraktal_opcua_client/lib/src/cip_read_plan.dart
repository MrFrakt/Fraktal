library;

import 'dart:async';
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

/// Bounded row acquisition over the canonical schema. Fragment members of one
/// row share a guard. Nested collections get their own rows; a document is not
/// represented as one atomic sample. No observation frame is consulted.
final class CipReadPlan {
  final CipPublication publication;
  final CipReadTransport wire;
  final int Function() _clockUs;
  final CipReadCoherenceGuard guard;
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

  Future<Object> _read(CipFieldSource source, String concrete,
      {bool element = false,
      int? countOverride,
      CipReadTransport? transport}) async {
    final m = source.member,
        count = countOverride ?? (m.isArray && !element ? m.info : 1);
    final size = m.isStructure
        ? publication.decoder.templates[m.handle]!.byteSize * count
        : m.atomic == 0xc1
            ? (m.isArray && !element ? ((count + 31) ~/ 32) * 4 : 1)
            : CipTemplateDecoder.atomicByteSize(m.atomic) * count;
    final bytes = await CipNamespace.readExact(
        transport ?? wire, _physicalPath(source, concrete), size,
        structureHandle: m.isStructure
            ? publication.namespace.templates[m.handle]!.structureHandle
            : null,
        atomic: m.isStructure ? null : m.atomic,
        elementCount: count);
    final layout = countOverride == null
        ? m
        : CipTemplateMember(m.name, countOverride, m.code, m.offset);
    return publication.decoder.decodeMember(layout, bytes, element: element);
  }

  Future<int> _count(String path, {CipReadTransport? transport}) async {
    final field = publication.fields[cipSchemaKey(path)];
    if (field == null ||
        field.commandOnly ||
        field.member.isStructure ||
        field.member.isArray ||
        field.sources.length != 1)
      throw const FormatException('Invalid count source.');
    final raw = await _read(field.sources.single, path, transport: transport);
    if (raw is BigInt && raw >= BigInt.zero && raw <= BigInt.from(100000))
      return raw.toInt();
    if (raw is! int)
      throw const FormatException('Count source is not integral.');
    return raw;
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

  Future<void> _groupOn(
      CipReadTransport transport, CipPublishedField field, String path,
      {bool element = false, Set<String>? selection}) async {
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
    if (parts.isEmpty) return;
    final dependencies = _dependencies(field, path),
        binding =
            publication.manifest.coherence.singleWhere((b) => b.covers(path));
    Map<String, Object?> candidate = {};
    Map<String, String> types = {};
    Map<String, int> counts = {};
    var candidateStartedAtUs = _clockUs(), expectingPostCounter = false;
    final sample = await guard.read(
        binding: binding,
        readRevision: (symbol) {
          if (expectingPostCounter) {
            expectingPostCounter = false;
          } else {
            // Age starts before I/O for the attempt that supplies the row,
            // including its pre-counter read and asynchronous continuations.
            candidateStartedAtUs = _clockUs();
          }
          return CipNamespace.readDint(transport, symbol);
        },
        readGroup: () async {
          expectingPostCounter = true;
          candidate = {};
          types = {};
          counts = {};
          for (final d in dependencies) {
            final n = await _count(d.path, transport: transport);
            if (n < 0 || n > d.extent)
              throw const FormatException(
                  'Live count exceeds declared extent.');
            counts[d.path] = n;
          }
          if (dependencies
              .any((d) => d.index != null && d.index! >= counts[d.path]!))
            return Uint8List(0);
          for (final requested in parts)
            for (final source in requested.$1.sources) {
              int? nativeCount;
              if (source.member.isArray &&
                  !requested.$3 &&
                  !source.member.isStructure) {
                final a = requested.$1.annotation;
                var logical = a['elementCount'] as int;
                if (a['countPath'] != null)
                  logical = counts[
                      '${requested.$2.substring(0, requested.$2.lastIndexOf('/'))}/${(a['countPath'] as String).split('/').last}']!;
                if (a['indices'] != null)
                  logical = (a['indices'] as List).isEmpty
                      ? 0
                      : ((a['indices'] as List).last as int) + 1;
                if (logical == 0) continue;
                nativeCount =
                    a['logicalType'] == 'BOOL' && source.member.atomic == 0xd3
                        ? (logical + 31) ~/ 32
                        : logical;
              }
              final value = await _read(source, requested.$2,
                  element: requested.$3,
                  countOverride: nativeCount,
                  transport: transport);
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
        });
    final now = _clockUs();
    acquisitions.add({
      'path': path,
      'quality': sample.quality.name,
      'reason': sample.reason,
      'attempts': sample.attempts,
      'acquisitionUs': sample.acquisitionUs
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
          'coherenceAttempts': sample.attempts,
          'coherenceAcquisitionUs': sample.acquisitionUs,
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
    if (_tokens[symbol] == token) _revisionFinishedAt[symbol] = now;
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

  Future<void> acquire({Set<String>? paths}) async {
    final due = _refreshSlow || _clockUs() - _lastSlow >= slowIntervalUs;
    final seenCounts = <String>{};
    final statuses = <(CipPublishedField, String, bool)>[];
    var statusPhase = false;
    final grouped = wire;
    final concurrency = paths == null && grouped is CipGroupedReadTransport
        ? grouped.groupConcurrency
        : 1;
    final pending = <Future<void> Function()>[];
    Future<void> flush() async {
      final batch = List.of(pending);
      pending.clear();
      await Future.wait(batch.map((work) => work()));
    }

    Future<void> acquireGroup(CipPublishedField field, String concrete,
        {bool element = false, Set<String>? selection}) async {
      pending.add(() =>
          _group(field, concrete, element: element, selection: selection));
      if (pending.length >= concurrency) await flush();
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
            await flush();
            await _group(publication.fields[cipSchemaKey(cp)]!, cp);
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
      // A full row walk can outlast the fast Good interval. Deliver module
      // identity/status near its end without rereading rows or renewing ages.
      // A leaf module may already fit in one group together with its Status.
      // Other late rows still lose payload under the unchanged age rules.
      final statusPrefix =
          field.path.endsWith('/Status') ? field.path : '${field.path}/Status';
      if (paths == null &&
          !statusPhase &&
          !hasArrays &&
          m.isStructure &&
          publication.fields.containsKey('$statusPrefix/Name') &&
          publication.fields.containsKey('$statusPrefix/ModuleType')) {
        statuses.add((field, concrete, element));
        return;
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
        final consumed =
            paths == null ? leaves.where((p) => !_excluded(p)).toSet() : leaves;
        if (paths == null && consumed.isEmpty) return;
        if (paths == null && !due && consumed.every(_slow)) return;
        final selection =
            paths ?? (consumed.length != leaves.length ? consumed : null);
        if (selection?.isEmpty == true) return;
        await acquireGroup(field, concrete,
            element: element, selection: selection);
      }
    }

    for (final target
        in publication.records.where((r) => !r.fragment).map((r) => r.target)) {
      for (final child in _children(target))
        await visit(child, '$target/${child.member.name}');
    }
    await flush();
    statusPhase = true;
    for (final status in statuses)
      await visit(status.$1, status.$2, element: status.$3);
    await flush();
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
    if (paths == null && due) {
      _lastSlow = _clockUs();
      _refreshSlow = false;
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
