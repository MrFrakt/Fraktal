"""Reuse the sealed preparation pattern for the client-only lookup correction."""
from pathlib import Path

W = Path(__file__).parent
source = (W / 'prepare_root_diagnostic_01.py').read_text(encoding='utf-8')
replacements = {
    "OLD = W.parent / 'retry_template_01'": "OLD = W.parent / 'retry_root_diagnostic_01'",
    "D = W.parent / 'retry_root_diagnostic_01'": "D = W.parent / 'retry_lookup_01'",
    "\"D=W.parent/'retry_root_diagnostic_01'\"": "\"D=W.parent/'retry_lookup_01'\"",
    'missing_approval_cli_root_diagnostic_01': 'missing_approval_cli_lookup_01',
    'missing_approval_sdk_root_diagnostic_01': 'missing_approval_sdk_lookup_01',
    'root_diagnostic_authorization_checks_01.json': 'lookup_authorization_checks_01.json',
    "W / 'root_diagnostic_authorization_checks.py'": "W / 'lookup_authorization_checks.py'",
    'productionSourcesUnchanged=True': 'productionSourcesUnchanged=False',
}
for before, after in replacements.items():
    assert source.count(before) == 1, before
    source = source.replace(before, after)
exec(compile(source, str(W / 'prepare_root_diagnostic_01.py'), 'exec'), {'__file__': __file__})
