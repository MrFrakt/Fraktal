from pathlib import Path
W=Path(__file__).parent
source=(W/'cold_authorization_checks_01.py').read_text(encoding='utf-8')
for before,after in {
    "'missing_approval_cli_cold_01'":"'missing_approval_cli_cold_02'",
    "'missing_approval_sdk_cold_01'":"'missing_approval_sdk_cold_02'",
}.items():
    assert source.count(before)==1,before
    source=source.replace(before,after)
exec(compile(source,str(W/'cold_authorization_checks_01.py'),'exec'),{'__file__':__file__})
