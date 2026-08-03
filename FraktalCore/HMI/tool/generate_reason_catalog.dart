import 'dart:convert';
import 'dart:io';

final _reasonPattern = RegExp(
  r'^\s*([A-Z][A-Z0-9_]*)\s*(?::\s*DINT\s*)?:=\s*(\d+)\s*(?:[,;]|(?=\)))',
  multiLine: true,
);

const _priorityOrdinal = <String, int>{'LOW': 0, 'MED': 1, 'HIGH': 2};
const _categoryOrdinal = <String, int>{
  'PROCESS': 0,
  'SAFETY': 1,
  'SYSTEM': 2,
};

Future<void> main(List<String> arguments) async {
  final checkOnly = arguments.contains('--check');
  if (arguments.any((argument) => argument != '--check')) {
    stderr
        .writeln('Usage: dart run tool/generate_reason_catalog.dart [--check]');
    exitCode = 64;
    return;
  }

  final hmiRoot = File.fromUri(Platform.script).parent.parent;
  final repositoryRoot = hmiRoot.parent.parent;
  final sources = <File>[
    File('${hmiRoot.path}/../PLC/TwinCAT/Framework/Fraktal_Core/'
        'DUTs/E_Reason.TcDUT'),
    File('${hmiRoot.path}/../PLC/TwinCAT/Framework/Fraktal_Core/'
        'Params/PL_TcpDevReasons.TcGVL'),
    File('${hmiRoot.path}/../PLC/TwinCAT/Framework/Fraktal_Modules/'
        'Params/PL_ModuleReasons.TcGVL'),
  ];
  final metadataFile =
      File('${repositoryRoot.path}/Specification/reason_rationalization.json');
  final metadata = await _readMetadata(metadataFile);
  final reasons = <_Reason>[];
  final codes = <int>{};
  final symbols = <String>{};
  for (final source in sources) {
    if (!source.existsSync()) {
      throw StateError('Reason source is missing: ${source.path}');
    }
    final text = await source.readAsString();
    for (final match in _reasonPattern.allMatches(text)) {
      final symbol = match.group(1)!;
      final code = int.parse(match.group(2)!);
      if (code == 0) continue;
      if (!codes.add(code)) throw StateError('Duplicate reason code: $code');
      if (!symbols.add(symbol)) {
        throw StateError('Duplicate reason symbol: $symbol');
      }
      final rationalization = metadata[symbol];
      if (rationalization == null) {
        throw StateError('Missing rationalization for PLC reason $symbol.');
      }
      reasons.add(_Reason(
        code,
        symbol,
        _defaultText(symbol),
        rationalization,
      ));
    }
  }
  final unusedMetadata = metadata.keys.toSet()..removeAll(symbols);
  if (unusedMetadata.isNotEmpty) {
    throw StateError(
      'Rationalization exists for unknown PLC reason(s): '
      '${unusedMetadata.toList()..sort()}',
    );
  }
  reasons.sort((left, right) => left.code.compareTo(right.code));
  if (reasons.isEmpty) throw StateError('No PLC reasons were discovered.');

  final coreRoot = Directory(
    '${hmiRoot.path}/../PLC/TwinCAT/Framework/Fraktal_Core',
  );
  final outputs = <File, String>{
    File('${hmiRoot.path}/lib/localization/reason_catalog.g.dart'):
        _renderDart(reasons),
    File('${coreRoot.path}/Params/PL_ReasonCatalog.TcGVL'):
        _renderPlcCount(reasons.length),
    File('${coreRoot.path}/Platform/F_ReasonMetaByIndex.TcPOU'):
        _renderPlcByIndex(reasons),
    File('${coreRoot.path}/Platform/F_ReasonMeta.TcPOU'): _renderPlcLookup(),
  };
  if (checkOnly) {
    final stale = <String>[];
    for (final entry in outputs.entries) {
      final current =
          entry.key.existsSync() ? await entry.key.readAsString() : '';
      if (current != entry.value) stale.add(entry.key.path);
    }
    if (stale.isNotEmpty) {
      stderr.writeln('Generated reason catalog artifact(s) are stale:');
      for (final path in stale) {
        stderr.writeln('  $path');
      }
      stderr.writeln('Run: dart run tool/generate_reason_catalog.dart');
      exitCode = 1;
    }
    return;
  }
  for (final entry in outputs.entries) {
    await entry.key.parent.create(recursive: true);
    await entry.key.writeAsString(entry.value);
  }
  stdout.writeln(
    'Generated ${reasons.length} rationalized reasons into '
    '${outputs.length} derived artifacts.',
  );
}

Future<Map<String, _Rationalization>> _readMetadata(File file) async {
  if (!file.existsSync()) {
    throw StateError(
        'Reason rationalization registry is missing: ${file.path}');
  }
  final decoded = jsonDecode(await file.readAsString());
  if (decoded is! Map<String, dynamic> || decoded['schemaVersion'] != 1) {
    throw StateError('Unsupported reason rationalization schema.');
  }
  final rawReasons = decoded['reasons'];
  if (rawReasons is! Map<String, dynamic>) {
    throw StateError('Reason rationalization registry has no reasons object.');
  }
  return rawReasons.map((symbol, raw) {
    if (raw is! Map<String, dynamic>) {
      throw StateError('Invalid rationalization for $symbol.');
    }
    final priority = raw['priority'];
    final category = raw['category'];
    final shelvable = raw['shelvable'];
    final action = raw['action'];
    final consequence = raw['consequence'];
    if (!_priorityOrdinal.containsKey(priority) ||
        !_categoryOrdinal.containsKey(category) ||
        shelvable is! bool ||
        action is! String ||
        consequence is! String ||
        consequence.trim().isEmpty) {
      throw StateError('Incomplete rationalization for $symbol.');
    }
    if (category == 'SAFETY' && shelvable) {
      throw StateError('Safety reason $symbol cannot be shelvable.');
    }
    if (shelvable && action.trim().isEmpty) {
      throw StateError('Event-only reason $symbol cannot be shelvable.');
    }
    if (action.trim().isEmpty &&
        !symbol.startsWith('EVENT_') &&
        symbol != 'TEST_FAULT') {
      throw StateError('Alarm reason $symbol requires an operator action.');
    }
    return MapEntry(
      symbol,
      _Rationalization(priority, category, shelvable, action, consequence),
    );
  });
}

String _renderDart(List<_Reason> reasons) {
  final buffer = StringBuffer()
    ..writeln('// GENERATED FILE — DO NOT EDIT.')
    ..writeln(
        '// Source: PLC reason definitions + Specification/reason_rationalization.json.')
    ..writeln()
    ..writeln('library;')
    ..writeln()
    ..writeln('const generatedReasonEnglish = <String, String>{');
  for (final reason in reasons) {
    buffer.writeln(
      '  ${jsonEncode('std.reason.${reason.code}')}: '
      '${jsonEncode(reason.text)},',
    );
    if (reason.meta.action.isNotEmpty) {
      buffer.writeln(
        '  ${jsonEncode('std.reason.${reason.code}.action')}: '
        '${jsonEncode(reason.meta.action)},',
      );
    }
    buffer.writeln(
      '  ${jsonEncode('std.reason.${reason.code}.consequence')}: '
      '${jsonEncode(reason.meta.consequence)},',
    );
  }
  buffer
    ..writeln('};')
    ..writeln()
    ..writeln('const generatedReasonSymbolByCode = <int, String>{');
  for (final reason in reasons) {
    buffer.writeln('  ${reason.code}: ${jsonEncode(reason.symbol)},');
  }
  buffer
    ..writeln('};')
    ..writeln()
    ..writeln('const generatedReasonPriorityByCode = <int, int>{');
  for (final reason in reasons) {
    buffer.writeln(
      '  ${reason.code}: ${_priorityOrdinal[reason.meta.priority]},',
    );
  }
  buffer
    ..writeln('};')
    ..writeln()
    ..writeln('const generatedReasonCategoryByCode = <int, int>{');
  for (final reason in reasons) {
    buffer.writeln(
      '  ${reason.code}: ${_categoryOrdinal[reason.meta.category]},',
    );
  }
  buffer
    ..writeln('};')
    ..writeln()
    ..writeln('const generatedReasonShelvableByCode = <int, bool>{');
  for (final reason in reasons) {
    buffer.writeln('  ${reason.code}: ${reason.meta.shelvable},');
  }
  buffer
    ..writeln('};')
    ..writeln()
    ..writeln('const generatedReasonHasOperatorAction = <int>{');
  for (final reason
      in reasons.where((reason) => reason.meta.action.isNotEmpty)) {
    buffer.writeln('  ${reason.code},');
  }
  buffer
    ..writeln('};')
    ..writeln()
    ..writeln('String reasonDescriptionKey(int reasonCode, String fallback) =>')
    ..writeln(
        '    reasonCode != 0 && generatedReasonSymbolByCode.containsKey(reasonCode)')
    ..writeln("        ? 'std.reason.\$reasonCode'")
    ..writeln('        : fallback;')
    ..writeln()
    ..writeln('String reasonActionKey(int reasonCode) =>')
    ..writeln('    generatedReasonHasOperatorAction.contains(reasonCode)')
    ..writeln("        ? 'std.reason.\$reasonCode.action'")
    ..writeln("        : '';")
    ..writeln()
    ..writeln('String reasonConsequenceKey(int reasonCode) =>')
    ..writeln('    generatedReasonSymbolByCode.containsKey(reasonCode)')
    ..writeln("        ? 'std.reason.\$reasonCode.consequence'")
    ..writeln("        : '';");
  return buffer.toString();
}

String _renderPlcCount(int count) => '''<?xml version="1.0" encoding="utf-8"?>
<TcPlcObject Version="1.1.0.1" ProductVersion="3.1.4024.12">
  <GVL Name="PL_ReasonCatalog" Id="{51b77bda-8d2b-4dad-9187-16d040699e35}">
    <Declaration><![CDATA[{attribute 'qualified_only'}
// GENERATED FILE — DO NOT EDIT. §8.8/§8.9 catalog size.
VAR_GLOBAL CONSTANT
    COUNT : INT := $count;
END_VAR]]></Declaration>
  </GVL>
</TcPlcObject>
''';

String _renderPlcByIndex(List<_Reason> reasons) {
  final body = StringBuffer()
    ..writeln('F_ReasonMetaByIndex := FALSE;')
    ..writeln('Meta.ReasonCode := E_Reason.NONE;')
    ..writeln("Meta.OperatorAction := '';")
    ..writeln("Meta.Consequence := '';")
    ..writeln('Meta.Priority := E_Severity.LOW;')
    ..writeln('Meta.Category := E_Category.PROCESS;')
    ..writeln('Meta.Shelvable := FALSE;')
    ..writeln('CASE Index OF');
  for (var index = 0; index < reasons.length; index++) {
    final reason = reasons[index];
    body
      ..writeln('    ${index + 1}:')
      ..writeln('        Meta.ReasonCode := ${reason.code};')
      ..writeln(
        "        Meta.OperatorAction := '${reason.meta.action.isEmpty ? '' : 'std.reason.${reason.code}.action'}';",
      )
      ..writeln(
        "        Meta.Consequence := 'std.reason.${reason.code}.consequence';",
      )
      ..writeln('        Meta.Priority := E_Severity.${reason.meta.priority};')
      ..writeln('        Meta.Category := E_Category.${reason.meta.category};')
      ..writeln(
          '        Meta.Shelvable := ${reason.meta.shelvable.toString().toUpperCase()};');
  }
  body
    ..writeln('ELSE')
    ..writeln('    RETURN;')
    ..writeln('END_CASE')
    ..writeln('F_ReasonMetaByIndex := TRUE;');
  return '''<?xml version="1.0" encoding="utf-8"?>
<TcPlcObject Version="1.1.0.1" ProductVersion="3.1.4024.12">
  <POU Name="F_ReasonMetaByIndex" Id="{c23abbdb-75fc-481a-bd8e-e572f49cde5f}" SpecialFunc="None">
    <Declaration><![CDATA[// GENERATED FILE — DO NOT EDIT. Core §8.8/§8.9 complete catalog projection.
FUNCTION F_ReasonMetaByIndex : BOOL
VAR_INPUT
    Index : INT;
END_VAR
VAR_IN_OUT
    Meta : ST_AlarmMeta;
END_VAR]]></Declaration>
    <Implementation>
      <ST><![CDATA[$body]]></ST>
    </Implementation>
  </POU>
</TcPlcObject>
''';
}

String _renderPlcLookup() => '''<?xml version="1.0" encoding="utf-8"?>
<TcPlcObject Version="1.1.0.1" ProductVersion="3.1.4024.12">
  <POU Name="F_ReasonMeta" Id="{f5bb2674-c3b7-4528-b71d-d895984b9af1}" SpecialFunc="None">
    <Declaration><![CDATA[// Core §8.9 — resolve one generated rationalization by ReasonCode.
FUNCTION F_ReasonMeta : BOOL
VAR_INPUT
    Reason : E_Reason;
END_VAR
VAR_IN_OUT
    Meta : ST_AlarmMeta;
END_VAR
VAR
    i : INT;
    candidate : ST_AlarmMeta;
END_VAR]]></Declaration>
    <Implementation>
      <ST><![CDATA[F_ReasonMeta := FALSE;
FOR i := 1 TO PL_ReasonCatalog.COUNT DO
    IF F_ReasonMetaByIndex(Index := i, Meta := candidate)
    AND (candidate.ReasonCode = Reason) THEN
        Meta := candidate;
        F_ReasonMeta := TRUE;
        RETURN;
    END_IF
END_FOR]]></ST>
    </Implementation>
  </POU>
</TcPlcObject>
''';

String _defaultText(String symbol) {
  var words = symbol.split('_');
  if (words.first == 'EVENT') words = words.skip(1).toList();
  const replacements = <String, String>{
    'AIR': 'air',
    'CFG': 'configuration',
    'CPU': 'CPU',
    'CYL': 'cylinder',
    'DC': 'DC',
    'DEV': 'device',
    'IPC': 'IPC',
    'POS': 'position',
    'RESP': 'response',
    'RX': 'receive',
  };
  final normalized = [
    for (final word in words) replacements[word] ?? word.toLowerCase(),
  ];
  final first = normalized.first;
  normalized[0] = '${first[0].toUpperCase()}${first.substring(1)}';
  return '${normalized.join(' ')}.';
}

final class _Rationalization {
  final String priority;
  final String category;
  final bool shelvable;
  final String action;
  final String consequence;

  const _Rationalization(
    this.priority,
    this.category,
    this.shelvable,
    this.action,
    this.consequence,
  );
}

final class _Reason {
  final int code;
  final String symbol;
  final String text;
  final _Rationalization meta;

  const _Reason(this.code, this.symbol, this.text, this.meta);
}
