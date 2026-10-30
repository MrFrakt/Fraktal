import 'dart:convert';
import 'dart:io';
import 'package:fraktal_opcua_client/src/cip_namespace.dart';
import 'package:fraktal_opcua_client/src/cip_transport.dart';
import 'file:///C:/Users/SoftIndVM/Fraktal/FraktalCore/HMI/tool/cip_rehearsal_peer.dart';

Map<String,num> quantiles(Iterable<int> values) {
  final s=values.toList()..sort();
  num q(double p) {final n=(s.length-1)*p;return s[n.floor()]+(s[n.ceil()]-s[n.floor()])*(n-n.floor());}
  return {'minimum':s.first,'median':q(.5),'p95':q(.95),'maximum':s.last};
}
Future<void> main() async {
  final rows=<Map<String,Object?>>[];
  for(final scale in [0.0,1.0]) {
    final peer=await RehearsalPeer.start(
      capturePath:'C:/Users/SoftIndVM/Fraktal/Specification/AllenBradley/Evidence/AB_S4B_READER_RUNTIME_2026-10-26/Runtime/generic_capture.json.gz',
      expectSha256:'b0ebfbd06853fbaf1262c3b74549f88f99bd9af37e1585844dc5b9a4291afb4a',
      seed:7,delayScale:scale);
    final wires=<CipSocketTransport>[];
    try {
      for(var i=0;i<4;i++) {
        wires.add(await CipSocketTransport.connect(host:'127.0.0.1',port:peer.port,slot:0,expectSerial:'601FC87B'));
      }
      final before=peer.delayTimingsUs.length, rtt=<int>[];
      await Future.wait(wires.map((wire) async {
        for(var i=0;i<40;i++) {
          final timer=Stopwatch()..start();
          await CipNamespace.readDint(wire,peer.counters.single);
          rtt.add(timer.elapsedMicroseconds);
        }
      }));
      final delays=peer.delayTimingsUs.skip(before).toList();
      rows.add({'scale':scale,'requests':rtt.length,'connections':4,'outstandingPerSocket':1,
        'roundTripUs':quantiles(rtt),'requestedDelayUs':quantiles(delays.map((d)=>d[0])),
        'realizedDelayUs':quantiles(delays.map((d)=>d[1])),
        'overshootUs':quantiles(delays.map((d)=>d[1]-d[0])),
        'rawRoundTripsUs':rtt,'rawRequestedRealizedUs':delays});
    } finally {
      await Future.wait(wires.map((w)=>w.close()));
      await peer.close();
    }
  }
  final result={'kind':'Dart CLI calibration; no Flutter UI/no native acceptance',
    'controllerChanges':0,'rows':rows};
  stdout.writeln(jsonEncode(result));
}
