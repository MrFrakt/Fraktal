from pathlib import Path
import os
import subprocess
import sys
import re

W=Path(__file__).parent
suffix=sys.argv[1] if len(sys.argv)>1 else '01'
assert re.fullmatch(r'[0-9]{2}',suffix)
env=dict(os.environ,FLUTTER_ROOT='C:/work/fraktal-toolchains/flutter-3.47.5',
    FRAKTAL_AB_DESKTOP_FIXTURE=str(W.parent/'retry_reader_01'),
    FRAKTAL_AB_DESKTOP_OUTPUT=str(W.parent/('desktop_fixture_'+suffix)))
assert 'FRAKTAL_AB_DESKTOP_LIVE' not in env
raise SystemExit(subprocess.run(['C:/work/fraktal-toolchains/flutter-3.47.5/bin/flutter.bat',
    'test','--no-pub','--concurrency=1','--reporter','expanded',
    str(W/'desktop_readonly_qualification_test.dart')],cwd=W.parent/'hmi_verify_01',env=env).returncode)
