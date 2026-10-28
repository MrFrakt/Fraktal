from pathlib import Path
W=Path(__file__).parent
original=Path('C:/work/fraktal-ab-s4b-cold-20261026/offline_01/seal_runtime_01.py')
archive=Path('C:/Users/SoftIndVM/Fraktal/Specification/AllenBradley/Evidence/AB_S4B_COLD_DESKTOP_ATTEMPT_2026-10-27/Analysis/seal_runtime_01.py')
assert original.read_bytes()==archive.read_bytes()
source=original.read_text(encoding='utf-8')
replacements={
 'call_297cd0f6497b4493909e0f524643c7c9:0':'call_e167e16df752449e8bbb27e2ef44e6b7:0',
 "name=f'AB_S4B_COLD_DESKTOP_{kind}_{stamp}'":"name=f'AB_S4B_STATUS_ORDER_{kind}_{stamp}'",
 'AB_S4B_COLD_DESKTOP_PREPARATION_2026-10-26/manifest.json':'AB_S4B_STATUS_ORDER_PREPARATION_2026-10-27/manifest.json',
 '5c2833f6a8b45759c5417da9a11536e9926a883412cc8c60e4ddbcb80b4acf26':'a136bd8ede6f87ec9f1b63eb61e7ad4ef4ccca9644fe0c9c0a59d28cb3276ee6',
 "'authorize_cold_session_01.py'":"'authorize_status_retry_01.py'",
 "'build_runtime_analysis_01.py'":"'prepare_runtime_analysis_01.py'",
 "'seal_runtime_01.py',":"'seal_runtime_01.py','status_runtime_report_01.txt',",
 'fraktal.ab.s4b-cold-desktop-runtime':'fraktal.ab.s4b-status-order-runtime',
}
for before,after in replacements.items():
    expected=2 if before=='call_297cd0f6497b4493909e0f524643c7c9:0' else 1
    assert source.count(before)==expected,before
    source=source.replace(before,after)
start=source.index("report=f'''")
end=source.index("\nwith REPORT.open",start)
source=source[:start]+(W/'status_runtime_report_01.txt').read_text(encoding='utf-8')+source[end:]
exec(compile(source,str(original),'exec'),{'__file__':__file__})
