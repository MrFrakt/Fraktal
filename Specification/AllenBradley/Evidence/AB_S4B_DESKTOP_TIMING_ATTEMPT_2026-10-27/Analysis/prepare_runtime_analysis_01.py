from pathlib import Path
W=Path(__file__).parent
Q=Path('C:/work/fraktal-ab-s4b-partdiag-20261027/offline_01')
old='C:/work/fraktal-ab-s4b-partdiag-20261027/session_01'
new=(W.parent/'session_01').as_posix()
for name in ('inspect_cold_runtime_01.py','replay_pairs_01.py','compare_cold_config_pages_01.py',
 'analyze_cold_task_trace_01.py','peek_runtime_progress_01.py','summarize_runtime_01.py',
 'parse_startup_timing_01.py','analyze_part_reads_01.py'):
    source=(Q/name).read_text(encoding='utf-8').replace(old,new)
    if name=='summarize_runtime_01.py':
        for before,after in (
          ('call_438cc23f4aa04d9cbddadf9fd71508b4:0','call_65010f20595041d78cea54b482b0f09f:0'),
          ('Approve guarded S4b Part-read diagnostic session','Approve guarded S4b desktop timing session')):
            assert source.count(before)==1,before
            source=source.replace(before,after)
        before="save('runtime_summary_01.json',summary)";assert source.count(before)==1
        source=source.replace(before,"summary['cipPhaseTiming']=optional('cip_timing_analysis_01.json')\n"+before)
    if name=='parse_startup_timing_01.py':
        before="row['responseProcessingMs']=None"
        assert source.count(before)==1
        source=source.replace(before,"""for key in ('snapshotAwaitUs','serviceDecodeUs','validationUs'):
            if key in fields:row[key]=int(fields[key])
        row['responseProcessingMs']=None""")
    compile(source,str(W/name),'exec')
    with (W/name).open('x',encoding='utf-8',newline='') as f:f.write(source)
print('Prepared local outcome analysis; no controller access or bound-input changes.')
