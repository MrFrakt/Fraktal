"""Prepare guarded session files only. This script has no controller access."""
from pathlib import Path
import hashlib
import json
import shutil

W=Path(__file__).parent
OLD=Path('C:/work/fraktal-ab-s3h-20261024/frame_b7a501a104b448438e1e3566840fa12f')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest().upper()
source=(W/'prepare/Program.cs').read_text();oldsha=sha(W/'s3i_bench_03.L5X');newsha=sha(W/'s3i_bench_05.L5X')
assert source.count(oldsha)==1
with (W/'prepare/Program.cs').open('w',encoding='utf-8',newline='\n') as out:
    out.write(source.replace(oldsha,newsha).replace('s3i_bench_03.L5X','s3i_bench_05.L5X'))

for folder in ('scripts','session'):(W/folder).mkdir(exist_ok=False)
for relative in ('scripts/guard_echo.py','scripts/preflight.py','session/Program.cs','ensure_manual.py','final_checks.py','measure_timing.py'):
    source=(OLD/relative).read_text().replace(str(OLD).replace('\\','/'),str(W).replace('\\','/'))
    if relative=='session/Program.cs':
        source=source.replace('s3h','s3i').replace('s3i_frame_canonical.ACD','s3i_canonical.ACD')
        needle='!approved.GetProperty("ConfigurationVectorsAuthorized").GetBoolean() ||'
        assert source.count(needle)==1
        source=source.replace(needle,needle+'\n        !approved.GetProperty("NativeLineVectorsAuthorized").GetBoolean() ||')
    with (W/relative).open('x',encoding='utf-8',newline='\n') as out:out.write(source)
for old,new in (('FrameSession.csproj','S3iSession.csproj'),('NuGet.Config','NuGet.Config')):
    shutil.copyfile(OLD/'session'/old,W/'session'/new)

# The baseline for stage growth is the accepted S3h frame, not S3g.
baseline=OLD/'capacity_auto_01.json'
shutil.copyfile(baseline,W/'baseline_capacity.json')
with (W/'baseline_reference.json').open('x') as out:
    json.dump(dict(capacitySha256=sha(baseline),evidence='AB_S3H_CANONICAL_OBSERVATION_FRAME_RUNTIME_2026-10-24',
        capacitySource=str(baseline),canonicalSha256='E07C419651A2C6A785D150CAA0BB1894A57CB4453036A0CC2EF2FA8413649745'),out,indent=2)
with (W/'authorization.json').open('x') as out:
    json.dump(dict(CurrentOwnerApproved=False,AccessVectorsAuthorized=False,ConfigurationVectorsAuthorized=False,
        NativeLineVectorsAuthorized=False,Serial='601FC87B',CanonicalSha256=None,
        note='Offline contract approval does not authorize this session; exact image/session approval is pending.'),out,indent=2)
print('Session prepared with all controller authorization flags false')
