from pathlib import Path
W=Path(__file__).parent
original=Path('C:/work/fraktal-ab-s4b-cold-20261026/offline_01/seal_runtime_01.py')
archive=Path('C:/Users/SoftIndVM/Fraktal/Specification/AllenBradley/Evidence/AB_S4B_COLD_DESKTOP_ATTEMPT_2026-10-27/Analysis/seal_runtime_01.py')
assert original.read_bytes()==archive.read_bytes()
source=original.read_text(encoding='utf-8')
for before,after,count in (
 ('cold-start/desktop outcome','parallel-reader outcome',1),
 ('call_297cd0f6497b4493909e0f524643c7c9:0','call_18bf5754fcb54411bfc34409e002243f:0',2),
 ('AB_S4B_COLD_DESKTOP_{kind}_{stamp}','AB_S4B_PARALLEL_READER_{kind}_{stamp}',1),
 ('AB_S4B_COLD_DESKTOP_PREPARATION_2026-10-26/manifest.json','AB_S4B_PARALLEL_READER_PREPARATION_2026-10-27/manifest.json',1),
 ('5c2833f6a8b45759c5417da9a11536e9926a883412cc8c60e4ddbcb80b4acf26','7fa998b5ca54355799157a9e658bc07e3ed3e83b8b32f286fab9a73d2e815ade',1),
 ('authorize_cold_session_01.py','authorize_parallel_session_01.py',1),
 ('build_runtime_analysis_01.py','prepare_runtime_analysis_01.py',1),
 ('authorize_session_01.log','authorize_parallel_session_01.log',1),
 ('authorize_session_01_exit.json','authorize_parallel_session_01_exit.json',1),
 ('fraktal.ab.s4b-cold-desktop-runtime','fraktal.ab.s4b-parallel-reader-runtime',1)):
    assert source.count(before)==count,before
    source=source.replace(before,after)
start=source.index("report=f'''");end=source.index("\nwith REPORT.open",start)
source=source[:start]+(W/'parallel_runtime_report_01.txt').read_text(encoding='utf-8')+source[end:]
before="'peek_runtime_progress_01.py','summarize_runtime_01.py','seal_runtime_01.py',"
assert source.count(before)==1
source=source.replace(before,"'peek_runtime_progress_01.py','summarize_runtime_01.py','seal_runtime_01.py',\n    'parallel_runtime_report_01.txt','prepare_runtime_seal_01.py','parse_startup_timing_01.py',")
compile(source,str(W/'seal_runtime_01.py'),'exec')
with (W/'seal_runtime_01.py').open('x',encoding='utf-8',newline='') as f:f.write(source)
print('Prepared outcome-derived parallel-reader runtime sealer; no controller access.')
