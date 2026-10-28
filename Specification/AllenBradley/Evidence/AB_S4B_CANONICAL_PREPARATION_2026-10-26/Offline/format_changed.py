from pathlib import Path
import subprocess
R=Path('C:/Users/SoftIndVM/Fraktal')
paths=subprocess.check_output(['git','diff','--name-only','--diff-filter=ACM','--','FraktalCore/HMI'],cwd=R,text=True).splitlines()
paths=[p for p in paths if p.endswith('.dart') and p!='FraktalCore/HMI/lib/ui/facet_cards.dart']
raise SystemExit(subprocess.run(['C:/work/fraktal-toolchains/flutter-3.47.5/bin/cache/dart-sdk/bin/dart.exe','format',*paths],cwd=R).returncode)
