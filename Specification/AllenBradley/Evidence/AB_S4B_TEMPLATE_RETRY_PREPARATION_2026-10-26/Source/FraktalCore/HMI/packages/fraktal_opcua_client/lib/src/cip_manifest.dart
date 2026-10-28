library;

import 'dart:convert';
import 'dart:typed_data';

import 'cip_read_coherence.dart';

const _limit = 100000;
const _typeColumns = {
  'TypeName',
  'MemberName',
  'LogicalType',
  'LowerBound',
  'ElementCount',
  'CountMember',
  'EffectiveAccess'
};
const _bindingColumns = {'SourceSymbol', 'TargetRoot'};
const _serviceColumns = {
  'Kind',
  'Version',
  'BuildRevision',
  'RequestSymbol',
  'RequestMember',
  'ResponseSymbol'
};
const _productColumns = {'SourceSymbol', 'CoreType', 'CanonicalRoot'};
const _commandText = {
  'RootSymbol',
  'PayloadSymbol',
  'ArgumentsMember',
  'CommitSymbol',
  'ResponseSymbol',
  'StatusSymbol',
  'ReadRole',
  'CapabilitiesSymbol',
  'KeysSymbol'
};
const _commandColumns = {
  ..._commandText,
  'Version',
  'ConnectionBytes',
  'MaximumPayloadBytes',
  'CapabilitiesCount',
  'KeysCount'
};
const _operationColumns = {
  'Kind',
  'Supported',
  'RequiresSetStage',
  'RefusalKey'
};
const _coherenceColumns = {
  'CanonicalPrefix',
  'RevisionSymbol',
  'Protocol',
  'MutationPeriodUs'
};
const _readServiceColumns = {'Kind', 'Version', 'RootSymbol', 'CanonicalRoot'};
const _logical = {
  '',
  'BOOL',
  'ENUM',
  'DURATION',
  'TIMESTAMP',
  'BITSTRING32',
  'UINT16'
};
const _access = {'', 'Read Only', 'Read/Write'};
final _identifier = RegExp(r'^[A-Za-z_][A-Za-z0-9_]{0,39}$');
final _path = RegExp(
    r'^[A-Za-z_][A-Za-z0-9_]*(?:\[\*\])?(?:/[A-Za-z_][A-Za-z0-9_]*(?:\[\*\])?)+$');

bool _sameKeys(Map value, Set<String> keys) =>
    value.length == keys.length && value.keys.every(keys.contains);
void _require(bool condition, String message) {
  if (!condition) throw FormatException(message);
}

bool _int(Object? value, int low, int high) =>
    value is int && value >= low && value <= high;
bool _name(Object? value) => value is String && _identifier.hasMatch(value);
Object? _freeze(Object? value) {
  if (value is Map)
    return Map<String, Object?>.unmodifiable(
        {for (final e in value.entries) e.key as String: _freeze(e.value)});
  if (value is List) return List<Object?>.unmodifiable(value.map(_freeze));
  return value;
}

/// Exact validated V6.4–V6.8 wire metadata. A live session additionally requires
/// V6.7; older recorded captures are supported only for logical replay tests.
final class CipManifest {
  final Map<String, Object?> document;
  CipManifest._(this.document);
  int get minor => document['schemaMinor'] as int;
  String get contentHash => document['contentHash'] as String;
  int get revision => document['configRevision'] as int;
  int get fragmentRevision => document['fragmentRevision'] as int;
  List<Map<String, Object?>> rows(String name) => [
        for (final row in document[name] as List? ?? const [])
          Map<String, Object?>.from(row as Map)
      ];
  List<CipReadCoherenceBinding> get coherence => [
        for (final row in rows('readCoherenceBindings'))
          CipReadCoherenceBinding(row['CanonicalPrefix'] as String,
              row['RevisionSymbol'] as String, row['MutationPeriodUs'] as int)
      ];

  static bool looksLike(Set<String> names) => names.containsAll({
        'Magic',
        'SchemaMajor',
        'SchemaMinor',
        'PublicationStage',
        'Valid',
        'Truncated',
        'ContentHash',
        'ConfigRevision',
        'LegacyContentHash',
        'TypeAnnotationsCount',
        'TypeAnnotationsCapacity'
      });

  factory CipManifest.fromPhysical(Map<String, Object?> record) {
    final minor = record['SchemaMinor'];
    _require(_int(minor, 4, 8) && record['Magic'] == 0x46524b36,
        'Unsupported canonical manifest.');
    final version = minor as int;
    final expected = <String>{
      'Magic',
      'SchemaMajor',
      'SchemaMinor',
      'PublicationStage',
      'Valid',
      'Truncated',
      'ContentHash',
      'ConfigRevision',
      'LegacyContentHash',
      'FragmentRevision'
    };
    List<Object?> table(
        String name, Set<String> columns, int minimum, int maximum,
        {bool always = false}) {
      expected.addAll({name + 'Count', name + 'Capacity'});
      final count = record[name + 'Count'],
          capacity = record[name + 'Capacity'];
      _require(
          _int(count, minimum, maximum) && capacity == count && capacity is int,
          'Invalid $name allocation.');
      if ((count as int) > 0 || always) expected.add(name);
      final rows = record[name] ?? const [];
      _require(rows is List && rows.length == count,
          'Invalid $name physical count.');
      for (final row in rows as List)
        _require(row is Map && _sameKeys(row, columns), 'Invalid $name row.');
      return List<Object?>.from(rows);
    }

    final normalized = <String, Object?>{
      'schemaMajor': record['SchemaMajor'],
      'schemaMinor': version,
      'publicationStage': record['PublicationStage'],
      'valid': record['Valid'],
      'truncated': record['Truncated'],
      'contentHash': record['ContentHash'],
      'configRevision': record['ConfigRevision'],
      'legacyContentHash': record['LegacyContentHash'],
      'fragmentRevision': record['FragmentRevision'],
      'bindings': table('Bindings', _bindingColumns, 0, 1024),
      'services': table('Services', _serviceColumns, 0, 16),
      'typeAnnotations':
          table('TypeAnnotations', _typeColumns, 1, _limit, always: true),
      'pathExceptions':
          table('PathExceptions', {'CanonicalPath', 'Indices'}, 0, _limit),
      if (version >= 5)
        'dataProducts': table('DataProducts', _productColumns, 0, 1024),
      if (version >= 6)
        'commandBindings':
            table('CommandBindings', _commandColumns, 1, 1024, always: true),
      if (version >= 6)
        'commandOperations':
            table('CommandOperations', _operationColumns, 39, 39, always: true),
      if (version >= 7)
        'readCoherenceBindings': table(
            'ReadCoherenceBindings', _coherenceColumns, 1, 1024,
            always: true),
      if (version >= 8)
        'readServices':
            table('ReadServices', _readServiceColumns, 1, 1024, always: true),
    };
    _require(
        _sameKeys(record, expected), 'Unexpected canonical manifest member.');
    return CipManifest.fromNormalized(normalized);
  }

  factory CipManifest.fromNormalized(Map<String, Object?> input) {
    // Own a deep copy: caller mutation must not change negotiated publication.
    final d = Map<String, Object?>.from(jsonDecode(jsonEncode(input)) as Map);
    final minor = d['schemaMinor'];
    _require(
        d['schemaMajor'] == 6 &&
            _int(minor, 4, 8) &&
            d['valid'] == true &&
            d['truncated'] == false &&
            _int(d['publicationStage'], 2, 0x7fffffff) &&
            _int(d['fragmentRevision'], 0, 0x7fffffff),
        'Invalid manifest version/state.');
    final version = minor as int;
    final keys = <String>{
      'schemaMajor',
      'schemaMinor',
      'publicationStage',
      'valid',
      'truncated',
      'contentHash',
      'configRevision',
      'legacyContentHash',
      'fragmentRevision',
      'bindings',
      'services',
      'typeAnnotations',
      'pathExceptions',
      if (version >= 5) 'dataProducts',
      if (version >= 6) ...['commandBindings', 'commandOperations'],
      if (version >= 7) 'readCoherenceBindings',
      if (version >= 8) 'readServices'
    };
    _require(_sameKeys(d, keys), 'Unexpected normalized manifest field.');
    List<Map> table(String key, Set<String> columns, int minimum, int maximum) {
      final value = d[key];
      _require(
          value is List && value.length >= minimum && value.length <= maximum,
          'Invalid $key count.');
      return [
        for (final row in value as List)
          if (row is Map && _sameKeys(row, columns))
            row
          else
            throw FormatException('Invalid $key columns.')
      ];
    }

    final pairs = <String>{};
    for (final row in table('typeAnnotations', _typeColumns, 1, _limit)) {
      final lower = row['LowerBound'], count = row['ElementCount'];
      _require(
          _name(row['TypeName']) &&
              _name(row['MemberName']) &&
              pairs.add('${row['TypeName']}/${row['MemberName']}') &&
              _logical.contains(row['LogicalType']) &&
              _access.contains(row['EffectiveAccess']) &&
              _int(lower, -0x80000000, 0x7fffffff) &&
              _int(count, 0, _limit) &&
              (count != 0 || lower == 0) &&
              row['CountMember'] is String &&
              (row['CountMember'] == '' ||
                  _name(row['CountMember']) && count != 0) &&
              (row['LogicalType'] != '' ||
                  row['EffectiveAccess'] != '' ||
                  count != 0),
          'Invalid type annotation.');
    }
    final paths = <String>{};
    for (final row
        in table('pathExceptions', {'CanonicalPath', 'Indices'}, 0, _limit)) {
      final path = row['CanonicalPath'];
      _require(
          path is String &&
              _path.hasMatch(path) &&
              utf8.encode(path).length <= 255 &&
              paths.add(path) &&
              row['Indices'] is String,
          'Invalid path exception.');
      final indices = jsonDecode(row['Indices'] as String);
      _require(
          indices is List &&
              indices.every((i) => _int(i, 0, _limit - 1)) &&
              [
                for (var i = 1; i < indices.length; i++)
                  indices[i] > indices[i - 1]
              ].every((v) => v),
          'Invalid path index selection.');
    }
    final sources = <String>{};
    for (final row in table('bindings', _bindingColumns, 0, 1024)) {
      _require(
          row.values.every((v) =>
                  v is String &&
                  RegExp(r'^[A-Za-z_][A-Za-z0-9_]{0,79}$').hasMatch(v)) &&
              sources.add(row['SourceSymbol'] as String) &&
              row['SourceSymbol'] != row['TargetRoot'],
          'Invalid fragment binding.');
    }
    final kinds = <int>{};
    for (final row in table('services', _serviceColumns, 0, 16)) {
      _require(
          _int(row['Kind'], 1, version >= 6 ? 3 : 2) &&
              kinds.add(row['Kind'] as int) &&
              row['Version'] == 1 &&
              _int(row['BuildRevision'], 1, 0x7fffffff) &&
              ['RequestSymbol', 'RequestMember', 'ResponseSymbol'].every((k) =>
                  row[k] is String &&
                  RegExp(r'^[A-Za-z_][A-Za-z0-9_]{0,79}$')
                      .hasMatch(row[k] as String)),
          'Invalid service descriptor.');
    }
    if (version >= 5) {
      sources.clear();
      final roots = <String>{};
      for (final row in table('dataProducts', _productColumns, 0, 1024)) {
        final root = row['CanonicalRoot'];
        _require(
            _name(row['SourceSymbol']) &&
                _name(row['CoreType']) &&
                sources.add(row['SourceSymbol'] as String) &&
                root is String &&
                _path.hasMatch(root) &&
                !root.contains('[') &&
                utf8.encode(root).length <= 255 &&
                !roots.any((old) =>
                    root == old ||
                    root.startsWith('$old/') ||
                    old.startsWith('$root/')),
            'Invalid data product.');
        roots.add(root as String);
      }
    }
    if (version >= 6) {
      final roots = <String>{}, endpoints = <String>{};
      for (final row in table('commandBindings', _commandColumns, 1, 1024)) {
        _require(
            (_commandColumns.difference(_commandText))
                    .every((k) => row[k] is int) &&
                row['Version'] == 1 &&
                row['ReadRole'] == 'CommandOnly' &&
                _int(row['ConnectionBytes'], 500, 4000) &&
                _int(row['MaximumPayloadBytes'], 1,
                    (row['ConnectionBytes'] as int) - 256) &&
                _int(row['CapabilitiesCount'], 0, _limit) &&
                _int(row['KeysCount'], 1, _limit) &&
                _commandText
                    .difference({'ReadRole', 'CapabilitiesSymbol'}).every(
                        (k) => _name(row[k])) &&
                (row['CapabilitiesCount'] == 0
                    ? row['CapabilitiesSymbol'] == ''
                    : _name(row['CapabilitiesSymbol'])) &&
                roots.add(row['RootSymbol'] as String),
            'Invalid command binding.');
        final selected = [
          for (final k in ['PayloadSymbol', 'CommitSymbol', 'ResponseSymbol'])
            row[k] as String
        ];
        _require(
            selected.toSet().length == 3 &&
                !selected.contains(row['RootSymbol']) &&
                selected.every(endpoints.add),
            'Duplicate command endpoint.');
      }
      var kind = 0;
      for (final row in table('commandOperations', _operationColumns, 39, 39)) {
        _require(
            row['Kind'] == kind++ &&
                row['Kind'] is int &&
                row['Supported'] is bool &&
                row['RequiresSetStage'] is bool &&
                row['RefusalKey'] is String &&
                utf8.encode(row['RefusalKey'] as String).length <= 255 &&
                ((row['RefusalKey'] as String).isEmpty ==
                    (row['Supported'] == true)) &&
                (row['RequiresSetStage'] != true || row['Supported'] == true),
            'Invalid command operation inventory.');
      }
    }
    if (version >= 7) {
      final roots = <String>{};
      for (final row
          in table('readCoherenceBindings', _coherenceColumns, 1, 1024)) {
        _require(
            row['Protocol'] == 1 &&
                row['Protocol'] is int &&
                row['CanonicalPrefix'] is String &&
                utf8.encode(row['CanonicalPrefix'] as String).length <= 255 &&
                row['RevisionSymbol'] is String &&
                row['MutationPeriodUs'] is int,
            'Invalid coherence descriptor.');
        final b = CipReadCoherenceBinding(row['CanonicalPrefix'] as String,
            row['RevisionSymbol'] as String, row['MutationPeriodUs'] as int);
        _require(
            !roots.any((old) =>
                b.covers(old) ||
                old == b.canonicalPrefix ||
                b.canonicalPrefix.startsWith('$old/')),
            'Overlapping coherence scope.');
        roots.add(b.canonicalPrefix);
      }
    }
    if (version >= 8) {
      final roots = <String>{}, products = <String>{};
      for (final row in table('readServices', _readServiceColumns, 1, 1024)) {
        _require(
            row['Kind'] == 1 &&
                row['Version'] == 1 &&
                row['Kind'] is int &&
                row['Version'] is int &&
                _name(row['RootSymbol']) &&
                roots.add(row['RootSymbol'] as String) &&
                row['CanonicalRoot'] is String &&
                products.add(row['CanonicalRoot'] as String) &&
                (d['dataProducts'] as List).any(
                    (p) => (p as Map)['CanonicalRoot'] == row['CanonicalRoot']),
            'Invalid read service descriptor.');
      }
    }
    final body = <String, Object?>{
      'schemaMajor': 6,
      'schemaMinor': version,
      'publicationStage': d['publicationStage'],
      'legacyContentHash': d['legacyContentHash'],
      'bindings': d['bindings'],
      'services': d['services'],
      'typeAnnotations': d['typeAnnotations'],
      'pathExceptions': d['pathExceptions'],
      if (version >= 5) 'dataProducts': d['dataProducts'],
      if (version >= 6) 'commandBindings': d['commandBindings'],
      if (version >= 6) 'commandOperations': d['commandOperations'],
      if (version >= 7) 'readCoherenceBindings': d['readCoherenceBindings'],
      if (version >= 8) 'readServices': d['readServices']
    };
    final legacy = d['legacyContentHash'], digest = d['contentHash'];
    _require(
        legacy is String &&
            RegExp(r'^[A-F0-9]{16}$').hasMatch(legacy) &&
            digest is String &&
            RegExp(r'^[A-F0-9]{64}$').hasMatch(digest),
        'Invalid manifest digest format.');
    _require(
        cipSha256(utf8.encode(cipCanonicalJson(body))).toUpperCase() ==
                digest &&
            d['configRevision'] ==
                (int.parse((digest as String).substring(0, 7), radix: 16) == 0
                    ? 1
                    : int.parse(digest.substring(0, 7), radix: 16)) &&
            d['configRevision'] is int,
        'Manifest content hash/revision mismatch.');
    return CipManifest._(_freeze(d) as Map<String, Object?>);
  }
}

/// Python's wire canonical form: sorted ASCII keys, compact JSON, ensure_ascii.
String cipCanonicalJson(Object? value) {
  if (value is Map) {
    final keys = value.keys.cast<String>().toList()..sort();
    return '{${keys.map((k) => '${cipCanonicalJson(k)}:${cipCanonicalJson(value[k])}').join(',')}}';
  }
  if (value is List) return '[${value.map(cipCanonicalJson).join(',')}]';
  if (value is String) {
    final encoded = jsonEncode(value);
    final out = StringBuffer();
    for (final unit in encoded.codeUnits) {
      out.write(unit >= 128
          ? '\\u${unit.toRadixString(16).padLeft(4, '0')}'
          : String.fromCharCode(unit));
    }
    return out.toString();
  }
  if (value == null || value is bool || value is int) return jsonEncode(value);
  throw const FormatException('Noninteger manifest number.');
}

/// SHA-256 for the wire content digest; no additional package or native bridge.
String cipSha256(List<int> input) {
  if (input.length > 16 * 1024 * 1024)
    throw const FormatException('Manifest hash budget exceeded.');
  const k = [
    0x428a2f98,
    0x71374491,
    0xb5c0fbcf,
    0xe9b5dba5,
    0x3956c25b,
    0x59f111f1,
    0x923f82a4,
    0xab1c5ed5,
    0xd807aa98,
    0x12835b01,
    0x243185be,
    0x550c7dc3,
    0x72be5d74,
    0x80deb1fe,
    0x9bdc06a7,
    0xc19bf174,
    0xe49b69c1,
    0xefbe4786,
    0x0fc19dc6,
    0x240ca1cc,
    0x2de92c6f,
    0x4a7484aa,
    0x5cb0a9dc,
    0x76f988da,
    0x983e5152,
    0xa831c66d,
    0xb00327c8,
    0xbf597fc7,
    0xc6e00bf3,
    0xd5a79147,
    0x06ca6351,
    0x14292967,
    0x27b70a85,
    0x2e1b2138,
    0x4d2c6dfc,
    0x53380d13,
    0x650a7354,
    0x766a0abb,
    0x81c2c92e,
    0x92722c85,
    0xa2bfe8a1,
    0xa81a664b,
    0xc24b8b70,
    0xc76c51a3,
    0xd192e819,
    0xd6990624,
    0xf40e3585,
    0x106aa070,
    0x19a4c116,
    0x1e376c08,
    0x2748774c,
    0x34b0bcb5,
    0x391c0cb3,
    0x4ed8aa4a,
    0x5b9cca4f,
    0x682e6ff3,
    0x748f82ee,
    0x78a5636f,
    0x84c87814,
    0x8cc70208,
    0x90befffa,
    0xa4506ceb,
    0xbef9a3f7,
    0xc67178f2
  ];
  final h = [
    0x6a09e667,
    0xbb67ae85,
    0x3c6ef372,
    0xa54ff53a,
    0x510e527f,
    0x9b05688c,
    0x1f83d9ab,
    0x5be0cd19
  ];
  final size = ((input.length + 9 + 63) ~/ 64) * 64,
      raw = Uint8List(((input.length + 9 + 63) ~/ 64) * 64)..setAll(0, input);
  raw[input.length] = 128;
  final data = ByteData.sublistView(raw);
  data.setUint32(size - 4, input.length * 8, Endian.big);
  int rotate(int n, int b) => ((n >>> b) | (n << (32 - b))) & 0xffffffff;
  for (var at = 0; at < size; at += 64) {
    final w = List<int>.filled(64, 0);
    for (var i = 0; i < 16; i++) w[i] = data.getUint32(at + 4 * i, Endian.big);
    for (var i = 16; i < 64; i++)
      w[i] = (w[i - 16] +
              (rotate(w[i - 15], 7) ^
                  rotate(w[i - 15], 18) ^
                  (w[i - 15] >>> 3)) +
              w[i - 7] +
              (rotate(w[i - 2], 17) ^
                  rotate(w[i - 2], 19) ^
                  (w[i - 2] >>> 10))) &
          0xffffffff;
    var a = h[0],
        b = h[1],
        c = h[2],
        d = h[3],
        e = h[4],
        f = h[5],
        g = h[6],
        v = h[7];
    for (var i = 0; i < 64; i++) {
      final t1 = (v +
              (rotate(e, 6) ^ rotate(e, 11) ^ rotate(e, 25)) +
              ((e & f) ^ ((~e) & g)) +
              k[i] +
              w[i]) &
          0xffffffff;
      final t2 = ((rotate(a, 2) ^ rotate(a, 13) ^ rotate(a, 22)) +
              ((a & b) ^ (a & c) ^ (b & c))) &
          0xffffffff;
      v = g;
      g = f;
      f = e;
      e = (d + t1) & 0xffffffff;
      d = c;
      c = b;
      b = a;
      a = (t1 + t2) & 0xffffffff;
    }
    final state = [a, b, c, d, e, f, g, v];
    for (var i = 0; i < 8; i++) h[i] = (h[i] + state[i]) & 0xffffffff;
  }
  return h.map((n) => n.toRadixString(16).padLeft(8, '0')).join();
}
