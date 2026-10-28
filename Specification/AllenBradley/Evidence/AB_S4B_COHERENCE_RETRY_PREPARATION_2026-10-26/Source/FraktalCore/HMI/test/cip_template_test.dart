import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:fraktal_opcua_client/src/cip_template.dart';

Uint8List hex(String text) => Uint8List.fromList([
      for (var index = 0; index < text.length; index += 2)
        int.parse(text.substring(index, index + 2), radix: 16)
    ]);

Object? normalized(Object? value) => switch (value) {
      BigInt n => n.toString(),
      Map m => {for (final e in m.entries) e.key: normalized(e.value)},
      List l => l.map(normalized).toList(),
      _ => value,
    };

void main() {
  test('native genealogy and press records match independent Python goldens',
      () {
    final document = jsonDecode(utf8.decode(gzip.decode(
        File('test/fixtures/cip_template_goldens.json.gz')
            .readAsBytesSync()))) as Map;
    expect(document['schema'], 'fraktal.cip.template-goldens.v1');
    for (final vector in document['vectors'] as List) {
      final decoder = CipTemplateDecoder.fromCapture(
          List<Object?>.from(vector['templates'] as List));
      for (final record in vector['records'] as List) {
        expect(
            normalized(decoder.decode(record['handle'], hex(record['rawHex']))),
            record['expected'],
            reason: '${vector['name']}: ${record['tag']}');
      }
    }
  });

  test('structure stride uses attribute 5 and full 12-bit handles', () {
    final decoder = CipTemplateDecoder([
      CipTemplate(1, 'Parent', 20, [CipTemplateMember('Rows', 2, 0xa1c4, 0)]),
      CipTemplate(0x1c4, 'Child', 8, [CipTemplateMember('Value', 0, 0xc4, 0)]),
    ]);
    final raw = ByteData(20)
      ..setInt32(0, 11, Endian.little)
      ..setInt32(8, 22, Endian.little)
      ..setInt32(16, 999, Endian.little);
    expect(decoder.decode(1, raw.buffer.asUint8List()), {
      'Rows': [
        {'Value': 11},
        {'Value': 22}
      ]
    });
  });

  test('BOOL members and arrays use native packed bits', () {
    final decoder = CipTemplateDecoder([
      CipTemplate(1, 'Flags', 12, [
        CipTemplateMember('LastBit', 31, 0xc1, 0),
        CipTemplateMember('Flags', 35, 0x20c1, 4),
      ])
    ]);
    final raw = ByteData(12)
      ..setUint32(0, 0x80000000, Endian.little)
      ..setUint32(4, 0x80000001, Endian.little)
      ..setUint32(8, 5, Endian.little);
    expect(decoder.decode(1, raw.buffer.asUint8List()), {
      'LastBit': true,
      'Flags': [
        for (var index = 0; index < 35; index++) {0, 31, 32, 34}.contains(index)
      ]
    });
  });

  test('64-bit integers and LDT preserve every bit', () {
    final decoder = CipTemplateDecoder([
      CipTemplate(1, 'Wide', 24, [
        CipTemplateMember('Minimum', 0, 0xc5, 0),
        CipTemplateMember('Maximum', 0, 0xc9, 8),
        CipTemplateMember('Stamp', 0, 0xcc, 16),
      ])
    ]);
    expect(
        normalized(decoder.decode(
            1, hex('0000000000000080ffffffffffffffff0100000000000000'))),
        {
          'Minimum': '-9223372036854775808',
          'Maximum': '18446744073709551615',
          'Stamp': '1'
        });
  });

  test('StringFamily validates byte-counted UTF-8 LEN', () {
    final decoder = CipTemplateDecoder([
      CipTemplate(1, 'Text', 12, [
        CipTemplateMember('LEN', 0, 0xc4, 0),
        CipTemplateMember('DATA', 8, 0x20c2, 4),
      ])
    ]);
    expect(decoder.decode(1, hex('02000000c3a9000000000000')), 'é');
    for (final raw in [
      '090000000000000000000000',
      '01000000c300000000000000',
      'ffffffff0000000000000000'
    ]) {
      expect(() => decoder.decode(1, hex(raw)), throwsFormatException);
    }
  });

  test('malformed, cyclic and unsupported layouts fail closed', () {
    expect(
        () => CipTemplateDecoder([
              CipTemplate(
                  1, 'Cycle', 4, [CipTemplateMember('Self', 0, 0x8001, 0)])
            ]),
        throwsFormatException);
    expect(
        () => CipTemplateDecoder([
              CipTemplate(
                  1, 'Missing', 4, [CipTemplateMember('Child', 0, 0x8002, 0)])
            ]),
        throwsFormatException);
    expect(
        () => CipTemplateMember('Rows', 1, 0x40c4, 0), throwsFormatException);
    for (final member in [
      CipTemplateMember('Value', 0, 0xc4, 3),
      CipTemplateMember('Unknown', 0, 0xab, 0)
    ]) {
      final decoder = CipTemplateDecoder([
        CipTemplate(1, 'Broken', 4, [member])
      ]);
      expect(() => decoder.decode(1, Uint8List(4)), throwsFormatException);
      expect(() => decoder.decode(1, Uint8List(3)), throwsFormatException);
    }
  });

  test('NaN and Infinity cannot become Good numeric values', () {
    final decoder = CipTemplateDecoder([
      CipTemplate(1, 'Number', 8, [CipTemplateMember('Value', 0, 0xcb, 0)])
    ]);
    for (final value in [
      double.nan,
      double.infinity,
      double.negativeInfinity
    ]) {
      final raw = ByteData(8)..setFloat64(0, value, Endian.little);
      expect(() => decoder.decode(1, raw.buffer.asUint8List()),
          throwsFormatException);
    }
  });

  test('small aliased layouts cannot expand beyond the decoded-value budget',
      () {
    final decoder = CipTemplateDecoder([
      CipTemplate(
          1, 'Many', 65535 * 4, [CipTemplateMember('Rows', 65535, 0xa002, 0)]),
      CipTemplate(2, 'Aliases', 4, [
        for (var index = 0; index < 1000; index++)
          CipTemplateMember('Flag$index', 0, 0xc1, 0)
      ])
    ]);
    expect(
        () => decoder.decode(1, Uint8List(65535 * 4)), throwsFormatException);
  });
}
