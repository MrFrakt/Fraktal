"""Account for every legacy fact the press harness reads (read-only analysis).

1. Every subscript of a declared Unit/chart/module layout member in
   fraktal_ab_press_execute.py must appear in FACTS below (completeness check).
2. The selected declaration's canonical cyclic ST (the copy layer WP6.6 R8
   removes) is generated, and each fact is classified by the assignments that
   read it: a bare copy into a canonical leaf, an expression, or none.

Imports the generator but contacts no controller and writes only its output.
"""
from pathlib import Path
import json, os, re, sys

T = Path(sys.argv[1]).resolve()
out = Path(sys.argv[2])
sys.path.insert(0, str(T))
os.environ['FRAKTAL_AB_DECLARATION'] = 'fraktal_ab_press_canonical_echo38'
import fraktal_ab_canonical_publication as publication  # noqa: E402
import fraktal_ab_generate as gen  # noqa: E402
import fraktal_ab_station as station  # noqa: E402

app = station.application()
# (surface, member) -> (how the harness uses it, harness rows)
FACTS = {
    ('Unit', 'SchemaVersion'): ('compared', ['fingerprint']),
    ('Unit', 'Par_TaskPeriodMs'): ('compared', ['fingerprint']),
    ('Unit', 'CycleCount'): ('compared', ['1']),
    ('Unit', 'Error'): ('zero/nonzero', ['1', '2', '3', '4', '5', '6', '7', '8', '9', '11', '14']),
    ('Unit', 'Aborted'): ('zero/nonzero', ['1', '13']),
    ('Unit', 'OrderFail'): ('compared', ['1']),
    ('Unit', 'Step'): ('compared', ['2', '3', '4', '5', '6', '9', '12', '14']),
    ('Unit', 'ReportedCount'): ('compared', ['2', '6']),
    ('Unit', 'ReportedReason'): ('compared', ['2', '6']),
    ('Unit', 'ReportedSource'): ('compared', ['2']),
    ('Unit', 'StartLatched'): ('zero/nonzero', ['3']),
    ('Unit', 'ErrorID'): ('compared', ['4']),
    ('Unit', 'ErrorSource'): ('compared', ['4']),
    ('Unit', 'Running'): ('zero/nonzero', ['4', '5', '11', '13', 'home']),
    ('Unit', 'DecisionId'): ('compared', ['7', '9']),
    ('Unit', 'ScrapCount'): ('compared', ['8', '9']),
    ('Unit', 'Complete'): ('zero/nonzero', ['11', 'home']),
    ('Unit', 'Mode'): ('compared', ['12']),
    ('Unit', 'ModeSwitches'): ('compared', ['12']),
    ('Chart', 'Visited'): ('counted', ['1 observed', '15']),
    ('Chart', 'StallReason'): ('compared', ['4', '6 observed', '7', '14']),
    ('Chart', 'LastMs'): ('counted', ['15']),
    ('Chart', 'StepCursor'): ('observed only', ['15']),
    ('TwoHand', 'OutImm_Armed'): ('zero/nonzero', ['two_hand_press']),
    ('PartSlide', 'ErrorID'): ('observed only', ['4']),
    ('PartSlide', 'OutImm_ExecState'): ('observed only', ['4']),
    ('PartSlide', 'Execute'): ('zero/nonzero', ['4']),
    ('Door', 'RunCount'): ('observed only', ['10']),
    ('Door', 'DoneCount'): ('compared', ['10']),
    ('Door', 'Execute'): ('zero/nonzero', ['10']),
    ('Door', 'ManualCmd'): ('zero/nonzero', ['10']),
    ('Door', 'OutImm_Pos'): ('compared', ['10']),
    ('Door', 'Error'): ('zero/nonzero', ['10']),
}
SCALARS = ['FRK_{0}_ScanCount', 'FRK_{0}_TaskPeriodMs', 'FRK_{0}_OrderFail', '{1}Tag.SchemaVersion']

source = (T / 'fraktal_ab_press_execute.py').read_text(encoding='utf-8')
layouts = {'Unit': gen.unit_context_members(app), 'Chart': gen.chart_members(app)}
layouts.update({m.name: gen.module_members(m) for m in app.modules})
names = {member.name for layout in layouts.values() for member in layout}
used = set(re.findall(r'\["([A-Za-z_]\w*)"\]', source)) & names
missing = sorted(used - {member for unused, member in FACTS})
assert not missing, f'harness reads unaccounted layout members: {missing}'
for (surface, member) in FACTS:
    assert member in {m.name for m in layouts[surface]}, (surface, member)

lines = publication.cyclic(app)
assign = re.compile(r'^\s*([A-Za-z_][\w.\[\]]*)\s*:=\s*(.+?);\s*$')
published = re.compile(rf'^{re.escape(app.name)}\.')
rows = []
for (surface, member), (use, harness_rows) in FACTS.items():
    tag = f'FRK_{app.name}_{surface}' if surface in ('Unit', 'Chart') else gen.ctx_tag_for(app, surface)
    token = re.compile(re.escape(f'{tag}.{member}') + r'(?!\w)')
    copies, expressions, conditions = [], [], 0
    for line in lines:
        if not token.search(line):
            continue
        match = assign.match(line)
        if match and match.group(2).strip() == f'{tag}.{member}':
            copies.append(match.group(1))
        elif match:
            expressions.append(f'{match.group(1)} := {match.group(2).strip()}')
        else:
            conditions += 1
    canonical = [c.replace('.', '/') for c in copies if published.match(c)]
    if canonical:
        kind = 'exact canonical copy'
    elif use == 'zero/nonzero' and any(e.startswith(f'{app.name}.') and e.endswith(f'{tag}.{member} <> 0')
                                       for e in expressions):
        kind = 'canonical zero/nonzero equivalent'
        canonical = [e.split(' := ')[0].replace('.', '/') for e in expressions
                     if e.endswith(f'{tag}.{member} <> 0') and published.match(e)]
    else:
        kind = 'no canonical copy'
    rows.append(dict(surface=surface, member=member, harnessUse=use, harnessRows=harness_rows,
                     classification=kind, canonicalPaths=canonical, privateCopies=[
                         c for c in copies if not published.match(c)],
                     expressionCount=len(expressions), conditionLines=conditions))
counts = {}
for row in rows:
    counts[row['classification']] = counts.get(row['classification'], 0) + 1
result = dict(schema='fraktal.ab.s6-press-fact-accounting', schemaVersion=1,
              declaration=os.environ['FRAKTAL_AB_DECLARATION'], application=app.name,
              canonicalPublicationStage=app.canonical_publication_stage, cyclicLines=len(lines),
              harness='fraktal_ab_press_execute.py', layoutMembersSubscripted=sorted(used),
              counts=counts, facts=rows,
              separateScalars=[s.format(app.name, app.records[0].name) for s in SCALARS],
              note='A copy-layer inventory: "no canonical copy" is not proof that no '
                   'semantically equivalent published fact exists.')
with out.open('x', encoding='utf-8') as f:
    json.dump(result, f, indent=2)
print(json.dumps(counts))
