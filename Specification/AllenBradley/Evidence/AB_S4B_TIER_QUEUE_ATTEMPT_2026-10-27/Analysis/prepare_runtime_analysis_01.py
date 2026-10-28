from pathlib import Path
W=Path(__file__).parent;T=Path('C:/work/fraktal-ab-s4b-timing-20261027/offline_01')
old='C:/work/fraktal-ab-s4b-timing-20261027/session_01';new=(W.parent/'session_01').as_posix()
for name in ('inspect_cold_runtime_01.py','replay_pairs_01.py','compare_cold_config_pages_01.py',
 'analyze_cold_task_trace_01.py','peek_runtime_progress_01.py','summarize_runtime_01.py',
 'parse_startup_timing_01.py','analyze_part_reads_01.py','analyze_cip_timing_01.py'):
    source=(T/name).read_text(encoding='utf-8').replace(old,new)
    if name=='summarize_runtime_01.py':
        for before,after in (
          ('call_65010f20595041d78cea54b482b0f09f:0','call_a6801bdef7184d1c95927b1b41c26fde:0'),
          ('Approve guarded S4b desktop timing session','Approve guarded S4b tier/queue retry')):
            assert source.count(before)==1,before
            source=source.replace(before,after)
        before="save('runtime_summary_01.json',summary)";assert source.count(before)==1
        source=source.replace(before,"summary['tierQueueCorrection']=dict(logicalArrayTiers=True,consumedLeavesGovernGroup=True,responseClockStartsAtWorkerReceipt=True,sourceTimestampsUnchanged=True,proofRetryFreshnessLimitsUnchanged=True)\n"+before)
    compile(source,str(W/name),'exec')
    with (W/name).open('x',encoding='utf-8',newline='') as f:f.write(source)
print('Prepared outcome analysis for the corrected tier/queue session; no controller access.')
