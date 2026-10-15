import hashlib, json, os, shutil, sys
from pathlib import Path

work = Path(__file__).resolve().parent
repo = Path('C:/Projects/Fraktal')
plc = repo/'FraktalCore/PLC/Siemens'
archive = plc/'Evidence/Archives/TIA_SEQUENCE_RECOVERY_2026-10-15'
assert not archive.exists()
checks = {}
for name in ('recovery01', 'profile02_regression', 'diagnostic_regression', 'view02_regression', 'restore_regression'):
    rows = [json.loads(line) for line in (work/'runtime09'/(name+'.jsonl')).read_text('ascii').splitlines()]
    last = rows[-1]
    assert last['event'] == 'summary' and last['complete'] and last['passed'] == last['checks'], name
    assert all(row['passed'] for row in rows if row['event'] == 'check'), name
    checks[name] = last['checks']
assert sum(checks.values()) == 415, checks
assert json.loads((work/'runtime09/normalized.json').read_bytes())['complete']
assert all(row['exit_code'] == 0 for row in json.loads((work/'gates_verified.json').read_bytes()).values())
assert json.loads((work/'publish_credentials.json').read_bytes())['complete']

# The local knowledge database backup contains unrelated engineering knowledge;
# its integrity/index report is sufficient for this publication's scope.
shutil.copytree(work, archive/'Runs', ignore=shutil.ignore_patterns('kb_before.sqlite', '__pycache__'))
snapshot = archive/'SourceSnapshot'
shutil.copytree(plc, snapshot/'FraktalCore/PLC/Siemens',
                ignore=shutil.ignore_patterns('Evidence', 'bin', 'obj', '__pycache__', '.vs'))
for relative in ('AGENTS.md', '.gitattributes', '.gitignore', 'analysis_options.yaml', '.vscode/settings.json',
    'Specification/Fraktal_Core_Part_I.md', 'Specification/Fraktal_TIA_Part_IV.md',
    'Specification/HMI_CONTRACT.md', 'Specification/OPCUA_TRANSPORT.md', 'Specification/README.md',
    'FraktalCore/PLC/TwinCAT/IMPLEMENTATION_NOTES.md', 'tools/check_consistency.py', 'tools/test_check_consistency.py'):
    target = snapshot/relative; target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(repo/relative, target)
shutil.copytree(repo/'Specification/Siemens', snapshot/'Specification/Siemens')
# Freeze every Core contract dependency used by the generated frame.
metadata = json.loads((work/'runtime09/frames/manifest.json').read_bytes())
for relative, expected in metadata['core_inputs'].items():
    source = repo/relative
    assert hashlib.sha256(source.read_bytes()).hexdigest() == expected, relative
    target = snapshot/relative
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
kb = Path('C:/Projects/SiemensAgent/siemens-kb/tia-automation')
shutil.copytree(kb, snapshot/'Knowledge/tia-automation', ignore=shutil.ignore_patterns('*.db', '*.sqlite'))
files = sorted(path for path in archive.rglob('*') if path.is_file())
patterns = [os.environ[name].encode('utf-8') for name in
            ('FRAKTAL_TIA_ADMIN_PIN', 'FRAKTAL_TIA_OPERATOR_PIN', 'FRAKTAL_TIA_WEB_PASSWORD')]
lines, total = [], 0
for path in files:
    raw = path.read_bytes()
    assert not any(pattern in raw for pattern in patterns), 'Plaintext credential in archive '+str(path.relative_to(archive))
    total += len(raw)
    lines.append(hashlib.sha256(raw).hexdigest()+'  '+path.relative_to(repo).as_posix())
manifest = archive/'SHA256SUMS'
manifest.write_bytes(('\n'.join(lines)+'\n').encode('ascii'))
for line in lines:
    expected, relative = line.split('  ', 1)
    assert hashlib.sha256((repo/relative).read_bytes()).hexdigest() == expected, relative
result = {'archive': str(archive), 'files': len(files), 'bytes': total,
          'manifest_sha256': hashlib.sha256(manifest.read_bytes()).hexdigest(),
          'checks': checks, 'verified': True}
with Path(sys.argv[1]).open('x', encoding='ascii') as stream:
    json.dump(result, stream, indent=2); stream.write('\n')
print(json.dumps(result))
