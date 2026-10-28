from pathlib import Path
W=Path(__file__).parent
source=(W/'seal_runtime_01.py').read_text(encoding='utf-8')
before='## Actual results\n'
assert source.count(before)==1
source=source.replace(before,"""## Actual results

**The fixture stopped after 25/41 cases**: 15 main, two Access and eight
configuration/set-store cases. The SFC adopted-fault record then raised
`part snapshot changed during every bounded read` from the legacy Part reader.
All 53 completed paired captures independently replay with exact values/types;
this is partial proof and does not satisfy the 87-pair/full-fixture gate.
The unchanged original replay gate first refused incomplete fixture counts;
separate partial analysis retains that refusal and reports the actual subset.
The first partial-count analysis also refused an incorrect assumption that
Access/config checks had not run; the corrected analysis counts all 25 cases.

The original three-attempt Part proof remains enforced. The failed run did not
record its before/body/after counter values or per-read timings, so the failure
does not isolate contention, counter changes or a publisher defect. Desktop,
independent page comparison, idle/generic acquisition and final timing were
not reached. No complete S4b acceptance or controlled performance comparison
with earlier, longer workloads is inferred from the shorter observer run.
""")
before="'parallel_runtime_report_01.txt','prepare_runtime_seal_01.py','parse_startup_timing_01.py',"
assert source.count(before)==1
source=source.replace(before,"'parallel_runtime_report_01.txt','prepare_runtime_seal_01.py','parse_startup_timing_01.py',\n    'summarize_partial_runtime_02.py','replay_partial_pairs_02.py','replay_partial_pairs_03.py','prepare_partial_runtime_seal_02.py',")
compile(source,str(W/'seal_partial_runtime_02.py'),'exec')
with (W/'seal_partial_runtime_02.py').open('x',encoding='utf-8',newline='') as f:f.write(source)
print('Prepared partial-scope sealer; original 41-case/87-pair acceptance unchanged.')
