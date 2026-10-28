// Does a libplctag connected write of the commit word fire the mailbox ack?
// Writes Sequence=6 (ack currently 4), then reads back Sequence + HmiResponse.
// Usage: dart run tool/probe_libplctag_write.dart [host]
//
// ignore_for_file: avoid_print
import 'dart:io';

import '../lib/data/cip/libplctag_bridge.dart';

int read(LibPlctag plc, String tag, String type) {
  final h = plc.create('protocol=ab_eip&gateway=127.0.0.1&path=1,0&plc=lgx'
      '&name=$tag&elem_type=$type&elem_count=1');
  try {
    plc.read(h);
    return plc.int32(h, 0);
  } finally {
    plc.destroy(h);
  }
}

Future<void> main(List<String> args) async {
  final host = args.isNotEmpty ? args[0] : '127.0.0.1';
  final plc = LibPlctag.open();
  plc.setDebugLevel(5);
  print('Sequence before: ${read(plc, 'FRK_Press_HmiRequest.Sequence', 'DINT')}');
  print('Ack before: ${read(plc, 'FRK_Press_HmiResponse', 'DINT')}');

  final h = plc.create('protocol=ab_eip&gateway=$host&path=1,0&plc=lgx'
      '&name=FRK_Press_HmiRequest.Sequence&elem_type=DINT&elem_count=1');
  try {
    plc.setInt32(h, 0, 6);
    plc.write(h);
    print('write completed');
  } finally {
    plc.destroy(h);
  }
  await Future.delayed(const Duration(milliseconds: 800));
  print('Sequence after: ${read(plc, 'FRK_Press_HmiRequest.Sequence', 'DINT')}');
  print('Ack after: ${read(plc, 'FRK_Press_HmiResponse', 'DINT')}');
  stdout.flush();
}
