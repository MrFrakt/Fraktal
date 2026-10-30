import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';
import 'package:fraktal_opcua_client/src/cip_namespace.dart';
import 'package:fraktal_opcua_client/src/cip_manifest.dart';
import 'package:fraktal_opcua_client/src/cip_publication.dart';
import 'package:fraktal_opcua_client/src/cip_template.dart';
import 'package:fraktal_opcua_client/src/cip_transport.dart';
import 'package:fraktal_opcua_client/src/cip_read_coherence.dart';
import 'file:///C:/Users/SoftIndVM/Fraktal/FraktalCore/HMI/tool/cip_rehearsal_peer.dart';

const capture = 'C:/Users/SoftIndVM/Fraktal/Specification/AllenBradley/Evidence/AB_S4B_READER_RUNTIME_2026-10-26/Runtime/generic_capture.json.gz';
const pin = 'b0ebfbd06853fbaf1262c3b74549f88f99bd9af37e1585844dc5b9a4291afb4a';
Map<String,num> quantiles(Iterable<int> values) {
  final s=values.toList()..sort(); if(s.isEmpty)return {};
  num q(double p) {final n=(s.length-1)*p;return s[n.floor()]+(s[n.ceil()]-s[n.floor()])*(n-n.floor());}
  return {'minimum':s.first,'median':q(.5),'p95':q(.95),'maximum':s.last};
}
Future<void> main() async {
  final raw=jsonDecode(utf8.decode(gzip.decode(File(capture).readAsBytesSync()))) as Map;
  final ns=CipNamespace.fromCapture(raw);
  final pub=CipPublication(ns,CipManifest.fromNormalized(Map<String,Object?>.from(raw['manifest'] as Map)));
  List<CipBatchRead> packet(bool structured,int limit) {
    final result=<CipBatchRead>[];
    for(final f in pub.fields.values) {
      if(f.commandOnly || f.sources.length!=1)continue;
      final s=f.sources.single,m=s.member;
      if(s.chain.any((m)=>m.isArray) || m.isStructure!=structured)continue;
      final size=structured?ns.templates[m.handle]!.byteSize:m.atomic==0xc1?1:CipTemplateDecoder.atomicByteSize(m.atomic);
      if(size>1000)continue;
      final r=CipBatchRead(cipSymbolPath([s.record.source,...s.chain.map((m)=>m.name)].join('.')),
        (ByteData(6)..setUint16(0,1,Endian.little)).buffer.asUint8List(),size+(structured?4:2),
        atomic:structured?null:m.atomic,structureHandle:structured?ns.templates[m.handle]!.structureHandle:null);
      if(cipEncodeReadBatch([...result,r],4000)==null)continue;
      result.add(r); if(result.length==limit)break;
    }
    return result;
  }
  final scalar=packet(false,64), structures=packet(true,7);
  final rows=<Map<String,Object?>>[];
  for(final scale in [0.0,1.0]) {
    final peer=await RehearsalPeer.start(capturePath:capture,expectSha256:pin,seed:7,delayScale:scale);
    final wires=<CipSocketTransport>[];
    try {
      for(var i=0;i<4;i++) {
        wires.add(await CipSocketTransport.connect(host:'127.0.0.1',port:peer.port,expectSerial:'601FC87B'));
      }
      for(final (name,reads) in [('counter',<CipBatchRead>[]),('atomic64',scalar),('structures7',structures)]) {
        final samples=<CipCoherentSample>[],bodyTimes=<int>[];
        final started=Stopwatch()..start();
        await Future.wait(wires.map((w) async {
          final g=CipReadCoherenceGuard(maxAttempts:20);
          for(var i=0;i<20;i++) {
            samples.add(await g.read(binding:CipReadCoherenceBinding(pub.roots.first,peer.counters.single,10000),
              readRevision:(s)=>CipNamespace.readDint(w,s),readGroup:() async {
                final timer=Stopwatch()..start();
                if(reads.isEmpty) {
                  await CipNamespace.readDint(w,peer.counters.single);
                } else {
                  for(final reply in await w.readBatch(reads)) {reply.requireSuccess();}
                }
                bodyTimes.add(timer.elapsedMicroseconds);return Uint8List(0);
              }));
          }
        }));
        rows.add({'scale':scale,'body':name,'reads':reads.length,'wallUs':started.elapsedMicroseconds,
          'samples':samples.length,'good':samples.where((s)=>s.quality==CipSampleQuality.good).length,
          'attempts':quantiles(samples.map((s)=>s.attempts)),'bodyRttUs':quantiles(bodyTimes),
          'acceptedWindowsUs':quantiles(samples.map((s)=>s.acceptedWindowUs).whereType<int>()),
          'failureWindowsUs':quantiles(samples.expand((s)=>s.failures).map((f)=>f['windowUs'] as int)),
          'raw':[for(final s in samples){'quality':s.quality.name,'attempts':s.attempts,'window':s.acceptedWindowUs,'failures':s.failures}]});
      }
    } finally {await Future.wait(wires.map((w)=>w.close()));await peer.close();}
  }
  stdout.writeln(jsonEncode({'kind':'same-process CLI control; not Flutter/native acceptance','controllerChanges':0,'rows':rows}));
}
