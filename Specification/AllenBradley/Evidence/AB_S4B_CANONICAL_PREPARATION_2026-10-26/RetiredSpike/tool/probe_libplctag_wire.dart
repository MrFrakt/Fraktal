// Capture libplctag's exact wire bytes for a member read, to diff against
// the pure-Dart client's request for the same tag. DETAIL (5) makes
// libplctag hex-dump every packet to stderr.
// Usage: dart run tool/probe_libplctag_wire.dart [host] 2> wire.log
//
// ignore_for_file: avoid_print
import 'dart:io';

import '../lib/data/cip/libplctag_bridge.dart';

Future<void> main(List<String> args) async {
  final host = args.isNotEmpty ? args[0] : '127.0.0.1';
  final plc = LibPlctag.open();
  plc.setDebugLevel(5);
  final tag = plc.create('protocol=ab_eip&gateway=$host&path=1,0&plc=lgx'
      '&name=FRK_Press_MfHeader.KeyLength&elem_type=DINT&elem_count=1');
  try {
    plc.read(tag);
    print('KeyLength=${plc.int32(tag, 0)}');
  } finally {
    plc.destroy(tag);
  }
  stdout.flush();
}
