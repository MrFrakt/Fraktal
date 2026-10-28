from pathlib import Path
W=Path(__file__).parent
U=Path('C:/work/fraktal-ab-s4b-startup-20261027/offline_01')
old='C:/work/fraktal-ab-s4b-startup-20261027/session_01'
new=(W.parent/'session_01').as_posix()
for name in ('inspect_cold_runtime_01.py','replay_cold_pairs_01.py','compare_cold_config_pages_01.py',
 'analyze_cold_task_trace_01.py','peek_runtime_progress_01.py','summarize_runtime_01.py','parse_startup_timing_01.py'):
    source=(U/name).read_text(encoding='utf-8').replace(old,new)
    if name=='summarize_runtime_01.py':
        for before,after in (
          ('call_7d2226c74b974b268cf6aa63ab8aaae6:0','call_18bf5754fcb54411bfc34409e002243f:0'),
          ('Approve guarded S4b startup diagnostic session','Approve guarded S4b parallel-reader session'),
          ("summary['desktopCoverage']['helperSecondaryError']=desktop_error", "summary['desktopCoverage']['helperSecondaryError']=desktop_error if desktop_error and 'Null check operator' in desktop_error else None")):
            assert source.count(before)==1,before
            source=source.replace(before,after)
        before="save('runtime_summary_01.json',summary)"
        assert source.count(before)==1
        source=source.replace(before,"summary['parallelReader']=dict(connections=4,serialPinned=True,outstandingPerSocket=1,guardedRowLease=True,proofAndFreshnessRulesUnchanged=True)\n"+before)
    compile(source,str(W/name),'exec')
    with (W/name).open('x',encoding='utf-8',newline='') as f:f.write(source)
print('Prepared seven local evidence analysis tools; no controller access or bound-input changes.')
