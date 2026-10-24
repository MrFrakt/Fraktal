"""Prepare an offline S3h helper; no controller authority is transferred."""
from pathlib import Path
import hashlib,json,shutil
P=Path(__file__).parent
PRIOR=Path('C:/work/fraktal-ab-s3g-20261023/prepare_feb76c7a0968442293ee0d20b812eb17')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest().upper()
rows=[]
for label in ('echo','physical'):
    text=(P/f'native_{label}_03.log').read_text()
    result=json.loads(text[text.rindex('\n{')+1:])
    assert result['BuildAccepted'] and result['InputUnchanged'] and result['InputSha256']==sha(P/'s3h_candidate_03.L5X')
    assert json.loads((P/f'{label}_readback_03.log').read_text())['Equivalent']
    rows.append(dict(result,case='canonical',sourceSha256=result['InputSha256']))
with (P/'native_summary_final.json').open('x') as f:json.dump(dict(passed=True,rows=rows),f,indent=2)
(P/'session').mkdir();(P/'scripts').mkdir()
text=(PRIOR/'session/Program.cs').read_text().replace(PRIOR.as_posix(),P.as_posix()).replace('s3g_native_candidate_01.L5X','s3h_candidate_03.L5X').replace('s3g','s3h').replace('S3g','S3h')
text=text.replace('        !approved.GetProperty("NativeMetricsVectorsAuthorized").GetBoolean() ||\n','')
assert 'NativeMetricsVectorsAuthorized' not in text
with (P/'session/Program.cs').open('x') as f:f.write(text)
for old,new in (('S3gSession.csproj','S3hSession.csproj'),('NuGet.Config','NuGet.Config')):
    shutil.copyfile(PRIOR/'session'/old,P/'session'/new)
for name in ('guard_echo.py','preflight.py'):
    with (P/'scripts'/name).open('x') as f:f.write((PRIOR/'scripts'/name).read_text().replace(PRIOR.as_posix(),P.as_posix()))
for name in ('ensure_manual.py','final_checks.py','measure_timing.py','audit_baseline_access.py'):
    with (P/name).open('x') as f:f.write((PRIOR/name).read_text().replace(PRIOR.as_posix(),P.as_posix()))
shutil.copyfile(PRIOR/'capacity_review.json',P/'baseline_capacity.json')
with (P/'baseline_reference.json').open('x') as f:json.dump(dict(source=(PRIOR/'capacity_review.json').as_posix(),capacitySha256=sha(P/'baseline_capacity.json')),f,indent=2)
print(json.dumps(dict(passed=True,controllerChangesAuthorized=False,sourceSha256=sha(P/'s3h_candidate_03.L5X'))))
