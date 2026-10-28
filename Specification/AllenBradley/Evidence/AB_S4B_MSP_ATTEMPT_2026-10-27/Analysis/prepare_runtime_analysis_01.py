"""Prepare local-only analysis of the approved body-only packet session."""
from pathlib import Path
W=Path(__file__).parent
C=Path('C:/work/fraktal-ab-s4b-refill-20261027/offline_01')
old_session=C.parent/'session_01';session=W.parent/'session_01'
for name in ('inspect_cold_runtime_01.py','replay_pairs_01.py','compare_cold_config_pages_01.py',
    'analyze_cold_task_trace_01.py','peek_runtime_progress_01.py','summarize_runtime_01.py',
    'parse_startup_timing_01.py','analyze_part_reads_01.py','analyze_cip_timing_01.py','replay_login_busy_01.py'):
    source=(C/name).read_text(encoding='utf-8').replace(old_session.as_posix(),session.as_posix())
    if name=='summarize_runtime_01.py':
        for before,after in (
            ('call_a03c1071e32641f687cf1970bb701ef9:0','call_2e3b8f619b2a46728c4e2e0627acc9c2:0'),
            ('Approve guarded S4b row-refill retry','Approve guarded S4b body-packet qualification')):
            assert source.count(before)==1,before
            source=source.replace(before,after)
        before="save('runtime_summary_01.json',summary)"
        assert source.count(before)==1
        source=source.replace(before,"""summary['bodyPacketReader']=dict(bodyOnly=True,separateCompletedCounters=True,
    intraPacketOrderAssumed=False,sourceAgesProofRetriesFreshnessUnchanged=True,
    fourSerialPinnedConnections=True,oneOutstandingPerSocket=True,writeVectorsUnchanged=True)
save('runtime_summary_01.json',summary)""")
    with (W/name).open('x',encoding='utf-8',newline='') as f:f.write(source)
print('Prepared ten local-only analyses; no controller access or frozen-input changes.')
