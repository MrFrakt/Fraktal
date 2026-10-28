from pathlib import Path

W = Path(__file__).parent
source = (W / 'prepare_root_diagnostic_01.py').read_text(encoding='utf-8')
for before, after in {
    "\nD = W.parent / 'retry_root_diagnostic_01'": "\nD = W.parent / 'retry_freshness_01'",
    "\nOLD = W.parent / 'retry_template_01'": "\nOLD = W.parent / 'retry_coherence_01'",
    "\"D=W.parent/'retry_root_diagnostic_01'\"": "\"D=W.parent/'retry_freshness_01'\"",
    'missing_approval_cli_root_diagnostic_01': 'missing_approval_cli_freshness_01',
    'missing_approval_sdk_root_diagnostic_01': 'missing_approval_sdk_freshness_01',
    'root_diagnostic_authorization_checks_01.json': 'freshness_authorization_checks_01.json',
    "W / 'root_diagnostic_authorization_checks.py'": "W / 'freshness_authorization_checks.py'",
    'productionSourcesUnchanged=True': 'productionSourcesUnchanged=False',
}.items():
    assert source.count(before) == 1, before
    source = source.replace(before, after)
exec(compile(source, str(W / 'prepare_root_diagnostic_01.py'), 'exec'), {'__file__': __file__})
