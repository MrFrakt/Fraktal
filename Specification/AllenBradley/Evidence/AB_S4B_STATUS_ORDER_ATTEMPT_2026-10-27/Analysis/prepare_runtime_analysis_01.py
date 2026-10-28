from pathlib import Path
W=Path(__file__).parent
N=Path('C:/work/fraktal-ab-s4b-cold-20261026/offline_01')
old='C:/work/fraktal-ab-s4b-cold-20261026/session_01'
new=(W.parent/'session_01').as_posix()
for name in ('inspect_cold_runtime_01.py','replay_cold_pairs_01.py','compare_cold_config_pages_01.py',
    'analyze_cold_task_trace_01.py','peek_runtime_progress_01.py','summarize_runtime_01.py'):
    source=(N/name).read_text(encoding='utf-8')
    source=source.replace(old,new)
    if name=='summarize_runtime_01.py':
        before='call_297cd0f6497b4493909e0f524643c7c9:0'
        assert source.count(before)==1
        source=source.replace(before,'call_e167e16df752449e8bbb27e2ef44e6b7:0')
        before='Approve guarded S4b cold-start/desktop session'
        assert source.count(before)==1
        source=source.replace(before,'Approve guarded S4b Status-order retry')
    if name=='peek_runtime_progress_01.py':
        before="print(json.dumps(dict(controllerAccess=False,captureFiles=len(files),firstAndLatest=rows)))"
        assert source.count(before)==1
        source=source.replace(before,"""observer=None
if (S/'dart_qualification.json.gz').is_file():
    try:
        report=json.loads(gzip.decompress((S/'dart_qualification.json.gz').read_bytes()))
        observer=dict(passed=report['passed'],error=report['error'],samples=len(report['samples']),
            configurationPages=len(report['configurationPages']))
    except (OSError,EOFError,ValueError):observer=dict(stillWriting=True)
print(json.dumps(dict(controllerAccess=False,captureFiles=len(files),firstAndLatest=rows,observer=observer)))""")
    with (W/name).open('x',encoding='utf-8',newline='') as f:f.write(source)
print('Prepared six post-run/progress tools; no controller access.')
