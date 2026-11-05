"""WP6.6 inventory: the data flow of every legacy context member (read-only analysis).

For each S6-Q declaration, generate the image in memory and record, for every
Unit, chart and module context member, where it is written and read in the
emitted ST and ladder. Inside an AOI a context is a parameter of the context's
type: the type AOI's `Ctx` stands for every instance of the type, and another
AOI's `Ctx<Name>` for one instance.

The owner is the AOI that computes the context: the module's type AOI, or the
Unit AOI for the Unit context and the chart. The publication is every routine
whose name contains `Canonical`, where the copy layer runs. Each member gets:
- `ownerWrites`/`ownerReads`: whether its owner touches it;
- `externalWriters`/`externalReaders`: routines outside the owner, readers
  without the publication;
- `published`: each canonical target an assignment fills from it, `exact` when
  the right-hand side is the member alone;
- `harnesses`: the harnesses the HX accounting found asserting it;

and one class, the first that applies:
- `unused`: touched by no routine;
- `shared`: written both by its owner and outside it;
- `input`: written only outside its owner;
- `output`: read outside its owner and its publication;
- `published`: read outside its owner only by the publication;
- `private`: touched only by its owner.

`--declaration DECL` runs one declaration (station selection is process
state); the default runs both and writes the report. Contacts no controller.
"""
import argparse, collections, json, os, re, subprocess, sys, tempfile
from pathlib import Path
import xml.etree.ElementTree as ET

R = Path(__file__).resolve().parents[5]
T = R / 'FraktalCore/PLC/Allen-Bradley/tools'
HX = R / 'Specification/AllenBradley/Evidence/AB_S6_HX_FACT_ACCOUNTING_OFFLINE_2026-11-03/Investigation/hx_fact_accounting_02.json'
DECLARATIONS = ('fraktal_ab_genealogy_s4b_owner_demo', 'fraktal_ab_press_canonical_echo38')
LD_WRITES = {'OTE', 'OTL', 'OTU', 'RES', 'ONS', 'OSR', 'OSF'}
LD_DEST_LAST = {'MOV', 'COP', 'CPS', 'ADD', 'SUB', 'MUL', 'DIV', 'CLR', 'MOD', 'BTD', 'CPT', 'NEG', 'ABS'}
CONTROL = re.compile(r'\s*(IF|ELSIF|ELSE|END_IF|FOR|END_FOR|WHILE|END_WHILE|CASE|END_CASE|REPEAT|UNTIL)\b')


def statements(lines):
    """ST text as statements: lines joined until a `;` or a control keyword, comments removed."""
    text = re.sub(r'\(\*.*?\*\)', ' ', '\n'.join(lines), flags=re.S)
    text = re.sub(r'//[^\n]*', ' ', text)
    out, current = [], []
    for line in text.split('\n'):
        current.append(line.strip())
        if line.rstrip().endswith(';') or CONTROL.match(line):
            out.append(' '.join(current))
            current = []
    if current:
        out.append(' '.join(current))
    return out


def one(declaration):
    os.environ['FRAKTAL_AB_DECLARATION'] = declaration
    sys.path.insert(0, str(T))
    import fraktal_ab_generate as gen
    import fraktal_ab_library as library
    import fraktal_ab_station as station
    from test_fraktal_ab_generate import SEED_38
    app = station.application()
    with tempfile.TemporaryDirectory() as folder:
        seed, out = Path(folder) / 'seed.L5X', Path(folder) / 'app.L5X'
        seed.write_text(SEED_38, encoding='utf-8')
        gen.generate(app, seed, out)
        root = ET.parse(out).getroot()
    unit_aoi = gen.unit_aoi_name(app)
    surfaces = {'Unit': (f'FRK_{app.name}_Unit', gen.unit_context_name(app), unit_aoi, gen.unit_context_members(app)),
                'Chart': (f'FRK_{app.name}_Chart', gen.chart_name(app), unit_aoi, gen.chart_members(app))}
    for m in app.modules:
        mtype = library.type_of(m)
        surfaces[m.name] = (gen.ctx_tag_for(app, m.name), gen.module_context_name(mtype),
                            gen.type_aoi_name(mtype), gen.module_members(m))
    bodies = []  # (routine, aoi or None, kind, lines)
    for program in root.iter('Program'):
        for routine in program.iter('Routine'):
            kind = 'RLL' if routine.get('Type') == 'RLL' else 'ST'
            lines = [t.text or '' for t in routine.iter('Text')] if kind == 'RLL' else [l.text or '' for l in routine.iter('Line')]
            bodies.append((routine.get('Name'), None, kind, lines))
    aoi_params = {}
    for aoi in root.iter('AddOnInstructionDefinition'):
        aoi_params[aoi.get('Name')] = {p.get('Name'): p.get('DataType') for p in aoi.iter('Parameter')}
        for routine in aoi.iter('Routine'):
            kind = 'RLL' if routine.get('Type') == 'RLL' else 'ST'
            lines = [t.text or '' for t in routine.iter('Text')] if kind == 'RLL' else [l.text or '' for l in routine.iter('Line')]
            bodies.append((aoi.get('Name') + '/' + routine.get('Name'), aoi.get('Name'), kind, lines))
    parsed = [(name, aoi, kind, statements(lines) if kind == 'ST' else lines) for name, aoi, kind, lines in bodies]

    def prefixes(surface, aoi):
        tag, dtype, owner, _ = surfaces[surface]
        if aoi is None:
            return [tag]
        return [p for p, t in aoi_params[aoi].items()
                if t == dtype and (surface in ('Unit', 'Chart') or aoi == owner or p == f'Ctx{surface}')]

    hx = json.loads(HX.read_bytes())['privateUnion'].get(declaration, {}).get('facts', {})
    members_out, never_written = {}, []
    for surface, (tag, dtype, owner, members) in surfaces.items():
        for member in members:
            writes, reads, published = collections.Counter(), collections.Counter(), []
            for routine, aoi, kind, units in parsed:
                names = prefixes(surface, aoi)
                if not names:
                    continue
                ref = r'(?<![\w.])(?:' + '|'.join(re.escape(p) for p in names) + r')\.' + re.escape(member.name) + r'(?:\[[^\]]*\])?(?![\w.])'
                pattern = re.compile(ref)
                for unit in units:
                    for hit in pattern.finditer(unit):
                        if kind == 'ST':
                            written = re.match(r'\s*:=', unit[hit.end():]) is not None
                            (writes if written else reads)[routine] += 1
                            if not written and 'Canonical' in routine:
                                assign = re.match(r'\s*(?:(?:IF|ELSIF) .*? THEN |ELSE )?\s*([\w.\[\]]+)\s*:=\s*(.*?);\s*$', unit)
                                if assign and hit.start() >= assign.start(2):
                                    published.append(dict(routine=routine, target=assign.group(1),
                                                          exact=re.fullmatch(ref, assign.group(2).strip()) is not None))
                        else:
                            before = unit[:hit.start()]
                            call = re.search(r'([A-Z]+)\(([^()]*)$', before)
                            op = call.group(1) if call else ''
                            last = op in LD_DEST_LAST and re.match(r'\s*\)', unit[hit.end():]) is not None
                            (writes if op in LD_WRITES or last else reads)[routine] += 1
            own = lambda r: r.startswith(owner + '/')
            ext_w = sorted(r for r in writes if not own(r))
            ext_r = sorted(r for r in reads if not own(r) and 'Canonical' not in r)
            pub_r = sorted(r for r in reads if not own(r) and 'Canonical' in r)
            ow, orr = any(own(r) for r in writes), any(own(r) for r in reads)
            if not writes and not reads:
                klass = 'unused'
            elif ow and ext_w:
                klass = 'shared'
            elif ext_w:
                klass = 'input'
            elif ext_r:
                klass = 'output'
            elif pub_r:
                klass = 'published'
            else:
                klass = 'private'
            if reads and not writes:
                never_written.append(f'{surface}.{member.name}')
            members_out[f'{surface}.{member.name}'] = dict(
                surface=surface, owner=owner, kind=member.kind, dimension=member.dimension,
                classification=klass, ownerWrites=ow, ownerReads=orr,
                externalWriters=ext_w, externalReaders=ext_r, publicationReaders=pub_r,
                published=published, harnesses=hx.get(f'{surface}.{member.name}', []))
    return dict(declaration=declaration, application=app.name, routines=len(bodies),
                neverWritten=never_written, members=members_out)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--declaration')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if args.declaration:
        print(json.dumps(one(args.declaration)))
        return 0
    results = {}
    for declaration in DECLARATIONS:
        done = subprocess.run([sys.executable, __file__, '--declaration', declaration],
                              capture_output=True, text=True, check=True)
        results[declaration] = json.loads(done.stdout.strip().splitlines()[-1])
    summary = {}
    for d, r in results.items():
        by = collections.defaultdict(collections.Counter)
        for m in r['members'].values():
            by[m['surface']][m['classification']] += 1
        summary[d] = dict(total=dict(collections.Counter(m['classification'] for m in r['members'].values())),
                          bySurface={s: dict(c) for s, c in by.items()},
                          withHarnessFacts=sum(1 for m in r['members'].values() if m['harnesses']),
                          exactlyPublished=sum(1 for m in r['members'].values() if any(p['exact'] for p in m['published'])),
                          neverWritten=len(r['neverWritten']))
    with args.output.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(dict(schema='fraktal.ab.s6-collapse-dataflow', schemaVersion=1, summary=summary, results=results),
                  stream, indent=1)
        stream.write('\n')
    print(json.dumps(summary, indent=1))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
