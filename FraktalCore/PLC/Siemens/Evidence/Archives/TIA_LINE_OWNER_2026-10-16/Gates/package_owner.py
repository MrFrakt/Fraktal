"""One-off immutable public evidence selection; no engineering projects/secrets."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

REPO = Path(r'C:\Projects\Fraktal')
WORK = Path(__file__).resolve().parent
ARCHIVES = REPO/'FraktalCore/PLC/Siemens/Evidence/Archives'
OUT = ARCHIVES/'TIA_LINE_OWNER_2026-10-16'
OUT.mkdir(exist_ok=False)


def copy(source, relative):
    target = OUT/relative
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()


omitted = []
for path in (WORK/'native03/sources').iterdir():
    if not path.is_file() or path.suffix not in ('.scl', '.udt', '.db'): continue
    if path.name == '38_ConfigBenchRoutines.scl':
        text = path.read_text('ascii')
        public, count = re.subn(r'^FUNCTION "F_AccessBenchProvision"(?=\s|:).*?^END_FUNCTION\s*', '', text, flags=re.M|re.S)
        assert count == 1
        target = OUT/'Sources/38_ConfigBenchRoutines.public.scl'
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(public.encode('ascii'))
        omitted.append(dict(path='Sources/'+path.name, sha256=sha(path), reason='private credential initializer; remaining two FCs preserved in .public source'))
    else: copy(path, 'Sources/'+path.name)

for path in (WORK/'native03/native').rglob('*'):
    if not path.is_file(): continue
    relative = path.relative_to(WORK/'native03/native')
    if path.stem == 'F_AccessBenchProvision':
        omitted.append(dict(path='Native/'+relative.as_posix(), sha256=sha(path), reason='private credential initializer'))
    else: copy(path, 'Native'/relative)

for path in (WORK/'current_frames_complete').iterdir():
    if path.is_file(): copy(path, 'Frames/'+path.name)
for name in ('owner_verified_private.json','build.log','download.log','download_guard.json','isolated_download.plan'):
    copy(WORK/'native03'/name, 'NativeRun/'+('verified_full.json' if name=='owner_verified_private.json' else name))
for name in ('owner_probe01.jsonl','owner_probe02.jsonl','owner_probe03.jsonl','web_provision01.log',
             'host.log','host.stderr','host2.log','host2.stderr','original_final.json',
             'frame_replay.json','press_compile.plan','press_compile.log','press_replay.log',
             'consistency.log','candidate.log','lint.log','lint_final.log','tools_tests.log','tools_tests_final.log','kb_index.json'):
    copy(WORK/name, 'Runs/'+name)
for folder in ('hmi01','hmi02','hmi03','hmi04'):
    for path in (WORK/folder).iterdir():
        if path.is_file(): copy(path, 'Runs'/Path(folder)/path.name)

snapshot = OUT/'SourceSnapshot'
previous = ARCHIVES/'TIA_LINE_ENGINE_2026-10-15_R1/SourceSnapshot'
for path in previous.rglob('*'):
    if not path.is_file(): continue
    relative = path.relative_to(previous)
    assert not {'.dart_tool','__pycache__','build'}.intersection(relative.parts)
    copy(REPO/relative, 'SourceSnapshot'/relative)
for relative in ('FraktalCore/PLC/Siemens/Tests/Line/bench_owner.json',
                 'FraktalCore/PLC/Siemens/Tests/Line/make_owner_fixture.py',
                 'FraktalCore/PLC/Siemens/Tests/Line/owner_target.py',
                 'FraktalCore/PLC/Siemens/Tests/Line/probe_owner.py',
                 'FraktalCore/PLC/Siemens/Tests/Line/verify_owner_exports.py',
                 'FraktalCore/PLC/Siemens/Tests/Line/run_owner_hmi.py',
                 'FraktalCore/HMI/test/live_tia_line_test.dart',
                 'FraktalCore/HMI/test/support/tia_line_transport.dart'):
    copy(REPO/relative, 'SourceSnapshot'/Path(relative))
copy(Path(__file__), 'Gates/package_owner.py')
(OUT/'Gates/omissions.json').write_text(json.dumps(omitted,indent=2)+'\n',encoding='ascii')

# A private initializer must never survive in another exported source.
for path in OUT.rglob('*'):
    if path.suffix in ('.scl','.db','.udt') and path.is_file():
        assert not re.search(r'Rows\[\d+\]\.(?:Salt|PinHash)\[\d+\]\s*:=\s*BYTE#16#',path.read_text('utf-8-sig')),path

verifier = snapshot/'FraktalCore/PLC/Siemens/Tests/Line/verify_owner_exports.py'
result = subprocess.run([sys.executable,'-B',str(verifier),str(OUT/'Sources'),str(OUT/'Native'),str(OUT/'Gates/verified_public.json')],capture_output=True,text=True)
(OUT/'Gates/public_replay.log').write_text(result.stdout+result.stderr,encoding='utf-8')
assert result.returncode == 0,result.stderr
generator = snapshot/'FraktalCore/PLC/Siemens/tools/fraktal_tia_generate.py'
result = subprocess.run([sys.executable,'-B',str(generator),'--verify',str(OUT/'Frames')],capture_output=True,text=True)
(OUT/'Gates/frame_replay.log').write_text(result.stdout+result.stderr,encoding='utf-8')
assert result.returncode == 0,result.stderr

assert not any(p.suffix=='.pyc' or {'.dart_tool','__pycache__','build'}.intersection(p.relative_to(OUT).parts) for p in OUT.rglob('*'))
payload = [p for p in sorted(OUT.rglob('*')) if p.is_file()]
(OUT/'packaging.json').write_text(json.dumps(dict(
    source_revision='591f21cd5b5132ecb61613660111d98ce617e6e2 + owner working changes',
    full_native_blocks=402,public_replay_blocks=401,omitted_private_initializer='F_AccessBenchProvision',
    workbench_only=True,simulated_restart_checks=54,tool_tests=231,
    generic_hmi='hmi04 passed; component test, not full shell navigation',
    excluded=['engineering projects','simulator storage','credentials','private SQLite backups','generated caches']
),indent=2)+'\n',encoding='ascii')
print(json.dumps(dict(archive=str(OUT),files=len(payload)+1,public_replay=result.returncode)))
