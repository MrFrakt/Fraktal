from pathlib import Path
import os
import re
import subprocess
import sys

W=Path(__file__).parent
suffix=sys.argv[1]
assert re.fullmatch(r'[0-9]{2}',suffix)
env=dict(os.environ,FLUTTER_ROOT='C:/work/fraktal-toolchains/flutter-3.47.5',
    FRAKTAL_AB_DESKTOP_FIXTURE='C:/work/fraktal-ab-s4b-20261025/desktop_scan_continue_01',
    FRAKTAL_AB_DESKTOP_EXPECTED_INVENTORY='C:/work/fraktal-ab-s4b-20261025/desktop_fixture_06/result.json',
    FRAKTAL_AB_DESKTOP_OUTPUT=str(W.parent/('desktop_diagnostic_fixture_'+suffix)))
assert 'FRAKTAL_AB_DESKTOP_LIVE' not in env
if '--force-startup-failure' in sys.argv[2:]:env['FRAKTAL_AB_DESKTOP_FORCE_STARTUP_FAILURE_FIXTURE']='1'
if '--force-stale' in sys.argv[2:]:env['FRAKTAL_AB_DESKTOP_FORCE_STALE_FIXTURE']='1'
result=subprocess.run(['C:/work/fraktal-toolchains/flutter-3.47.5/bin/flutter.bat','test','--no-pub',
    '--concurrency=1','--reporter','expanded',str(W/'desktop_diagnostic_qualification_test.dart')],
    cwd='C:/work/fraktal-ab-s4b-20261025/hmi_verify_01',env=env)
raise SystemExit(result.returncode)
