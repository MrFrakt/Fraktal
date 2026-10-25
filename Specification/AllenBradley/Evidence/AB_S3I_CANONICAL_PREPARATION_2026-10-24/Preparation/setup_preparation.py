from pathlib import Path
import hashlib
import shutil

W=Path(__file__).parent
OLD=Path('C:/work/fraktal-ab-s3h-20261024/frame_b7a501a104b448438e1e3566840fa12f')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest().upper()
prepared=W/'prepare';prepared.mkdir(exist_ok=False)
for old,new in (('FramePrepare.csproj','LinePrepare.csproj'),('NuGet.Config','NuGet.Config')):
    shutil.copyfile(OLD/'prepare'/old,prepared/new)
source=(OLD/'prepare/Program.cs').read_text()
for before,after in (
    (str(OLD).replace('\\','/'),str(W).replace('\\','/')),
    ('BF456BCA68745C39D0903D0DE96B9B8AD4EC9DC502E809F38DA82599D2EFB1F2',sha(W/'s3i_bench_02.L5X')),
    ('s3h_frame_candidate_01.L5X','s3i_bench_02.L5X'),('s3h_frame_canonical.ACD','s3i_canonical.ACD'),
    ('frame_prepared_readback.L5X','prepared_readback.L5X'),('frame_canonical.sha256','canonical.sha256'),
    ('observation-frame S3h','Line/shift S3i')):
    assert before in source,before;source=source.replace(before,after)
with (prepared/'Program.cs').open('x',encoding='utf-8',newline='\n') as f:f.write(source)
source=(OLD/'verify_compatibility.py').read_text()
source=source.replace("sha(P/'s3h_frame_candidate_01.L5X')","'BF456BCA68745C39D0903D0DE96B9B8AD4EC9DC502E809F38DA82599D2EFB1F2'")
with (W/'verify_compatibility.py').open('x',encoding='utf-8',newline='\n') as f:f.write(source)
source=(OLD/'audit_access.py').read_text().replace('import fraktal_ab_genealogy_s3h_demo as demo','import fraktal_ab_genealogy_s3i_demo as demo\nimport fraktal_ab_s3i_native_checks as native')
source=source.replace('|set(observation.public_tags(app)))','|set(observation.public_tags(app))|{native.tag(app)})')
# The bench adds only read-only results and two inaccessible save records.
with (W/'audit_access.py').open('x',encoding='utf-8',newline='\n') as f:f.write(source)
print('Offline helper, access audit and prior-image compatibility checks prepared')
