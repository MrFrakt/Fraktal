"""C2 is a storage rename and nothing else: proved against the C1 image, routine by routine.

For each pair (the C1 image of source 08, the C2 image), every ST line, SFC
line and ladder rung of every program routine and AOI is compared with all
whitespace removed, after exactly the changes C2 intends are applied to the
C1 side:
- `fraktal_ab_collapse.rename_storage`, the very pass C2 runs, renames each
  moved member;
- the copies it makes redundant (`<path> := <path>;`) are dropped;
- the C2 side's added `Root`/root arguments and the R8 AOI names are taken out;
- the V5 localization renumbering is accounted for exactly. C2 removes the
  moved members' field-path keys, and every later numeric key shifts. So the
  two texts are compared with every integer literal abstracted, and must then
  be identical. At each aligned literal that differs, the C1 number must be a
  localization key that the two images' own tables (same key text) renumber
  to precisely the C2 number, or one of the values derived from those tables:
  the key count, the exclusive bound one past it, and the V5 build revision
  (the V5 content hash, which those keys feed). An offset into the constant
  canonical text pool (`CanonicalTextWork.Offset :=`) is explained when the
  pool bytes at the C1 offset in C1 equal those at the C2 offset in C2: the
  pool holds those key texts too, so it shrinks with them. Any other
  differing literal is a difference, and is reported with its context.

Anything else that differs is reported, and the run fails. Also compares the
Unit and part AOI parameter lists: C2's must be C1's plus `Root`.
Usage: c2_rename_proof_01.py <output.json> <declaration> <c1.L5X> <c2.L5X> [...]
"""
import json, os, re, sys
import xml.etree.ElementTree as ET
from pathlib import Path

T = Path(__file__).resolve().parents[5] / 'FraktalCore/PLC/Allen-Bradley/tools'
sys.path.insert(0, str(T))


def bodies(root):
    """Each routine's code lines, in order: ST and SFC lines, ladder rung texts."""
    out = {}
    for kind, containers in (('program', root.iter('Program')), ('aoi', root.iter('AddOnInstructionDefinition'))):
        for container in containers:
            for routine in container.iter('Routine'):
                key = (kind, container.get('Name'), routine.get('Name'))
                out[key] = [e.text or '' for e in routine.iter() if e.tag in ('Line', 'Text')]
    return out


def tokens(text):
    """The executed-ST model's tokens; whitespace and comments carry no meaning."""
    import fraktal_ab_st_model as st
    return [(tok.kind, tok.text) for tok in st.tokenize(text) if tok.kind != 'eof']


def renumbering(c1_path, c2_path):
    import fraktal_ab_schema_identity as si
    text = lambda v: v['DATA'].strip().strip("'")
    tables = []
    for path in (c1_path, c2_path):
        tags = si.surface(Path(path))['tags']
        rows = tags['FRK_Press_MfLocalization']['Data']
        keys = {text(r['PortableKey']): int(r['NumericKey']) for r in rows if int(r['PortableKey']['LEN'])}
        header = tags['FRK_Press_MfHeader']['Data']
        tables.append((keys, int(header['LocalizationCount']), int(header['ConfigRevision'])))
    (old, old_count, old_revision), (new, new_count, new_revision) = tables
    mapping = {old[k]: new[k] for k in old if k in new and old[k] != new[k]}
    for a, b in ((old_count, new_count), (old_count + 1, new_count + 1), (old_revision, new_revision)):
        if a != b:
            mapping[a] = b
    return mapping


def pool(path, name):
    root = ET.parse(path).getroot()
    tag = next(t for t in root.find('Controller').find('Tags') if t.get('Name') == name)
    return [int(e.get('Value')) for e in tag.iter('Element')]


def compare(declaration, c1_path, c2_path):
    os.environ['FRAKTAL_AB_DECLARATION'] = declaration
    import fraktal_ab_collapse as collapse
    import fraktal_ab_generate as gen
    import fraktal_ab_part as part
    import fraktal_ab_station as station
    app = station.application()
    new_unit, new_part = gen.unit_aoi_name(app), part.service_name(app) if app.part_carrier else None
    old_unit = new_unit[:-len(collapse.AOI_SUFFIX)]
    old_part = new_part[:-len(collapse.AOI_SUFFIX)] if new_part else None
    c1_text = Path(c1_path).read_text(encoding='utf-8')
    renamed = collapse.rename_storage(c1_text, app, {old_unit, *([old_part] if old_part else [])})
    c1, c2 = bodies(ET.fromstring(renamed.encode('utf-8'))), bodies(ET.parse(c2_path).getroot())
    copy = re.compile(r'^\s*((?:Root|' + re.escape(app.name) + r')\.[\w.\[\]]+)\s*:=\s*\1\s*;\s*$')
    mapping = renumbering(c1_path, c2_path)
    import fraktal_ab_canonical_text as text_pool
    pools = pool(c1_path, text_pool.pool_tag(app)), pool(c2_path, text_pool.pool_tag(app))
    renumbered, unexplained, moved = [0], [], [0]

    def same_text(x, y):
        a, b = pools[0][x:x + 16], pools[1][y:y + 16]
        return bool(a) and a == b

    def normal_c1(lines):
        return tokens('\n'.join(line for line in lines if not copy.match(line)))

    def normal_c2(lines):
        text = '\n'.join(lines)
        if new_part:
            text = re.sub(re.escape(new_part) + r'\s*\(((?:[^,()]*,){5})\s*(?:Root|' + re.escape(app.name) + r')\s*,',
                          lambda m: old_part + '(' + m.group(1), text)
        text = re.sub(re.escape(new_unit) + r'\s*\(((?:[^,()]*,){3})\s*' + re.escape(app.name) + r'\s*,',
                      lambda m: old_unit + '(' + m.group(1), text)
        return tokens(text)

    def same(a, b):
        if len(a) != len(b):
            return False
        ok = True
        for i, (x, y) in enumerate(zip(a, b)):
            if x == y:
                continue
            if x[0] == y[0] == 'number' and mapping.get(int(x[1])) == int(y[1]):
                renumbered[0] += 1
                continue
            before = [v for _, v in a[max(0, i - 4):i]]
            offset = len(before) == 4 and before[0].endswith('_CanonicalTextWork') and before[1:] == ['.', 'Offset', ':=']
            if x[0] == y[0] == 'number' and offset and same_text(int(x[1]), int(y[1])):
                moved[0] += 1
                continue
            unexplained.append(dict(c1=x[1], c2=y[1], context=' '.join(v for _, v in a[max(0, i - 8):i])))
            ok = False
        return ok

    rename_key = lambda k: (k[0], {new_unit: old_unit, new_part: old_part}.get(k[1], k[1]), k[2])
    c2 = {rename_key(k): v for k, v in c2.items()}
    differences = []
    for key in sorted(set(c1) | set(c2)):
        a, b = normal_c1(c1.get(key, [])), normal_c2(c2.get(key, []))
        if not same(a, b):
            differences.append(dict(routine=list(key), tokens=[len(a), len(b)], unexplained=unexplained[:12]))
            unexplained.clear()
    params = {}
    for path, names in ((c1_path, (old_unit, old_part)), (c2_path, (new_unit, new_part))):
        root = ET.parse(path).getroot()
        for aoi in root.iter('AddOnInstructionDefinition'):
            if aoi.get('Name') in names:
                params.setdefault(rename_key(('aoi', aoi.get('Name'), ''))[1], []).append(
                    [p.get('Name') for p in aoi.iter('Parameter')])
    parameter_findings = [name for name, (before, after) in params.items()
                          if [p for p in after if p != 'Root'] != before or after.count('Root') != 1]
    return dict(declaration=declaration, routines=len(c1), renumberedKeys=len(mapping),
                renumberedLiterals=renumbered[0], movedPoolOffsets=moved[0],
                poolBytes=[len(pools[0]), len(pools[1])], differences=differences,
                parameterFindings=parameter_findings, passed=not differences and not parameter_findings and len(params) >= 1)


if __name__ == '__main__':
    import subprocess
    output, rest = Path(sys.argv[1]), sys.argv[2:]
    if rest and rest[0] == '--one':
        print(json.dumps(compare(*rest[1:4])))
        raise SystemExit(0)
    results = []
    for i in range(0, len(rest), 3):
        done = subprocess.run([sys.executable, __file__, str(output), '--one', *rest[i:i + 3]],
                              capture_output=True, text=True, check=True)
        results.append(json.loads(done.stdout.strip().splitlines()[-1]))
    with output.open('x', encoding='utf-8', newline='\n') as f:
        json.dump(dict(passed=all(r['passed'] for r in results), results=results), f, indent=1)
    print(json.dumps([dict(declaration=r['declaration'], routines=r['routines'], renumberedKeys=r['renumberedKeys'],
                           renumberedLiterals=r['renumberedLiterals'], movedPoolOffsets=r['movedPoolOffsets'],
                           poolBytes=r['poolBytes'],
                           differences=len(r['differences']),
                           parameterFindings=r['parameterFindings'], passed=r['passed']) for r in results]))
    raise SystemExit(0 if all(r['passed'] for r in results) else 1)
