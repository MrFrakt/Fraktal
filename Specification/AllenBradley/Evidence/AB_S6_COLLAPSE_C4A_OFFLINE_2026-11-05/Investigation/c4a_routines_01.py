"""C4a adds the fixture observation and removes the S3h frame, and changes no other code.

For each pair (the C3 image of source 10, the C4a image of source 11), every
program routine and AOI body is compared token by token (the executed-ST
model's tokenizer). Each routine must be identical, except:
- a routine only C4a has must be the fixture observation's;
- a routine only C3 has must be the frame's;
- the scan plan (the main routine) may differ only by the JSRs that call
  them;
- a routine may lose exactly one contiguous block of lines, the frame's: it
  opens with `IF (FRK_<Root>_ScanCount MOD <n>) = 0 THEN`, closes with
  `END_IF;`, and every line between names the frame or its generation or is
  an `END_IF;`. It may gain nothing.

Any other difference fails. Usage: c4a_routines_01.py <output.json> <c3.L5X> <c4a.L5X> [...]
"""
import json, re, sys
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[5] / 'FraktalCore/PLC/Allen-Bradley/tools'))
import fraktal_ab_st_model as st


def bodies(path):
    root = ET.parse(path).getroot()
    out = {}
    for kind, containers in (('program', root.iter('Program')), ('aoi', root.iter('AddOnInstructionDefinition'))):
        for container in containers:
            for routine in container.iter('Routine'):
                text = '\n'.join(e.text or '' for e in routine.iter() if e.tag in ('Line', 'Text'))
                out[f"{kind}/{container.get('Name')}/{routine.get('Name')}"] = [
                    (t.kind, t.text) for t in st.tokenize(text) if t.kind != 'eof']
    return out


def jsr_free(tokens, names):
    """The token list without `JSR ( <name> , 0 ) ;` for each name given."""
    out, i = [], 0
    while i < len(tokens):
        window = [v for _, v in tokens[i:i + 7]]
        if len(window) == 7 and window[0] == 'JSR' and window[2] in names and window[1] == '(':
            i += 7
            continue
        out.append(tokens[i])
        i += 1
    return out


def code_lines(path):
    root = ET.parse(path).getroot()
    out = {}
    for kind, containers in (('program', root.iter('Program')), ('aoi', root.iter('AddOnInstructionDefinition'))):
        for container in containers:
            for routine in container.iter('Routine'):
                out[f"{kind}/{container.get('Name')}/{routine.get('Name')}"] = [
                    (e.text or '').strip() for e in routine.iter() if e.tag in ('Line', 'Text')]
    return out


def frame_block_only(before, after):
    """Whether `after` is `before` less exactly one frame block, and nothing else."""
    import difflib
    blocks = [op for op in difflib.SequenceMatcher(None, before, after, autojunk=False).get_opcodes() if op[0] != 'equal']
    if len(blocks) != 1 or blocks[0][0] != 'delete':
        return False
    removed = before[blocks[0][1]:blocks[0][2]]
    if not (re.fullmatch(r'IF \(FRK_\w+_ScanCount MOD \d+\) = 0 THEN', removed[0]) and removed[-1] == 'END_IF;'):
        return False
    return all(re.search(r'Observation(Frame|Generation)', line) or line == 'END_IF;' for line in removed[1:-1])


def compare(c3, c4):
    a, b = bodies(c3), bodies(c4)
    la, lb = code_lines(c3), code_lines(c4)
    added, removed = sorted(set(b) - set(a)), sorted(set(a) - set(b))
    findings = []
    findings += [f'unexpected added routine {r}' for r in added if not r.endswith('ScanFixtureObservation')]
    findings += [f'unexpected removed routine {r}' for r in removed if 'Observation' not in r]
    moved = {r.rsplit('/', 1)[1] for r in added + removed}
    changed = []
    for key in sorted(set(a) & set(b)):
        if a[key] != b[key]:
            if jsr_free(a[key], moved) == jsr_free(b[key], moved):
                changed.append(f'{key} (only the JSRs of {sorted(moved)})')
            elif frame_block_only(la[key], lb[key]):
                changed.append(f'{key} (only the frame block removed)')
            else:
                findings.append(f'unexpected change in {key}')
    return dict(c3=str(c3), c4a=str(c4), routines=[len(a), len(b)], added=added, removed=removed,
                explained=changed, findings=findings, passed=not findings)


if __name__ == '__main__':
    output, pairs = Path(sys.argv[1]), sys.argv[2:]
    results = [compare(Path(pairs[i]), Path(pairs[i + 1])) for i in range(0, len(pairs), 2)]
    with output.open('x', encoding='utf-8', newline='\n') as f:
        json.dump(dict(passed=all(r['passed'] for r in results), results=results), f, indent=1)
    print(json.dumps([{k: r[k] for k in ('routines', 'added', 'removed', 'explained', 'findings', 'passed')} for r in results],
                     indent=1))
    raise SystemExit(0 if all(r['passed'] for r in results) else 1)
