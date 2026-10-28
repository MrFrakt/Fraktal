library;

import 'dart:convert';
import 'dart:typed_data';

import 'cip_template.dart';
import 'cip_transport.dart';

final class CipSymbol {
  final String name;
  final int instance, typeCode;
  CipSymbol(this.name, this.instance, this.typeCode);
  int get rank => (typeCode >> 13) & 3;
  bool get structured => typeCode & 0x8000 != 0;
  int get handle => typeCode & 0xfff;
  int get atomic => typeCode & 0xff;

  factory CipSymbol.fromCapture(Map row) => CipSymbol(
      row['name'] as String,
      row['instance'] as int? ?? 0,
      row['typeCode'] as int? ??
          (row['handle'] != null
              ? 0x8000 |
                  (row['arrayRank'] as int? ?? 0) << 13 |
                  (row['handle'] as int)
              : (row['atomic'] as int) |
                  (row['arrayRank'] as int? ?? 0) << 13));
}

/// Raw Template metadata is kept separately until publication selection. An
/// unrelated system/predefined or multidimensional tag must not prevent a
/// canonical root from being discovered; only selected layouts are decoded.
final class CipRawTemplate {
  final int handle, byteSize, structureHandle;
  final String name;
  final List<Map<String, Object?>> members;
  CipRawTemplate(this.handle, this.name, this.byteSize, this.structureHandle,
      this.members);
  CipTemplate checked() => CipTemplate(
      handle,
      name,
      byteSize,
      members.map((m) => CipTemplateMember(m['name'] as String,
          m['info'] as int, m['code'] as int, m['offset'] as int)));
  bool get hasStatus => members.any((m) =>
      m['name'] == 'Status' &&
      (m['code'] as int) & 0x8000 != 0 &&
      (m['code'] as int) & 0x6000 == 0);
}

final class CipNamespace {
  static const maxLeaves = 100000, maxBytes = 16 * 1024 * 1024;
  final Map<String, CipSymbol> symbols;
  final Map<int, CipRawTemplate> templates;
  CipNamespace(this.symbols, this.templates);

  factory CipNamespace.fromCapture(Map capture) {
    final symbols = <String, CipSymbol>{};
    final templates = <int, CipRawTemplate>{};
    for (final row in capture['symbols'] as List) {
      final symbol = CipSymbol.fromCapture(row as Map);
      if (symbols.containsKey(symbol.name))
        throw const FormatException('Duplicate Symbol.');
      symbols[symbol.name] = symbol;
    }
    for (final row in capture['templates'] as List) {
      final r = row as Map;
      final handle = r['handle'] as int;
      if (templates.containsKey(handle))
        throw const FormatException('Duplicate Template.');
      templates[handle] = CipRawTemplate(handle, r['name'] as String,
          r['byteSize'] as int, r['structureHandle'] as int? ?? 0, [
        for (final member in r['members'] as List)
          Map<String, Object?>.from(member as Map)
      ]);
    }
    return CipNamespace(symbols, templates);
  }

  static Future<CipNamespace> discover(CipReadTransport wire) async {
    final symbols = <String, CipSymbol>{};
    var next = 0;
    var symbolCount = 0;
    for (var page = 0; page < maxLeaves; page++) {
      // Attributes 1 and 2 suffice: names/type carry the complete rank/handle.
      final reply = await wire.request(
          0x55, cipObjectPath(0x6b, next), cipWords([2, 1, 2]));
      if (reply.status != 0 && reply.status != 6) reply.requireSuccess();
      final data = ByteData.sublistView(reply.data);
      var at = 0, last = next - 1;
      while (at < reply.data.length) {
        if (at + 8 > reply.data.length)
          throw const FormatException('Truncated Symbol row.');
        final instance = data.getUint32(at, Endian.little),
            length = data.getUint16(at + 4, Endian.little);
        at += 6;
        if (instance < next ||
            instance <= last ||
            length < 1 ||
            length > 2048 ||
            at + length + 2 > reply.data.length) {
          throw const FormatException('Invalid Symbol cursor/name extent.');
        }
        final name =
            utf8.decode(Uint8List.sublistView(reply.data, at, at + length));
        at += length;
        final code = data.getUint16(at, Endian.little);
        at += 2;
        last = instance;
        if (++symbolCount > maxLeaves)
          throw const FormatException('Symbol budget exceeded.');
        if (code & 0x1000 == 0 &&
            RegExp(r'^[A-Za-z_][A-Za-z0-9_]*$').hasMatch(name) &&
            !name.startsWith('__')) {
          if (symbols.containsKey(name))
            throw const FormatException('Duplicate controller Symbol.');
          symbols[name] = CipSymbol(name, instance, code);
        }
      }
      if (reply.status == 0) break;
      if (last < next || last == 0xffffffff)
        throw const FormatException('Symbol cursor made no progress.');
      next = last + 1;
      if (page == maxLeaves - 1)
        throw const FormatException('Symbol pagination budget exceeded.');
    }
    final templates = <int, CipRawTemplate>{};
    var definitionBytes = 0, memberCount = 0;
    final queue = <int>{
      for (final s in symbols.values)
        if (s.structured) s.handle
    };
    while (queue.isNotEmpty) {
      final handle = queue.first;
      queue.remove(handle);
      if (templates.containsKey(handle)) continue;
      if (handle < 1 || handle > 0xfff)
        throw const FormatException('Invalid full Template handle.');
      final attributes = await wire.request(
          3, cipObjectPath(0x6c, handle), cipWords([4, 4, 5, 2, 1]));
      attributes.requireSuccess();
      final data = ByteData.sublistView(attributes.data);
      var at = 2;
      if (data.lengthInBytes < 2 || data.getUint16(0, Endian.little) != 4)
        throw const FormatException('Invalid Template attribute count.');
      final values = <int, int>{};
      for (final attribute in [4, 5, 2, 1]) {
        final width = attribute >= 4 ? 4 : 2;
        if (at + 4 + width > data.lengthInBytes ||
            data.getUint16(at, Endian.little) != attribute ||
            data.getUint16(at + 2, Endian.little) != 0) {
          throw const FormatException('Invalid Template attribute result.');
        }
        values[attribute] = width == 4
            ? data.getUint32(at + 4, Endian.little)
            : data.getUint16(at + 4, Endian.little);
        at += 4 + width;
      }
      if (at != data.lengthInBytes ||
          values[2]! < 1 ||
          values[5]! < 1 ||
          values[5]! > maxBytes)
        throw const FormatException('Invalid Template extent.');
      final documentedBytes = values[4]! * 4 - 23;
      // Echo stores the final names in the complete DINT allocation. Recorded
      // native S0 definitions have their last NUL at documentedBytes itself;
      // requesting only that many bytes truncates it despite service success.
      final bytes = ((documentedBytes + 3) ~/ 4) * 4;
      if (documentedBytes < values[2]! * 8 + 2 ||
          bytes > maxBytes ||
          (definitionBytes += bytes) > maxBytes ||
          (memberCount += values[2]!) > maxLeaves)
        throw const FormatException('Template definition budget exceeded.');
      final buffer = BytesBuilder();
      var offset = 0;
      while (offset < bytes) {
        final body = ByteData(6)
          ..setUint32(0, offset, Endian.little)
          ..setUint16(4, (bytes - offset).clamp(1, 65535), Endian.little);
        final reply = await wire.request(
            0x4c, cipObjectPath(0x6c, handle), body.buffer.asUint8List());
        if (reply.status != 0 && reply.status != 6) reply.requireSuccess();
        if (reply.data.isEmpty || offset + reply.data.length > bytes)
          throw const FormatException(
              'Template fragment made no valid progress.');
        // Definition storage rounds to a DINT; up to three final pad bytes are allowed.
        buffer.add(reply.data);
        offset += reply.data.length;
        if (reply.status == 0) break;
        if (offset >= bytes)
          throw const FormatException(
              'Template fragment status exceeds its allocation.');
      }
      if (offset < documentedBytes)
        throw const FormatException('Incomplete Template definition.');
      final raw = buffer.takeBytes(), fields = ByteData.sublistView(raw);
      var cursor = values[2]! * 8;
      String name(int member) {
        final end = raw.indexOf(0, cursor);
        if (end < 0) {
          final tail = raw
              .skip(raw.length > 64 ? raw.length - 64 : 0)
              .map((b) => b.toRadixString(16).padLeft(2, '0'))
              .join();
          throw FormatException(
              'Unterminated Template 0x${handle.toRadixString(16)} member $member name; '
              'cursor=$cursor bytes=${raw.length} documented=$documentedBytes allocation=$bytes tail=$tail.');
        }
        final result = utf8.decode(Uint8List.sublistView(raw, cursor, end));
        cursor = end + 1;
        return result;
      }

      // The type-name suffix carries vendor scope/access bytes, not UTF-8 text.
      final typeEnd = raw.indexOf(0, cursor),
          separator = raw.indexOf(0x3b, cursor);
      if (typeEnd < 0)
        throw const FormatException('Unterminated Template type name.');
      final typeName = utf8.decode(Uint8List.sublistView(raw, cursor,
          separator >= cursor && separator < typeEnd ? separator : typeEnd));
      cursor = typeEnd + 1;
      final members = <Map<String, Object?>>[];
      for (var i = 0; i < values[2]!; i++) {
        final memberName = name(i + 1),
            code = fields.getUint16(i * 8 + 2, Endian.little);
        members.add(dictMember(
            memberName,
            fields.getUint16(i * 8, Endian.little),
            code,
            fields.getUint32(i * 8 + 4, Endian.little)));
        if (code & 0x8000 != 0 && !templates.containsKey(code & 0xfff))
          queue.add(code & 0xfff);
      }
      templates[handle] =
          CipRawTemplate(handle, typeName, values[5]!, values[1]!, members);
    }
    if (symbols.isEmpty)
      throw const FormatException('Empty controller Symbol namespace.');
    return CipNamespace(Map.unmodifiable(symbols), Map.unmodifiable(templates));
  }

  static Map<String, Object?> dictMember(
          String name, int info, int code, int offset) =>
      {'name': name, 'info': info, 'code': code, 'offset': offset};

  CipTemplateDecoder decoderFor(Iterable<int> roots) {
    final selected = <int, CipTemplate>{};
    void add(int handle, int depth) {
      if (selected.containsKey(handle)) return;
      if (depth > 64 || !templates.containsKey(handle))
        throw const FormatException('Missing/deep Template.');
      final type = templates[handle]!.checked();
      selected[handle] = type;
      for (final member in type.members) {
        if (member.isStructure) add(member.handle, depth + 1);
      }
    }

    for (final handle in roots) add(handle, 0);
    return CipTemplateDecoder(selected.values);
  }

  Future<Uint8List> readStruct(
          CipReadTransport wire, String path, int handle) =>
      readExact(wire, path, templates[handle]!.byteSize,
          structureHandle: templates[handle]!.structureHandle);

  static Future<Uint8List> readExact(
      CipReadTransport wire, String path, int bytes,
      {int? structureHandle, int? atomic, int elementCount = 1}) async {
    if (bytes < 1 ||
        bytes > maxBytes ||
        (structureHandle == null) == (atomic == null) ||
        elementCount < 1 ||
        elementCount > 65535)
      throw const FormatException('Invalid exact-read layout.');
    final symbol = cipSymbolPath(path);
    final buffer = BytesBuilder();
    var offset = 0;
    for (var fragment = 0; fragment < 8192; fragment++) {
      final body = ByteData(6)
        ..setUint16(0, elementCount, Endian.little)
        ..setUint32(2, offset, Endian.little);
      final reply = await wire.request(0x52, symbol, body.buffer.asUint8List());
      if (reply.status != 0 && reply.status != 6) reply.requireSuccess();
      final header = ByteData.sublistView(reply.data);
      final length = structureHandle == null ? 2 : 4;
      if (reply.data.length <= length ||
          header.getUint16(0, Endian.little) != (atomic ?? 0x02a0) ||
          structureHandle != null &&
              header.getUint16(2, Endian.little) != structureHandle) {
        throw const FormatException(
            'Tag read type/structure handle differs from discovery.');
      }
      final payload = Uint8List.sublistView(reply.data, length);
      if (offset + payload.length > bytes)
        throw const FormatException('Tag read exceeds discovered extent.');
      buffer.add(payload);
      offset += payload.length;
      if (reply.status == 0) {
        if (offset != bytes)
          throw const FormatException(
              'Tag read is shorter than discovered extent.');
        return buffer.takeBytes();
      }
      if (offset >= bytes)
        throw const FormatException(
            'Tag fragment status contradicts its extent.');
    }
    throw const FormatException('Tag fragmentation budget exceeded.');
  }

  static Future<int> readDint(CipReadTransport wire, String symbol) async =>
      ByteData.sublistView(await readExact(wire, symbol, 4, atomic: 0xc4))
          .getInt32(0, Endian.little);
}
