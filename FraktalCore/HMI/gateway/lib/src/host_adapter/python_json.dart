/// Python's `json` text forms, so files the adapter writes are the bytes the
/// engineering code writes (a set document, a host-event sink, a cursor).
library;

/// Python's `json.dumps(..., ensure_ascii=True)` string form.
String pythonJsonString(String value) {
  final out = StringBuffer('"');
  for (final unit in value.codeUnits) {
    switch (unit) {
      case 0x22:
        out.write(r'\"');
      case 0x5c:
        out.write(r'\\');
      case 0x0a:
        out.write(r'\n');
      case 0x0d:
        out.write(r'\r');
      case 0x09:
        out.write(r'\t');
      case 0x08:
        out.write(r'\b');
      case 0x0c:
        out.write(r'\f');
      default:
        // Python escapes everything outside space..tilde, DEL included.
        out.write(unit < 0x20 || unit > 0x7e
            ? '\\u${unit.toRadixString(16).padLeft(4, '0')}'
            : String.fromCharCode(unit));
    }
  }
  return (out..write('"')).toString();
}

/// Python's `json.dumps(value, sort_keys=True)`: default separators, ASCII.
/// Only the JSON types host records use; a double is refused, not guessed.
String pythonJsonDumps(Object? value) {
  if (value == null) return 'null';
  if (value is bool) return value ? 'true' : 'false';
  if (value is int) return '$value';
  if (value is String) return pythonJsonString(value);
  if (value is List) return '[${value.map(pythonJsonDumps).join(', ')}]';
  if (value is Map) {
    final keys = [for (final k in value.keys) k as String]..sort(_codePointOrder);
    return '{${keys.map((k) => '${pythonJsonString(k)}: ${pythonJsonDumps(value[k])}').join(', ')}}';
  }
  throw ArgumentError('not a host-record JSON value: ${value.runtimeType}');
}

// Python sorts str keys by code point; Dart's compareTo compares UTF-16 units,
// which differs only above the BMP. Keys here are ASCII; compare by rune anyway.
int _codePointOrder(String a, String b) {
  final x = a.runes.toList(), y = b.runes.toList();
  for (var i = 0; i < x.length && i < y.length; i++) {
    if (x[i] != y[i]) return x[i] - y[i];
  }
  return x.length - y.length;
}

/// Strict JSON: what the engineering code writes parses, nothing looser does.
Object? strictJsonDecode(String text) => _StrictJson(text).document();

/// A strict JSON reader: duplicate members, non-finite constants and raw
/// control characters refuse, as Python's loader with the set hooks does.
final class _StrictJson {
  final String s;
  int i = 0;
  _StrictJson(this.s);

  Object? document() {
    final value = _value();
    _space();
    if (i != s.length) throw const FormatException('trailing data');
    return value;
  }

  void _space() {
    while (i < s.length && ' \t\n\r'.contains(s[i])) {
      i++;
    }
  }

  Object? _value() {
    _space();
    if (i >= s.length) throw const FormatException('end of input');
    final c = s[i];
    if (c == '{') return _object();
    if (c == '[') return _array();
    if (c == '"') return _string();
    for (final (word, value) in [('true', true), ('false', false), ('null', null)]) {
      if (s.startsWith(word, i)) {
        i += word.length;
        return value;
      }
    }
    return _number();
  }

  Map<String, Object?> _object() {
    i++;
    final out = <String, Object?>{};
    _space();
    if (i < s.length && s[i] == '}') {
      i++;
      return out;
    }
    while (true) {
      _space();
      if (i >= s.length || s[i] != '"') throw const FormatException('key');
      final key = _string();
      _space();
      if (i >= s.length || s[i] != ':') throw const FormatException('colon');
      i++;
      if (out.containsKey(key)) throw const FormatException('duplicate JSON member');
      out[key] = _value();
      _space();
      if (i < s.length && s[i] == ',') {
        i++;
        continue;
      }
      if (i < s.length && s[i] == '}') {
        i++;
        return out;
      }
      throw const FormatException('object');
    }
  }

  List<Object?> _array() {
    i++;
    final out = <Object?>[];
    _space();
    if (i < s.length && s[i] == ']') {
      i++;
      return out;
    }
    while (true) {
      out.add(_value());
      _space();
      if (i < s.length && s[i] == ',') {
        i++;
        continue;
      }
      if (i < s.length && s[i] == ']') {
        i++;
        return out;
      }
      throw const FormatException('array');
    }
  }

  String _string() {
    i++;
    final out = StringBuffer();
    while (true) {
      if (i >= s.length) throw const FormatException('unterminated string');
      final c = s.codeUnitAt(i++);
      if (c == 0x22) return out.toString();
      if (c < 0x20) throw const FormatException('control character');
      if (c != 0x5c) {
        out.writeCharCode(c);
        continue;
      }
      if (i >= s.length) throw const FormatException('escape');
      final e = s[i++];
      switch (e) {
        case '"' || r'\' || '/':
          out.write(e);
        case 'b':
          out.write('\b');
        case 'f':
          out.write('\f');
        case 'n':
          out.write('\n');
        case 'r':
          out.write('\r');
        case 't':
          out.write('\t');
        case 'u':
          if (i + 4 > s.length) throw const FormatException('escape');
          out.writeCharCode(int.parse(s.substring(i, i + 4), radix: 16));
          i += 4;
        default:
          throw const FormatException('escape');
      }
    }
  }

  Object _number() {
    final match = RegExp(r'-?(?:0|[1-9][0-9]*)(\.[0-9]+)?([eE][+-]?[0-9]+)?')
        .matchAsPrefix(s, i);
    if (match == null || match.end == i) throw const FormatException('value');
    i = match.end;
    final text = match.group(0)!;
    // A fraction or exponent is a float in Python: never an integer field.
    return match.group(1) != null || match.group(2) != null
        ? double.parse(text)
        : int.parse(text);
  }
}
