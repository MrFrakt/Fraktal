from pathlib import Path
W=Path(__file__).parent
P=Path('C:/work/fraktal-ab-s4b-pool-20261027/offline_01')
source=(P/'seal_runtime_01.py').read_text(encoding='utf-8')
for before,after,count in (
 ('S4b parallel read-only reader qualification','S4b legacy Part-read diagnostic qualification',1),
 ('AB_S4B_PARALLEL_READER_{kind}_{stamp}','AB_S4B_PART_READ_DIAGNOSTIC_{kind}_{stamp}',1),
 ('AB_S4B_PARALLEL_READER_PREPARATION_2026-10-27','AB_S4B_PART_READ_DIAGNOSTIC_PREPARATION_2026-10-27',2),
 ('7fa998b5ca54355799157a9e658bc07e3ed3e83b8b32f286fab9a73d2e815ade','674b92e475449c9d4156c9bd8d0c848ef337f249c35ee64e25b635754461e98b',1),
 ('Approve guarded S4b parallel-reader session','Approve guarded S4b Part-read diagnostic session',1),
 ('call_18bf5754fcb54411bfc34409e002243f:0','call_438cc23f4aa04d9cbddadf9fd71508b4:0',2),
 ('authorize_parallel_session_01.py','authorize_partdiag_session_01.py',1),
 ('authorize_parallel_session_01.log','authorize_partdiag_session_01.log',1),
 ('authorize_parallel_session_01_exit.json','authorize_partdiag_session_01_exit.json',1),
 ('replay_cold_pairs_01.py','replay_pairs_01.py',1),
 ('fraktal.ab.s4b-parallel-reader-runtime','fraktal.ab.s4b-part-read-diagnostic-runtime',1)):
    assert source.count(before)==count,(before,source.count(before))
    source=source.replace(before,after)
before='## Actual results\n'
assert source.count(before)==1
source=source.replace(before,"""## Session-only Part-read diagnostic

The original legacy Part reader, its requests, three-attempt default, projection
and even-revision acceptance rule are unchanged. The session wraps its Read
calls only to retain schema/revision words, before/body/after phase, attempt and
timing. No Part payload/UID or PIN is recorded. It forwards requests exactly
once and preserves the original return value or refusal. The original function
is restored on context exit. Trace work adds overhead; recorded timings include
that work. No new PLC reads/writes, retry or acceptance rule is introduced.

Diagnostic summary: `{json.dumps({{k:v for k,v in (q.get('partReadDiagnostics') or {{}}).items() if k!='rows'}},ensure_ascii=False)}`.
Only actually recorded header equality/parity and timing are classified. Missing
headers, payload integrity, contention or a particular host/publisher cause are
not inferred. A successful diagnostic acquisition is not proof of why an earlier
unrecorded acquisition refused. Raw JSONL and the independent analysis are
archived. The preparation's six tracing tests preserve original call counts,
arguments, attempt budget, exact return/error and payload exclusion.

## Actual results
""".replace('{{','{').replace('}}','}'))
before="'parallel_runtime_report_01.txt','prepare_runtime_seal_01.py','parse_startup_timing_01.py',"
assert source.count(before)==1
source=source.replace(before,"'prepare_runtime_seal_01.py','parse_startup_timing_01.py','analyze_part_reads_01.py','part_read_diagnostics.py','test_part_read_diagnostics.py',")
before='The preparation binds **660 HMI tests passed /12 skipped**, analyzer, Windows'
assert source.count(before)==1
source=source.replace(before,'The preparation adds six session-only tracing tests and transfers unchanged\nshipping inputs: **660 HMI tests passed /12 skipped**, analyzer, Windows')
compile(source,str(W/'seal_runtime_01.py'),'exec')
with (W/'seal_runtime_01.py').open('x',encoding='utf-8',newline='') as f:f.write(source)
print('Prepared outcome-derived Part-read diagnostic sealer; no controller access.')
