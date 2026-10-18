"""Compile the standalone chart before binding its owner into the Unit frame."""
import argparse
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / 'tools'))
from fraktal_tia_program_layout import organize


def prepare(work, project, previous=None):
    organize(work/'sources', work/'grouped', project, work/'native')
    plan = (work/'grouped/import.plan').read_text('ascii').splitlines()
    if previous:
        expected = {p.name for p in (previous/'sources').iterdir() if p.suffix in ('.scl', '.udt', '.db', '.xml')}
        current = {p.name for p in (work/'sources').iterdir() if p.suffix in ('.scl', '.udt', '.db', '.xml')}
        assert expected == current, 'Incremental fixture requires the same complete source inventory'
        changed = {name for name in current if (work/'sources'/name).read_bytes() != (previous/'sources'/name).read_bytes()}
        assert changed and all(name in {'08_GDB_RecoveryTest.db', '08_GDB_RecoveryWork.db', '28_RecoveryOwner.scl', '38_ConfigBenchRoutines.scl', '16_SequenceServices.scl'} for name in changed)
        lines = [plan[0]]+[line for line in plan if line.startswith('import-sources ') and any('--only "'+name+'"' in line for name in changed)]
        lines += ['compile --plc PLC_1', 'export --plc PLC_1 --out "'+str(work/'native')+'" --scl true', 'save']
        (work/'grouped/import.plan').write_bytes(('\n'.join(lines)+'\n').encode('ascii'))
        return
    bootstrap = work/'bootstrap'
    bootstrap.mkdir()
    first, owner, final_frames = [], [], []
    for line in plan:
        if line.startswith(('compile ', 'save', 'list-groups ', 'export ')):
            continue
        if '28_RecoveryOwner.scl' in line:
            owner.append(line)
            continue
        if line.startswith('import-sources ') and '--only "20_' in line:
            name = re.search(r'--only "([^"]+)"', line)[1]
            text = (work/'sources'/name).read_text('ascii')
            text, removed = re.subn(r'^.*"F_TestRecovery"\(.*\n', '', text, flags=re.M)
            if removed:
                assert removed == 1
                (bootstrap/name).write_bytes(text.encode('ascii'))
                final_frames.append(line)
                line = re.sub(r'--dir "[^"]+"', '--dir "'+str(bootstrap).replace('\\', '/')+'"', line)
        first.append(line)
    assert len(owner) == 1 and final_frames
    tail = ['compile --plc PLC_1', 'list-groups --plc PLC_1',
            'export --plc PLC_1 --out "'+str(work/'native')+'" --scl true', 'save']
    lines = first+['compile --plc PLC_1', 'save']+owner+final_frames+tail
    (work/'grouped/import.plan').write_bytes(('\n'.join(lines)+'\n').encode('ascii'))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('work', type=Path)
    parser.add_argument('project', type=Path)
    parser.add_argument('--previous', type=Path)
    args = parser.parse_args()
    prepare(args.work, args.project, args.previous)
