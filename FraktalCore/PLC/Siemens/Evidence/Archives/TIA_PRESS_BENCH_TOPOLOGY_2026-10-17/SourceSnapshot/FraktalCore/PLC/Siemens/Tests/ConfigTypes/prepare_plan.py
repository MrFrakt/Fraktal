"""Prepare full or source-hash-scoped delta plans with the existing driver."""
import argparse
import json
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'tools'))
from fraktal_tia_program_layout import organize


def prepare(work, project, previous=None):
    organize(work/'sources', work/'grouped', project, work/'native')
    plan = work/'grouped/import.plan'
    if previous:
        changed = {p.name for p in (work/'sources').iterdir() if p.is_file()
                   and (not (previous/'sources'/p.name).exists() or p.read_bytes() != (previous/'sources'/p.name).read_bytes())}
        lines = []
        for line in plan.read_text('ascii').splitlines():
            if line.startswith('delete-blocks '): continue
            if line.startswith('import-sources ') and re.search(r'--only "([^"]+)"', line)[1] not in changed: continue
            lines.append(line)
        plan.write_bytes(('\n'.join(lines)+'\n').encode('ascii'))
        print(json.dumps(dict(changed=sorted(changed))))
    (work/'download.plan').write_bytes(('\n'.join([
        'open-project --path "'+str(project)+'"', 'compile --plc PLC_1', '${download}', 'save', ''])).encode('ascii'))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('work', type=Path)
    parser.add_argument('project', type=Path)
    parser.add_argument('--previous', type=Path)
    args = parser.parse_args()
    prepare(args.work, args.project, args.previous)
