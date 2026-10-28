"""Read-only syntax census for the pre-S6 migration review, not acceptance."""
from pathlib import Path
from collections import Counter
import ast
import datetime
import hashlib
import json

W = Path(__file__).parent
R = Path('C:/Users/SoftIndVM/Fraktal')
T = R / 'FraktalCore/PLC/Allen-Bradley/tools'
bindings = json.loads((W.parent / 'retry_reader_01/source_bindings.json').read_bytes())['sha256']
rows = []
modules = {}
for path in sorted(T.glob('*.py')):
    source = path.read_bytes()
    digest = hashlib.sha256(source).hexdigest()
    assert digest.upper() == bindings[path.as_posix()].upper(), path
    tree = ast.parse(source.decode('utf-8-sig'), filename=str(path))
    imports, uses, definitions = [], [], []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            for alias in node.names:
                imports.append(dict(module=node.module, name=alias.name,
                    alias=alias.asname, line=node.lineno))
        elif isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(dict(module=alias.name, name=None,
                    alias=alias.asname, line=node.lineno))
        elif isinstance(node, ast.Call):
            name = node.func.id if isinstance(node.func, ast.Name) else (
                node.func.attr if isinstance(node.func, ast.Attribute) else '')
            if name in ('read_unit', 'read_layout') or name.endswith('_context_members'):
                uses.append(dict(name=name, line=node.lineno))
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and (
            node.name in ('read_unit', 'read_layout') or node.name.endswith('_context_members')):
            definitions.append(dict(name=node.name, line=node.lineno))
    references = [entry for entry in imports if entry['module'] == 'fraktal_ab_projection'
        or entry['name'] in ('read_unit', 'read_layout')
        or (entry['name'] or '').endswith('_context_members')]
    observation = [entry for entry in imports if entry['module'] == 'fraktal_ab_canonical_observation']
    frame = [entry for entry in imports if entry['module'] in ('fraktal_ab_mailbox_frame',
        'fraktal_ab_s3h_equivalence', 'fraktal_ab_press_s3k_equivalence')]
    row = dict(path=path.relative_to(R).as_posix(), module=path.stem, sha256=digest,
        kind='test' if path.name.startswith('test_') else 'tool',
        imports=imports, legacyImports=references, legacyCalls=uses,
        legacyDefinitions=definitions, observationImports=observation,
        migrationFrameRelatedImports=frame)
    rows.append(row)
    modules[path.stem] = row

direct = {row['module'] for row in rows if row['legacyImports'] or row['legacyCalls']}
dependent = set(direct)
while True:
    additions = {row['module'] for row in rows if any(
        entry['module'] in dependent for entry in row['imports'])} - dependent
    if not additions:
        break
    dependent.update(additions)
summary = dict(scanned=len(rows), directLegacyReferences=dict(Counter(
    row['kind'] for row in rows if row['module'] in direct)),
    transitiveDependents=dict(Counter(row['kind'] for row in rows if row['module'] in dependent)),
    legacyDefinitionOwners=[row['path'] for row in rows if row['legacyDefinitions']],
    observationImporters=[row['path'] for row in rows if row['observationImports']])
result = dict(schema='fraktal.ab.pre-s6-static-consumer-census', schemaVersion=1,
    readOnly=True, controllerAccess=False, sourceBindingsMatched=True,
    utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    acceptance=False, summary=summary,
    limitations=['Static Python syntax only; string/dynamic imports and external callers need review.',
        'Direct calls can include canonical or test doubles; classify owners before migration.',
        'Transitive import dependence does not prove a live controller read.',
        'No source edits, migration, deletion or retirement acceptance is claimed.'],
    directLegacyModules=sorted(direct), transitiveLegacyModules=sorted(dependent), files=rows)
with (W / 'legacy_consumer_inventory_01.json').open('x', encoding='utf-8') as stream:
    json.dump(result, stream, indent=2)
    stream.write('\n')
print(json.dumps(summary))
