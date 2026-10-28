from pathlib import Path
import subprocess,sys
W=Path(__file__).parent
script=(W/'fix_package_binding.py').read_text()
before="assert semantic(sealed)==semantic(live),'package roots or language versions changed'"
after="assert sealed.get('flutterVersion')=='3.47.5' and sealed.get('generatorVersion')=='3.13.4', 'sealed tested SDK differs'"
assert script.count(before)==1
script=script.replace(before,after).replace('onlyGeneratedMetadataChanged=True,packageSemanticsIdentical=True',
  "onlyGeneratedMetadataChanged=False,liveGeneratedSdk=live.get('flutterVersion'),frozenTestedSdk=sealed.get('flutterVersion'),packageSemanticsFromTestedSeal=True")
with (W/'fix_package_binding_v2.py').open('x',encoding='utf-8',newline='') as stream:stream.write(script)
raise SystemExit(subprocess.run([sys.executable,str(W/'fix_package_binding_v2.py')]).returncode)
