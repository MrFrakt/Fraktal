"""Prepare the one-shot S3g helper offline; no historical authority transfers."""
from pathlib import Path
import hashlib,json,shutil
P=Path(__file__).parent
E=Path('C:/work/fraktal-ab-s3f-20261022/prepare_3816927132f14d4998876bc62e22f342')
R=Path('C:/work/fraktal-ab-s3f-revision-20261023/prepare_c66f76a368304f6981b436dbf651e009')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest().upper()
rows=[]
for label in ('echo','physical'):
    text=(P/f'bench_native_{label}_01.log').read_text()
    result=json.loads(text[text.rindex('\n{')+1:])
    assert result['BuildAccepted'] and result['InputUnchanged'] and result['InputSha256']==sha(P/'s3g_native_candidate_01.L5X')
    assert json.loads((P/f'bench_{label}_readback_01.log').read_text())['Equivalent']
    rows.append(dict(result,case='canonical',sourceSha256=result['InputSha256']))
with (P/'native_summary_final.json').open('x') as f:json.dump(dict(passed=True,rows=rows),f,indent=2)
(P/'session').mkdir();(P/'scripts').mkdir()
text=(E/'session/Program.cs').read_text().replace(E.as_posix(),P.as_posix()).replace('genealogy_s3f_05.L5X','s3g_native_candidate_01.L5X').replace('s3f','s3g').replace('S3f','S3g')
anchor='!approved.GetProperty("ConfigurationVectorsAuthorized").GetBoolean() ||'
assert text.count(anchor)==1
text=text.replace(anchor,anchor+'\n        !approved.GetProperty("NativeMetricsVectorsAuthorized").GetBoolean() ||')
with (P/'session/Program.cs').open('x') as f:f.write(text)
for old,new in (('S3fSession.csproj','S3gSession.csproj'),('NuGet.Config','NuGet.Config')):
    shutil.copyfile(E/'session'/old,P/'session'/new)
for name in ('guard_echo.py','preflight.py'):
    with (P/'scripts'/name).open('x') as f:f.write((E/'scripts'/name).read_text().replace(E.as_posix(),P.as_posix()))
for name in ('ensure_manual.py','final_checks.py','measure_timing.py','audit_baseline_access.py'):
    with (P/name).open('x') as f:f.write((R/name).read_text().replace(R.as_posix(),P.as_posix()))
shutil.copyfile(R/'capacity_review.json',P/'baseline_capacity.json')
with (P/'baseline_reference.json').open('x') as f:json.dump(dict(source=(R/'capacity_review.json').as_posix(),capacitySha256=sha(P/'baseline_capacity.json')),f,indent=2)
print(json.dumps(dict(passed=True,controllerChangesAuthorized=False,sourceSha256=sha(P/'s3g_native_candidate_01.L5X'))))
