// Fixed read-only native packet probe on the restored baseline, not acceptance.
import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';
import 'package:fraktal_opcua_client/src/cip_transport.dart';

Future<void> main() async {
  final output=File(Platform.environment['FRAKTAL_BATCH_OUTPUT']!);
  if(output.existsSync()) throw StateError('Refusing existing packet probe output.');
  final wire=await CipSocketTransport.connect(host:'127.0.0.1',slot:0,expectSerial:'601FC87B');
  final tags=['FRK_Press_HealthProbe.Samples','FRK_Press_HealthProbe.TaskLastScanUs','FRK_Press_HealthProbe.Samples'];
  final reads=[for(final tag in tags)CipBatchRead(cipSymbolPath(tag),Uint8List.fromList([1,0,0,0,0,0]),6)];
  final clock=Stopwatch()..start(),rows=<Map<String,Object?>>[];
  try {
    for(var index=0;index<20;index++) {
      final before=clock.elapsedMicroseconds;
      final replies=await wire.readBatch(reads);
      final elapsed=clock.elapsedMicroseconds-before;
      final values=[for(final reply in replies)
        ByteData.sublistView(reply.data).getInt32(2,Endian.little)];
      if(replies.any((r)=>r.status!=0)||values.any((v)=>v<0)) throw StateError('Invalid fixed read reply.');
      rows.add({'elapsedUs':elapsed,'values':values,'equalSampleCounter':values.first==values.last});
    }
  } finally {await wire.close();}
  final times=[for(final row in rows)row['elapsedUs'] as int]..sort();
  final result={'passed':true,'readOnly':true,'serial':'601FC87B','packets':20,
    'embeddedReads':60,'tagWrites':0,'rows':rows,
    'requestUs':{'minimum':times.first,'median':(times[9]+times[10])/2,'maximum':times.last},
    'equalSampleCounterPackets':rows.where((r)=>r['equalSampleCounter']==true).length,
    'canonicalCoherenceClaim':false,'desktopAcceptanceClaim':false};
  output.writeAsStringSync(jsonEncode(result));
  print(jsonEncode({...result}..remove('rows')));
}
