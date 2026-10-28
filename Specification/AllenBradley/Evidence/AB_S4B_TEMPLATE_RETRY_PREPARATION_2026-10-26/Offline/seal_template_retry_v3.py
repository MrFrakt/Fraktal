from pathlib import Path
import subprocess,sys
W=Path(__file__).parent
source=(W/'seal_template_retry_fixed.py').read_text(encoding='utf-8')
source=source.replace("==m['reportSha256']","==m['reportSha256'].lower()")
source=source.replace("==row['sha256'] and","==row['sha256'].lower() and")
source=source.replace("==row['expandedSha256']","==row['expandedSha256'].lower()")
with (W/'seal_template_retry_final.py').open('x',encoding='utf-8',newline='') as stream:stream.write(source)
raise SystemExit(subprocess.run([sys.executable,str(W/'seal_template_retry_final.py')]).returncode)
