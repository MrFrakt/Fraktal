"""Run the existing eight failure-injected workflow checks against the new session."""
from pathlib import Path
import sys
W = Path(__file__).parent
old = Path('C:/work/fraktal-ab-s4b-20261025/offline_01')
source = (old / 'test_ready_workflow_01.py').read_text(encoding='utf-8')
before = 'W=Path(__file__).parent'
assert source.count(before) == 1
source = source.replace(before, f'W=Path({str(old)!r})')
before = 'replace("SOURCE=W.parent/\'desktop_scan_01\'",f"SOURCE=W.parent/{folder!r}")'
assert source.count(before) == 1
source = source.replace(before, 'replace("SOURCE=W.parent/\'desktop_scan_01\'", "SOURCE=Path(\'C:/work/fraktal-ab-s4b-pool-20261027/session_01\')")')
sys.argv = [sys.argv[0], 'desktop_scan_continue_01']
exec(compile(source, str(old / 'test_ready_workflow_01.py'), 'exec'), globals())
