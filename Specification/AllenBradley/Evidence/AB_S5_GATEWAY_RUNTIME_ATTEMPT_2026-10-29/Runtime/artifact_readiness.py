"""Derive static SDK read dependencies and fail before any controller call."""
from pathlib import Path
import hashlib,json,re

def validate(directory):
    directory=Path(directory)
    source=(directory/'session/Program.cs').read_text()
    names=set(re.findall(r'File\.ReadAllText\(Path\.Combine\(root,\s*"([^"]+)"\)\)',source))
    # These are products of this session, verified by the SDK after backup /
    # download has begun. Every other read dependency is an offline input.
    names-= {'backup.sha256','deploy_attempt.json'}
    names.update(['host_cpu_monitor.ps1','task_monitor.py','session_ready.py',
        'scripts/guard_echo.py','scripts/preflight.py','gateway_stage.py','commission_candidate.py',
        'cleanup_owned_session.py','session_ownership.py','readonly_stages.py',
        'p5_configuration_comparison.py','configuration_comparison.py','candidate_equivalence.py',
        'ensure_manual_baseline.py','ensure_manual_candidate.py','pre_restore_guard.py',
        'restore_original_medium.py','audit_access.py','measure_timing.py',
        'gateway_fixture.json','dart_package_config.json','gateway_package_hashes.json'])
    assert 'canonical_prepared_compare.json' in names,'SDK input inventory changed'
    missing=sorted(name for name in names if not (directory/name).is_file())
    if missing:raise ValueError('missing offline SDK inputs: '+', '.join(missing))
    comparison=json.loads((directory/'canonical_prepared_compare.json').read_bytes())
    if comparison.get('Equivalent') is not True:raise ValueError('prepared readback is not equivalent')
    first=Path(comparison['Inventory']['First'])
    second=Path(comparison['Inventory']['Second'])
    digest=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest().upper()
    if digest(first)!=digest(directory/'s5_canonical.L5X') or digest(second)!=digest(directory/'prepared_readback.L5X'):
        raise ValueError('readback comparison does not bind these inputs')
    return dict(passed=True,controllerAccess=False,staticSdkInputs=sorted(names))
