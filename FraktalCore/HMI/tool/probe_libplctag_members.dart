// Compare: libplctag (proven on this Echo) reading dotted member tags whose
// values are known — the pure-Dart client returns an identical 4-byte body
// for every member, so something about its member request is wrong.
// Usage: dart run tool/probe_libplctag_members.dart [host]
//
// ignore_for_file: avoid_print
import 'dart:io';
import 'dart:typed_data';

import '../lib/data/cip/libplctag_bridge.dart';

Future<void> main(List<String> args) async {
  final host = args.isNotEmpty ? args[0] : '127.0.0.1';
  final plc = LibPlctag.open();
  const tags = [
    'FRK_Press_MfHeader.KeyLength', // DINT, known 56
    'FRK_Press_Unit.Mode', // DINT, 0..4
    'FRK_Press_HmiResponse', // 3-DINT struct
  ];
  for (final tag in tags) {
    final attrib = 'protocol=ab_eip&gateway=$host&path=1,0&plc=lgx'
        '&name=$tag&elem_type=DINT&elem_count=1';
    final handle = plc.create(attrib);
    try {
      plc.read(handle);
      final size = plc.size(handle);
      final raw = plc.rawBytes(handle);
      print('$tag size=$size: '
          '${raw.take(24).map((b) => b.toRadixString(16).padLeft(2, '0')).join(' ')}'
          '${size >= 4 ? '  int32@0=${plc.int32(handle, 0)}' : ''}');
    } on Object catch (error) {
      print('$tag FAILED: $error');
    } finally {
      plc.destroy(handle);
    }
  }

  // Diagnostic 637 is a NumericKey, not a row index: read the whole pool and
  // print the row(s) whose NumericKey matches (plus the neighbours).
  final pool = plc.create('protocol=ab_eip&gateway=$host&path=1,0&plc=lgx'
      '&name=FRK_Press_MfLocalization&elem_count=688');
  try {
    plc.read(pool, timeoutMs: 15000);
    final raw = plc.rawBytes(pool);
    print('Localization pool: ${raw.length} B (want ${688 * 64})');
    const width = 64;
    final data = ByteData.sublistView(raw);
    for (var row = 0; row < 688 && (row + 1) * width <= raw.length; row++) {
      final numeric = data.getInt32(row * width, Endian.little);
      if (numeric >= 645 && numeric <= 660 || numeric == 637) {
        final len =
            data.getInt32(row * width + 4, Endian.little).clamp(0, 56).toInt();
        final text = String.fromCharCodes(
            raw.sublist(row * width + 8, row * width + 8 + len));
        print('  row[$row] NumericKey=$numeric text="$text"');
      }
    }
  } on Object catch (error) {
    print('Localization pool FAILED: $error');
  } finally {
    plc.destroy(pool);
  }
  // Last committed request, for the record (write-only members refuse reads).
  final seq = plc.create('protocol=ab_eip&gateway=$host&path=1,0&plc=lgx'
      '&name=FRK_Press_HmiRequest.Sequence&elem_type=DINT&elem_count=1');
  try {
    plc.read(seq);
    print('HmiRequest.Sequence=${plc.int32(seq, 0)}');
  } on Object catch (error) {
    print('HmiRequest.Sequence FAILED: $error');
  } finally {
    plc.destroy(seq);
  }
  stdout.flush();
}
