"""Offline AST predicate/bound proof, static legacy-call reachability gate, and L5X/runtime hash-pin proof for C5b3 runner slice."""
from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
import subprocess
import sys

W = Path(__file__).parent
REPO = Path('C:/Users/SoftIndVM/Fraktal')
TOOLS = REPO / 'FraktalCore/PLC/Allen-Bradley/tools'
PARENT = '6865e75fd4e224bd917c9874acc4dfd58d23d84f'

EXPECTED_L5X = {
    'fraktal_ab_genealogy_s6_collapse_demo': '57FDB0BC88CF1D8E6F3D5F325B51F61DFD5C110CE5C795A6BE9871B26F5042FE',
    'fraktal_ab_press_s6_collapse_echo38': '0E3E19A822B781EDEFCC38259DDA6F533D94624E66A68415DB20174DAD3AF7A0',
    'fraktal_ab_press_s6_shelving_echo38': 'D7FB6960255F48EDC9FF9288A625A903BE8A93BF2CE26D71353C0AA34D6A131D',
}


def git_show(commit: str, rel_posix: str) -> str:
    res = subprocess.run(['git', 'show', f'{commit}:{rel_posix}'],
                         cwd=REPO, capture_output=True, text=True, check=True)
    return res.stdout


def extract_checks_and_waits(source: str):
    tree = ast.parse(source)
    checks = []
    waits = []
    assigns = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            if isinstance(node.value, ast.Constant):
                assigns[node.targets[0].id] = node.value.value
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr == 'check' and len(node.args) >= 2:
                checks.append({
                    'cond': ast.unparse(node.args[0]),
                    'msg': ast.unparse(node.args[1]),
                    'line': node.lineno,
                })
            elif node.func.attr == 'wait' and len(node.args) >= 2:
                kw = {k.arg: ast.unparse(k.value) for k in node.keywords if k.arg}
                waits.append({
                    'pred': ast.unparse(node.args[0]),
                    'label': ast.unparse(node.args[1]),
                    'timeout': kw.get('timeout', 'default'),
                    'line': node.lineno,
                })
    return checks, waits, assigns


def scan_legacy_calls(path: Path):
    source = path.read_text(encoding='utf-8')
    sha = hashlib.sha256(path.read_bytes()).hexdigest().upper()
    tree = ast.parse(source)
    legacy_prefixes = ('projection.', 'manifest.', 'live.', 'broker.', 'reader.', 'sets.', 'tower.project', 'px.read_layout')

    results = []

    def visit_block(stmts, func_name, guarded_legacy):
        after_collapse_early_return = False
        for stmt in stmts:
            currently_guarded = guarded_legacy or after_collapse_early_return
            if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
                visit_block(stmt.body, stmt.name, False)
                continue
            if isinstance(stmt, ast.ClassDef):
                for item in stmt.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        visit_block(item.body, f'{stmt.name}.{item.name}', False)
                continue
            if isinstance(stmt, ast.If):
                test_src = ast.unparse(stmt.test)
                is_pos_collapse = 'canonical_collapse' in test_src and not test_src.lstrip().startswith('not ')
                is_neg_collapse = 'canonical_collapse' in test_src and test_src.lstrip().startswith('not ')
                # Inspect test expression itself
                for sub in ast.walk(stmt.test):
                    if isinstance(sub, ast.Call):
                        call_name = ast.unparse(sub.func)
                        if any(call_name == p or call_name.startswith(p) for p in legacy_prefixes):
                            results.append(dict(file=path.name, sha256=sha, line=sub.lineno,
                                                function=func_name, call=call_name,
                                                guardedLegacyOnly=currently_guarded))
                visit_block(stmt.body, func_name, currently_guarded or is_neg_collapse)
                visit_block(stmt.orelse, func_name, currently_guarded or is_pos_collapse)
                if is_pos_collapse and stmt.body and isinstance(stmt.body[-1], (ast.Return, ast.Raise)):
                    after_collapse_early_return = True
                continue
            if isinstance(stmt, (ast.Try,)):
                visit_block(stmt.body, func_name, currently_guarded)
                for h in stmt.handlers:
                    visit_block(h.body, func_name, currently_guarded)
                visit_block(stmt.orelse, func_name, currently_guarded)
                visit_block(stmt.finalbody, func_name, currently_guarded)
                continue
            if isinstance(stmt, (ast.With, ast.For, ast.While)):
                visit_block(stmt.body, func_name, currently_guarded)
                visit_block(stmt.orelse, func_name, currently_guarded)
                continue
            for sub in ast.walk(stmt):
                if isinstance(sub, ast.Call):
                    call_name = ast.unparse(sub.func)
                    if any(call_name == p or call_name.startswith(p) for p in legacy_prefixes):
                        results.append(dict(file=path.name, sha256=sha, line=sub.lineno,
                                            function=func_name, call=call_name,
                                            guardedLegacyOnly=currently_guarded))

    visit_block(tree.body, '<module>', False)
    return results


def main():
    # 1. Predicate & disconnect-bound verification
    targets = (
        'FraktalCore/PLC/Allen-Bradley/tools/fraktal_ab_tower_execute.py',
        'FraktalCore/PLC/Allen-Bradley/tools/fraktal_ab_part_execute.py',
        'FraktalCore/PLC/Allen-Bradley/tools/fraktal_ab_genealogy_execute.py',
    )
    predicate_report = {'parentCommit': PARENT, 'files': {}, 'passed': True}
    for rel in targets:
        before_src = git_show(PARENT, rel)
        after_src = (REPO / rel).read_text(encoding='utf-8')
        b_checks, b_waits, b_assigns = extract_checks_and_waits(before_src)
        a_checks, a_waits, a_assigns = extract_checks_and_waits(after_src)
        b_msgs = [c['msg'] for c in b_checks]
        a_msgs = [c['msg'] for c in a_checks]
        # Every parent check message must still be present!
        missing_msgs = [m for m in b_msgs if m not in a_msgs]
        b_wait_keys = [(w['label'], w['timeout']) for w in b_waits]
        a_wait_keys = [(w['label'], w['timeout']) for w in a_waits]
        waits_equal = (b_wait_keys == a_wait_keys)
        file_ok = (not missing_msgs) and waits_equal
        extra = {}
        if rel.endswith('fraktal_ab_tower_execute.py'):
            disconnected_ok = a_assigns.get('disconnected') == 3.2
            expiry_checks = [c for c in a_checks if 'elapsed < 4.0' in c['cond'] and "not expired['SignalTower/TestActive']" in c['cond']]
            expiry_ok = len(expiry_checks) == 1
            file_ok = file_ok and disconnected_ok and expiry_ok
            extra = {
                'disconnectedSeconds': a_assigns.get('disconnected'),
                'disconnectedPreserved': disconnected_ok,
                'expiryDeadlineCheck': expiry_checks,
                'expiryPreserved': expiry_ok,
            }
        predicate_report['files'][Path(rel).name] = {
            'beforeCheckCount': len(b_checks),
            'afterCheckCount': len(a_checks),
            'missingCheckMessages': missing_msgs,
            'beforeWaitCount': len(b_waits),
            'afterWaitCount': len(a_waits),
            'waitsIdentical': waits_equal,
            **extra,
            'passed': file_ok,
        }
        if not file_ok:
            predicate_report['passed'] = False

    with (W / 'predicate_diff_01.json').open('x', encoding='utf-8') as out:
        json.dump(predicate_report, out, indent=2)
    assert predicate_report['passed'], f'Predicate diff failed: {predicate_report}'

    # 2. Static legacy-call reachability inventory
    migrated_runners = (
        'fraktal_ab_tower_execute.py',
        'fraktal_ab_part_execute.py',
        'fraktal_ab_genealogy_execute.py',
        'fraktal_ab_resource_execute.py',
        'fraktal_ab_text_resource_execute.py',
    )
    migrated_calls = []
    for name in migrated_runners:
        migrated_calls.extend(scan_legacy_calls(TOOLS / name))
    unguarded_migrated = [c for c in migrated_calls if not c['guardedLegacyOnly']]
    remaining_launcher = scan_legacy_calls(TOOLS / 'fraktal_ab_press_canonical_execute.py')
    inventory_report = {
        'passed': len(unguarded_migrated) == 0,
        'migratedRunners': list(migrated_runners),
        'migratedLegacyCallsTotal': len(migrated_calls),
        'migratedUnguardedCollapsedReachable': unguarded_migrated,
        'migratedRetainedLegacyBranchCalls': migrated_calls,
        'remainingStandaloneLauncherCalls': remaining_launcher,
        'controllerAccess': False,
    }
    with (W / 'runner_inventory_01.json').open('x', encoding='utf-8') as out:
        json.dump(inventory_report, out, indent=2)
    assert inventory_report['passed'], f'Unguarded legacy calls in migrated runners: {unguarded_migrated}'

    # 3. Byte-identical L5X generation & C5b2 runtime/Dart hash-pin check
    l5x_dir = W / 'generated_l5x'
    l5x_dir.mkdir(exist_ok=False)
    l5x_hashes = {}
    for decl_name, expected_sha in EXPECTED_L5X.items():
        out_path = l5x_dir / f'{decl_name}.L5X'
        cmd = [sys.executable, str(TOOLS / 'fraktal_ab_generate.py'),
               '--seed', 'C:/work/echo38_5580_seed.L5X',
               '--output', str(out_path)]
        env = dict(**__import__('os').environ, FRAKTAL_AB_DECLARATION=decl_name)
        subprocess.run(cmd, cwd=TOOLS, env=env, check=True, capture_output=True, text=True)
        actual_sha = hashlib.sha256(out_path.read_bytes()).hexdigest().upper()
        l5x_hashes[decl_name] = {
            'expectedSha256': expected_sha,
            'actualSha256': actual_sha,
            'byteIdentical': actual_sha == expected_sha,
            'bytes': out_path.stat().st_size,
        }
        assert actual_sha == expected_sha, f'L5X hash mismatch on {decl_name}: {actual_sha} != {expected_sha}'

    c5b2_bindings_path = REPO / 'Specification/AllenBradley/Evidence/AB_S6_COLLAPSE_C5B2_OFFLINE_2026-11-06/Gates/runtime_bindings_01.json'
    c5b2 = json.loads(c5b2_bindings_path.read_text(encoding='utf-8'))
    source_mismatches = []
    for rel, expected_sha in c5b2.get('shippingSources', {}).items():
        actual = hashlib.sha256((REPO / rel).read_bytes()).hexdigest().upper()
        if actual != expected_sha.upper():
            source_mismatches.append({'file': rel, 'expected': expected_sha, 'actual': actual})
    exe_checks = {}
    for key in ('gateway', 'hostAdapter'):
        info = c5b2.get(key, {})
        exe_path = Path(info['path']) if 'path' in info else None
        if exe_path and exe_path.exists():
            actual = hashlib.sha256(exe_path.read_bytes()).hexdigest().upper()
            exe_checks[key] = {'path': str(exe_path), 'expectedSha256': info['sha256'].upper(),
                               'actualSha256': actual, 'matches': actual == info['sha256'].upper()}
            assert exe_checks[key]['matches'], f'Runtime binary changed: {key}'

    pins_report = {
        'passed': not source_mismatches and all(v['byteIdentical'] for v in l5x_hashes.values()),
        'l5xProfiles': l5x_hashes,
        'c5b2Reference': str(c5b2_bindings_path.relative_to(REPO).as_posix()),
        'shippingSourceCount': len(c5b2.get('shippingSources', {})),
        'shippingSourceMismatches': source_mismatches,
        'preparedExecutables': exe_checks,
        'controllerAccess': False,
    }
    with (W / 'l5x_and_runtime_pins_01.json').open('x', encoding='utf-8') as out:
        json.dump(pins_report, out, indent=2)
    assert pins_report['passed'], f'Pins check failed: {pins_report}'
    print(json.dumps({'passed': True, 'l5xProfiles': len(l5x_hashes), 'migratedRunners': len(migrated_runners)}))


if __name__ == '__main__':
    main()
