from pathlib import Path
W=Path(__file__).parent
P=Path('C:/work/fraktal-ab-s4b-pool-20261027/offline_01')
old='C:/work/fraktal-ab-s4b-pool-20261027/session_01'
new=(W.parent/'session_01').as_posix()
for name in ('inspect_cold_runtime_01.py','compare_cold_config_pages_01.py',
 'analyze_cold_task_trace_01.py','peek_runtime_progress_01.py','summarize_runtime_01.py','parse_startup_timing_01.py'):
    source=(P/name).read_text(encoding='utf-8').replace(old,new)
    if name=='summarize_runtime_01.py':
        for before,after in (
          ('call_18bf5754fcb54411bfc34409e002243f:0','call_438cc23f4aa04d9cbddadf9fd71508b4:0'),
          ('Approve guarded S4b parallel-reader session','Approve guarded S4b Part-read diagnostic session')):
            assert source.count(before)==1,before
            source=source.replace(before,after)
        before="save('runtime_summary_01.json',summary)"
        assert source.count(before)==1
        source=source.replace(before,"summary['partReadDiagnostics']=optional('part_read_analysis_01.json')\n"+before)
    compile(source,str(W/name),'exec')
    with (W/name).open('x',encoding='utf-8',newline='') as f:f.write(source)
print('Prepared local evidence analysis tools; no controller access.')
