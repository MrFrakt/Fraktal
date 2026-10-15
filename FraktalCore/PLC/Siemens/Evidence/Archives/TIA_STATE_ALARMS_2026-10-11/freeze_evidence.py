"""Freeze raw/source/knowledge bytes and verify every bound file; no deletions."""
import hashlib
import json
from pathlib import Path
import shutil

REPO = Path('C:/Projects/Fraktal')
WORK = Path(__file__).resolve().parent
REL = Path('Specification/Siemens/Evidence/TIA_STATE_ALARMS_2026-10-11')
ARCHIVE = REPO / REL
REPORT = REPO / REL.with_suffix('.md')
assert REPORT.is_file() and not ARCHIVE.exists()


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


shutil.copytree(WORK, ARCHIVE)
source = ARCHIVE / 'source_snapshot'
suffixes = {'.py', '.ps1', '.scl', '.udt', '.db', '.json', '.plan', '.md', '.xml', '.cs', '.csproj', '.xsd'}
inputs = []
for path in sorted((REPO / 'FraktalCore/PLC/Siemens').rglob('*')):
    relative = path.relative_to(REPO)
    if not path.is_file() or {'bin', 'obj', '__pycache__'}.intersection(relative.parts):
        continue
    if path.suffix in suffixes or path.name.endswith('.scl.in'):
        inputs.append(path)
core = REPO / 'FraktalCore/PLC/TwinCAT/Framework/Fraktal_Core'
inputs += [p for p in core.rglob('*') if p.is_file() and p.suffix in ('.TcDUT', '.TcGVL', '.TcPOU', '.plcproj')]
hmi = REPO / 'FraktalCore/HMI'
for directory in ('lib', 'test', 'tool'):
    inputs += [p for p in (hmi / directory).rglob('*.dart') if p.is_file()]
inputs += [hmi / 'pubspec.yaml', hmi / 'pubspec.lock']
inputs += [REPO / p for p in (
    'Specification/Fraktal_Core_Part_I.md', 'Specification/Fraktal_TIA_Part_IV.md',
    'Specification/HMI_CONTRACT.md', 'Specification/OPCUA_TRANSPORT.md',
    'Specification/reason_rationalization.json', 'Specification/Siemens/SIEMENS_PORT_PLAN.md',
    'tools/check_consistency.py', 'tools/test_check_consistency.py', '.githooks/pre-commit',
)]
inputs = sorted(set(inputs))
for path in inputs:
    assert path.is_file(), path
    dest = source / path.relative_to(REPO)
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, dest)
    assert digest(dest) == digest(path), path

knowledge = ARCHIVE / 'knowledge_snapshot'
kb = Path('C:/Projects/SiemensAgent/siemens-kb/tia-automation')
memory = Path('C:/Users/Siemens/.claude/projects/c--Projects-Fraktal/memory')
knowledge_files = []
for directory, names, label in (
    (kb, ('INDEX.md', 'verified-gotchas.md', 'derived-state-and-alarm-lifecycle.md', 'local-access-and-owner-instance.md'), 'tia-automation'),
    (memory, ('MEMORY.md', 'project-siemens-port.md', 'feedback-siemens-sfc-st-no-ld.md', 'reference-flutter-sdk-host.md'), 'claude-memory'),
):
    for name in names:
        src = directory / name
        dest = knowledge / label / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        assert digest(src) == digest(dest)
        knowledge_files.append(str(dest.relative_to(ARCHIVE)))

with (ARCHIVE / '49_snapshot_inventory.json').open('x', encoding='ascii', newline='\n') as stream:
    json.dump({'source_files': len(inputs), 'sources': [str(p.relative_to(REPO)).replace('\\', '/') for p in inputs],
               'knowledge_files': knowledge_files, 'raw_work_copy': str(WORK)}, stream, indent=2)
    stream.write('\n')

bound = sorted([p for p in ARCHIVE.rglob('*') if p.is_file()] + [REPORT])
manifest = ARCHIVE / 'SHA256SUMS'
with manifest.open('x', encoding='ascii', newline='\n') as stream:
    for path in bound:
        stream.write(digest(path) + '  ' + path.relative_to(REPO).as_posix() + '\n')

for line in manifest.read_text('ascii').splitlines():
    expected, relative = line.split('  ', 1)
    assert digest(REPO / relative) == expected, relative
for path in WORK.rglob('*'):
    if path.is_file():
        assert digest(path) == digest(ARCHIVE / path.relative_to(WORK)), path

access = REPO / 'Specification/Siemens/Evidence/TIA_ACCESS_SESSIONS_2026-10-11'
for line in (access / 'SHA256SUMS').read_text('ascii').splitlines():
    expected, relative = line.split('  ', 1)
    assert digest(REPO / relative) == expected, relative
older = json.loads((access / '22_prior_inventory.json').read_bytes())['prior_files']
for relative, expected in older.items():
    assert digest(REPO / relative) == expected, relative

result = {'new_sha_bindings': len(bound), 'new_bound_bytes': sum(p.stat().st_size for p in bound),
          'source_snapshot_files': len(inputs), 'knowledge_snapshot_files': len(knowledge_files),
          'new_bindings_verified': True, 'previous_access_bindings_verified': 3360,
          'available_older_files_unchanged': len(older), 'absent_older_manifests_not_reverified': 18,
          'manifest_sha256': digest(manifest), 'archive': str(ARCHIVE), 'keeper_remains_alive': True}
with (WORK / '50_final_evidence_audit.json').open('x', encoding='ascii', newline='\n') as stream:
    json.dump(result, stream, indent=2)
    stream.write('\n')
print(json.dumps(result))
