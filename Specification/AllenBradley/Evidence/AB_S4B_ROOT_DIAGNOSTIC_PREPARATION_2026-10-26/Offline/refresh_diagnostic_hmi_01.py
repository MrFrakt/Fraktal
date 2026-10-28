from pathlib import Path
import hashlib
import json
import shutil
import subprocess

R = Path('C:/Users/SoftIndVM/Fraktal')
H = R / 'FraktalCore/HMI'
W = Path(__file__).parent
OUT = W.parent / 'hmi_verify_01'
previous = json.loads((W / 'isolated_hmi_sources_02.json').read_bytes())
changed = [row['source'] for row in previous['files']
           if hashlib.sha256(Path(row['source']).read_bytes()).hexdigest() != row['sha256']]
assert changed == [(H / 'tool/qualify_cip_canonical.dart').as_posix()], changed
names = set()
for arguments in (['git', 'ls-files', '-z', '--', 'FraktalCore/HMI'],
                  ['git', 'ls-files', '--others', '--exclude-standard', '-z', '--', 'FraktalCore/HMI']):
    names.update(n for n in subprocess.check_output(arguments, cwd=R).decode().split('\0') if n)
rows = []
for name in sorted(names):
    source = R / name
    if not source.is_file():
        continue
    relative = source.relative_to(H)
    assert not any(part in ('build', '.dart_tool', '.git') for part in relative.parts)
    target = OUT / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)
    assert target.read_bytes() == source.read_bytes()
    rows.append(dict(source=source.as_posix(), copy=target.as_posix(),
        sha256=hashlib.sha256(source.read_bytes()).hexdigest(), bytes=source.stat().st_size))
with (W / 'isolated_hmi_sources_03.json').open('x', encoding='utf-8') as stream:
    json.dump(dict(passed=True, files=rows, productionSourcesUnchanged=True,
                   changes=changed, added='test/cip_qualification_test.dart'), stream, indent=2)
print(json.dumps(dict(passed=True, files=len(rows), productionSourcesUnchanged=True)))
