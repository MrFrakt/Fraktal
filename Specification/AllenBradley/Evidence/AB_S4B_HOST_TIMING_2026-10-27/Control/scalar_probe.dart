// Diagnostic apparatus only: bounded reads of one public baseline counter.
// No canonical acceptance, source freshness, PLC write or UI success claim.
import 'dart:async';
import 'dart:isolate';
import 'package:fraktal_opcua_client/src/cip_namespace.dart';
import 'package:fraktal_opcua_client/src/cip_read_pool.dart';

Map<String, Object?> summarize(List<int> source) {
  final values=List<int>.of(source)..sort();
  return {'count':values.length,'minimum':values.first,
    'median':values.length.isOdd?values[values.length~/2]:
      (values[values.length~/2-1]+values[values.length~/2])/2,
    'p95':values[(values.length*.95).floor().clamp(0,values.length-1)],
    'maximum':values.last};
}

Future<Map<String,Object?>> measure() async {
  final clock=Stopwatch()..start();
  final pool=await CipReadPool.connect(host:'127.0.0.1',slot:0,expectSerial:'601FC87B');
  final connectedUs=clock.elapsedMicroseconds;
  final times=<int>[],samples=<int>[];
  try {
    // One lease per lane, one outstanding request on that lane's socket.
    await Future.wait(List.generate(4,(_) => pool.withGroup((wire) async {
      for(var index=0;index<40;index++) {
        final before=clock.elapsedMicroseconds;
        final value=await CipNamespace.readDint(wire,'FRK_Press_HealthProbe.Samples');
        times.add(clock.elapsedMicroseconds-before);
        if(value<0) throw StateError('Invalid public sample counter.');
        samples.add(value);
      }
    })));
  } finally {await pool.close();}
  final readAndCloseUs=clock.elapsedMicroseconds-connectedUs;
  final timers=<int>[];
  for(var index=0;index<40;index++) {
    final before=clock.elapsedMicroseconds;
    await Future<void>.delayed(const Duration(milliseconds:1));
    timers.add(clock.elapsedMicroseconds-before);
  }
  return {'readOnly':true,'tag':'FRK_Press_HealthProbe.Samples','serial':'601FC87B',
    'connections':4,'oneOutstandingPerSocket':true,'reads':times.length,
    'connectUs':connectedUs,'readAndCloseUs':readAndCloseUs,
    'requestUs':summarize(times),'oneMsTimerUs':summarize(timers),
    'counterAdvanced':samples.last>samples.first,'elapsedUs':clock.elapsedMicroseconds,
    'plcWrites':0,'canonicalAcceptanceClaim':false,'desktopAcceptanceClaim':false};
}

Future<void> worker(SendPort port) async {
  try {port.send(await measure());}
  on Object catch(error,stack) {port.send({'error':error.toString(),'stack':stack.toString()});}
}

Future<Map<String,Object?>> measureWorker() async {
  final receive=ReceivePort();
  final isolate=await Isolate.spawn(worker,receive.sendPort);
  try {
    final message=Map<String,Object?>.from(await receive.first.timeout(const Duration(seconds:20)) as Map);
    if(message.containsKey('error')) throw StateError(message['error'] as String);
    return message;
  } finally {
    receive.close();
    isolate.kill(priority:Isolate.immediate); // only this diagnostic worker
  }
}
