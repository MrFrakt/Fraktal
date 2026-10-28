library;

import 'dart:typed_data';
import 'dart:convert';

import 'cip_manifest.dart';
import 'cip_namespace.dart';
import 'cip_template.dart';
import 'cip_config_read_view.dart';

const cipCanonicalTypes = {
  0xc1: 'Boolean',
  0xc2: 'SByte',
  0xc3: 'Int16',
  0xc4: 'Int32',
  0xc5: 'Int64',
  0xc6: 'Byte',
  0xc7: 'UInt16',
  0xc8: 'UInt32',
  0xc9: 'UInt64',
  0xca: 'Float',
  0xcb: 'Double',
  0xd3: 'UInt32',
  0xcc: 'DateTime'
};
final _wildIndex = RegExp(r'\[-?\d+\]');
String cipSchemaKey(String path) => path.replaceAll(_wildIndex, '[*]');

final class CipPublishedRecord {
  final String source, target;
  final int handle;
  final bool fragment, moduleRoot;
  CipPublishedRecord(this.source, this.target, this.handle,
      {this.fragment = false, this.moduleRoot = false});
}

final class CipFieldSource {
  final CipPublishedRecord record;
  final List<CipTemplateMember> chain;
  CipFieldSource(this.record, this.chain);
  CipTemplateMember get member => chain.last;
}

final class CipPublishedField {
  final String path;
  final CipTemplateMember member;
  final Map<String, Object?> annotation;
  final List<CipFieldSource> sources;
  final bool commandOnly;
  CipPublishedField(this.path, this.member, this.annotation, this.sources,
      {this.commandOnly = false});
}

/// Publication schema comes only from Templates and the hash-checked manifest.
/// The same schema drives offline full-record replay and live bounded groups.
final class CipPublication {
  final CipNamespace namespace;
  final CipManifest manifest;
  late final CipTemplateDecoder decoder;
  final List<CipPublishedRecord> records = [];
  final Set<String> roots = {};
  final Map<String, CipPublishedField> fields = {};
  final Map<String, Map<String, Object?>> commandArguments = {};

  CipPublication(this.namespace, this.manifest) {
    final selected = <int>{};
    for (final symbol in namespace.symbols.values) {
      if (symbol.structured &&
          symbol.rank == 0 &&
          namespace.templates[symbol.handle]?.hasStatus == true) {
        roots.add(symbol.name);
        records.add(CipPublishedRecord(symbol.name, symbol.name, symbol.handle,
            moduleRoot: true));
        selected.add(symbol.handle);
      }
    }
    if (roots.isEmpty)
      throw const FormatException('No canonical root Unit with Status.');
    int structured(String source) {
      final s = namespace.symbols[source];
      if (s == null ||
          !s.structured ||
          s.rank != 0 ||
          !namespace.templates.containsKey(s.handle))
        throw FormatException(
            'Missing structured publication Symbol: $source.');
      selected.add(s.handle);
      return s.handle;
    }

    final sources = {...roots};
    for (final row in manifest.rows('dataProducts')) {
      final source = row['SourceSymbol'] as String,
          target = row['CanonicalRoot'] as String;
      if (!sources.add(source) ||
          roots.any((r) =>
              target == r ||
              target.startsWith('$r/') ||
              r.startsWith('$target/')))
        throw const FormatException('Product/root collision.');
      records.add(CipPublishedRecord(source, target, structured(source)));
    }
    for (final row in manifest.rows('bindings')) {
      final source = row['SourceSymbol'] as String,
          target = row['TargetRoot'] as String;
      if (!sources.add(source) || !roots.contains(target))
        throw const FormatException('Invalid fragment root/source.');
      records.add(CipPublishedRecord(source, target, structured(source),
          fragment: true));
    }
    final forbidden = {
      for (final row in manifest.rows('services')) row['RequestSymbol'],
      for (final row in manifest.rows('commandBindings')) ...[
        row['PayloadSymbol'],
        row['ResponseSymbol']
      ]
    };
    if (sources.any(forbidden.contains))
      throw const FormatException(
          'Command/provider input or private reply in cyclic publication.');
    for (final row in manifest.rows('commandBindings')) {
      for (final key in ['PayloadSymbol', 'ResponseSymbol', 'StatusSymbol'])
        structured(row[key] as String);
    }
    decoder = namespace.decoderFor(selected);
    final products =
        records.where((r) => !r.fragment).map((r) => r.target).toSet();
    if (manifest.minor >= 7) {
      final bindings = manifest.coherence;
      if (bindings.length != products.length ||
          bindings.any((b) => !products.contains(b.canonicalPrefix)))
        throw const FormatException(
            'Coherence scopes do not exactly cover roots/products.');
      for (final b in bindings) {
        final s = namespace.symbols[b.revisionSymbol];
        if (s == null || s.structured || s.rank != 0 || s.atomic != 0xc4)
          throw const FormatException('Coherence Symbol is not DINT.');
      }
    }
    final annotations = <String, Map<String, Object?>>{};
    for (final row in manifest.rows('typeAnnotations')) {
      annotations['${row['TypeName']}/${row['MemberName']}'] = {
        if (row['LogicalType'] != '') 'logicalType': row['LogicalType'],
        if (row['EffectiveAccess'] != '')
          'effectiveAccess': row['EffectiveAccess'],
        if (row['ElementCount'] != 0) ...{
          'lowerBound': row['LowerBound'],
          'elementCount': row['ElementCount']
        },
        if (row['CountMember'] != '') 'countMember': row['CountMember']
      };
    }
    final used = <String>{};
    void walk(CipPublishedRecord record, int handle, String prefix,
        List<CipTemplateMember> chain,
        {bool commandOnly = false, int depth = 0}) {
      if (depth > 64)
        throw const FormatException('Publication depth exceeded.');
      final type = decoder.templates[handle]!;
      for (final member in type.members) {
        if (record.fragment && member.name == 'Status')
          throw const FormatException('Fragment redefines module identity.');
        final path = '$prefix/${member.name}',
            pair = '${type.name}/${member.name}';
        final annotation =
            Map<String, Object?>.from(annotations[pair] ?? const {});
        if (annotations.containsKey(pair)) used.add(pair);
        final count = annotation.remove('countMember');
        if (count != null) annotation['countPath'] = '$prefix/$count';
        final previous = fields[path];
        if (previous != null &&
            (!record.fragment ||
                previous.commandOnly ||
                commandOnly ||
                !previous.member.isStructure ||
                !member.isStructure ||
                previous.member.isArray != member.isArray ||
                member.isArray && previous.member.info != member.info ||
                decoder.templates[previous.member.handle]!.stringByteCapacity !=
                    null ||
                decoder.templates[member.handle]!.stringByteCapacity != null ||
                cipCanonicalJson(previous.annotation) !=
                    cipCanonicalJson(annotation))) {
          throw FormatException(
              'Colliding publication leaves/containers: $path.');
        }
        final source = CipFieldSource(record, [...chain, member]);
        if (previous == null)
          fields[path] = CipPublishedField(path, member, annotation, [source],
              commandOnly: commandOnly);
        else
          previous.sources.add(source);
        if (fields.length > 100000)
          throw const FormatException('Publication schema budget exceeded.');
        if (member.isStructure &&
            decoder.templates[member.handle]!.stringByteCapacity == null) {
          walk(record, member.handle, path + (member.isArray ? '[*]' : ''),
              [...chain, member],
              commandOnly: commandOnly, depth: depth + 1);
        }
      }
    }

    for (final record in records) {
      if (decoder.templates[record.handle]!.stringByteCapacity != null)
        throw const FormatException('Publication root is a string.');
      walk(record, record.handle, record.target, []);
    }
    for (final row in manifest.rows('commandBindings')) {
      final root = row['RootSymbol'] as String;
      if (!roots.contains(root))
        throw const FormatException('Command root is not a Unit.');
      final args = _commandSchema(row);
      final before = fields.keys.toSet();
      walk(
          CipPublishedRecord(row['PayloadSymbol'] as String, root, args,
              fragment: true),
          args,
          '$root/HmiRequest',
          [],
          commandOnly: true);
      for (final path in fields.keys.toSet().difference(before)) {
        final m = fields[path]!.member;
        final width = m.isStructure
            ? decoder.templates[m.handle]!.stringByteCapacity
            : null;
        commandArguments[path] = {
          'readRole': 'CommandOnly',
          'nativeType': width != null ? 'String' : cipCanonicalTypes[m.atomic],
          if (width != null) 'byteCapacity': width
        };
      }
    }
    if (used.length != annotations.length ||
        !annotations.keys.every(used.contains))
      throw const FormatException(
          'Annotation refers to an absent Template member.');
    final names = <String, String>{};
    for (final type in decoder.templates.values) {
      if (!annotations.keys.any((p) => p.startsWith('${type.name}/'))) continue;
      final signature = '${type.byteSize}:' +
          type.members
              .map((m) => '${m.name}:${m.info}:${m.code}:${m.offset}')
              .join(',');
      if (names.containsKey(type.name) && names[type.name] != signature)
        throw const FormatException('Ambiguous annotated Template name.');
      names[type.name] = signature;
    }
    for (final row in manifest.rows('pathExceptions')) {
      final field = fields[row['CanonicalPath']];
      if (field == null)
        throw const FormatException('Exception path absent from publication.');
      field.annotation['indices'] = jsonDecode(row['Indices'] as String);
    }
    for (final field in fields.values) _validateField(field);
    for (final service in manifest.rows('readServices')) {
      if (!roots.contains(service['RootSymbol']))
        throw const FormatException('Read service root is not a Unit.');
      final product = records
          .where((r) => !r.fragment && r.target == service['CanonicalRoot'])
          .single;
      final view = decoder.templates[product.handle]!;
      const names = {
        'SchemaVersion',
        'RootIdentity',
        'Revision',
        'DefinitionCount',
        'DefinitionCapacity',
        'Definitions',
        'ValueCount',
        'ValueCapacity',
        'Values'
      };
      if (view.members.length != names.length ||
          !view.members.every((m) => names.contains(m.name)) ||
          view.members.first.name != 'SchemaVersion')
        throw const FormatException('Invalid configuration view envelope.');
      for (final m in view.members) {
        if (m.name == 'RootIdentity') {
          if (!m.isStructure ||
              m.isArray ||
              decoder.templates[m.handle]!.stringByteCapacity != 80)
            throw const FormatException('Invalid read-view identity.');
        } else if (const {'Definitions', 'Values'}.contains(m.name)) {
          if (!m.isStructure || !m.isArray)
            throw const FormatException('Invalid read-view rows.');
        } else if (m.isStructure || m.isArray || m.atomic != 0xc4)
          throw const FormatException('Invalid read-view scalar.');
      }
      final definitions =
              view.members.singleWhere((m) => m.name == 'Definitions'),
          definitionType = decoder.templates[definitions.handle]!;
      if (definitionType.members.length != cipConfigDefinitionLayout.length ||
          definitionType.members
              .any((m) => !cipConfigDefinitionLayout.containsKey(m.name)))
        throw const FormatException(
            'Incomplete configuration definition layout.');
      for (final m in definitionType.members) {
        final layout = cipConfigDefinitionLayout[m.name]!;
        if (m.isArray ||
            (layout.$2 > 0
                ? !m.isStructure ||
                    decoder.templates[m.handle]!.stringByteCapacity != layout.$2
                : m.isStructure || m.atomic != layout.$1))
          throw const FormatException('Configuration definition type differs.');
      }
      final values = view.members.singleWhere((m) => m.name == 'Values'),
          type = decoder.templates[values.handle]!;
      const valueNames = {
        'DefinitionIndex',
        'ModelOrdinal',
        'ModelCode',
        'ValueText',
        'Readable',
        'Revision'
      };
      if (type.members.length != valueNames.length ||
          !type.members.every((m) => valueNames.contains(m.name)))
        throw const FormatException('Invalid configuration value row.');
      for (final m in type.members) {
        if (m.name == 'ModelCode' || m.name == 'ValueText') {
          if (!m.isStructure ||
              m.isArray ||
              decoder.templates[m.handle]!.stringByteCapacity !=
                  (m.name == 'ModelCode' ? 64 : 255))
            throw const FormatException('Invalid configuration string width.');
        } else if (m.isStructure ||
            m.isArray ||
            m.atomic != (m.name == 'Readable' ? 0xc1 : 0xc4))
          throw const FormatException('Invalid configuration value type.');
      }
    }
  }

  int _commandSchema(Map<String, Object?> row) {
    CipTemplate type(String key) =>
        decoder.templates[namespace.symbols[row[key]]!.handle]!;
    final payload = type('PayloadSymbol');
    final members = {for (final m in payload.members) m.name: m};
    void nonoverlapping(CipTemplate record) {
      final spans = <(int, int)>[];
      for (final m in record.members) {
        if (m.isArray)
          throw const FormatException('Array in typed command record.');
        final start =
            m.offset * 8 + (m.atomic == 0xc1 && !m.isStructure ? m.info : 0);
        final width = m.isStructure
            ? decoder.templates[m.handle]!.byteSize * 8
            : m.atomic == 0xc1
                ? 1
                : CipTemplateDecoder.atomicByteSize(m.atomic) * 8;
        if (start < 0 ||
            start + width > record.byteSize * 8 ||
            spans.any((s) => start < s.$2 && s.$1 < start + width))
          throw const FormatException(
              'Overlapping/out-of-bounds command members.');
        spans.add((start, start + width));
      }
    }

    nonoverlapping(payload);
    final argument = row['ArgumentsMember'] as String;
    if (members.keys.toSet().difference({
          'SchemaVersion',
          'ManifestRevision',
          'StagedSequence',
          argument
        }).isNotEmpty ||
        members.length != 4 ||
        payload.byteSize > (row['MaximumPayloadBytes'] as int))
      throw const FormatException('Invalid command envelope.');
    for (final key in ['SchemaVersion', 'ManifestRevision', 'StagedSequence']) {
      final m = members[key]!;
      if (m.isStructure || m.isArray || m.atomic != 0xc4)
        throw const FormatException('Invalid command envelope scalar.');
    }
    final a = members[argument]!;
    if (!a.isStructure || a.isArray)
      throw const FormatException('Invalid command arguments.');
    final args = decoder.templates[a.handle]!,
        fields = {
          for (final m in decoder.templates[a.handle]!.members) m.name: m
        };
    nonoverlapping(args);
    const widths = {
      'TargetPath': 255,
      'NameValue': 160,
      'TextValue': 255,
      'User': 32,
      'Secret': 32
    };
    const names = {
      'Kind',
      'TargetPath',
      'NameValue',
      'TextValue',
      'User',
      'Secret',
      'IntValue',
      'BoolValue',
      'DurationMs'
    };
    if (fields.length != names.length || !fields.keys.every(names.contains))
      throw const FormatException('Invalid Core argument set.');
    for (final m in fields.values) {
      if (m.isArray) throw const FormatException('Array command argument.');
      if (widths.containsKey(m.name)) {
        if (!m.isStructure ||
            decoder.templates[m.handle]!.stringByteCapacity != widths[m.name])
          throw const FormatException('Command string width differs.');
      } else if (m.isStructure ||
          m.atomic != (m.name == 'BoolValue' ? 0xc1 : 0xc4))
        throw const FormatException('Command scalar differs.');
    }
    final commit = namespace.symbols[row['CommitSymbol']];
    if (commit == null ||
        commit.structured ||
        commit.rank != 0 ||
        commit.atomic != 0xc4)
      throw const FormatException('Invalid command commit.');
    final status = type('StatusSymbol');
    if (!status.members.any((m) =>
        m.name == 'CoreSerial' &&
        !m.isStructure &&
        !m.isArray &&
        m.atomic == 0xc4))
      throw const FormatException('Invalid command status.');
    final root = type('RootSymbol'), response = type('ResponseSymbol');
    if (!root.members.any((m) =>
        m.name == 'HmiResponse' &&
        m.isStructure &&
        !m.isArray &&
        m.handle == response.handle))
      throw const FormatException('Command reply/root mismatch.');
    for (final entry in [
      ('KeysSymbol', row['KeysCount'], {'NumericKey', 'PortableKey'}),
      (
        'CapabilitiesSymbol',
        row['CapabilitiesCount'],
        {'CapabilityIndex', 'WriteKeyKey', 'ConfigKind'}
      )
    ]) {
      if (entry.$2 == 0) continue;
      final symbol = namespace.symbols[row[entry.$1]];
      if (symbol == null ||
          !symbol.structured ||
          symbol.rank != 1 ||
          !namespace.templates[symbol.handle]!.members
              .map((m) => m['name'])
              .toSet()
              .containsAll(entry.$3))
        throw const FormatException('Command side-table mismatch.');
    }
    return args.handle;
  }

  void _validateField(CipPublishedField field) {
    final m = field.member, a = field.annotation, logical = a['logicalType'];
    if (!m.isStructure && !cipCanonicalTypes.containsKey(m.atomic))
      throw const FormatException('Native type lacks canonical mapping.');
    const permitted = {
      'ENUM': {0xc4},
      'DURATION': {0xc4},
      'TIMESTAMP': {0xcc},
      'BITSTRING32': {0xd3, 0xc4},
      'UINT16': {0xc4},
      'BOOL': {0xc1}
    };
    if (logical != null &&
        !(m.isArray && logical == 'BOOL'
                ? const {0xc1, 0xd3}
                : permitted[logical] ?? const <int>{})
            .contains(m.atomic))
      throw FormatException('Logical/native type mismatch: ${field.path}.');
    if (m.isArray) {
      final count = a['elementCount'], lower = a['lowerBound'];
      if (count is! int || count < 1 || count > 100000 || lower is! int)
        throw FormatException(
            'Array lacks explicit bound/extent: ${field.path}.');
      if (logical == 'BOOL' && m.atomic == 0xd3
          ? m.info < (count + 31) ~/ 32
          : m.info < count)
        throw const FormatException('Logical extent exceeds storage.');
      final indices = a['indices'];
      if (indices != null &&
          ((indices as List).any((i) => i is! int || i < 0 || i >= count) ||
              a['countPath'] != null))
        throw const FormatException('Invalid logical selection.');
      final path = a['countPath'];
      if (path != null) {
        final target = fields[path];
        if (target == null ||
            target.member.isStructure ||
            target.member.isArray ||
            !const {0xc2, 0xc3, 0xc4, 0xc5, 0xc6, 0xc7, 0xc8, 0xc9}
                .contains(target.member.atomic) ||
            (path as String).substring(0, path.lastIndexOf('/')) !=
                field.path.substring(0, field.path.lastIndexOf('/')))
          throw const FormatException('Invalid sibling count reference.');
      }
    } else if (a.keys.any(
        const {'lowerBound', 'elementCount', 'indices', 'countPath'}.contains))
      throw const FormatException('Array annotation on scalar.');
  }

  /// Project only the explicit cyclic record set; persisted argument bytes are
  /// refused before decoding, including a correctly named Secret/TextValue.
  Map<String, Object?> projectRecords(Map<String, Uint8List> raw) {
    if (raw.length != records.length ||
        !records.every((r) => raw.containsKey(r.source)))
      throw const FormatException('Unbound or command-only cyclic record.');
    final decoded = <String, Object?>{}, samples = <String, Object?>{};
    for (final record in records) {
      final value = decoder.decode(record.handle, raw[record.source]!);
      samples[record.source] = value;
      if (!record.fragment) decoded[record.target] = value;
    }
    Object merge(Object? left, Object? right) {
      if (left is Map && right is Map) {
        final result = Map<String, Object?>.from(left);
        for (final e in right.entries) {
          result[e.key as String] = result.containsKey(e.key)
              ? merge(result[e.key], e.value)
              : e.value;
        }
        return result;
      }
      if (left is List && right is List && left.length == right.length)
        return [for (var i = 0; i < left.length; i++) merge(left[i], right[i])];
      throw const FormatException('Fragment count view has colliding leaves.');
    }

    for (final record in records.where((r) => r.fragment))
      decoded[record.target] =
          merge(decoded[record.target], samples[record.source]);
    for (final root in roots) {
      final value = decoded[root] as Map, status = value['Status'];
      if (status is! Map || status['Name'] != root || status['ModuleType'] != 1)
        throw const FormatException(
            'Canonical Unit identity differs from Symbol.');
    }
    Object? lookup(String concrete) {
      final root = decoded.keys.where((r) => concrete.startsWith('$r/')).first;
      Object? value = decoded[root];
      var prefix = root;
      for (final part in concrete.substring(root.length + 1).split('/')) {
        final match = RegExp(r'^([A-Za-z_][A-Za-z0-9_]*)(?:\[(-?\d+)\])?$')
            .firstMatch(part);
        if (match == null)
          throw const FormatException('Invalid concrete count path.');
        prefix += '/${match[1]}';
        value = (value as Map)[match[1]];
        if (match[2] != null) {
          value = (value as List)[int.parse(match[2]!) -
              (fields[cipSchemaKey(prefix)]!.annotation['lowerBound'] as int)];
          prefix += '[${match[2]}]';
        }
      }
      return value;
    }

    final values = <String, Object?>{}, types = <String, String>{};
    void put(String path, Object? value, String type) {
      if (values.containsKey(path) || values.length >= 100000)
        throw const FormatException('Duplicate/oversized canonical values.');
      values[path] = value;
      types[path] = type;
    }

    late void Function(String, Object?, int, int) record;
    void walk(String path, Object? value, CipTemplateMember member, int depth) {
      final annotation = fields[cipSchemaKey(path)]!.annotation;
      if (member.isArray) {
        final extent = annotation['elementCount'] as int,
            lower = annotation['lowerBound'] as int;
        Iterable<int> indices = annotation['indices'] == null
            ? List.generate(extent, (i) => i)
            : List<int>.from(annotation['indices'] as List);
        if (annotation['countPath'] != null) {
          final pathToCount =
              '${path.substring(0, path.lastIndexOf('/'))}/${(annotation['countPath'] as String).split('/').last}';
          final actual = lookup(pathToCount);
          final count = actual is BigInt &&
                  actual >= BigInt.zero &&
                  actual <= BigInt.from(extent)
              ? actual.toInt()
              : actual;
          if (count is! int || count < 0 || count > extent)
            throw const FormatException('Live logical count exceeds extent.');
          indices = List.generate(count, (i) => i);
        }
        final items = value as List;
        for (final index in indices) {
          final itemPath = '$path[${index + lower}]';
          if (annotation['logicalType'] == 'BOOL') {
            put(
                itemPath,
                member.atomic == 0xd3
                    ? ((items[index ~/ 32] as int) >> (index % 32)) & 1 != 0
                    : items[index],
                'Boolean');
          } else if (member.isStructure)
            record(itemPath, items[index], member.handle, depth + 1);
          else {
            final result = scalar(member.atomic, annotation, items[index]);
            put(itemPath, result.$1, result.$2);
          }
        }
      } else if (member.isStructure)
        record(path, value, member.handle, depth + 1);
      else {
        final result = scalar(member.atomic, annotation, value);
        put(path, result.$1, result.$2);
      }
    }

    record = (String path, Object? value, int handle, int depth) {
      if (depth > 64) throw const FormatException('Canonical depth exceeded.');
      final type = decoder.templates[handle]!;
      if (type.stringByteCapacity != null) {
        if (value is! String)
          throw const FormatException('Invalid string value.');
        put(path, value, 'String');
        return;
      }
      final data = value as Map;
      if (type.members.any((m) => m.name == 'Status' && m.isStructure)) {
        final status = data['Status'];
        if (status is! Map ||
            status['Name'] != path.replaceAll('/', '.') ||
            !const {1, 2, 3}.contains(status['ModuleType']))
          throw const FormatException(
              'Module identity/type differs from browse path.');
      }
      for (final member in type.members)
        walk('$path/${member.name}', data[member.name], member, depth);
    };
    for (final r in records) record(r.target, samples[r.source], r.handle, 0);
    return snapshotDocument(values, types);
  }

  Map<String, Object?> snapshotDocument(
          Map<String, Object?> values, Map<String, String> types) =>
      {
        'schema': 'fraktal.opcua.snapshot.v1',
        'protocol': 'fraktal.opcua.snapshot.v1',
        'schemaVersion': 1,
        'values': values,
        'types': types,
        'nodeCount': values.length,
        'moduleCount': roots.length +
            values.keys
                .where((p) =>
                    p.endsWith('/Status/Name') &&
                    !roots.any((r) => p == '$r/Status/Name'))
                .length,
        'contentHash': manifest.contentHash,
        'configRevision': manifest.revision,
        'truncated': false,
        'dataValues': {
          for (final e in values.entries)
            e.key: {'value': e.value, 'type': types[e.key], 'status': 0}
        },
        if (manifest.minor >= 6)
          'commandBindings': manifest.rows('commandBindings'),
        if (manifest.minor >= 6) 'commandArguments': commandArguments,
        if (manifest.minor >= 7)
          'readCoherenceBindings': manifest.rows('readCoherenceBindings'),
        if (manifest.minor >= 8) 'readServices': manifest.rows('readServices'),
      };

  List<String> discoverPaths() {
    final paths = <String>{};
    for (final field in fields.values.where((f) =>
        !f.commandOnly &&
        (!f.member.isStructure ||
            decoder.templates[f.member.handle]!.stringByteCapacity != null))) {
      final pattern = field.path + (field.member.isArray ? '[*]' : '');
      void expand(int offset, String concrete, String schema) {
        if (offset == pattern.split('/').length) {
          if (paths.length >= 100000)
            throw const FormatException('Canonical path budget exceeded.');
          paths.add(concrete);
          return;
        }
        final part = pattern.split('/')[offset],
            base = part.replaceFirst(RegExp(r'\[\*\]$'), '');
        final key = schema.isEmpty ? base : '$schema/$base',
            prefix = concrete.isEmpty ? base : '$concrete/$base';
        if (part.endsWith('[*]')) {
          final a = fields[key]!.annotation, lower = a['lowerBound'] as int;
          final indices = a['indices'] == null
              ? List.generate(a['elementCount'] as int, (i) => i)
              : List<int>.from(a['indices'] as List);
          for (final i in indices)
            expand(offset + 1, '$prefix[${lower + i}]', '$key[*]');
        } else {
          expand(offset + 1, prefix, key);
        }
      }

      expand(0, '', '');
    }
    return paths.toList()..sort();
  }

  /// Project one coherently acquired physical subtree. Counts are supplied by
  /// the same guarded read, using concrete logical paths rather than PLC names.
  Map<String, Object?> projectSubtree(String path, CipTemplateMember member,
      Object? value, Map<String, int> counts,
      {bool element = false}) {
    final values = <String, Object?>{}, types = <String, String>{};
    void put(String p, Object? v, String t) {
      if (values.containsKey(p) || values.length >= 100000)
        throw const FormatException('Invalid subtree extent.');
      values[p] = v;
      types[p] = t;
    }

    late void Function(String, CipTemplateMember, Object?, bool) walk;
    void record(String p, int handle, Object? v) {
      final type = decoder.templates[handle]!;
      if (type.stringByteCapacity != null) {
        if (v is! String)
          throw const FormatException('Invalid StringFamily value.');
        put(p, v, 'String');
        return;
      }
      final data = v as Map;
      if (type.members.any((m) => m.name == 'Status' && m.isStructure)) {
        final status = data['Status'];
        if (status is! Map ||
            status['Name'] != p.replaceAll('/', '.') ||
            !const {1, 2, 3}.contains(status['ModuleType']))
          throw const FormatException('Module identity differs.');
      }
      for (final m in type.members)
        walk('$p/${m.name}', m, data[m.name], false);
    }

    walk = (p, m, v, one) {
      final key = cipSchemaKey(p).replaceFirst(RegExp(r'\[\*\]$'), '');
      final field = fields[key];
      if (field == null || field.commandOnly)
        throw const FormatException('Unbound cyclic subtree.');
      final a = field.annotation;
      if (m.isArray && !one) {
        final extent = a['elementCount'] as int, lower = a['lowerBound'] as int;
        var count = extent;
        if (a['countPath'] != null) {
          final cp =
              '${p.substring(0, p.lastIndexOf('/'))}/${(a['countPath'] as String).split('/').last}';
          final n = counts[cp];
          if (n == null || n < 0 || n > extent)
            throw const FormatException(
                'Missing/invalid guarded logical count.');
          count = n;
        }
        final selected = a['indices'] == null
            ? List.generate(count, (i) => i)
            : List<int>.from(a['indices'] as List);
        for (final i in selected) {
          if (a['logicalType'] == 'BOOL') {
            final items = v as List;
            put(
                '$p[${i + lower}]',
                m.atomic == 0xd3
                    ? ((items[i ~/ 32] as int) >> (i % 32)) & 1 != 0
                    : items[i],
                'Boolean');
          } else {
            walk('$p[${i + lower}]', m, (v as List)[i], true);
          }
        }
      } else if (m.isStructure) {
        record(p, m.handle, v);
      } else {
        final converted = scalar(m.atomic, a, v);
        put(p, converted.$1, converted.$2);
      }
    };
    walk(path, member, value, element);
    return {'values': values, 'types': types};
  }

  static (Object?, String) scalar(
      int code, Map<String, Object?> annotation, Object? value) {
    var type = cipCanonicalTypes[code];
    if (type == null)
      throw const FormatException('Native type has no canonical mapping.');
    if (code == 0xc5 || code == 0xc9) value = (value as BigInt).toString();
    if (code == 0xcc) {
      final ns = value as BigInt;
      if (ns == BigInt.zero)
        value = 0;
      else {
        final billion = BigInt.from(1000000000);
        var seconds = ns ~/ billion, nanos = ns.remainder(billion);
        if (nanos < BigInt.zero) {
          seconds -= BigInt.one;
          nanos += billion;
        }
        final date = DateTime.fromMillisecondsSinceEpoch(seconds.toInt() * 1000,
                isUtc: true)
            .toIso8601String()
            .split('.')
            .first;
        final fraction = nanos
            .toString()
            .padLeft(9, '0')
            .replaceFirst(RegExp(r'0+$'), '')
            .padRight(3, '0');
        value = '$date.${fraction}Z';
      }
    }
    if (annotation['logicalType'] == 'BITSTRING32') {
      value = (value as int) & 0xffffffff;
      type = 'UInt32';
    }
    if (annotation['logicalType'] == 'UINT16') {
      if (value is! int || value < 0 || value > 65535)
        throw const FormatException('Logical UInt16 outside range.');
      type = 'UInt16';
    }
    return (value, type);
  }
}
