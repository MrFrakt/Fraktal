from pathlib import Path
W=Path(__file__).parent;OLD=Path('C:/work/fraktal-ab-s4b-observer-20261029/offline_01')
raw=(OLD/'qualify_observer_peer_01.py').read_text(encoding='utf-8')
needle="""            completed=subprocess.run(command,cwd=H,stdout=output,stderr=subprocess.STDOUT,timeout=180,**flags)
"""
replacement=needle+"""        with (W/'configuration_peer_01.log').open('x',encoding='utf-8') as output:
            configuration=subprocess.run([str(DART),'--packages='+str(H/'.dart_tool/package_config.json'),
                str(H/'tool/qualify_cip_configuration.dart'),endpoint,str(W/'configuration_peer_01.json.gz')],
                cwd=H,stdout=output,stderr=subprocess.STDOUT,timeout=180,**flags)
"""
assert raw.count(needle)==1;raw=raw.replace(needle,replacement)
needle="report=json.loads(gzip.decompress((W/'observer_01.json.gz').read_bytes()))"
replacement=needle+"""
configuration_report=json.loads(gzip.decompress((W/'configuration_peer_01.json.gz').read_bytes()))
assert configuration.returncode==0 and configuration_report['passed'] and configuration_report['writes']==0
import sys
sys.path.insert(0,str(W))
from configuration_comparison import compare
frozen=R/'Specification/AllenBradley/Evidence/AB_S4B_READER_RUNTIME_2026-10-26/Runtime/idle_equivalence.json.gz'
comparison=compare(configuration_report,json.loads(gzip.decompress(frozen.read_bytes())))
with (W/'configuration_peer_comparison_01.json').open('x') as stream:json.dump(comparison,stream,indent=2)
"""
assert raw.count(needle)==1;raw=raw.replace(needle,replacement)
raw=raw.replace("'test/cip_qualification_test.dart']","'test/cip_qualification_test.dart','tool/qualify_cip_configuration.dart','test/cip_configuration_qualification_test.dart']")
with (W/'qualify_peer_01.py').open('x',encoding='utf-8') as f:f.write(raw)
print('Independent observer/configuration peer qualification with exact 1,100-scalar oracle join')
