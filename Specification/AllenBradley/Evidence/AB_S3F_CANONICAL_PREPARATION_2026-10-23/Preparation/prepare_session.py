"""Offline helper construction, with controller authorization deliberately absent."""
import hashlib,json,shutil
from pathlib import Path
W=Path(__file__).parent
E=Path('C:/work/fraktal-ab-s3e-20261022/prepare_768bb43d842d4b008ab1dfb322741aea')
assert not (W/'session').exists()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest().upper()
rows=[]
for target in ('echo','physical'):
    text=(W/f'native_{target}_05.log').read_text()
    row=json.loads(text[text.rindex('\n{')+1:])
    assert row['BuildAccepted'] and row['InputUnchanged'] and row['InputSha256']==sha(W/'genealogy_s3f_05.L5X')
    assert json.loads((W/f'{target}_readback_06.log').read_text())['Equivalent']
    assert json.loads((W/f'{target}_audit_01.log').read_text())['Clean']
    rows.append(dict(row,case='canonical',sourceSha256=row['InputSha256']))
with (W/'native_summary_final.json').open('x') as f:json.dump(dict(passed=True,rows=rows),f,indent=2)
(W/'session').mkdir();(W/'scripts').mkdir()
source=(E/'session/Program.cs').read_text().replace(E.as_posix(),W.as_posix()).replace('S3e','S3f').replace('s3e','s3f').replace('genealogy_s3f_01.L5X','genealogy_s3f_05.L5X')
anchor='!approved.GetProperty("AccessVectorsAuthorized").GetBoolean() ||'
assert source.count(anchor)==1
source=source.replace(anchor,anchor+'\n        !approved.GetProperty("ConfigurationVectorsAuthorized").GetBoolean() ||')
with (W/'session/Program.cs').open('x') as f:f.write(source)
for old,new in [('S3eSession.csproj','S3fSession.csproj'),('NuGet.Config','NuGet.Config')]:shutil.copyfile(E/'session'/old,W/'session'/new)
for name in ('guard_echo.py','preflight.py'):
    text=(E/'scripts'/name).read_text().replace(E.as_posix(),W.as_posix())
    with (W/'scripts'/name).open('x') as f:f.write(text)
for name in ('ensure_manual.py','final_checks.py','measure_timing.py'):
    text=(E/name).read_text().replace(E.as_posix(),W.as_posix()).replace('S3e','S3f').replace('s3e','s3f')
    with (W/name).open('x') as f:f.write(text)
shutil.copyfile(E/'capacity_review.json',W/'baseline_capacity.json')
with (W/'baseline_reference.json').open('x') as f:json.dump(dict(source=(E/'capacity_review.json').as_posix(),capacitySha256=sha(W/'baseline_capacity.json'),sourceAcdSha256='95E85B507387A548553688C1B5CCF52D7D99B35751C68F1B02DE92AC2A1B240B'),f,indent=2)
print(json.dumps(dict(passed=True,sourceSha256=sha(W/'genealogy_s3f_05.L5X'),controllerChangesAuthorized=False)))
