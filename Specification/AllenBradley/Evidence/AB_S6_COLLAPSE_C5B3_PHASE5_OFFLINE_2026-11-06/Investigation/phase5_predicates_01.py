"""Verify all 21 Phase 5 row-site predicates and all wait lambdas are preserved after acquisition/key normalization."""
from pathlib import Path
import ast, copy, json, subprocess

R = Path('C:/Users/SoftIndVM/Fraktal')
W = Path(__file__).parent
PATH = 'FraktalCore/PLC/Allen-Bradley/tools/fraktal_ab_phase5_execute.py'

class Normalize(ast.NodeTransformer):
    def visit_Call(self, node):
        node = self.generic_visit(node)
        func = ast.unparse(node.func)
        if func == 'key':
            return ast.Call(func=ast.Name(id='published_key', ctx=ast.Load()), args=[node.args[-1]], keywords=[])
        if func == 'values.get' and len(node.args) == 1 and ast.unparse(node.args[0]) == "f'{ROOT}/RunStyle'":
            return ast.Name(id='run_style', ctx=ast.Load())
        return node

def collect(raw):
    tree = ast.parse(raw)
    rows = {}
    waits = []
    legacy_calls = []
    for func in [n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]:
        for node in ast.walk(func):
            if not isinstance(node, ast.Call):
                continue
            called = ast.unparse(node.func)
            if called == 'px.read_layout' or (called.startswith('projection.') and func.name != 'timed_oee_card'):
                legacy_calls.append(dict(function=func.name, line=node.lineno, call=ast.unparse(node)))
            if called == 'px.row':
                label = ast.unparse(node.args[0])
                assert label not in rows, label
                norm = ast.dump(Normalize().visit(copy.deepcopy(node.args[-1])), include_attributes=False)
                rows[label] = dict(
                    function=func.name,
                    label=label,
                    expectation=ast.unparse(node.args[1]),
                    predicate=norm,
                    source=ast.unparse(node.args[-1]),
                )
            elif called in ('px.await_unit', 'px.await_module'):
                idx = 2 if called == 'px.await_module' else 1
                lam = node.args[idx]
                waits.append(dict(
                    function=func.name,
                    kind=called,
                    predicate=ast.dump(lam, include_attributes=False),
                    source=ast.unparse(lam),
                ))
    return rows, waits, legacy_calls

before_raw = subprocess.check_output(['git', 'show', '7b793c516:' + PATH], cwd=R).decode()
after_raw = (R / PATH).read_text(encoding='utf-8')
before_rows, before_waits, before_legacy = collect(before_raw)
after_rows, after_waits, after_legacy = collect(after_raw)

assert len(before_rows) == 21 and set(before_rows) == set(after_rows)
assert before_waits == after_waits
assert not after_legacy, after_legacy

row_diffs = [
    dict(label=k, before=before_rows[k]['source'], after=after_rows[k]['source'])
    for k in before_rows
    if before_rows[k]['predicate'] != after_rows[k]['predicate']
    or before_rows[k]['expectation'] != after_rows[k]['expectation']
]
assert not row_diffs, row_diffs

result = dict(
    schema='fraktal.ab.c5b3-phase5-predicate-proof',
    schemaVersion=1,
    passed=True,
    parentCommit='7b793c516bc48bb50ae5b2337e99b8ab63e001bd',
    path=PATH,
    rowCount=len(after_rows),
    waitCount=len(after_waits),
    directLegacyCallsBefore=len(before_legacy),
    unconditionalLegacyCallsAfter=len(after_legacy),
    normalization='Only deployed key lookup key(comm, ...) and the run_style variable alias for values.get(f"{ROOT}/RunStyle"); all 21 row expectations, logical operators, value comparisons, tolerances and all 16 wait predicates are identical.',
    rows=[dict(label=k, function=after_rows[k]['function'], before=before_rows[k]['source'], after=after_rows[k]['source']) for k in before_rows],
    controllerAccess=False,
)
with (W / 'phase5_predicates_01.json').open('x', encoding='utf-8') as out:
    json.dump(result, out, indent=2)
print(json.dumps(dict(passed=True, rows=len(after_rows), waits=len(after_waits), legacyAfter=len(after_legacy))))
