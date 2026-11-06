"""C3 moves each module context into its AOI instance and changes nothing else: proved against C2.

For each pair (the C2 image of source 09, the C3 image), every ST line, SFC
line and ladder rung of every program routine and AOI is compared token by
token (the executed-ST model's tokenizer), after applying to the C2 side
exactly the changes C3 intends:
- `fraktal_ab_collapse.rename_contexts`, the very pass C3 runs: each
  `FRK_<Root>_Ctx<Name>` becomes `FRK_<Root>_Inst<Name>`;
- inside the type AOIs, `Ctx.<member>` becomes `<member>`;
- each module call loses its context argument;
- the S3h frame's copies of module contexts are dropped.

The C3 side's module AOI names (R8) are mapped back to C2's (R3). No numeric
literal may differ: C3 changes no member list, so nothing renumbers. Also
checks each module AOI's parameters: C2's minus `Ctx`, plus one Input per
context member.
Usage: c3_proof_01.py <output.json> <declaration> <c2.L5X> <c3.L5X> [...]
"""
import json, os, re, subprocess, sys
import xml.etree.ElementTree as ET
from pathlib import Path

T = Path(__file__).resolve().parents[5] / 'FraktalCore/PLC/Allen-Bradley/tools'
sys.path.insert(0, str(T))


def bodies(root):
    out = {}
    for kind, containers in (('program', root.iter('Program')), ('aoi', root.iter('AddOnInstructionDefinition'))):
        for container in containers:
            for routine in container.iter('Routine'):
                out[(kind, container.get('Name'), routine.get('Name'))] = [
                    e.text or '' for e in routine.iter() if e.tag in ('Line', 'Text')]
    return out


def tokens(text):
    import fraktal_ab_st_model as st
    return [(tok.kind, tok.text) for tok in st.tokenize(text) if tok.kind != 'eof']


def compare(declaration, c2_path, c3_path):
    os.environ['FRAKTAL_AB_DECLARATION'] = declaration
    import fraktal_ab_collapse as collapse
    import fraktal_ab_generate as gen
    import fraktal_ab_library as library
    import fraktal_ab_station as station
    app = station.application()
    n = app.name
    new_names = {gen.module_aoi_name(app, m) for m in app.modules}
    to_old = {name: name.replace(collapse.MODULE_SUFFIX, collapse.R3_SUFFIX, 1) for name in new_names}
    before = collapse.rename_contexts(Path(c2_path).read_text(encoding='utf-8'), app)
    c2, c3 = bodies(ET.fromstring(before.encode('utf-8'))), bodies(ET.parse(c3_path).getroot())
    old_names = set(to_old.values())
    ctx = re.compile(r'(?<![\w.])Ctx\.(\w+)')
    call = re.compile(r'(' + '|'.join(map(re.escape, sorted(old_names))) + r')\s*\(\s*([^,()]+),\s*FRK_' + re.escape(n) +
                      r'_Inst\w+\s*,')
    frame = re.compile(r'^\s*CPS\(\s*FRK_' + re.escape(n) + r'_Inst\w+\s*,\s*\S*ObservationFrame\.FRK_' + re.escape(n) +
                       r'_Ctx\w+\s*,\s*1\s*\)\s*;\s*$')

    def normal_c2(key, lines):
        if key[0] == 'aoi' and key[1] in old_names:
            lines = [ctx.sub(r'\1', line) for line in lines]
        text = '\n'.join(line for line in lines if not frame.match(line))
        return tokens(call.sub(lambda m: f'{m.group(1)}({m.group(2)},', text))

    def normal_c3(lines):
        text = '\n'.join(lines)
        for new, old in to_old.items():
            text = re.sub(rf'(?<![\w.]){re.escape(new)}(?![\w])', old, text)
        return tokens(text)

    c3 = {(k[0], to_old.get(k[1], k[1]), k[2]): v for k, v in c3.items()}
    differences = []
    for key in sorted(set(c2) | set(c3)):
        a, b = normal_c2(key, c2.get(key, [])), normal_c3(c3.get(key, []))
        if a != b:
            i = next((j for j, (x, y) in enumerate(zip(a, b)) if x != y), min(len(a), len(b)))
            differences.append(dict(routine=list(key), tokens=[len(a), len(b)],
                                    c2=' '.join(v for _, v in a[max(0, i - 10):i + 10]),
                                    c3=' '.join(v for _, v in b[max(0, i - 10):i + 10])))
    findings = []
    roots = ET.parse(c2_path).getroot(), ET.parse(c3_path).getroot()
    for mtype in library.types_used(app):
        new = gen.module_aoi_name(app, next(m for m in app.modules if library.type_of(m) == mtype))
        old = to_old[new]
        params = [[(p.get('Name'), p.get('Usage')) for p in next(a for a in r.iter('AddOnInstructionDefinition')
                   if a.get('Name') == name).iter('Parameter')] for r, name in ((roots[0], old), (roots[1], new))]
        members = [(m.name, 'Input') for m in gen.module_context_members(mtype, True)]
        if [p for p in params[0] if p[0] != 'Ctx'] + members != params[1]:
            findings.append(mtype.type_key)
    return dict(declaration=declaration, routines=len(c2), differences=differences,
                parameterFindings=findings, passed=not differences and not findings)


if __name__ == '__main__':
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
    print(json.dumps([dict(declaration=r['declaration'], routines=r['routines'], differences=len(r['differences']),
                           parameterFindings=r['parameterFindings'], passed=r['passed']) for r in results]))
    raise SystemExit(0 if all(r['passed'] for r in results) else 1)
