"""C4a adds the fixture observation and removes the S3h frame, and changes no other code.

Check 02, for source 12. Source 11 called the fixture copy from the scan plan,
after the canonical generation's closing increment; source 12 calls it from
the canonical publication, just before that close. For each pair (the C3
image of source 10, the C4a image of source 12), every program routine and
AOI body is compared token by token (the executed-ST model's tokenizer).
Each routine must be identical, except:
- a routine only C4a has must be the fixture copy, `FRK_<Root>_CopyFixtureObservation`;
- a routine only C3 has must be the frame's;
- a routine may lose exactly one contiguous block of lines, the frame's: it
  opens with `IF (FRK_<Root>_ScanCount MOD <n>) = 0 THEN`, closes with
  `END_IF;`, and every line between names the frame or its generation or is
  an `END_IF;`;
- a routine may gain exactly one line, `JSR(FRK_<Root>_CopyFixtureObservation, 0);`,
  and only immediately before `FRK_<Root>_CanonicalGeneration := ... + 1;`.
  It may gain nothing else.

Any other difference fails. Usage: c4a_routines_02.py <output.json> <c3.L5X> <c4a.L5X> [...]
"""
import difflib, json, re, sys
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[5] / 'FraktalCore/PLC/Allen-Bradley/tools'))
import fraktal_ab_st_model as st

COPY = re.compile(r'program/\w+/FRK_\w+_CopyFixtureObservation\Z')


def bodies(path):
    root = ET.parse(path).getroot()
    out = {}
    for kind, containers in (('program', root.iter('Program')), ('aoi', root.iter('AddOnInstructionDefinition'))):
        for container in containers:
            for routine in container.iter('Routine'):
                text = '\n'.join(e.text or '' for e in routine.iter() if e.tag in ('Line', 'Text'))
                out[f"{kind}/{container.get('Name')}/{routine.get('Name')}"] = (
                    [(t.kind, t.text) for t in st.tokenize(text) if t.kind != 'eof'],
                    [line.strip() for line in text.splitlines()])
    return out


def explained(before, after, copies):
    """The description of an allowed edit from `before` to `after`, or None."""
    ops = [op for op in difflib.SequenceMatcher(None, before, after, autojunk=False).get_opcodes()
           if op[0] != 'equal']
    found = []
    for tag, i1, i2, j1, j2 in ops:
        if tag == 'delete':
            removed = before[i1:i2]
            if not (re.fullmatch(r'IF \(FRK_\w+_ScanCount MOD \d+\) = 0 THEN', removed[0])
                    and removed[-1] == 'END_IF;'
                    and all(re.search(r'Observation(Frame|Generation)', line) or line == 'END_IF;'
                            for line in removed[1:-1])):
                return None
            found.append('the frame block removed')
        elif tag == 'insert' and j2 - j1 == 1 and after[j1] in copies and j2 < len(after) \
                and re.fullmatch(r'(FRK_\w+_CanonicalGeneration) := \1 \+ 1;', after[j2]):
            found.append('the fixture copy called before the generation close')
        else:
            return None
    if not found or len(found) != len(set(found)):
        return None
    return ' and '.join(found)


def compare(c3, c4):
    a, b = bodies(c3), bodies(c4)
    added, removed = sorted(set(b) - set(a)), sorted(set(a) - set(b))
    findings = []
    findings += [f'unexpected added routine {r}' for r in added if not COPY.fullmatch(r)]
    findings += [f'unexpected removed routine {r}' for r in removed if 'Observation' not in r]
    copies = {f"JSR({r.rsplit('/', 1)[1]}, 0);" for r in added if COPY.fullmatch(r)}  # as emitted
    changed = []
    for key in sorted(set(a) & set(b)):
        if a[key][0] != b[key][0]:
            why = explained(a[key][1], b[key][1], copies)
            if why:
                changed.append(f'{key} ({why})')
            else:
                findings.append(f'unexpected change in {key}')
    return dict(c3=str(c3), c4a=str(c4), routines=[len(a), len(b)], added=added, removed=removed,
                explained=changed, findings=findings, passed=not findings)


if __name__ == '__main__':
    output, pairs = Path(sys.argv[1]), sys.argv[2:]
    results = [compare(Path(pairs[i]), Path(pairs[i + 1])) for i in range(0, len(pairs), 2)]
    with output.open('x', encoding='utf-8', newline='\n') as f:
        json.dump(dict(passed=all(r['passed'] for r in results), results=results), f, indent=1)
    print(json.dumps([{k: r[k] for k in ('routines', 'added', 'removed', 'explained', 'findings', 'passed')}
                      for r in results], indent=1))
    raise SystemExit(0 if all(r['passed'] for r in results) else 1)
