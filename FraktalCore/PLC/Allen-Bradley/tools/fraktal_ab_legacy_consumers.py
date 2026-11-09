"""S6 syntax census and migration classification; never imports PLC tooling.

The original read-reference census is retained for comparison. Classification
also covers the plan's explicit retirement owners and their importers: a pure
migration oracle may contain no legacy read itself and still has to retire.
This is an engineering inventory, not controller or retirement acceptance.
"""
from __future__ import annotations

import argparse
import ast
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re


SCHEMA = 'fraktal.ab.s6-consumer-classification'
RUNTIME = frozenset(('fraktal_ab_projection', 'fraktal_ab_projection_replay',
                     'fraktal_ab_gateway', 'fraktal_ab_mailbox_probe'))
ORACLES = frozenset(('fraktal_ab_canonical_equivalence',
                     'fraktal_ab_canonical_observation',
                     'fraktal_ab_paired_observation', 'fraktal_ab_mailbox_frame'))
GENERATORS = frozenset(('fraktal_ab_generate', 'fraktal_ab_resources'))
ADAPTERS = frozenset(('fraktal_ab_host_events', 'fraktal_ab_sets',
                     'fraktal_ab_set_broker', 'fraktal_ab_medium'))
ORACLE_NAME = re.compile(
    r'fraktal_ab_(?:press_)?s\d+[a-z]?_'
    r'(?:equivalence|reference|fixture_execute|revision_execute|lifetime_execute|io_execute)\Z')
EXTERNAL_RUNTIME = (
    'FraktalCore/PLC/Allen-Bradley/tools/requirements-gateway.txt',
    'FraktalCore/HMI/test/live_ab_gateway_test.dart',
    'FraktalCore/HMI/test/live_ab_command_test.dart',
)
ACTIONS = {
    'RT': ('WP6.7', 'retire-runtime'),
    'MO': ('WP6.3/WP6.7', 'final-replay-then-retire'),
    'GN': ('WP6.6', 'collapse-storage'),
    'AD': ('WP6.5', 'rehome-host-service'),
    'HX': ('WP6.2', 'migrate-canonical-reads'),
    'UT': ('WP6.6', 'review-canonical-structure-assertions'),
    'HL': ('WP6.2/WP6.6', 'replace-legacy-dependency'),
}


def _legacy_name(name):
    return name in ('read_unit', 'read_layout') or name.endswith('_context_members')


def inspect_source(path, root):
    if path.is_symlink() or not path.resolve().is_relative_to(root.resolve()):
        raise ValueError('source must be a regular file within the repository')
    source = path.read_bytes()
    tree = ast.parse(source.decode('utf-8-sig'), filename=str(path))
    imports, calls, definitions, dynamic = [], [], [], []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            imports.extend(dict(module=node.module, name=a.name, line=node.lineno)
                           for a in node.names)
        elif isinstance(node, ast.Import):
            imports.extend(dict(module=a.name, name=None, line=node.lineno)
                           for a in node.names)
        elif isinstance(node, ast.Call):
            name = (node.func.id if isinstance(node.func, ast.Name) else
                    node.func.attr if isinstance(node.func, ast.Attribute) else '')
            if _legacy_name(name):
                calls.append(dict(name=name, line=node.lineno))
            if name in ('import_module', '__import__'):
                dynamic.append(dict(line=node.lineno,
                    literal=(node.args[0].value if node.args and
                             isinstance(node.args[0], ast.Constant) and
                             isinstance(node.args[0].value, str) else None)))
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and _legacy_name(node.name):
            definitions.append(dict(name=node.name, line=node.lineno))
    references = [r for r in imports if r['module'] == 'fraktal_ab_projection'
                  or _legacy_name(r['name'] or '')]
    return dict(path=path.relative_to(root).as_posix(), module=path.stem,
                sha256=hashlib.sha256(source).hexdigest().upper(),
                kind='test' if path.name.startswith('test_') else 'tool',
                imports=imports, legacyImports=references, legacyCalls=calls,
                legacyDefinitions=definitions, dynamicImports=dynamic)


def _retirement_role(name):
    owner = name.removeprefix('test_')
    if owner in RUNTIME:
        return 'RT'
    if owner in ORACLES or ORACLE_NAME.fullmatch(owner):
        return 'MO'
    return None


def _closure(seeds, imports):
    result = set(seeds)
    while True:
        additions = {name for name, dependencies in imports.items()
                     if dependencies & result} - result
        if not additions:
            return result
        result.update(additions)


def classify(name, kind, *, affected):
    """Plan WP6.1 first-match roles. Tests of generators/adapters remain UT."""
    if kind not in ('tool', 'test') or (kind == 'test') != name.startswith('test_'):
        raise ValueError('unknown or inconsistent module kind')
    retired = _retirement_role(name)
    if retired:
        return retired
    if name in GENERATORS:
        return 'GN'
    if name in ADAPTERS:
        return 'AD'
    if kind == 'tool' and (name.endswith('_execute') or
                          name == 'fraktal_ab_press_parity' or
                          name.startswith('fraktal_ab_s9_')):
        return 'HX'
    if not affected:
        return None
    if kind == 'test' and name.startswith('test_fraktal_ab_'):
        return 'UT'
    if kind == 'tool' and name.startswith('fraktal_ab_'):
        return 'HL'
    raise ValueError('unclassified affected module: ' + name)


def inventory(root):
    root = Path(root).resolve()
    tools = root / 'FraktalCore/PLC/Allen-Bradley/tools'
    rows = [inspect_source(p, root) for p in sorted(tools.glob('*.py'))]
    if not rows:
        raise ValueError('no AB Python modules found')
    names = {r['module'] for r in rows}
    imports = {r['module']: {i['module'] for i in r['imports']} & names for r in rows}
    users = {name: {n for n, deps in imports.items() if name in deps} for name in names}
    direct = {r['module'] for r in rows if r['legacyImports'] or r['legacyCalls']}
    dependent = _closure(direct, imports)
    explicit = {r['module'] for r in rows if
                classify(r['module'], r['kind'], affected=False) is not None}
    affected = _closure(direct | explicit, imports)
    classes = {r['module']: classify(r['module'], r['kind'], affected=r['module'] in affected)
               for r in rows}
    # Only proven exclusive helper bundles follow retired owners. A helper with
    # no importers may be a CLI entry point, so absence of edges never retires it.
    follow = {}
    while True:
        added = {}
        for name in sorted(affected):
            if classes[name] != 'HL' or name in follow:
                continue
            bundle = {name, 'test_' + name} & names
            consumers = set().union(*(users[n] for n in bundle)) - bundle
            roles = {follow.get(n, classes[n]) for n in consumers}
            if consumers and roles <= {'RT', 'MO'}:
                added[name] = 'MO' if 'MO' in roles else 'RT'
                if 'test_' + name in bundle:
                    added['test_' + name] = added[name]
        if not added:
            break
        follow.update(added)
    classified, unaffected = [], []
    for row in rows:
        name = row['module']
        if name not in affected:
            unaffected.append(row)
            continue
        role = classes[name]
        if role not in ACTIONS:
            raise ValueError('unclassified affected module: ' + name)
        effective = follow.get(name, role)
        stage, action = ACTIONS[effective]
        if role == 'HX' and name not in dependent:
            # Standalone ABI/memory probes have no legacy station read to
            # replace. Their fixture-specific byte/identity checks must stay.
            action = 'verify-canonical-or-standalone-probe'
        classified.append(dict(**row, classification=role, effectiveClassification=effective,
            helperFollows=follow.get(name), stage=stage, action=action,
            directLegacyReference=name in direct, legacyImportDependent=name in dependent,
            importedBy=sorted(users[name]), localImports=sorted(imports[name])))
    external = []
    rt_present = any(r['module'] in RUNTIME for r in rows)
    for name in EXTERNAL_RUNTIME:
        path = root / name
        if not path.is_file() or path.is_symlink():
            if rt_present:
                raise ValueError('planned retirement artifact missing: ' + name)
            continue
        external.append(dict(path=name, classification='RT', action=ACTIONS['RT'][1],
                             stage=ACTIONS['RT'][0], sha256=hashlib.sha256(path.read_bytes()).hexdigest().upper()))
    return dict(schema=SCHEMA, schemaVersion=1, rules='canonical-plan-WP6.1',
        readOnly=True, controllerAccess=False, retirementAcceptance=False,
        utc=datetime.now(timezone.utc).isoformat(),
        summary=dict(scanned=len(rows), directLegacyReferences=len(direct),
            directByKind=dict(Counter(r['kind'] for r in rows if r['module'] in direct)),
            legacyImportDependents=len(dependent), classifiedPythonModules=len(classified),
            explicitNonPythonArtifacts=len(external), unaffectedPythonModules=len(unaffected),
            byClass=dict(sorted(Counter(r['classification'] for r in classified).items())),
            byEffectiveClass=dict(sorted(Counter(r['effectiveClassification'] for r in classified).items())),
            unclassified=0),
        limitations=['Syntax references include test doubles; role is not a claim of a live read.',
            'Dynamic imports and external CLI callers require review; they are listed, not executed.',
            'Transitive-only helpers/tests follow changed owners and need not have a direct read to replace.',
            'Retirement still requires the final replay and a fresh import census before deletion.'],
        consumers=classified, externalArtifacts=external, unaffected=unaffected)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[4])
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    if args.output.exists():
        parser.error('new classification output required')
    result = inventory(args.root)
    with args.output.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    print(json.dumps(result['summary']))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
