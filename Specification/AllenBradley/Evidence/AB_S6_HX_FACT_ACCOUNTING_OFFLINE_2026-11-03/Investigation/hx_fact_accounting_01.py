"""Account for the legacy context facts every HX harness reads (read-only analysis).

WP6.6 R8 deletes the Unit, chart and module contexts. O10 moves the private
facts that acceptance harnesses assert into one acceptance-only structure.
That needs the exact private set per S6-Q declaration.

Two stages:

1. ``--copy-layer DECL`` (run once per declaration, in its own process because
   station selection is process state): generate DECL's canonical cyclic ST
   and classify EVERY Unit/chart/module context member by the assignments
   that read it. A bare copy into a published leaf is ``exact``. A published
   ``<leaf> := <member> <> 0`` is ``zero-nonzero``, valid only where the harness
   compares that fact with zero. Anything else is ``private``.
2. Default: scan each HX module the S6 census classifies
   ``migrate-canonical-reads``. Each key subscripted (``["X"]``, ``['X']``,
   ``.get('X')``) that names a context member is a strong use. Any other
   string literal naming one, for example a key tuple iterated into a
   subscript, is a weak use to review. Uses are matched to every surface that
   declares the name, so an ambiguous name is reported rather than guessed.

Reads of other legacy structures through ``read_layout`` are listed, not
classified. Contacts no controller; writes only its output file.
"""
import argparse
import ast
import json
import os
from pathlib import Path
import re
import subprocess
import sys

R = Path(__file__).resolve().parents[5]
T = R / 'FraktalCore/PLC/Allen-Bradley/tools'
CENSUS = R / 'Specification/AllenBradley/AB_S6_CONSUMER_CLASSIFICATION_2026-11-02_03.json'
DECLARATIONS = ('fraktal_ab_genealogy_s4b_owner_demo', 'fraktal_ab_press_canonical_echo38')


def copy_layer(declaration):
    os.environ['FRAKTAL_AB_DECLARATION'] = declaration
    sys.path.insert(0, str(T))
    import fraktal_ab_canonical_publication as publication
    import fraktal_ab_generate as gen
    import fraktal_ab_station as station
    app = station.application()
    surfaces = {'Unit': (f'FRK_{app.name}_Unit', gen.unit_context_members(app)),
                'Chart': (f'FRK_{app.name}_Chart', gen.chart_members(app))}
    surfaces.update({m.name: (gen.ctx_tag_for(app, m.name), gen.module_members(m))
                     for m in app.modules})
    lines = publication.cyclic(app)
    assign = re.compile(r'^\s*([A-Za-z_][\w.\[\]]*)\s*:=\s*(.+?);\s*$')
    published = re.compile(rf'^{re.escape(app.name)}\.')
    result = {}
    for surface, (tag, members) in surfaces.items():
        for member in members:
            source = f'{tag}.{member.name}'
            token = re.compile(re.escape(source) + r'(?!\w)')
            exact, zero = [], []
            for line in lines:
                match = assign.match(line) if token.search(line) else None
                if not match or not published.match(match.group(1)):
                    continue
                if match.group(2).strip() == source:
                    exact.append(match.group(1).replace('.', '/'))
                elif match.group(2).strip() == source + ' <> 0':
                    zero.append(match.group(1).replace('.', '/'))
            kind = 'exact' if exact else 'zero-nonzero' if zero else 'private'
            result[f'{surface}.{member.name}'] = dict(classification=kind, canonical=exact or zero)
    return dict(declaration=declaration, application=app.name,
                stage=app.canonical_publication_stage, cyclicLines=len(lines), members=result)


def literals(tree):
    strong, weak, layouts = set(), set(), []
    for node in ast.walk(tree):
        if isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Constant) \
                and isinstance(node.slice.value, str):
            strong.add(node.slice.value)
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) \
                and node.func.attr == 'get' and node.args and isinstance(node.args[0], ast.Constant) \
                and isinstance(node.args[0].value, str):
            strong.add(node.args[0].value)
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            weak.add(node.value)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) \
                and node.func.attr == 'read_layout' and len(node.args) >= 2:
            layouts.append(ast.unparse(node.args[1]))
    return strong, weak - strong, layouts


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--copy-layer')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if args.copy_layer:
        print(json.dumps(copy_layer(args.copy_layer)))
        return
    layers = {}
    for declaration in DECLARATIONS:
        reply = subprocess.run([sys.executable, __file__, '--copy-layer', declaration],
                               capture_output=True, text=True, check=True)
        layers[declaration] = json.loads(reply.stdout.strip().splitlines()[-1])
    census = json.loads(CENSUS.read_text(encoding='utf-8'))
    harnesses = [c for c in census['consumers'] if c['effectiveClassification'] == 'HX'
                 and c['action'] == 'migrate-canonical-reads']
    names = {}
    for layer in layers.values():
        for key in layer['members']:
            surface, member = key.split('.', 1)
            names.setdefault(member, set()).add(surface)
    rows, union = [], {d: {} for d in DECLARATIONS}
    for consumer in sorted(harnesses, key=lambda c: c['module']):
        path = R / consumer['path']
        tree = ast.parse(path.read_text(encoding='utf-8'))
        strong, weak, layouts = literals(tree)
        facts = []
        for strength, keys in (('subscript', strong), ('literal', weak)):
            for member in sorted(keys & names.keys()):
                per = {}
                for declaration, layer in layers.items():
                    found = {s: layer['members'][f'{s}.{member}'] for s in sorted(names[member])
                             if f'{s}.{member}' in layer['members']}
                    per[declaration] = found
                    if strength == 'subscript':
                        for surface, entry in found.items():
                            if entry['classification'] != 'exact':
                                union[declaration].setdefault(f'{surface}.{member}', set()).add(
                                    consumer['module'])
                facts.append(dict(member=member, use=strength, surfaces=sorted(names[member]),
                                  declarations=per))
        exact_only = all(entry['classification'] == 'exact'
                         for fact in facts if fact['use'] == 'subscript'
                         for found in fact['declarations'].values() for entry in found.values())
        rows.append(dict(module=consumer['module'], sha256=consumer['sha256'],
                         directLegacyReference=consumer['directLegacyReference'],
                         subscriptFacts=sum(f['use'] == 'subscript' for f in facts),
                         literalOnlyFacts=sum(f['use'] == 'literal' for f in facts),
                         onlyExactSubscriptFacts=exact_only, otherReadLayout=sorted(set(layouts)),
                         facts=facts))
    summary = {d: dict(nonExactSubscriptedFacts=len(u),
                       facts={k: sorted(v) for k, v in sorted(u.items())}) for d, u in union.items()}
    described = {}
    for declaration, layer in layers.items():
        described[declaration] = {k: v for k, v in layer.items() if k != 'members'}
        described[declaration]['counts'] = {
            c: sum(m['classification'] == c for m in layer['members'].values())
            for c in ('exact', 'zero-nonzero', 'private')}
    result = dict(schema='fraktal.ab.s6-hx-fact-accounting', schemaVersion=1,
                  census=CENSUS.relative_to(R).as_posix(), copyLayers=described,
                  harnesses=rows, privateUnion=summary,
                  note='Static inventory. A literal-only use needs review; "private" means no '
                       'canonical copy, not proof that no equivalent published fact exists. '
                       'A zero-nonzero equivalent holds only where the harness compares with zero.')
    with args.output.open('x', encoding='utf-8') as f:
        json.dump(result, f, indent=2)
    print(json.dumps({r['module']: [r['subscriptFacts'], r['literalOnlyFacts'],
                                    r['onlyExactSubscriptFacts']] for r in rows}, indent=1))
    print(json.dumps({d: s['nonExactSubscriptedFacts'] for d, s in summary.items()}))


if __name__ == '__main__':
    main()
