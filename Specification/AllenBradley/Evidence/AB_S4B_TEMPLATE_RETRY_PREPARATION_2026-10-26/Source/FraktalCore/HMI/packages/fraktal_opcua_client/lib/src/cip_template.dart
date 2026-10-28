library;

import 'dart:convert';
import 'dart:typed_data';

/// Physical Logix layout from Symbol/Template discovery, without station facts.
/// Logical units, array bounds and access belong to the validated manifest.
final class CipTemplateDecoder {
  static const maxBytes = 16 * 1024 * 1024;
  static const maxMembers = 100000;
  static const maxDepth = 64;
  final Map<int, CipTemplate> templates;

  CipTemplateDecoder(Iterable<CipTemplate> discovered)
      : templates = _registry(discovered) {
    final complete = <int>{};
    void visit(int handle, Set<int> stack) {
      if (stack.contains(handle) || stack.length >= maxDepth) {
        throw const FormatException('Recursive or over-deep CIP Template.');
      }
      if (complete.contains(handle)) return;
      final template = templates[handle];
      if (template == null) {
        throw const FormatException('Missing referenced CIP Template.');
      }
      for (final member in template.members) {
        if (member.isStructure) visit(member.handle, {...stack, handle});
      }
      complete.add(handle);
    }

    for (final handle in templates.keys) {
      visit(handle, {});
    }
  }

  factory CipTemplateDecoder.fromCapture(List<Object?> rows) =>
      CipTemplateDecoder(rows.map((row) {
        if (row is! Map) {
          throw const FormatException('Invalid CIP Template descriptor.');
        }
        return CipTemplate.fromCapture(Map<String, Object?>.from(row));
      }));

  static Map<int, CipTemplate> _registry(Iterable<CipTemplate> discovered) {
    final result = <int, CipTemplate>{};
    var members = 0;
    for (final template in discovered) {
      members += template.members.length;
      if (result.containsKey(template.handle) || members > maxMembers) {
        throw const FormatException('Duplicate or oversized CIP Template set.');
      }
      result[template.handle] = template;
    }
    if (result.isEmpty) throw const FormatException('No CIP Templates.');
    return Map.unmodifiable(result);
  }

  /// Decode exactly one record using attribute 5's size, including array stride.
  /// Int64, UInt64 and native 64-bit time values use BigInt so no bit is lost.
  Object decode(int handle, Uint8List raw) {
    final template = templates[handle];
    if (template == null || raw.length != template.byteSize) {
      throw const FormatException('CIP record size differs from its Template.');
    }
    var remaining = maxMembers;
    void spend(int count) {
      remaining -= count;
      if (remaining < 0) {
        throw const FormatException('CIP decoded value budget exceeded.');
      }
    }

    return _record(template, ByteData.sublistView(raw), 0, spend);
  }

  /// Decode a directly addressed member or one structure-array element. BOOL
  /// tag replies contain a value byte; the enclosing record's bit offset does
  /// not apply to that reply.
  Object decodeMember(CipTemplateMember member, Uint8List raw,
      {bool element = false}) {
    var remaining = maxMembers;
    void spend(int count) {
      remaining -= count;
      if (remaining < 0)
        throw const FormatException('CIP value budget exceeded.');
    }

    final count = member.isArray && !element ? member.info : 1;
    final bytes = ByteData.sublistView(raw);
    if (member.isStructure) {
      final type = templates[member.handle]!;
      if (raw.length != type.byteSize * count) {
        throw const FormatException('Addressed structure extent differs.');
      }
      final values = [
        for (var i = 0; i < count; i++)
          _record(type, bytes, i * type.byteSize, spend)
      ];
      return member.isArray && !element ? values : values.single;
    }
    if (member.atomic == 0xc1) {
      final width = member.isArray && !element ? ((count + 31) ~/ 32) * 4 : 1;
      if (raw.length != width)
        throw const FormatException('BOOL reply extent differs.');
      if (width == 1) {
        return raw[0] != 0;
      }
      return [
        for (var i = 0; i < count; i++)
          bytes.getUint8(i ~/ 8) & (1 << (i % 8)) != 0
      ];
    }
    final width = atomicByteSize(member.atomic);
    if (raw.length != count * width)
      throw const FormatException('Atomic reply extent differs.');
    final values = [
      for (var i = 0; i < count; i++) _atomic(bytes, i * width, member.atomic)
    ];
    return member.isArray && !element ? values : values.single;
  }

  Object _record(
      CipTemplate template, ByteData raw, int base, void Function(int) spend) {
    spend(template.members.length + 1);
    void require(int offset, int length) {
      if (offset < 0 || length < 0 || offset + length > template.byteSize) {
        throw const FormatException('CIP member exceeds its Template extent.');
      }
    }

    final stringWidth = template.stringByteCapacity;
    if (stringWidth != null) {
      final lengthMember = template.members[0];
      final dataMember = template.members[1];
      require(lengthMember.offset, 4);
      require(dataMember.offset, stringWidth);
      if (dataMember.offset < lengthMember.offset + 4) {
        throw const FormatException('Overlapping StringFamily members.');
      }
      final length = raw.getInt32(base + lengthMember.offset, Endian.little);
      if (length < 0 || length > stringWidth) {
        throw const FormatException('StringFamily LEN exceeds byte capacity.');
      }
      return utf8.decode(raw.buffer
          .asUint8List(raw.offsetInBytes + base + dataMember.offset, length));
    }

    final result = <String, Object?>{};
    for (final member in template.members) {
      final offset = member.offset;
      final at = base + offset;
      final count = member.isArray ? member.info : 1;
      spend(count);
      if (member.isStructure) {
        final child = templates[member.handle]!;
        require(offset, child.byteSize * count);
        final values = [
          for (var index = 0; index < count; index++)
            _record(child, raw, at + index * child.byteSize, spend)
        ];
        result[member.name] = member.isArray ? values : values.single;
      } else if (member.atomic == 0xc1) {
        if (member.isArray) {
          require(offset, ((count + 31) ~/ 32) * 4);
          result[member.name] = [
            for (var index = 0; index < count; index++)
              raw.getUint8(at + index ~/ 8) & (1 << (index % 8)) != 0
          ];
        } else {
          if (member.info > 31) {
            throw const FormatException('Invalid CIP BOOL bit number.');
          }
          require(offset, member.info ~/ 8 + 1);
          result[member.name] =
              raw.getUint8(at + member.info ~/ 8) & (1 << (member.info % 8)) !=
                  0;
        }
      } else {
        final width = atomicByteSize(member.atomic);
        require(offset, count * width);
        final values = [
          for (var index = 0; index < count; index++)
            _atomic(raw, at + index * width, member.atomic)
        ];
        result[member.name] = member.isArray ? values : values.single;
      }
    }
    return result;
  }

  static int atomicByteSize(int code) => switch (code) {
        0xc2 || 0xc6 => 1,
        0xc3 || 0xc7 => 2,
        0xc4 || 0xc8 || 0xca || 0xd3 || 0xd6 => 4,
        0xc5 || 0xc9 || 0xcb || 0xc0 || 0xcc || 0xd7 || 0xdf => 8,
        _ => throw FormatException('Unsupported CIP atomic type: $code.'),
      };

  static Object _atomic(ByteData bytes, int at, int code) {
    if ({0xc5, 0xc9, 0xc0, 0xcc, 0xd7, 0xdf}.contains(code)) {
      final unsigned = BigInt.from(bytes.getUint32(at, Endian.little)) |
          (BigInt.from(bytes.getUint32(at + 4, Endian.little)) << 32);
      return code != 0xc9 && (unsigned & (BigInt.one << 63)) != BigInt.zero
          ? unsigned - (BigInt.one << 64)
          : unsigned;
    }
    final Object value = switch (code) {
      0xc2 => bytes.getInt8(at),
      0xc6 => bytes.getUint8(at),
      0xc3 => bytes.getInt16(at, Endian.little),
      0xc7 => bytes.getUint16(at, Endian.little),
      0xc4 || 0xd6 => bytes.getInt32(at, Endian.little),
      0xc8 || 0xd3 => bytes.getUint32(at, Endian.little),
      0xca => bytes.getFloat32(at, Endian.little),
      0xcb => bytes.getFloat64(at, Endian.little),
      _ => throw FormatException('Unsupported CIP atomic type: $code.'),
    };
    if (value is double && !value.isFinite) {
      throw const FormatException('Non-finite CIP floating-point value.');
    }
    return value;
  }
}

final class CipTemplate {
  final int handle;
  final String name;
  final int byteSize;
  final List<CipTemplateMember> members;

  CipTemplate(this.handle, this.name, this.byteSize,
      Iterable<CipTemplateMember> discovered)
      : members = List.unmodifiable(discovered
            .where((member) => !member.name.startsWith('ZZZZZZZZZZ'))
            .toList()
          ..sort((a, b) {
            final offset = a.offset.compareTo(b.offset);
            return offset != 0 ? offset : a.info.compareTo(b.info);
          })) {
    if (handle <= 0 ||
        handle > 0xfff ||
        name.isEmpty ||
        byteSize <= 0 ||
        byteSize > CipTemplateDecoder.maxBytes ||
        members.length > CipTemplateDecoder.maxMembers ||
        members.map((member) => member.name).toSet().length != members.length) {
      throw const FormatException(
          'Invalid CIP Template identity/size/members.');
    }
  }

  factory CipTemplate.fromCapture(Map<String, Object?> row) {
    final members = row['members'];
    if (row['name'] is! String || members is! List) {
      throw const FormatException('Invalid CIP Template descriptor.');
    }
    return CipTemplate(_integer(row, 'handle'), row['name'] as String,
        _integer(row, 'byteSize'), members.map((member) {
      if (member is! Map) {
        throw const FormatException('Invalid CIP Template member descriptor.');
      }
      final value = Map<String, Object?>.from(member);
      if (value['name'] is! String) {
        throw const FormatException('Missing CIP Template member name.');
      }
      return CipTemplateMember(value['name'] as String, _integer(value, 'info'),
          _integer(value, 'code'), _integer(value, 'offset'));
    }));
  }

  int? get stringByteCapacity {
    if (members.length != 2) return null;
    final length = members[0], data = members[1];
    return length.name == 'LEN' &&
            !length.isStructure &&
            length.atomic == 0xc4 &&
            !length.isArray &&
            data.name == 'DATA' &&
            !data.isStructure &&
            data.atomic == 0xc2 &&
            data.isArray
        ? data.info
        : null;
  }
}

final class CipTemplateMember {
  final String name;
  final int info;
  final int code;
  final int offset;

  CipTemplateMember(this.name, this.info, this.code, this.offset) {
    if (!RegExp(r'^[A-Za-z_][A-Za-z0-9_]*$').hasMatch(name) ||
        info < 0 ||
        info > 0xffff ||
        code < 0 ||
        code > 0xffff ||
        offset < 0 ||
        offset > CipTemplateDecoder.maxBytes ||
        (code & 0x6000) >> 13 > 1 ||
        isArray && info == 0) {
      throw const FormatException('Invalid CIP Template member.');
    }
  }

  bool get isStructure => code & 0x8000 != 0;
  bool get isArray => code & 0x6000 != 0;
  int get handle => code & 0xfff;
  int get atomic => code & 0xff;
}

int _integer(Map<String, Object?> row, String key) {
  final value = row[key];
  if (value is! int) throw FormatException('Invalid CIP integer: $key.');
  return value;
}
