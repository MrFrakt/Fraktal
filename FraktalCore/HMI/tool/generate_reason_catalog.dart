import 'dart:convert';
import 'dart:io';

final _reasonPattern = RegExp(
  r'^\s*([A-Z][A-Z0-9_]*)\s*(?::\s*DINT\s*)?:=\s*(\d+)\s*[,;]',
  multiLine: true,
);

Future<void> main(List<String> arguments) async {
  final checkOnly = arguments.contains('--check');
  if (arguments.any((argument) => argument != '--check')) {
    stderr
        .writeln('Usage: dart run tool/generate_reason_catalog.dart [--check]');
    exitCode = 64;
    return;
  }

  final hmiRoot = File.fromUri(Platform.script).parent.parent;
  final sources = <File>[
    File('${hmiRoot.path}/../PLC/TwinCAT/Framework/Fraktal_Core/'
        'DUTs/E_Reason.TcDUT'),
    File('${hmiRoot.path}/../PLC/TwinCAT/Framework/Fraktal_Core/'
        'Params/PL_TcpDevReasons.TcGVL'),
    File('${hmiRoot.path}/../PLC/TwinCAT/Framework/Fraktal_Modules/'
        'Params/PL_ModuleReasons.TcGVL'),
  ];
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
      reasons.add(_Reason(code, symbol, _defaultText(symbol)));
    }
  }
  reasons.sort((left, right) => left.code.compareTo(right.code));
  if (reasons.isEmpty) throw StateError('No PLC reasons were discovered.');

  final generated = _render(reasons);
  final output = File('${hmiRoot.path}/lib/localization/reason_catalog.g.dart');
  if (checkOnly) {
    final current = output.existsSync() ? await output.readAsString() : '';
    if (current != generated) {
      stderr.writeln('Generated reason catalog is stale. Run:');
      stderr.writeln('  dart run tool/generate_reason_catalog.dart');
      exitCode = 1;
    }
    return;
  }
  await output.writeAsString(generated);
  stdout.writeln('Generated ${reasons.length} reasons at ${output.path}');
}

String _render(List<_Reason> reasons) {
  final buffer = StringBuffer()
    ..writeln('// GENERATED FILE — DO NOT EDIT.')
    ..writeln('// Source: PLC E_Reason + registered PL_*Reasons constants.')
    ..writeln()
    ..writeln('library;')
    ..writeln()
    ..writeln('const generatedReasonEnglish = <String, String>{');
  for (final reason in reasons) {
    buffer.writeln(
      '  ${jsonEncode('std.reason.${reason.code}')}: '
      '${jsonEncode(reason.text)},',
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
    ..writeln('String reasonDescriptionKey(int reasonCode, String fallback) =>')
    ..writeln('    reasonCode != 0 && generatedReasonSymbolByCode.containsKey(reasonCode)')
    ..writeln("        ? 'std.reason.\$reasonCode'")
    ..writeln('        : fallback;');
  return buffer.toString();
}

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

final class _Reason {
  final int code;
  final String symbol;
  final String text;

  const _Reason(this.code, this.symbol, this.text);
}
