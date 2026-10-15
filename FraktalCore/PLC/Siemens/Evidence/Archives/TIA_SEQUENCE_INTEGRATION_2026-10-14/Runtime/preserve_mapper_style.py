from pathlib import Path
import subprocess
ROOT=Path(r'C:\Projects\Fraktal');WORK=Path(__file__).resolve().parent
baseline=ROOT/'FraktalCore/PLC/Siemens/Evidence/Archives/TIA_CONFIG_TRANSACTIONS_2026-10-11/source_snapshot/FraktalCore/HMI/lib/data/opcua_snapshot_mapper.dart'
target=ROOT/'FraktalCore/HMI/lib/data/opcua_snapshot_mapper.dart'
text=baseline.read_text('utf-8-sig')
anchor="import '../localization/reason_catalog.g.dart';"
assert text.count(anchor)==1
text=text.replace(anchor,anchor+"\nimport 'opcua_browse_paths.dart';")
text=text.replace('_buildParentPaths(values.keys)','buildBrowseParentPaths(values.keys)')
text=text.replace('_buildParentPaths):','buildBrowseParentPaths):')
start=text.index('Set<String> _buildParentPaths(');end=text.index('Object? _arrayElement(',start)
text=text[:start]+text[end:]
candidate=WORK/'mapper_style_candidate.dart';candidate.write_text(text,encoding='utf-8',newline='\n')
subprocess.run([r'C:\Users\Siemens\Documents\FlutterSdk\flutter\bin\cache\dart-sdk\bin\dart.exe','format','--language-version=3.0',str(candidate)],check=True,capture_output=True)
if candidate.read_bytes()==target.read_bytes():
    target.write_text(text,encoding='utf-8',newline='\n')
    print('Restored existing style; formatted bytes prove no authored changes lost')
else:
    print('Baseline differs; preserving current source')
