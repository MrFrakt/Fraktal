from pathlib import Path
W=Path(__file__).parent
source=(W/'status_authorization_checks_01.py').read_text(encoding='utf-8')
for before,after in (('cli_refusal_01','cli_refusal_02'),('missing_approval_cli_cold_01','missing_approval_cli_cold_02'),
 ('missing_approval_sdk_cold_01','missing_approval_sdk_cold_02'),('status_authorization_checks_01.json','status_authorization_checks_02.json')):
    assert source.count(before)>=1,before
    source=source.replace(before,after)
exec(compile(source,str(W/'status_authorization_checks_01.py'),'exec'),{'__file__':__file__})
