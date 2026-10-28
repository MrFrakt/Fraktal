from pathlib import Path
W=Path(__file__).parent
OLD=Path('C:/work/fraktal-ab-s4b-20261025/offline_01')
S=W.parent/'session_01'
jobs=[
 ('inspect_cold_runtime_01.py','inspect_lookup_runtime_01.py',"D = W.parent / 'retry_lookup_01'"),
 ('replay_cold_pairs_01.py','replay_lookup_pairs_01.py',"D = Path('C:/work/fraktal-ab-s4b-20261025/retry_lookup_01')"),
 ('compare_cold_config_pages_01.py','compare_reader_config_pages_01.py',"D = W.parent / 'retry_reader_01'"),
 ('analyze_cold_task_trace_01.py','analyze_desktop_task_trace_01.py',"D=W.parent/'desktop_scan_continue_01'")]
for output,original,needle in jobs:
    source=(OLD/original).read_text(encoding='utf-8')
    assert source.count(needle)==1
    source=source.replace(needle,f'D = Path({S.as_posix()!r})')
    if output.startswith('inspect_'):
        needle="pageKeys=list(page['page']), entries=len(page['page'].get('entries', []))"
        assert source.count(needle)==1
        source=source.replace(needle,"scalars=len(page['page']), entries=page['page']['EntryCount']")
    with (W/output).open('x',encoding='utf-8',newline='') as f:
        f.write(source)
print('Prepared four read-only post-run analyses; no controller access.')
