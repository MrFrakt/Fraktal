from pathlib import Path
W=Path(__file__).parent
M=Path('C:/work/fraktal-ab-s4b-status-20261027/offline_01')
text=(M/'status_runtime_report_01.txt').read_text(encoding='utf-8')
for before,after in (
    ('S4b Status-order qualification','S4b desktop startup diagnostic qualification'),
    ('AB_S4B_STATUS_ORDER_PREPARATION_2026-10-27.md','AB_S4B_STARTUP_DIAGNOSTIC_PREPARATION_2026-10-27.md'),
    ('sealed Status-order package','sealed startup diagnostic package'),
    ('Approve guarded S4b Status-order retry','Approve guarded S4b startup diagnostic session'),
    ('call_e167e16df752449e8bbb27e2ef44e6b7:0','call_7d2226c74b974b268cf6aa63ab8aaae6:0')):
    assert text.count(before)==1,before
    text=text.replace(before,after)
before='## TASK and desktop evidence'
assert text.count(before)==1
text=text.replace(before,"""## Measured refusal timing

The only shipping-code addition is a refusal diagnostic. Accepted source ages,
freshness limits, row proofs, retries and write policy are unchanged. The helper
retains the primary startup exception/stack before using app state.

Repository timing analysis: `{json.dumps(q.get('desktopFreshnessDiagnostics'),ensure_ascii=False)}`.
The numeric reconciliation uses source + transit = received age, then received
age + local processing = effective age. It checks the server-processing
subtraction and the unchanged Good boundary. A source already over its limit,
a crossing at receipt and a crossing during local processing are distinguished
only when measured fields support that conclusion. Missing observations are
not inferred. This arithmetic does not isolate a code routine or host cause.
The [transport contract](../../OPCUA_TRANSPORT.md) requires conservative complete
acquisition age; no timestamp is renewed to obtain a LIVE result.

## TASK and desktop evidence""")
with (W/'startup_runtime_report_01.txt').open('x',encoding='utf-8',newline='') as f:f.write(text)
source=(M/'seal_runtime_01.py').read_text(encoding='utf-8')
for before,after in (
    ('AB_S4B_STATUS_ORDER_{kind}_{stamp}','AB_S4B_STARTUP_DIAGNOSTIC_{kind}_{stamp}'),
    ('AB_S4B_STATUS_ORDER_PREPARATION_2026-10-27/manifest.json','AB_S4B_STARTUP_DIAGNOSTIC_PREPARATION_2026-10-27/manifest.json'),
    ('a136bd8ede6f87ec9f1b63eb61e7ad4ef4ccca9644fe0c9c0a59d28cb3276ee6','a2e966ee642f47052c35b144f58b3bb809aa8234ddf389592cb01d7843fbfd58'),
    ('call_e167e16df752449e8bbb27e2ef44e6b7:0','call_7d2226c74b974b268cf6aa63ab8aaae6:0'),
    ('authorize_status_retry_01.py','authorize_startup_session_01.py'),
    ('status_runtime_report_01.txt','startup_runtime_report_01.txt'),
    ('fraktal.ab.s4b-status-order-runtime','fraktal.ab.s4b-startup-diagnostic-runtime')):
    assert source.count(before)>=1,before
    source=source.replace(before,after)
before='"\'seal_runtime_01.py\',\'startup_runtime_report_01.txt\',"'
after='"\'seal_runtime_01.py\',\'startup_runtime_report_01.txt\',\'parse_startup_timing_01.py\',\'prepare_runtime_seal_01.py\',"'
assert source.count(before)==1
source=source.replace(before,after)
with (W/'seal_runtime_01.py').open('x',encoding='utf-8',newline='') as f:f.write(source)
print('Prepared outcome-derived startup diagnostic report and append-only sealer.')
