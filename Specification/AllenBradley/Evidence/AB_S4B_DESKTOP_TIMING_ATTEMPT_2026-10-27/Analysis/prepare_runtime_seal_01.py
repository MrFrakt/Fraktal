from pathlib import Path
W=Path(__file__).parent
Q=Path('C:/work/fraktal-ab-s4b-partdiag-20261027/offline_01')
source=(Q/'seal_runtime_01.py').read_text(encoding='utf-8')
for before,after,count in (
 ('actual parallel-reader outcome','actual desktop timing outcome',1),
 ('S4b legacy Part-read diagnostic qualification','S4b desktop phase-timing qualification',1),
 ('AB_S4B_PART_READ_DIAGNOSTIC_{kind}_{stamp}','AB_S4B_DESKTOP_TIMING_{kind}_{stamp}',1),
 ('AB_S4B_PART_READ_DIAGNOSTIC_PREPARATION_2026-10-27','AB_S4B_DESKTOP_TIMING_PREPARATION_2026-10-27',2),
 ('674b92e475449c9d4156c9bd8d0c848ef337f249c35ee64e25b635754461e98b','fed4a614842da063744c56dfa37c9bf029f84b716ba08265faa18f3a6ab4c03f',1),
 ('Approve guarded S4b Part-read diagnostic session','Approve guarded S4b desktop timing session',1),
 ('call_438cc23f4aa04d9cbddadf9fd71508b4:0','call_65010f20595041d78cea54b482b0f09f:0',2),
 ('authorize_partdiag_session_01.py','authorize_timing_session_01.py',1),
 ('authorize_partdiag_session_01.log','authorize_timing_session_01.log',1),
 ('authorize_partdiag_session_01_exit.json','authorize_timing_session_01_exit.json',1),
 ('fraktal.ab.s4b-part-read-diagnostic-runtime','fraktal.ab.s4b-desktop-timing-runtime',1)):
    assert source.count(before)==count,(before,source.count(before))
    source=source.replace(before,after)
before='## Actual results\n';assert source.count(before)==1
source=source.replace(before,"""## Worker and frontend timing evidence

Qualification launchers enable `fraktal.cip.trace=true`; normal builds keep
worker tracing disabled. Completed snapshots record worker queue, manifest/
progress checks, acquisition, projection, age selection, path expansion,
assembly/trace preparation and SendPort delivery. The eight slowest guarded
groups retain paths, quality, attempts and elapsed times, without PLC values.
The existing frontend rejection log separates snapshot wait, service decoding
and validation from later local work. The original response age bracket and
age arithmetic remain in their original positions. No reads, snapshot values,
proofs, retries, deadlines, freshness limits or write policy change.

Recorded stream/phase summary:
`{json.dumps({{name:{{'snapshots':data['snapshots'],'deliveries':data['deliveries'],'phases':data['phases']}} for name,data in (q.get('cipPhaseTiming') or {{}}).get('streams',{{}}).items()}},ensure_ascii=False)}`.
Only measured intervals are summarized. They include instrumentation and
scheduling. Missing phase rows are not inferred successful, and a particular
host, network or PLC cause is not inferred from these aggregates. Slowest and
first snapshot rows are retained in `cip_timing_analysis_01.json`; the complete
observer/desktop stdout retains every recorded phase row.

## Actual results
""".replace('{{','{').replace('}}','}'))
start=source.index('The preparation adds six session-only tracing tests and transfers unchanged')
end=source.index('Runtime execution changes no shipping source.',start)
source=source[:start]+"""The preparation binds **660 HMI tests passed /12 skipped**, 40 trace-enabled
focused tests, analyzer, Windows build and enforced lockfile, using Flutter
**3.47.5 /Dart 3.13.4** and the identical 318-input mirror. Three existing HMI
source/test files add diagnostics. Six unchanged session-only Part trace tests
pass. All **373 PLC/gate bindings** remain unchanged: **2,339 AB tests**, both
v38 build/read-back/access/SDK gates, 15 byte-identical prior images and exact
65% Capacity transfer by hashes. **74 root tests** and spec/contracts/strict
consistency/whitespace pass. """+source[end:]
before="'prepare_runtime_seal_01.py','parse_startup_timing_01.py','analyze_part_reads_01.py'"
assert source.count(before)==1
source=source.replace(before,"'prepare_runtime_seal_01.py','parse_startup_timing_01.py','analyze_cip_timing_01.py','analyze_part_reads_01.py'")
compile(source,str(W/'seal_runtime_01.py'),'exec')
with (W/'seal_runtime_01.py').open('x',encoding='utf-8',newline='') as f:f.write(source)
print('Prepared outcome-derived timing report/sealer; no controller access.')
