import 'dart:convert';
import 'dart:io';
import 'package:fraktal_opcua_client/src/cip_manifest.dart';
import 'package:fraktal_opcua_client/src/cip_namespace.dart';
import 'package:fraktal_opcua_client/src/cip_publication.dart';
import 'file:///C:/Users/SoftIndVM/Fraktal/FraktalCore/HMI/lib/data/opcua_field_tier.dart';
void main() {
  final file=File('C:/Users/SoftIndVM/Fraktal/Specification/AllenBradley/Evidence/AB_S4B_READER_RUNTIME_2026-10-26/Runtime/generic_capture.json.gz');
  final cap=jsonDecode(utf8.decode(gzip.decode(file.readAsBytesSync()))) as Map;
  final pub=CipPublication(CipNamespace.fromCapture(cap),CipManifest.fromNormalized(Map<String,Object?>.from(cap['manifest'] as Map)));
  final rows=<String,List<String>>{};
  for(final path in pub.discoverPaths()) {
    if(OpcUaFieldTier.isRequestPayload(path) ||
        OpcUaFieldTier.isManifestServed(path,hydratedPaths:const {}) ||
        OpcUaFieldTier.classify(path)!=FieldTier.config ||
        !OpcUaFieldTier.isManifestServed(path))continue;
    final container=path.split('/').map((p)=>p.split('[').first)
      .firstWhere(OpcUaFieldTier.manifestContainers.contains);
    rows.putIfAbsent(container,()=>[]).add(path);
  }
  final result={'kind':'proposed configuration-container heartbeat scope before exact manifest replacements',
    'implemented':false,'candidatePaths':rows.values.fold<int>(0,(a,b)=>a+b.length),'byContainer':rows,
    'oldTier':'fast until exact replacement','proposedTier':'slow; 5000ms period /7500ms Good /15000ms expiry',
    'statusAndCapabilitiesStayFast':true,'requiresOwnerContractDecision':true};
  stdout.writeln(jsonEncode(result));
}
