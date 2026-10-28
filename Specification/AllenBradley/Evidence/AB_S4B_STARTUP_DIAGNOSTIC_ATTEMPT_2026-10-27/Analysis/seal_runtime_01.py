from pathlib import Path
W=Path(__file__).parent
original=Path('C:/work/fraktal-ab-s4b-cold-20261026/offline_01/seal_runtime_01.py')
archive=Path('C:/Users/SoftIndVM/Fraktal/Specification/AllenBradley/Evidence/AB_S4B_COLD_DESKTOP_ATTEMPT_2026-10-27/Analysis/seal_runtime_01.py')
assert original.read_bytes()==archive.read_bytes()
source=original.read_text(encoding='utf-8')
replacements={
 'call_297cd0f6497b4493909e0f524643c7c9:0':'call_7d2226c74b974b268cf6aa63ab8aaae6:0',
 "name=f'AB_S4B_COLD_DESKTOP_{kind}_{stamp}'":"name=f'AB_S4B_STARTUP_DIAGNOSTIC_{kind}_{stamp}'",
 'AB_S4B_COLD_DESKTOP_PREPARATION_2026-10-26/manifest.json':'AB_S4B_STARTUP_DIAGNOSTIC_PREPARATION_2026-10-27/manifest.json',
 '5c2833f6a8b45759c5417da9a11536e9926a883412cc8c60e4ddbcb80b4acf26':'a2e966ee642f47052c35b144f58b3bb809aa8234ddf389592cb01d7843fbfd58',
 "'authorize_cold_session_01.py'":"'authorize_startup_session_01.py'",
 "'build_runtime_analysis_01.py'":"'prepare_runtime_analysis_01.py'",
 "'seal_runtime_01.py',":"'seal_runtime_01.py','startup_runtime_report_01.txt','parse_startup_timing_01.py','prepare_runtime_seal_01.py',",
 'fraktal.ab.s4b-cold-desktop-runtime':'fraktal.ab.s4b-startup-diagnostic-runtime',
}
for before,after in replacements.items():
    expected=2 if before=='call_297cd0f6497b4493909e0f524643c7c9:0' else 1
    assert source.count(before)==expected,before
    source=source.replace(before,after)
start=source.index("report=f'''")
end=source.index("\nwith REPORT.open",start)
source=source[:start]+(W/'startup_runtime_report_01.txt').read_text(encoding='utf-8')+source[end:]
exec(compile(source,str(original),'exec'),{'__file__':__file__})
