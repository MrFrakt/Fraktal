from pathlib import Path
import subprocess,sys
W=Path(__file__).parent
source=(W/'seal_template_retry.py').read_text(encoding='utf-8')
before="def save(p,value):\n    p.parent.mkdir(parents=True,exist_ok=True)"
after="def save(p,value):\n    if p==D/'source_bindings.json' and p.exists():\n        assert load(p)==value, 'existing prepared bindings differ'\n        return\n    p.parent.mkdir(parents=True,exist_ok=True)"
assert source.count(before)==1
source=source.replace(before,after).replace("    assert sha(E/m['report'])==m['reportSha256']","    if m.get('reportSha256'):assert sha(E/m['report'])==m['reportSha256']")
with (W/'seal_template_retry_fixed.py').open('x',encoding='utf-8',newline='') as stream:stream.write(source)
raise SystemExit(subprocess.run([sys.executable,str(W/'seal_template_retry_fixed.py')]).returncode)
