import 'dart:convert';
import 'file:///C:/Users/SoftIndVM/Fraktal/FraktalCore/HMI/test/cip_publication_test.dart' as golden;
void main() {
  final p=golden.publication(golden.fixtures().last['capture'] as Map);
  for(final f in p.fields.values.where((f)=>f.annotation['countPath']!=null)) {
    print(jsonEncode({'path':f.path,'count':f.annotation['countPath'],'command':f.commandOnly}));
  }
}
