"""Prepare local-only outcome analysis without touching frozen session inputs."""
from pathlib import Path

W=Path(__file__).parent
A=Path('C:/work/fraktal-ab-s4b-array-tiers-20261027/offline_01')
old_session=A.parent/'session_01'
session=W.parent/'session_01'
for name in ('inspect_cold_runtime_01.py','replay_pairs_01.py','compare_cold_config_pages_01.py',
    'analyze_cold_task_trace_01.py','peek_runtime_progress_01.py','summarize_runtime_01.py',
    'parse_startup_timing_01.py','analyze_part_reads_01.py','analyze_cip_timing_01.py'):
    source=(A/name).read_text(encoding='utf-8').replace(old_session.as_posix(),session.as_posix())
    if name=='summarize_runtime_01.py':
        old="save('runtime_summary_01.json',summary)"
        assert source.count(old)==1
        source=source.replace(old,"""busy=optional('login_busy_replay_01.json') or {}
summary['loginBusyWitness']=busy
summary['nativeAccepted']=bool(summary['nativeAccepted'] and busy.get('passed') is True)
save('runtime_summary_01.json',summary)""")
        source=source.replace('call_a6801bdef7184d1c95927b1b41c26fde:0','call_2cc806825e344c5686ae76e262dae694:0')
        source=source.replace('Approve guarded S4b tier/queue retry','Approve guarded S4b busy-witness retry')
    with (W/name).open('x',encoding='utf-8',newline='') as f:f.write(source)
print('Prepared nine local-only analyses; no controller access or frozen-input changes.')
