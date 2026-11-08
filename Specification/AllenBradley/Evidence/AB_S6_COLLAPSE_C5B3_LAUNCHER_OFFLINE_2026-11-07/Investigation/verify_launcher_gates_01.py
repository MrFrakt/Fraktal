"""Offline AST predicate/wait proof, static legacy/MO reachability gate, and L5X/runtime hash-pin proof for C5b3 standalone press launcher."""
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
PARENT = '0730d3feb4ee8877c0e63ad31710a73ad7c11644'

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
    sleeps = []
    for node in ast.walk(tree):
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
            elif ast.unparse(node.func) == 'time.sleep' and node.args:
                sleeps.append({
                    'arg': ast.unparse(node.args[0]),
                    'line': node.lineno,
                })
    checks.sort(key=lambda x: x['line'])
    waits.sort(key=lambda x: x['line'])
    sleeps.sort(key=lambda x: x['line'])
    return checks, waits, sleeps


def block_always_exits(stmts) -> bool:
    if not stmts:
        return False
    last = stmts[-1]
    if isinstance(last, (ast.Return, ast.Raise)):
        return True
    if isinstance(last, ast.Try):
        return block_always_exits(last.body) and (
            not last.handlers or all(block_always_exits(h.body) for h in last.handlers)
        )
    return False


def scan_legacy_and_mo_calls(path: Path):
    source = path.read_text(encoding='utf-8')
    sha = hashlib.sha256(path.read_bytes()).hexdigest().upper()
    tree = ast.parse(source)
    # In fraktal_ab_press_canonical_execute.py, `live` is `fraktal_ab_genealogy_execute` (migrated runner),
    # while `fraktal_ab_live` is `legacy_live`. In tower/part, `live` is `fraktal_ab_live`.
    is_launcher = path.name == 'fraktal_ab_press_canonical_execute.py'
    legacy_prefixes = (
        ('projection.', 'legacy_live.', 'medium.', 'typed.', 'equivalence.', 'candidate.',
         'paired_run', 'px.read_module', 'px.read_layout', 'px.read_unit', 'px.command')
        if is_launcher else
        ('projection.', 'manifest.', 'live.', 'broker.', 'reader.', 'sets.', 'tower.project',
         'px.read_layout')
    )
    legacy_only_functions = {'paired_run'} if is_launcher else set()

    results = []

    def is_pos_collapse_guard(test_src: str) -> bool:
        stripped = test_src.strip()
        if stripped == 'collapsed':
            return True
        return 'canonical_collapse' in stripped and not stripped.startswith('not ')

    def is_neg_collapse_guard(test_src: str) -> bool:
        stripped = test_src.strip()
        if stripped == 'not collapsed':
            return True
        return 'canonical_collapse' in stripped and stripped.startswith('not ')

    def record_calls_in_expr(node, func_name, guarded):
        for sub in ast.walk(node):
            if isinstance(sub, ast.Call):
                call_name = ast.unparse(sub.func)
                if any(call_name == p or call_name.startswith(p) for p in legacy_prefixes):
                    results.append(dict(
                        file=path.name,
                        sha256=sha,
                        line=sub.lineno,
                        function=func_name,
                        call=call_name,
                        guardedLegacyOnly=guarded,
                    ))
            elif isinstance(sub, ast.Name) and sub.id in legacy_only_functions:
                results.append(dict(
                    file=path.name,
                    sha256=sha,
                    line=sub.lineno,
                    function=func_name,
                    call=f'<ref:{sub.id}>',
                    guardedLegacyOnly=guarded,
                ))

    def visit_block(stmts, func_name, guarded_legacy):
        after_collapse_early_return = False
        for stmt in stmts:
            currently_guarded = guarded_legacy or after_collapse_early_return
            if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
                nested_name = stmt.name if func_name == '<module>' else f'{func_name}.{stmt.name}'
                fn_guarded = currently_guarded or (stmt.name in legacy_only_functions)
                visit_block(stmt.body, nested_name, fn_guarded)
                continue
            if isinstance(stmt, ast.ClassDef):
                for item in stmt.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        visit_block(item.body, f'{stmt.name}.{item.name}', False)
                continue
            if isinstance(stmt, ast.If):
                test_src = ast.unparse(stmt.test)
                pos_guard = is_pos_collapse_guard(test_src)
                neg_guard = is_neg_collapse_guard(test_src)
                record_calls_in_expr(stmt.test, func_name, currently_guarded)
                visit_block(stmt.body, func_name, currently_guarded or neg_guard)
                visit_block(stmt.orelse, func_name, currently_guarded or pos_guard)
                if pos_guard and block_always_exits(stmt.body):
                    after_collapse_early_return = True
                continue
            if isinstance(stmt, ast.Try):
                visit_block(stmt.body, func_name, currently_guarded)
                for h in stmt.handlers:
                    visit_block(h.body, func_name, currently_guarded)
                visit_block(stmt.orelse, func_name, currently_guarded)
                visit_block(stmt.finalbody, func_name, currently_guarded)
                continue
            if isinstance(stmt, ast.With):
                visit_block(stmt.body, func_name, currently_guarded)
                continue
            if isinstance(stmt, (ast.For, ast.While)):
                visit_block(stmt.body, func_name, currently_guarded)
                visit_block(stmt.orelse, func_name, currently_guarded)
                continue
            record_calls_in_expr(stmt, func_name, currently_guarded)

    visit_block(tree.body, '<module>', False)
    return results


def main():
    rel = 'FraktalCore/PLC/Allen-Bradley/tools/fraktal_ab_press_canonical_execute.py'
    before_src = git_show(PARENT, rel)
    after_src = (REPO / rel).read_text(encoding='utf-8')
    b_checks, b_waits, b_sleeps = extract_checks_and_waits(before_src)
    a_checks, a_waits, a_sleeps = extract_checks_and_waits(after_src)

    b_msgs = [c['msg'] for c in b_checks]
    a_msgs = [c['msg'] for c in a_checks]
    missing_msgs = [m for m in b_msgs if m not in a_msgs]
    b_wait_keys = [(w['label'], w['timeout']) for w in b_waits]
    a_wait_keys = [(w['label'], w['timeout']) for w in a_waits]
    waits_equal = b_wait_keys == a_wait_keys
    sleeps_equal = [s['arg'] for s in b_sleeps] == [s['arg'] for s in a_sleeps]
    pred_ok = (not missing_msgs) and waits_equal and sleeps_equal

    predicate_report = {
        'parentCommit': PARENT,
        'file': Path(rel).name,
        'beforeCheckCount': len(b_checks),
        'afterCheckCount': len(a_checks),
        'beforeCheckMessages': b_msgs,
        'afterCheckMessages': a_msgs,
        'missingCheckMessages': missing_msgs,
        'beforeWaitCount': len(b_waits),
        'afterWaitCount': len(a_waits),
        'beforeWaits': b_waits,
        'afterWaits': a_waits,
        'waitsIdentical': waits_equal,
        'sleepsIdentical': sleeps_equal,
        'beforeSleeps': b_sleeps,
        'afterSleeps': a_sleeps,
        'passed': pred_ok,
    }
    with (W / 'launcher_predicate_diff_01.json').open('x', encoding='utf-8') as out:
        json.dump(predicate_report, out, indent=2)
    assert pred_ok, f'Predicate diff failed: {predicate_report}'

    migrated_runners = (
        'fraktal_ab_press_canonical_execute.py',
        'fraktal_ab_tower_execute.py',
        'fraktal_ab_part_execute.py',
        'fraktal_ab_genealogy_execute.py',
        'fraktal_ab_resource_execute.py',
        'fraktal_ab_text_resource_execute.py',
    )
    all_calls = []
    for name in migrated_runners:
        all_calls.extend(scan_legacy_and_mo_calls(TOOLS / name))
    unguarded = [c for c in all_calls if not c['guardedLegacyOnly']]
    launcher_calls = [c for c in all_calls if c['file'] == 'fraktal_ab_press_canonical_execute.py']
    inventory_report = {
        'passed': len(unguarded) == 0,
        'migratedRunners': list(migrated_runners),
        'legacyAndMoCallsTotal': len(all_calls),
        'unguardedCollapsedReachable': unguarded,
        'launcherGuardedLegacyAndMoCalls': launcher_calls,
        'allGuardedCalls': all_calls,
        'remainingStationReadingHxModules': [
            'fraktal_ab_press_parity.py',
            'fraktal_ab_phase1_execute.py',
            'fraktal_ab_phase2_execute.py',
            'fraktal_ab_phase3_execute.py',
            'fraktal_ab_phase4_execute.py',
            'fraktal_ab_s3_execute.py',
        ],
        'controllerAccess': False,
    }
    with (W / 'launcher_reachability_01.json').open('x', encoding='utf-8') as out:
        json.dump(inventory_report, out, indent=2)
    assert inventory_report['passed'], f'Unguarded legacy/MO calls: {unguarded}'

    l5x_dir = W / 'generated_l5x_01'
    l5x_dir.mkdir(exist_ok=False)
    l5x_hashes = {}
    for decl_name, expected_sha in EXPECTED_L5X.items():
        out_path = l5x_dir / f'{decl_name}.L5X'
        cmd = [sys.executable, str(TOOLS / 'fraktal_ab_generate.py'),
               'C:/work/echo38_5580_seed.L5X', str(out_path),
               '--declaration', decl_name]
        subprocess.run(cmd, cwd=TOOLS, check=True, capture_output=True, text=True)
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
    sources = c5b2['sources']
    assert len(sources) == 84, f'Expected 84 shipping sources, got {len(sources)}'
    source_mismatches = []
    for rel_src, expected_sha in sorted(sources.items()):
        actual = hashlib.sha256((REPO / rel_src).read_bytes()).hexdigest().upper()
        if actual != expected_sha.upper():
            source_mismatches.append({'file': rel_src, 'expected': expected_sha, 'actual': actual})
    exe_checks = {}
    for key in ('gateway', 'hostAdapter'):
        info = c5b2[key]
        exe_path = Path(info['path'])
        actual = hashlib.sha256(exe_path.read_bytes()).hexdigest().upper()
        exe_checks[key] = {
            'path': str(exe_path),
            'expectedSha256': info['sha256'].upper(),
            'actualSha256': actual,
            'matches': actual == info['sha256'].upper(),
        }
        assert exe_checks[key]['matches'], f'Runtime binary changed: {key}'

    pins_report = {
        'passed': not source_mismatches and all(v['byteIdentical'] for v in l5x_hashes.values()),
        'l5xProfiles': l5x_hashes,
        'c5b2Reference': str(c5b2_bindings_path.relative_to(REPO).as_posix()),
        'shippingSourceCount': len(sources),
        'shippingSourceMismatches': source_mismatches,
        'preparedExecutables': exe_checks,
        'controllerAccess': False,
    }
    with (W / 'l5x_and_runtime_pins_01.json').open('x', encoding='utf-8') as out:
        json.dump(pins_report, out, indent=2)
    assert pins_report['passed'], f'Pins check failed: {pins_report}'
    print(json.dumps({
        'passed': True,
        'beforeChecks': len(b_checks),
        'afterChecks': len(a_checks),
        'waits': len(a_waits),
        'unguardedCalls': len(unguarded),
        'l5xProfiles': len(l5x_hashes),
        'shippingSources': len(sources),
    }))


if __name__ == '__main__':
    main()
