from pathlib import Path
W=Path(__file__).parent
M=Path('C:/work/fraktal-ab-s4b-status-20261027/offline_01')
old='C:/work/fraktal-ab-s4b-status-20261027/session_01'
new=(W.parent/'session_01').as_posix()
for name in ('inspect_cold_runtime_01.py','replay_cold_pairs_01.py','compare_cold_config_pages_01.py',
    'analyze_cold_task_trace_01.py','peek_runtime_progress_01.py','summarize_runtime_01.py'):
    source=(M/name).read_text(encoding='utf-8').replace(old,new)
    if name=='summarize_runtime_01.py':
        for before,after in (('call_e167e16df752449e8bbb27e2ef44e6b7:0','call_7d2226c74b974b268cf6aa63ab8aaae6:0'),
            ('Approve guarded S4b Status-order retry','Approve guarded S4b startup diagnostic session')):
            assert source.count(before)==1,before
            source=source.replace(before,after)
        before="save('runtime_summary_01.json',summary)"
        assert source.count(before)==1
        source=source.replace(before,"summary['desktopFreshnessDiagnostics']=optional('desktop_freshness_analysis_01.json')\n"+before)
    with (W/name).open('x',encoding='utf-8',newline='') as f:f.write(source)
print('Prepared six local evidence analysis tools; no controller access.')
