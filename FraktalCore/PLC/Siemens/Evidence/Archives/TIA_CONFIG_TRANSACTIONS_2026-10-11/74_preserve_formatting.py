from pathlib import Path
import subprocess
root=Path('C:/Projects/Fraktal')
for relative,start,end,anchor in [
 ('FraktalCore/HMI/lib/domain/types.dart','  /// Replace a measured value','  /// Presentation only:', '  /// Presentation only:'),
 ('FraktalCore/HMI/lib/data/opcua_snapshot_mapper.dart','        config: [','        nameplate:', '        config: configByModulePath[path] ?? const [],\n'),
 ('FraktalCore/HMI/test/opcua_snapshot_mapper_test.dart',"  test('live config values", "  test('shelf updates", "  test('shelf updates"),
]:
 path=root/relative
 current=path.read_bytes().decode('utf-8').replace('\r\n','\n')
 addition=current[current.index(start):current.index(end,current.index(start))]
 original=subprocess.check_output(['git','show','HEAD:'+relative],cwd=root).decode('utf-8').replace('\r\n','\n')
 assert original.count(anchor)==1
 path.write_bytes(original.replace(anchor,addition + (anchor if relative!='FraktalCore/HMI/lib/data/opcua_snapshot_mapper.dart' else ''),1).encode('utf-8'))
print('Preserved original formatting around the three new HMI changes; authored LF.')