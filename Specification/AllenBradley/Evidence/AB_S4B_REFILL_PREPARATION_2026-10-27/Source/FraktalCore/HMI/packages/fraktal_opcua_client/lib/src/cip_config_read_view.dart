library;

import 'dart:convert';

/// Each bounded fetch is a separate worker RPC so cyclic station reads can
/// run between configuration batches. Other banks contribute only routing
/// references; their ValueText and Readable payloads are never requested.
Future<Map<String, Object?>> cipAcquireConfiguration(
    {required String root,
    required int modelOrdinal,
    required Map<String, Object?> descriptor,
    required Future<Map<String, Object?>> Function(List<String>) fetch,
    required Future<Map<String, Object?>> Function(Map<String, Object?>)
        assemble}) async {
  final prefix = descriptor['CanonicalRoot'];
  if (prefix is! String || modelOrdinal < 0)
    throw const FormatException('Invalid configuration request.');
  final values = <String, Object?>{};
  Future<void> batch(List<String> paths, int maximum) async {
    for (var offset = 0; offset < paths.length; offset += maximum) {
      final end =
          offset + maximum < paths.length ? offset + maximum : paths.length;
      values.addAll(await fetch(paths.sublist(offset, end)));
    }
  }

  await batch([
    for (final n in [
      'SchemaVersion',
      'RootIdentity',
      'Revision',
      'DefinitionCount',
      'DefinitionCapacity',
      'ValueCount',
      'ValueCapacity'
    ])
      '$prefix/$n'
  ], 16);
  for (final key in ['DefinitionCapacity', 'ValueCapacity']) {
    if (values['$prefix/$key'] != descriptor[key])
      throw const FormatException(
          'Configuration capacity differs from discovery.');
  }
  final definitions = values['$prefix/DefinitionCount'],
      count = values['$prefix/ValueCount'];
  if (definitions is! int ||
      definitions < 1 ||
      definitions > 32767 ||
      count is! int ||
      count < 1 ||
      count > 65535)
    throw const FormatException('Configuration count is unavailable.');
  await batch(
      [for (var i = 0; i < definitions; i++) '$prefix/Definitions[$i]'], 16);
  await batch([
    for (var i = 0; i < count; i++)
      for (final n in [
        'DefinitionIndex',
        'ModelOrdinal',
        'ModelCode',
        'Revision'
      ])
        '$prefix/Values[$i]/$n'
  ], 64);
  await batch([
    for (var i = 0; i < count; i++)
      if (values['$prefix/Values[$i]/ModelOrdinal'] == modelOrdinal)
        '$prefix/Values[$i]'
  ], 16);
  return assemble(values);
}

// Version-one wire definition: (atomic code, StringFamily byte capacity).
const cipConfigDefinitionLayout = {
  'DefinitionIndex': (0xc4, 0),
  'Scope': (0x2a0, 255),
  'Item': (0x2a0, 255),
  'WriteKey': (0x2a0, 160),
  'WriteRevision': (0xc4, 0),
  'ConfigKind': (0xc4, 0),
  'ValueType': (0xc4, 0),
  'Writable': (0xc1, 0),
  'RequiresReady': (0xc1, 0),
  'HasMinimum': (0xc1, 0),
  'HasMaximum': (0xc1, 0),
  'Minimum': (0xcb, 0),
  'Maximum': (0xcb, 0),
  'Unit': (0x2a0, 16),
  'LabelKey': (0x2a0, 160),
  'EnumDomain': (0x2a0, 255),
  'UnitCode': (0xc4, 0),
  'EnumLabelKey': (0x2a0, 80),
  'ClassId': (0x2a0, 40),
  'ReadLevel': (0xc4, 0),
  'WriteLevel': (0xc4, 0),
  'ModelScoped': (0xc1, 0),
  'CaptureSource': (0x2a0, 255),
  'CanCapture': (0xc1, 0)
};

/// Version-one PLC-owned configuration view. This reconstructs the existing
/// configuration-entry contract from published definitions and value rows;
/// it never selects a page or model bank through a command mailbox.
Map<String, Object?> cipConfigurationPage(
    {required Map<String, Object?> values,
    required String canonicalRoot,
    required String rootSymbol,
    int modelOrdinal = 0}) {
  Object requiredValue(String suffix) {
    final path = '$canonicalRoot/$suffix';
    if (!values.containsKey(path))
      throw FormatException('Configuration view row unavailable: $suffix.');
    return values[path]!;
  }

  int integer(String suffix, int lower, int upper) {
    final value = requiredValue(suffix);
    if (value is! int || value < lower || value > upper)
      throw FormatException('Invalid configuration view $suffix.');
    return value;
  }

  if (requiredValue('SchemaVersion') != 1 ||
      requiredValue('RootIdentity') != rootSymbol ||
      modelOrdinal < 0)
    throw const FormatException('Configuration view identity/version differs.');
  final revision = integer('Revision', 0, 0xffffffff),
      definitions = integer('DefinitionCount', 1, 32767),
      definitionCapacity = integer('DefinitionCapacity', 1, 32767),
      count = integer('ValueCount', 1, 65535),
      capacity = integer('ValueCapacity', 1, 65535);
  if (definitions != definitionCapacity || count > capacity)
    throw const FormatException('Configuration view allocation differs.');
  final rows = <int, Map<String, Object?>>{},
      bankNames = <int, String>{},
      seen = <String>{},
      definitionRows = <int, Map<String, Object?>>{};
  for (var i = 0; i < definitions; i++) {
    final prefix = 'Definitions[$i]';
    if (integer('$prefix/DefinitionIndex', 0, definitions - 1) != i)
      throw const FormatException('Definition ordinal differs.');
    final row = <String, Object?>{};
    for (final e in values.entries
        .where((e) => e.key.startsWith('$canonicalRoot/$prefix/')))
      row[e.key.substring(canonicalRoot.length + prefix.length + 2)] = e.value;
    if (row.length != cipConfigDefinitionLayout.length ||
        row.keys.any((k) => !cipConfigDefinitionLayout.containsKey(k)))
      throw const FormatException('Incomplete configuration definition.');
    for (final e in cipConfigDefinitionLayout.entries) {
      final value = row[e.key], layout = e.value;
      if (layout.$2 > 0
          ? value is! String || utf8.encode(value).length > layout.$2
          : layout.$1 == 0xc1
              ? value is! bool
              : layout.$1 == 0xcb
                  ? value is! double || !value.isFinite
                  : value is! int ||
                      value < (e.key == 'WriteRevision' ? 0 : -0x80000000) ||
                      value >
                          (e.key == 'WriteRevision' ? 0xffffffff : 0x7fffffff))
        throw FormatException('Invalid configuration definition ${e.key}.');
    }
    definitionRows[i] = row;
  }
  for (var i = 0; i < count; i++) {
    final prefix = 'Values[$i]',
        definition = integer('$prefix/DefinitionIndex', 0, definitions - 1),
        ordinal = integer('$prefix/ModelOrdinal', 0, 32767);
    final code = requiredValue('$prefix/ModelCode');
    if (integer('$prefix/Revision', 0, 0xffffffff) != revision ||
        code is! String ||
        !seen.add('$definition/$ordinal') ||
        (ordinal == 0 ? code.isNotEmpty : code.isEmpty) ||
        ordinal > 0 && definitionRows[definition]!['ModelScoped'] != true)
      throw const FormatException('Configuration value row/revision differs.');
    if (ordinal > 0 && bankNames.putIfAbsent(ordinal, () => code) != code)
      throw const FormatException('Model identity differs between rows.');
    if (ordinal == modelOrdinal) {
      final text = requiredValue('$prefix/ValueText'),
          readable = requiredValue('$prefix/Readable');
      if (text is! String || readable is! bool || !readable && text.isNotEmpty)
        throw const FormatException('Invalid masked value.');
      rows[definition] = {
        ...definitionRows[definition]!,
        'ValueText': text,
        'Readable': readable
      };
    }
  }
  for (final e in definitionRows.entries) {
    if (!seen.contains('${e.key}/0') ||
        e.value['ModelScoped'] == true &&
            bankNames.keys.any((n) => !seen.contains('${e.key}/$n')))
      throw const FormatException('Incomplete configuration value set.');
  }
  if (bankNames.isNotEmpty &&
      List.generate(bankNames.length, (i) => i + 1)
          .any((n) => !bankNames.containsKey(n)))
    throw const FormatException('Model ordinals are not contiguous.');
  if (modelOrdinal > 0 && !bankNames.containsKey(modelOrdinal))
    throw const FormatException('Requested model bank is absent.');
  final selected = rows.entries.toList()
    ..sort((a, b) => a.key.compareTo(b.key));
  return {
    'PageCount': 1,
    'EntryCount': selected.length,
    for (var i = 0; i < selected.length; i++)
      for (final e in selected[i].value.entries)
        'Entries[${i + 1}]/${e.key}': e.value
  };
}
