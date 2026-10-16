"""Select public evidence; seal only after all gates finish."""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

REPO=Path(r'C:\Projects\Fraktal')
TIA=REPO/'FraktalCore/PLC/Siemens'
WORK=Path(__file__).resolve().parent
OWNER=WORK.parent/'Line_Owner_20261016'
OUT=TIA/'Evidence/Archives/TIA_LINE_SETS_MIRROR_2026-10-16'
PREVIOUS=TIA/'Evidence/Archives/TIA_LINE_OWNER_2026-10-16/SourceSnapshot'


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def copy(source,relative):
    target=OUT/relative;target.parent.mkdir(parents=True,exist_ok=True)
    if target.exists():assert target.read_bytes()==source.read_bytes(),target
    shutil.copyfile(source,target)


def package():
    assert not (OUT/'SHA256SUMS.txt').exists(),'sealed archives are immutable'
    OUT.mkdir(exist_ok=True)
    omitted=[]
    for label,revision,frames in [('Owner',OWNER/'native04',WORK/'CurrentFramesOwner'),
                                  ('Mirror',WORK/'native01',WORK/'CurrentFramesMirror')]:
        for path in (revision/'sources').iterdir():
            if path.suffix not in ('.scl','.udt','.db'):continue
            if path.name=='38_ConfigBenchRoutines.scl':
                public,count=re.subn(r'^FUNCTION "F_AccessBenchProvision"(?=\s|:).*?^END_FUNCTION\s*','',path.read_text('ascii'),flags=re.M|re.S)
                assert count==1
                target=OUT/label/'Sources/38_ConfigBenchRoutines.public.scl'
                target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(public.encode('ascii'))
                omitted.append(dict(path=label+'/Sources/'+path.name,sha256=sha(path),reason='private credential initializer; two remaining FCs preserved in public derivative'))
            else:copy(path,Path(label)/'Sources'/path.name)
        for path in (revision/'native').rglob('*'):
            if not path.is_file():continue
            relative=path.relative_to(revision/'native')
            if path.stem=='F_AccessBenchProvision':
                omitted.append(dict(path=label+'/Native/'+relative.as_posix(),sha256=sha(path),reason='private credential initializer'))
            else:copy(path,Path(label)/'Native'/relative)
        for path in frames.iterdir():
            if path.is_file():copy(path,Path(label)/'Frames'/path.name)
        for name in ('build.log','download.log','download_guard.json','isolated_download.plan','owner_verified_private.json'):
            copy(revision/name,Path(label)/'NativeRun'/('verified_full.json' if name=='owner_verified_private.json' else name))
    copy(OWNER/'sets_probe01.jsonl','Runs/owner_sets_probe01.jsonl')
    for name in ('mirror_probe01.jsonl','probe02.jsonl','probe03.jsonl','release.json','original_final.json',
                 'frame_replay.json','press_replay.json','press_compile.plan','press_compile.log',
                 'tools_tests_final.log','lint_final.log','consistency.log','consistency_tests.log','candidate.log','kb_index.json'):
        copy(WORK/name,'Runs/'+name)
    for path in (OWNER/'hmi05').iterdir():
        if path.is_file():copy(path,Path('Runs/hmi05')/path.name)
    for path in PREVIOUS.rglob('*'):
        if path.is_file():copy(REPO/path.relative_to(PREVIOUS),Path('SourceSnapshot')/path.relative_to(PREVIOUS))
    for path in (TIA/'Tests/Line').iterdir():
        if path.is_file():copy(path,Path('SourceSnapshot')/path.relative_to(REPO))
    copy(Path(__file__),'Gates/package_sets_mirror.py')
    copy(WORK/'finish_owner.py','Gates/finish_owner.py')
    (OUT/'Gates/omissions.json').write_text(json.dumps(omitted,indent=2)+'\n',encoding='ascii')
    snapshot=OUT/'SourceSnapshot'
    for label in ('Owner','Mirror'):
        commands=[
            [str(snapshot/'FraktalCore/PLC/Siemens/Tests/Line/verify_owner_exports.py'),str(OUT/label/'Sources'),str(OUT/label/'Native'),str(OUT/'Gates'/('verified_public_'+label.lower()+'.json'))],
            [str(snapshot/'FraktalCore/PLC/Siemens/tools/fraktal_tia_generate.py'),'--verify',str(OUT/label/'Frames')]]
        for i,command in enumerate(commands):
            r=subprocess.run([sys.executable,'-B',*command],capture_output=True,text=True)
            (OUT/'Gates'/('%s_replay_%d.log'%(label.lower(),i))).write_text(r.stdout+r.stderr,encoding='utf-8')
            assert r.returncode==0,r.stderr+r.stdout
    for path in OUT.rglob('*'):
        if not path.is_file():continue
        assert not {'.dart_tool','__pycache__','build'}.intersection(path.relative_to(OUT).parts)
        assert path.suffix not in ('.pyc','.sqlite','.ap20','.plf')
        if path.suffix in ('.scl','.db','.udt','.xml'):
            assert not re.search(r'Rows\[\d+\]\.(?:Salt|PinHash)\[\d+\]\s*:=\s*BYTE#16#',path.read_text('utf-8-sig')),path
    (OUT/'packaging.json').write_text(json.dumps(dict(
        source_revision='a0804775ff149e084202d78385b4c8f61ac49cc9 + sets/mirror working changes',
        workbench_only=True,owner_native_blocks=404,mirror_native_blocks=406,
        owner_public_blocks=403,mirror_public_blocks=405,owner_checks=165,mirror_checks=64,
        source_provider='synthetic local fixture; cross-controller transport unimplemented',
        tool_tests=235,hmi='generic editor/repository component; not full shell acceptance',
        excluded=['projects','simulator storage','credentials','private SQLite backups','generated caches']
    ),indent=2)+'\n',encoding='ascii')
    print(json.dumps(dict(files=sum(p.is_file() for p in OUT.rglob('*')),archive=str(OUT))))


if __name__=='__main__':package()
