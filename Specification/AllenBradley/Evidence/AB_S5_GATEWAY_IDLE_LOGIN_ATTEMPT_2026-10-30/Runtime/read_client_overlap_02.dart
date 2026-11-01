import 'dart:async';
import 'dart:convert';
import 'file:///C:/Users/SoftIndVM/Fraktal/FraktalCore/HMI/lib/data/opcua_gateway_client_io.dart';
import 'file:///C:/Users/SoftIndVM/Fraktal/FraktalCore/HMI/tool/qualify_cip_canonical.dart';

Future<void> main() async {
  final clients = <IoGatewayOpcUaClient>[];
  final clock = Stopwatch()..start();
  void record(Map<String, Object?> facts) => print(jsonEncode({
    'elapsedMs':clock.elapsedMilliseconds,'readOnly':true,'controllerWrites':0,...facts}));
  Future<IoGatewayOpcUaClient> connect() async {
    final client=await IoGatewayOpcUaClient.connect(Uri.parse('ws://127.0.0.1:18080/fraktal'));
    clients.add(client);
    final paths=await client.discoverPaths();

    final tiers=qualificationReadTiers(paths,configurationHeartbeat:client.configurationContainersUseHeartbeat);
    await client.setSlowPaths(tiers.slow); await client.setExcludedPaths(tiers.excluded); await client.snapshot();
    return client;
  }
  Future<void> sweep(IoGatewayOpcUaClient client,int id,int seconds) async {
    final until=clock.elapsed+Duration(seconds:seconds);
    while(clock.elapsed<until) {
      final start=clock.elapsedMicroseconds;
      try {
        final doc=await client.snapshot();
        final rpc=(clock.elapsedMicroseconds-start)/1000;
        final processing=(doc['responseProcessingMs'] as num?)?.toDouble()??0;
        record({'event':'snapshot','client':id,'rpcMs':rpc,'sourceAgeMs':doc['sampleAgeMs'],
          'processingMs':processing,'effectiveAgeMs':(doc['sampleAgeMs'] as num)+ (rpc-processing).clamp(0,double.infinity)});
      } on Object catch(error) {record({'event':'error','client':id,'error':'$error'});}
      final remaining=500000-(clock.elapsedMicroseconds-start);
      if(remaining>0)await Future<void>.delayed(Duration(microseconds:remaining));
    }
  }
  try {
    final first=await connect();
    record({'phase':'single'});
    await sweep(first,0,10);
    final second=await connect();
    record({'phase':'dual-with-targeted-access-reads'});
    await Future.wait([
      sweep(first,0,15),sweep(second,1,15),
      () async {
        final until=clock.elapsed+const Duration(seconds:15);
        while(clock.elapsed<until) {
          final start=clock.elapsedMicroseconds;
          try {await first.readValues(['Press/Access/LoginBusy','Press/Access/CurrentLevel',
              'Press/Access/CurrentUser','Press/Access/LoginResultSequence']);
            record({'event':'access-read','rpcMs':(clock.elapsedMicroseconds-start)/1000});
          } on Object catch(error) {record({'event':'access-error','error':'$error'});}
          await Future<void>.delayed(const Duration(milliseconds:50));
        }
      }(),
    ]);
  } finally {for(final client in clients) {await client.close();}}
}
